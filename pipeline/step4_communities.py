"""
Step 4: find communities with Louvain and check that they are real and stable.

Input:  pipeline/output/edges_undirected.csv (Step 3)
        the two databases (only for names and departments)
Output: pipeline/output/partitions_louvain.csv  all 50 Louvain runs (one column per seed)
        pipeline/output/communities.csv         best run, stability and department per person

Only the network is used here: people, links and the number of emails on each link.
No email text, and nothing from later steps.

Decisions:
  L1. Undirected weighted network: weight of A-B = emails A->B + emails B->A. A community is a
      group that works together, whichever way the email goes.
  L2. Louvain (NetworkX), weighted modularity, resolution 1 (the standard value, not tuned).
  L3. 50 runs with different seeds. The seed only changes the order in which Louvain visits people,
      but that can change the result. All 50 runs are kept (Step 7 averages P over them);
      the run with the highest Q is used to describe and name the communities.
  L4. "Compared to what?": Q of the real network against Q of 100 randomised networks of each kind:
        R1 rewired:  keeps every person's number of contacts and every link's email count,
                     but rewires who is linked to whom  -> is there group structure at all?
        R2 shuffled: keeps exactly who is linked to whom, shuffles the email counts between links
                     -> do the heavy links sit inside groups?
  L5. Stability: NMI between every pair of the 50 runs, and how often each person stays with
      their community.
  L6. Departments (person_info, as given; Step 5 corrects two people) are used only AFTER Louvain,
      to see what the communities are. NMI against shuffled department labels.

Run from the project root:
    uv run python pipeline/step4_communities.py
"""
import sqlite3
from itertools import combinations
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import normalized_mutual_info_score as nmi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
N_SEEDS = 50   # Louvain runs on the real network
N_NULL = 100   # randomised networks of each kind

# ---------------------------------------------------------------------------
# load the network and the people
edges = pd.read_csv(OUT / "edges_undirected.csv")
U = nx.Graph()
for a, b, w in zip(edges["a"], edges["b"], edges["emails"]):
    U.add_edge(a, b, weight=int(w))
nodes = sorted(U.nodes())
n = len(nodes)
m = U.number_of_edges()
W = U.size(weight="weight")

con = sqlite3.connect(ROOT / "data" / "enron_main_characters.sqlite")
con.execute(f"ATTACH DATABASE '{ROOT / 'data' / 'enron_external.sqlite'}' AS ext")
people = pd.read_sql("""SELECT p.person_id, p.name, i.jse_department AS department
                        FROM people p LEFT JOIN ext.person_info i USING (person_id)""",
                     con).set_index("person_id")
con.close()
name = people["name"]


def title(text):
    print("\n" + "=" * 75)
    print(text)
    print("=" * 75)


def louvain(G, seed, weight="weight"):
    """One Louvain run -> {person: community}, communities numbered 1, 2, ... from largest."""
    comms = nx.community.louvain_communities(G, weight=weight, resolution=1.0, seed=seed)
    comms = sorted(comms, key=len, reverse=True)
    return {person: c + 1 for c, members in enumerate(comms) for person in members}


def modularity(G, labels, weight="weight"):
    groups = {}
    for person, c in labels.items():
        groups.setdefault(c, set()).add(person)
    return nx.community.modularity(G, groups.values(), weight=weight)


def as_array(labels):
    """Labels in the fixed order of `nodes`, so runs can be compared with NMI."""
    return np.array([labels[p] for p in nodes])


def empirical_p(null, observed):
    """p = (1 + number of null values >= observed) / (1 + number of nulls)  (Week 2)."""
    return (1 + np.sum(np.array(null) >= observed)) / (1 + len(null))


# ---------------------------------------------------------------------------
title("0. Is the network the kind of network Louvain is made for?")
checks = [
    ("undirected (the course defines modularity for undirected networks)", not U.is_directed()),
    ("no self-loops (removed in Step 2)", nx.number_of_selfloops(U) == 0),
    ("one connected piece, nobody isolated", nx.is_connected(U)),
    ("weights are positive whole numbers (emails)", all(d["weight"] >= 1 for _, _, d in U.edges(data=True))),
]
for text, ok in checks:
    print(f"  [{'OK' if ok else 'NO'}] {text}")
print(f"\npeople {n}, links m = {m}, total weight W = {W} emails")

# ---------------------------------------------------------------------------
title(f"1. Louvain, weighted, resolution 1, {N_SEEDS} seeds (L2, L3)")
runs = []
for seed in range(N_SEEDS):
    labels = louvain(U, seed)
    runs.append({"seed": seed, "labels": labels, "Q": modularity(U, labels), "k": max(labels.values())})
Q = np.array([r["Q"] for r in runs])
k = pd.Series([r["k"] for r in runs])
print("number of communities found, and in how many runs:", k.value_counts().sort_index().to_dict())
print(f"Q: min {Q.min():.4f}, mean {Q.mean():.4f}, max {Q.max():.4f}")
for kk in sorted(k.unique()):
    print(f"   best Q among runs with {kk} communities: {Q[k == kk].max():.4f}")
best = runs[int(Q.argmax())]
best_labels = as_array(best["labels"])
print(f"best run: seed {best['seed']}, {best['k']} communities, Q = {best['Q']:.4f}")

# what is the difference between the solutions with different numbers of communities?
if k.nunique() > 1:
    best_of = {kk: as_array(runs[int(np.where(k == kk, Q, -1).argmax())]["labels"]) for kk in k.unique()}
    small, large = sorted(best_of)[:2]
    print(f"\npeople per community: best {large}-community run (rows) vs best {small}-community run (columns)")
    print(pd.crosstab(best_of[large], best_of[small]).to_string())

# ---------------------------------------------------------------------------
title("2. Are all communities connected inside? (Louvain does not guarantee it)")
n_total = n_broken = 0
for r in runs:
    for c in set(r["labels"].values()):
        members = [p for p, x in r["labels"].items() if x == c]
        n_total += 1
        n_broken += not nx.is_connected(U.subgraph(members))
print(f"communities that fall apart into pieces: {n_broken} of {n_total} (all {N_SEEDS} runs together)")

# ---------------------------------------------------------------------------
title(f"3. Compared to what? Q of the real network against {N_NULL} randomised networks (L4)")


def rewired(seed):
    """R1: pick two links A-B and C-D at random and swap their ends to A-D and C-B.
    Each link keeps its email count, so every person keeps their number of contacts and the
    network keeps all its link weights. A swap is skipped if it would create a self-loop or a
    link that already exists. 10 swaps per link, so almost every link is moved."""
    rng = np.random.default_rng(seed)
    links = [[a, b, d["weight"]] for a, b, d in U.edges(data=True)]
    present = {frozenset((a, b)) for a, b, _ in links}
    swaps = 0
    while swaps < 10 * m:
        i, j = rng.integers(m, size=2)
        a, b, w1 = links[i]
        c, d, w2 = links[j]
        if rng.random() < 0.5:   # either end of the second link can be swapped
            c, d = d, c
        if len({a, b, c, d}) < 4 or frozenset((a, d)) in present or frozenset((c, b)) in present:
            continue
        present -= {frozenset((a, b)), frozenset((c, d))}
        present |= {frozenset((a, d)), frozenset((c, b))}
        links[i], links[j] = [a, d, w1], [c, b, w2]
        swaps += 1
    R = nx.Graph()
    R.add_weighted_edges_from(links)
    return R


link_weights = np.array([d["weight"] for _, _, d in U.edges(data=True)])


def shuffled(seed):
    """R2: the real links exactly; the email counts are shuffled between them."""
    rng = np.random.default_rng(seed)
    R = nx.Graph()
    for (a, b), w in zip(U.edges(), rng.permutation(link_weights)):
        R.add_edge(a, b, weight=int(w))
    return R


# one Louvain run per randomised network (each real run is also one Louvain run)
null_rewired, null_shuffled = [], []
for s in range(N_NULL):
    R = rewired(s)
    null_rewired.append(modularity(R, louvain(R, s)))
    R = shuffled(s)
    null_shuffled.append(modularity(R, louvain(R, s)))

# what R1 does not keep: a person's total email changes when their links are swapped
R = rewired(0)
same_degree = all(R.degree(p) == U.degree(p) for p in nodes)
strength_real = pd.Series(dict(U.degree(weight="weight")))
strength_r1 = pd.Series(dict(R.degree(weight="weight")))[strength_real.index]
print(f"R1 check: every person keeps their number of contacts: {same_degree}; "
      f"links moved: {1 - len(set(map(frozenset, U.edges())) & set(map(frozenset, R.edges()))) / m:.0%}")
print(f"          total email per person is NOT kept (Spearman with the real totals: "
      f"{strength_real.corr(strength_r1, method='spearman'):.2f})\n")

print("              real Q (50 runs)      randomised Q (100 networks)")
print("              mean    lowest        mean ± SD        highest     z       p")
for label, null in [("R1 rewired ", null_rewired), ("R2 shuffled", null_shuffled)]:
    null = np.array(null)
    z = (Q.mean() - null.mean()) / null.std()
    hits = int(np.sum(null >= Q.mean()))
    print(f"{label}   {Q.mean():.3f}   {Q.min():.3f}         {null.mean():.3f} ± {null.std():.3f}    "
          f"{null.max():.3f}     {z:5.1f}   {empirical_p(null, Q.mean()):.3f}  ({hits} of {N_NULL} reach the real mean)")

# ---------------------------------------------------------------------------
title("4. Stability: how similar are the 50 runs? (L5)")
L = np.array([as_array(r["labels"]) for r in runs])  # one row per run
pair_nmi = [nmi(L[i], L[j]) for i, j in combinations(range(N_SEEDS), 2)]
print(f"NMI between the {len(pair_nmi)} pairs of runs: mean {np.mean(pair_nmi):.3f}, "
      f"min {np.min(pair_nmi):.3f}; identical pairs: {np.mean(np.isclose(pair_nmi, 1)):.0%}")

# together[i, j] = share of runs in which person i and person j are in the same community
together = np.zeros((n, n))
for row in L:
    together += row[:, None] == row[None, :]
together /= N_SEEDS

# a person is stable if they are always together with the members of their best-run community
stability = np.ones(n)
for i in range(n):
    same = best_labels == best_labels[i]
    same[i] = False
    if same.any():
        stability[i] = together[i, same].mean()
print("\nper community (best run): size and how often its members are together across runs")
for c in range(1, best["k"] + 1):
    inside = best_labels == c
    print(f"   C{c}: {inside.sum():3d} people, together {stability[inside].mean():.2f}")
print("\nthe 8 people who move most between runs:")
for i in np.argsort(stability)[:8]:
    print(f"   {name[nodes[i]]:18s} C{best_labels[i]}  together with own community {stability[i]:.2f}")

# ---------------------------------------------------------------------------
title("5. Do communities match departments? (L6; departments are not used by Louvain)")
dept = people.loc[nodes, "department"]
has = dept.notna().to_numpy()
d = dept[has].to_numpy()
observed = nmi(best_labels[has], d)
all_runs = np.mean([nmi(row[has], d) for row in L])
rng = np.random.default_rng(0)
null = np.array([nmi(best_labels[has], rng.permutation(d)) for _ in range(1000)])
print(f"people with a department: {has.sum()} of {n}, departments: {len(set(d))}")
print(f"NMI(best run, department) = {observed:.3f}; mean over all 50 runs {all_runs:.3f}")
print(f"shuffled departments (1000 times): {null.mean():.3f} (95%: {np.quantile(null, 0.95):.3f}), "
      f"{int(np.sum(null >= observed))} of 1000 reach it, p = {empirical_p(null, observed):.3f}")

# ---------------------------------------------------------------------------
title("6. The communities of the best run, and where Q comes from")
community_of = dict(zip(nodes, best_labels))  # person -> community in the best run
strength = pd.Series(dict(U.degree(weight="weight")))
inside_w = {c: 0 for c in range(1, best["k"] + 1)}   # emails on links inside c
for a, b, dd in U.edges(data=True):
    if community_of[a] == community_of[b]:
        inside_w[community_of[a]] += dd["weight"]

print("Q = sum over communities of (share of all email inside c) - (share expected by chance)")
print("expected share = (total email of c's members / 2W)^2\n")
print("      people  own email inside  share of all  expected  contribution")
rows = []
for c in range(1, best["k"] + 1):
    members = [p for p in nodes if community_of[p] == c]
    S_c = strength[members].sum()
    share, expected = inside_w[c] / W, (S_c / (2 * W)) ** 2
    rows.append((share, expected))
    print(f"C{c}:   {len(members):5d}     {2 * inside_w[c] / S_c:6.0%}          {share:6.1%}   "
          f"{expected:6.1%}     {share - expected:.3f}")
total_inside, total_expected = map(sum, zip(*rows))
print(f"all:              {sum(inside_w.values()) / W:6.1%}            {total_inside:6.1%}   "
      f"{total_expected:6.1%}     Q = {total_inside - total_expected:.4f}")

for c in range(1, best["k"] + 1):
    members = [p for p in nodes if community_of[p] == c]
    depts = people.loc[members, "department"].value_counts().head(3)
    top5 = strength[members].sort_values(ascending=False).head(5).index
    print(f"\nC{c} ({len(members)} people)")
    print("   departments:", "; ".join(f"{dep} ({cnt})" for dep, cnt in depts.items()))
    print("   most emails:", ", ".join(name[p] for p in top5))

# ---------------------------------------------------------------------------
# saved for a later check only (Step 12b, H2a): the same Louvain without weights
unweighted_runs = [louvain(U, s, weight=None) for s in range(N_SEEDS)]
Q_unweighted = [modularity(U, lab, weight=None) for lab in unweighted_runs]
best_u = as_array(unweighted_runs[int(np.argmax(Q_unweighted))])
print(f"\n(saved for Step 12b: unweighted Louvain, best of {N_SEEDS} runs, {best_u.max()} communities)")

pd.DataFrame(L.T, index=pd.Index(nodes, name="person_id"),
             columns=[f"seed_{r['seed']}" for r in runs]).to_csv(OUT / "partitions_louvain.csv")
pd.DataFrame({"name": name[nodes].to_numpy(), "department": dept.to_numpy(),
              "community": best_labels, "stability": stability.round(3),
              "community_unweighted": best_u},
             index=pd.Index(nodes, name="person_id")).to_csv(OUT / "communities.csv")
print(f"saved partitions_louvain.csv and communities.csv to {OUT}")
