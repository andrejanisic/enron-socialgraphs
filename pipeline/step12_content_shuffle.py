"""
Step 12: is the bridge advantage (H1) more than just MIXING communities? (H2b)

The idea: keep the network exactly as it is (who emails whom, how often, from which community),
but give every email the text of a random OTHER email from the SAME sender community. Then every
person receives 'typical' emails from each community they hear from. The diversity they get in
this shuffled world, E[D], is what their community mix alone predicts.

Input:  pipeline/output/vectors_index.csv, lsa_100.npy (Step 8), emails_clean.csv, recipients_clean.csv
        (Step 2), communities.csv (Step 4), bridge_measures.csv (Step 7)
Output: pipeline/output/h2b_people.csv     per person: D, E[D], R = D - E[D]
        pipeline/output/h2b_results.csv    the numbers of this step
        pipeline/figures/fig3b_mixing.png  draft figure

Decisions:
  S1. Shuffle the LSA vectors of the usable emails WITHIN each sender community (best Louvain run),
      200 times. A broadcast email is one email, so all its recipients get the same swapped text.
      Every person keeps the same 100 draws of 20 emails in the real world and in all 200 shuffled
      worlds, so differences come only from the swapped content, not from different random draws.
  S2. Main comparison: is the real rho(P, D) higher, equal or lower than rho in the shuffled worlds?
  S3. H2b: R = D - E[D] for every person; Spearman rho(P, R), D-residual shuffled within seniority
      groups (5,000 times), two-sided.
  S4. Sanity check: shuffle ALL emails, ignoring communities. Then rho(P, D) should be about 0.
  Meaning of the outcomes (written down before running):
      real rho ~ shuffled rho, rho(P,R) ~ 0 -> bridges get variety exactly because they mix communities
      real rho < shuffled rho, rho(P,R) < 0 -> bridges get LESS than their mix predicts (bandwidth cost)
      real rho > shuffled rho, rho(P,R) > 0 -> bridges get MORE than their mix predicts

Run from the project root (about a minute):
    uv run python pipeline/step12_content_shuffle.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
FIG = ROOT / "pipeline" / "figures"
N, DRAWS, REPLICATES, GLOBAL_REPLICATES, N_PERM = 20, 100, 200, 50, 5000
rng = np.random.default_rng(0)

index = pd.read_csv(OUT / "vectors_index.csv")
lsa = np.load(OUT / "lsa_100.npy")
emails = pd.read_csv(OUT / "emails_clean.csv", usecols=["email_id", "sender_id"])
recipients = pd.read_csv(OUT / "recipients_clean.csv")
community = pd.read_csv(OUT / "communities.csv", index_col="person_id")["community"]
bridge = pd.read_csv(OUT / "bridge_measures.csv", index_col="person_id")

# every vector row: which community sent this email?
index = index.merge(emails, on="email_id", how="left")
sender_comm = index["sender_id"].map(community).to_numpy()
row_of = pd.Series(np.arange(len(index)), index=index["email_id"])

# every person in the test: the vector rows of their inbox, and fixed draws of 20 emails from it
people = bridge.index[bridge["in_test"]]
arrows = recipients[recipients["email_id"].isin(row_of.index)]
inbox = arrows.groupby("recipient_id")["email_id"].apply(lambda ids: row_of[ids].to_numpy())
draws = {}
for p in people:
    rows = inbox[p]
    pick = np.argsort(rng.random((DRAWS, len(rows))), axis=1)[:, :N]   # 100 draws of 20, no repeats in a draw
    draws[p] = rows[pick]                                              # shape (100, 20): vector rows
P = bridge.loc[people, "P"].to_numpy()
senior = bridge.loc[people, "senior"].to_numpy()


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


def spearman(x, y):
    return np.corrcoef(rankdata(x), rankdata(y))[0, 1]


def diversity(vectors):
    """D of every person with the given email vectors: mean over the fixed draws of 1 - |mean vector|."""
    return np.array([np.mean(1 - np.linalg.norm(vectors[draws[p]].mean(axis=1), axis=1)) for p in people])


def shuffle_within(groups):
    """New row order: every row gets the vector of a random row from the same group."""
    order = np.arange(len(lsa))
    for g in np.unique(groups):
        rows = np.where(groups == g)[0]
        order[rows] = rng.permutation(rows)
    return order


# ---------------------------------------------------------------------------
title("1. The real world")
D_real = diversity(lsa)
rho_real = spearman(P, D_real)
step10 = pd.read_csv(OUT / "diversity.csv", index_col="person_id").loc[people, "D_lsa"].to_numpy()
print(f"rho(P, D) = {rho_real:+.3f}  (D from 100 fixed draws; agrees with Step 10's D: "
      f"rho = {spearman(D_real, step10):.3f})")

title(f"2. {REPLICATES} shuffled worlds: texts swapped WITHIN each sender community (S1, S2)")
D_shuffled = np.array([diversity(lsa[shuffle_within(sender_comm)]) for _ in range(REPLICATES)])
rho_shuffled = np.array([spearman(P, d) for d in D_shuffled])
expected = D_shuffled.mean(axis=0)
low, high = np.mean(rho_shuffled <= rho_real), np.mean(rho_shuffled >= rho_real)
p_two = min(1.0, 2 * (1 + min(np.sum(rho_shuffled <= rho_real), np.sum(rho_shuffled >= rho_real))) / (1 + REPLICATES))
print(f"rho(P, D) in shuffled worlds: mean {rho_shuffled.mean():+.3f}, 95% between "
      f"{np.quantile(rho_shuffled, 0.025):+.3f} and {np.quantile(rho_shuffled, 0.975):+.3f}")
print(f"real rho {rho_real:+.3f}: {low:.0%} of shuffled worlds are lower, {high:.0%} are higher "
      f"(two-sided p = {p_two:.3f})")
print(f"rho(P, E[D]) = {spearman(P, expected):+.3f}  (how strongly mixing ALONE ties P to D)")
print(f"diversity level: real D median {np.median(D_real):.3f}, E[D] median {np.median(expected):.3f}")

title("3. H2b: what people get beyond their community mix, R = D - E[D] (S3)")
R = D_real - expected
null = np.empty(N_PERM)
groups = [np.where(senior == s)[0] for s in np.unique(senior)]
for k in range(N_PERM):
    shuffled = R.copy()
    for g in groups:
        shuffled[g] = rng.permutation(R[g])
    null[k] = spearman(P, shuffled)
rho_R = spearman(P, R)
p_R = (1 + np.sum(np.abs(null) >= abs(rho_R))) / (1 + N_PERM)
print(f"rho(P, R) = {rho_R:+.3f}, p = {p_R:.4f} (two-sided, R shuffled within seniority groups)")
print(f"R: median {np.median(R):+.4f}; share of people with R < 0 (less than their mix predicts): {np.mean(R < 0):.0%}")
t = pd.DataFrame({"name": bridge.loc[people, "name"].to_numpy(), "community": bridge.loc[people, "community"].to_numpy(),
                  "P": P, "D": D_real, "E_D": expected, "R": R}, index=people)
print("\nthe 8 strongest bridges (by P):")
print(t.sort_values("P", ascending=False).head(8).round(3).to_string())
print("\nmedian R per community:")
print(t.groupby("community")["R"].median().round(4).to_dict())

title("3b. Why is the real rho LOWER than in the shuffled worlds? (check ADDED after seeing the result)")
# Almost everybody's real inbox is narrower than a random mix (R < 0). If that narrowing differs between
# people but has nothing to do with P, it only adds noise, and noise always weakens a correlation.
# Model: mixing + narrowing unrelated to P = E[D] + R shuffled across people.
mix_plus_noise = np.array([spearman(P, expected + rng.permutation(R)) for _ in range(N_PERM)])
print(f"rho(P, E[D] + R shuffled across people): mean {mix_plus_noise.mean():+.3f}, 95% between "
      f"{np.quantile(mix_plus_noise, 0.025):+.3f} and {np.quantile(mix_plus_noise, 0.975):+.3f}; real {rho_real:+.3f}")
print(f"spread between people: SD of E[D] {expected.std():.4f}, SD of R {R.std():.4f}")

title(f"4. Sanity check: {GLOBAL_REPLICATES} worlds with texts swapped among ALL emails (S4)")
everyone = np.zeros(len(lsa), dtype=int)
rho_global = np.array([spearman(P, diversity(lsa[shuffle_within(everyone)])) for _ in range(GLOBAL_REPLICATES)])
print(f"rho(P, D) when texts ignore communities: mean {rho_global.mean():+.3f} "
      f"(95% between {np.quantile(rho_global, 0.025):+.3f} and {np.quantile(rho_global, 0.975):+.3f}); should be about 0")

# ---------------------------------------------------------------------------
t.to_csv(OUT / "h2b_people.csv")
pd.DataFrame([
    {"quantity": "rho(P,D) real", "value": rho_real},
    {"quantity": "rho(P,D) within-community shuffle, mean", "value": rho_shuffled.mean()},
    {"quantity": "rho(P,D) within-community shuffle, 2.5%", "value": np.quantile(rho_shuffled, 0.025)},
    {"quantity": "rho(P,D) within-community shuffle, 97.5%", "value": np.quantile(rho_shuffled, 0.975)},
    {"quantity": "two-sided p, real vs within-community shuffle", "value": p_two},
    {"quantity": "rho(P,E[D])", "value": spearman(P, expected)},
    {"quantity": "rho(P,R)", "value": rho_R},
    {"quantity": "p for rho(P,R), within seniority", "value": p_R},
    {"quantity": "rho(P,D) global shuffle, mean", "value": rho_global.mean()},
    {"quantity": "rho(P, E[D] + R shuffled), mean (added check)", "value": mix_plus_noise.mean()},
    {"quantity": "rho(P, E[D] + R shuffled), 2.5% (added check)", "value": np.quantile(mix_plus_noise, 0.025)},
    {"quantity": "rho(P, E[D] + R shuffled), 97.5% (added check)", "value": np.quantile(mix_plus_noise, 0.975)},
]).to_csv(OUT / "h2b_results.csv", index=False)

# draft figure: (a) rho in the real world vs the two kinds of shuffled worlds, (b) R against P
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
bins = np.linspace(min(rho_global.min(), rho_shuffled.min(), rho_real) - 0.05,
                   max(rho_shuffled.max(), rho_real) + 0.05, 45)
ax.hist(rho_global, bins=bins, color="#cde2fb", edgecolor=SURFACE, label="texts swapped among ALL emails")
ax.hist(rho_shuffled, bins=bins, color="#3987e5", edgecolor=SURFACE, label="texts swapped within sender community")
ax.hist(mix_plus_noise, bins=bins, histtype="step", color=INK, lw=1.2, density=False,
        weights=np.full(len(mix_plus_noise), len(rho_shuffled) / len(mix_plus_noise)),
        label="mixing + narrowing unrelated to P")
ax.axvline(rho_real, color=INK, lw=1.5)
ax.text(rho_real, ax.get_ylim()[1] * 0.97, " real", color=INK, va="top")
ax.set_xlabel("Spearman ρ between P and D")
ax.set_yticks([])
ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper left")
ax.set_title("(a) How much of ρ(P, D) does mixing communities explain?", loc="left", color=INK, fontsize=9.5)
ax2.axhline(0, color="#c3c2b7", lw=1)
ax2.scatter(P, R, s=22, color="#2a78d6", edgecolor=SURFACE, linewidth=1, zorder=3)
ax2.set_xlabel("P: how evenly received email comes from different communities")
ax2.set_ylabel("R = D − E[D]")
ax2.set_title(f"(b) Diversity beyond the community mix (ρ = {rho_R:+.2f}, p = {p_R:.3f})", loc="left",
              color=INK, fontsize=9.5)
ax2.grid(color=GRID, lw=0.6)
for a in (ax, ax2):
    for side in ["top", "right"]:
        a.spines[side].set_visible(False)
ax.spines["left"].set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig3b_mixing.png", dpi=200)
print(f"\nsaved h2b_people.csv, h2b_results.csv to {OUT} and fig3b_mixing.png to {FIG}")
