"""Community detection and its checks (course week 4).

Pure analysis functions: they take a graph and tables and return numbers or
DataFrames. Loading lives in `enron.loaders`, figures in `enron.plots`, and
the script that runs everything is `enron.run_communities`.
"""

import itertools
from collections import Counter

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_mutual_info_score, normalized_mutual_info_score


# ---------------------------------------------------------------- helpers ---
def split_isolates(H: nx.Graph) -> tuple[nx.Graph, list]:
    """Return (graph without people who have no links, list of those people)."""
    isolates = sorted(nx.isolates(H))
    core = H.copy()
    core.remove_nodes_from(isolates)
    return core, isolates


def partition_labels(comms, nodes) -> np.ndarray:
    """List of node sets -> one label per node, in the order of `nodes`."""
    lookup = {n: i for i, c in enumerate(comms) for n in c}
    return np.array([lookup[n] for n in nodes])


def relabel_by_size(labels: np.ndarray) -> np.ndarray:
    """Renumber communities 1, 2, ... from largest to smallest."""
    rank = {c: i + 1 for i, (c, _) in enumerate(Counter(labels).most_common())}
    return np.array([rank[c] for c in labels])


def nmi(a, b) -> float:
    return normalized_mutual_info_score(a, b)


def empirical_p(null: np.ndarray, observed: float) -> float:
    """One-sided p-value: share of null values at least as large as observed."""
    return (np.sum(null >= observed) + 1) / (len(null) + 1)


# ---------------------------------------------------------------- Louvain ---
def run_louvain(H: nx.Graph, nodes, n_seeds: int, resolution: float = 1.0) -> list[dict]:
    """Louvain once per seed. Each run: seed, labels, modularity q, k communities."""
    runs = []
    for seed in range(n_seeds):
        comms = nx.community.louvain_communities(H, weight="weight", seed=seed,
                                                 resolution=resolution)
        runs.append({"seed": seed, "labels": partition_labels(comms, nodes),
                     "q": nx.community.modularity(H, comms, weight="weight"),
                     "k": len(comms)})
    return runs


def best_run(runs: list[dict]) -> dict:
    return max(runs, key=lambda r: r["q"])


def seed_stability(runs: list[dict]) -> dict:
    """How much the partition changes between seeds (NMI between every pair of runs)."""
    pairs = [nmi(a["labels"], b["labels"]) for a, b in itertools.combinations(runs, 2)]
    qs = np.array([r["q"] for r in runs])
    return {"nmi_mean": float(np.mean(pairs)), "nmi_min": float(np.min(pairs)),
            "q_min": float(qs.min()), "q_max": float(qs.max())}


# ------------------------------------------------------------ null models ---
def shuffled_graph(H: nx.Graph, seed: int) -> nx.Graph:
    """Degree-preserving edge swaps; the original weights are dealt out at random."""
    rng = np.random.default_rng(seed)
    m = H.number_of_edges()
    R = nx.Graph()
    R.add_nodes_from(H)
    R.add_edges_from(H.edges())
    nx.double_edge_swap(R, nswap=10 * m, max_tries=1000 * m, seed=int(seed))
    weights = rng.permutation([d["weight"] for _, _, d in H.edges(data=True)])
    for (u, v), w in zip(R.edges(), weights):
        R[u][v]["weight"] = int(w)
    return R


def modularity_null(H: nx.Graph, q_observed: float, n_null: int) -> dict:
    """Is Q higher than Louvain finds in shuffled graphs with the same degrees?"""
    null_q = []
    for i in range(n_null):
        R = shuffled_graph(H, seed=i)
        comms = nx.community.louvain_communities(R, weight="weight", seed=i)
        null_q.append(nx.community.modularity(R, comms, weight="weight"))
    null_q = np.array(null_q)
    return {"null_q": null_q, "mean": float(null_q.mean()), "sd": float(null_q.std()),
            "z": float((q_observed - null_q.mean()) / null_q.std()),
            "p": float(empirical_p(null_q, q_observed))}


def label_shuffle_test(comm, labels, n_perm: int, rng) -> dict:
    """NMI between communities and labels, against shuffled labels."""
    observed = nmi(comm, labels)
    null = np.array([nmi(comm, rng.permutation(labels)) for _ in range(n_perm)])
    return {"nmi": observed, "ami": adjusted_mutual_info_score(comm, labels),
            "null_mean": float(null.mean()), "null_sd": float(null.std()),
            "null_p95": float(np.percentile(null, 95)),
            "z": float((observed - null.mean()) / null.std()) if null.std() > 0 else np.nan,
            "p": float(empirical_p(null, observed))}


def compare_with_attributes(nodes, comm, people: pd.DataFrame, n_perm: int,
                            rng) -> pd.DataFrame:
    """Do communities follow department and role? People without a value are left out."""
    rows = []
    for attr, exclude in [("department", None), ("role", "Unknown")]:
        values = people.loc[nodes, attr]
        keep = (values.notna() & (values != exclude)).values
        res = label_shuffle_test(comm[keep], values[keep].astype(str).values, n_perm, rng)
        rows.append({"compared with": attr, "people": int(keep.sum()),
                     "groups": int(values[keep].nunique()), **res})
    return pd.DataFrame(rows)


# ------------------------------------------------- consensus and mixing ---
def seed_partitions(runs: list[dict], nodes, best_comm) -> pd.DataFrame:
    """All Louvain partitions in one table: index = person, one column per seed."""
    table = pd.DataFrame({f"seed_{r['seed']}": r["labels"] for r in runs}, index=nodes)
    table.insert(0, "community", best_comm)
    table.index.name = "person_id"
    return table


def consensus_matrix(partitions: pd.DataFrame) -> np.ndarray:
    """Share of runs in which each pair of people is in the same community
    (Lancichinetti & Fortunato 2012). Rows/columns follow the table's index."""
    runs = partitions.drop(columns="community").to_numpy()
    D = np.zeros((len(runs), len(runs)))
    for col in runs.T:
        D += col[:, None] == col[None, :]
    return D / runs.shape[1]


def consensus_order(D: pd.DataFrame, members: pd.DataFrame) -> list:
    """Order people by community (C1 first), and inside each community so that
    people who are usually grouped together sit next to each other
    (average-linkage clustering on 1 - consensus)."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    order = []
    for c in sorted(members["community"].unique()):
        ids = list(members.index[members["community"] == c])
        if len(ids) > 2:
            dist = 1 - D.loc[ids, ids].to_numpy()
            np.fill_diagonal(dist, 0)
            ids = [ids[i] for i in leaves_list(linkage(squareform(dist, checks=False),
                                                       method="average"))]
        order += ids
    return order


def consensus_by_community(D: pd.DataFrame, members: pd.DataFrame) -> pd.DataFrame:
    """For each community: mean share of runs in which two of its members are together."""
    rows = []
    for c in sorted(members["community"].unique()):
        ids = list(members.index[members["community"] == c])
        sub = D.loc[ids, ids].to_numpy()
        n = len(ids)
        rows.append({"community": f"C{c}", "people": n,
                     "together_share": float((sub.sum() - n) / (n * (n - 1))) if n > 1 else 1.0})
    return pd.DataFrame(rows)


def unstable_pair_share(D: np.ndarray, low: float = 0.1, high: float = 0.9) -> float:
    """Share of pairs that are together in some runs but not others."""
    upper = D[np.triu_indices_from(D, k=1)]
    return float(np.mean((upper > low) & (upper < high)))


def community_weight_totals(H: nx.Graph, comm_of: dict) -> tuple[pd.DataFrame, float]:
    """Email weight between every pair of communities (symmetric), and total weight W."""
    labels = sorted(set(comm_of.values()))
    M = pd.DataFrame(0.0, index=labels, columns=labels)
    for u, v, d in H.edges(data=True):
        a, b = comm_of[u], comm_of[v]
        M.loc[a, b] += d["weight"]
        if a != b:
            M.loc[b, a] += d["weight"]
    return M, float(sum(d["weight"] for *_, d in H.edges(data=True)))


def inside_share(H: nx.Graph, comm_of: dict) -> dict:
    """Share of email weight inside communities, and the share expected by chance
    given each community's total email (sum over c of (s_c / 2W)^2)."""
    M, W = community_weight_totals(H, comm_of)
    strength = Counter()
    for n, s in H.degree(weight="weight"):
        strength[comm_of[n]] += s
    observed = float(np.trace(M.to_numpy()) / W)
    expected = float(sum((s / (2 * W)) ** 2 for s in strength.values()))
    return {"observed": observed, "expected": expected}


def mixing_matrix(H: nx.Graph, comm_of: dict) -> pd.DataFrame:
    """Observed / expected email between communities (1 = as much as chance).

    Expected weight between c and d = s_c * s_d / (2W), as in modularity.
    Diagonal: internal weight counted from both ends (2 x inside) against s_c^2 / (2W).
    """
    M, W = community_weight_totals(H, comm_of)
    strength = Counter()
    for n, s in H.degree(weight="weight"):
        strength[comm_of[n]] += s
    s = pd.Series(strength).reindex(M.index)
    observed = M.copy()
    for c in M.index:
        observed.loc[c, c] = 2 * M.loc[c, c]
    expected = np.outer(s, s) / (2 * W)
    return observed / expected


# --------------------------------------------------------------- profiles ---
def community_members(H: nx.Graph, nodes, comm, people: pd.DataFrame) -> pd.DataFrame:
    """One row per person: name, role, department, community, strength, degree."""
    strength = dict(H.degree(weight="weight"))
    members = people.loc[nodes, ["folder", "full_name", "role", "department"]].copy()
    members["community"] = comm
    members["strength"] = [strength[n] for n in nodes]
    members["degree"] = [H.degree(n) for n in nodes]
    return members.sort_values(["community", "strength"], ascending=[True, False])


def community_profiles(H: nx.Graph, members: pd.DataFrame) -> pd.DataFrame:
    """One row per community: size, share of email kept inside, departments, roles, leaders."""
    comm_of = members["community"].to_dict()
    total = Counter()
    inside = Counter()
    for u, v, d in H.edges(data=True):
        total[comm_of[u]] += d["weight"]
        total[comm_of[v]] += d["weight"]
        if comm_of[u] == comm_of[v]:
            inside[comm_of[u]] += 2 * d["weight"]

    def top(series, n=3):
        counts = series.dropna().value_counts()
        return "; ".join(f"{k} ({v})" for k, v in counts.head(n).items())

    rows = []
    for c, grp in members.groupby("community"):
        rows.append({"community": f"C{c}", "people": len(grp),
                     "emails_inside_share": inside[c] / total[c] if total[c] else np.nan,
                     "top_departments": top(grp["department"]),
                     "top_roles": top(grp["role"]),
                     "best_connected": "; ".join(grp["full_name"].head(5))})
    return pd.DataFrame(rows)


def group_names(members: pd.DataFrame) -> dict:
    """Short name per community: its most common department."""
    names = {}
    for c, grp in members.groupby("community"):
        dept = grp["department"].dropna()
        names[c] = dept.value_counts().index[0] if len(dept) else ""
    return names


# --------------------------------------------------------- second methods ---
def compare_methods(H: nx.Graph, nodes, comm, louvain_q: float, louvain_k: int,
                    leiden_seeds: int = 10) -> pd.DataFrame:
    """Leiden and greedy modularity next to Louvain, with NMI against Louvain."""
    greedy = nx.community.greedy_modularity_communities(H, weight="weight")
    leiden_runs = []
    for seed in range(leiden_seeds):
        cs = nx.community.leiden_communities(H, weight="weight", seed=seed,
                                             metric="modularity")
        leiden_runs.append((nx.community.modularity(H, cs, weight="weight"), cs))
    leiden_q, leiden = max(leiden_runs, key=lambda t: t[0])
    return pd.DataFrame([
        {"method": "Louvain (best of seeds)", "communities": louvain_k, "Q": louvain_q,
         "NMI with Louvain": 1.0},
        {"method": f"Leiden (best of {leiden_seeds})", "communities": len(leiden),
         "Q": leiden_q, "NMI with Louvain": nmi(comm, partition_labels(leiden, nodes))},
        {"method": "Greedy modularity", "communities": len(greedy),
         "Q": nx.community.modularity(H, greedy, weight="weight"),
         "NMI with Louvain": nmi(comm, partition_labels(greedy, nodes))},
    ])


def resolution_sweep(H: nx.Graph, nodes, people: pd.DataFrame,
                     resolutions=(0.5, 0.75, 1.0, 1.5, 2.0), seeds: int = 10) -> pd.DataFrame:
    """How the number of communities and the match with department change with resolution."""
    dept = people.loc[nodes, "department"]
    has_dept = dept.notna().values
    rows = []
    for res in resolutions:
        run = best_run(run_louvain(H, nodes, seeds, resolution=res))
        comms = [set(np.array(nodes)[run["labels"] == c]) for c in set(run["labels"])]
        rows.append({"resolution": res, "communities": run["k"],
                     "Q (at resolution 1)": nx.community.modularity(H, comms, weight="weight"),
                     "NMI with department": nmi(run["labels"][has_dept],
                                                dept[has_dept].astype(str).values)})
    return pd.DataFrame(rows)


def agreement_with(comm, other: pd.Series) -> float:
    """NMI with another partition (e.g. the full-corpus communities), where it exists."""
    has = other.notna().values
    return nmi(comm[has], other[has].astype(int).values) if has.any() else np.nan


# --------------------------------------------------------------- backbone ---
def disparity_backbone(H: nx.Graph, alpha: float = 0.05, keep_strongest: bool = True,
                       reconnect: bool = True) -> nx.Graph:
    """Disparity filter (Serrano, Boguna & Vespignani 2009).

    Keeps a link when it is significant at `alpha` for at least one of its ends.
    keep_strongest: each person's strongest link is kept too, so nobody is left alone.
    reconnect: a group the filter cut off from the main network gets back its
    single strongest link to it, so the drawing does not suggest a split that
    is not in the data. Each link records why it was kept in `kept_by`
    ("filter", "strongest" or "reconnect").
    """
    strength = dict(H.degree(weight="weight"))
    B = nx.Graph()
    B.add_nodes_from(H)
    for u, v, d in H.edges(data=True):
        for node in (u, v):
            k = H.degree(node)
            if k <= 1 or (1 - d["weight"] / strength[node]) ** (k - 1) < alpha:
                B.add_edge(u, v, weight=d["weight"], kept_by="filter")
                break
    if keep_strongest:
        for node in H:
            nbrs = H[node]
            if nbrs:
                top = max(nbrs, key=lambda n: nbrs[n]["weight"])
                if not B.has_edge(node, top):
                    B.add_edge(node, top, weight=nbrs[top]["weight"], kept_by="strongest")
    if reconnect:
        while True:
            parts = sorted(nx.connected_components(B), key=len, reverse=True)
            if len(parts) == 1:
                break
            main, added = parts[0], False
            for part in parts[1:]:
                links = [(u, v, d["weight"]) for u, v, d in H.edges(part, data=True)
                         if (u in part) != (v in part) and (u in main or v in main)]
                if links:
                    u, v, w = max(links, key=lambda e: e[2])
                    B.add_edge(u, v, weight=w, kept_by="reconnect")
                    added = True
            if not added:  # pieces not linked to the main network in the data either
                break
    return B


def backbone_counts(B: nx.Graph) -> dict:
    """How many backbone links were kept for each reason."""
    return dict(Counter(d.get("kept_by", "filter") for _, _, d in B.edges(data=True)))
