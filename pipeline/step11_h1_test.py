"""
Step 11: H1, the main test. Do people whose received email comes from many communities (high P)
receive more topically varied email (high D)?

Input:  pipeline/output/bridge_measures.csv (Step 7), diversity.csv (Step 10)
Output: pipeline/output/h1_results.csv      all numbers of this step
        pipeline/output/h1_null.csv         the 5,000 shuffled correlations of the primary test
        pipeline/figures/fig2_p_vs_d.png    Figure 2 for the report: P against D, one dot per person
                                            (also as .pdf; no title, the caption is in the report)
        pipeline/figures/fig2b_h1_null.png  the 5,000 shuffled correlations with the real value (for slides)

The primary test was fixed in advance (proposal, 17 Nov, before any D existed):
  H1-1. Spearman rho between P and D_lsa for the 117 people. p-value from 5,000 shuffles of D
        WITHIN seniority groups (D is only swapped between two seniors or between two non-seniors),
        so seniority alone cannot create the correlation.
  H1-2. Two-sided: a negative result (bridges get LESS varied email) would also mean something.
Support (labelled as support, not as the main result):
  H1-3. (a) plain shuffle without seniority groups, (b) 95% bootstrap confidence interval
        (resample people), (c) regression D ~ P + log(emails received) + senior (+ own community).
  H1-4. Same test with constraint instead of P, and with D_lda instead of D_lsa.
  H1-5. Figure 2: P against D, one dot per person.

Run from the project root:
    uv run python pipeline/step11_h1_test.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
FIG = ROOT / "pipeline" / "figures"
N_PERM, N_BOOT = 5000, 2000
rng = np.random.default_rng(0)

bridge = pd.read_csv(OUT / "bridge_measures.csv", index_col="person_id")
div = pd.read_csv(OUT / "diversity.csv", index_col="person_id")
d = div[["name", "community", "senior", "received_usable", "D_lsa", "D_lda"]].join(
    bridge[["P", "constraint", "bandwidth", "outside_share"]])
senior = d["senior"].to_numpy()


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


def spearman(x, y):
    return np.corrcoef(rankdata(x), rankdata(y))[0, 1]


def permutation_test(x, y, strata=None):
    """Two-sided p-value: shuffle y (within strata if given) N_PERM times."""
    observed = spearman(x, y)
    null = np.empty(N_PERM)
    for k in range(N_PERM):
        y_shuffled = y.copy()
        groups = [np.arange(len(y))] if strata is None else [np.where(strata == s)[0] for s in np.unique(strata)]
        for g in groups:
            y_shuffled[g] = rng.permutation(y[g])
        null[k] = spearman(x, y_shuffled)
    p = (1 + np.sum(np.abs(null) >= abs(observed))) / (1 + N_PERM)
    return observed, p, null


def bootstrap_ci(x, y):
    n = len(x)
    values = [spearman(x[i], y[i]) for i in (rng.integers(0, n, n) for _ in range(N_BOOT))]
    return np.quantile(values, [0.025, 0.975])


results = []

# ---------------------------------------------------------------------------
title(f"1. PRIMARY TEST: Spearman(P, D_lsa), n = {len(d)}, D shuffled within seniority groups")
P, D = d["P"].to_numpy(), d["D_lsa"].to_numpy()
rho, p, null = permutation_test(P, D, strata=senior)
lo, hi = bootstrap_ci(P, D)
print(f"rho = {rho:+.3f}   p = {p:.4f} (two-sided, {N_PERM} shuffles within seniority groups)")
print(f"shuffled rho: mean {null.mean():+.3f}, 95% of shuffles between {np.quantile(null, 0.025):+.3f} "
      f"and {np.quantile(null, 0.975):+.3f}")
print(f"95% bootstrap confidence interval for rho: [{lo:+.3f}, {hi:+.3f}]")
results.append({"test": "PRIMARY: P vs D_lsa, shuffle within seniority", "rho": rho, "p": p, "ci_low": lo, "ci_high": hi})
pd.DataFrame({"rho_shuffled": null}).to_csv(OUT / "h1_null.csv", index=False)

# ---------------------------------------------------------------------------
title("2. Support (a): plain shuffle, and the correlation inside each seniority group")
rho_a, p_a, _ = permutation_test(P, D)
print(f"plain shuffle (no seniority groups): rho = {rho_a:+.3f}, p = {p_a:.4f}")
results.append({"test": "P vs D_lsa, plain shuffle", "rho": rho_a, "p": p_a})
for s, label in [(True, "seniors"), (False, "non-seniors")]:
    g = senior == s
    r, pv, _ = permutation_test(P[g], D[g])
    print(f"   only {label:11s} (n = {g.sum():3d}): rho = {r:+.3f}, p = {pv:.4f}")
    results.append({"test": f"P vs D_lsa, only {label}", "rho": r, "p": pv})

# ---------------------------------------------------------------------------
title("3. Support (c): regression of D_lsa on P with controls (coefficients in standard deviations)")


def regression(df, with_community):
    z = lambda v: (v - v.mean()) / v.std()                                   # noqa: E731
    X = pd.DataFrame({"P": z(df["P"]), "log_received": z(np.log(df["received_usable"])),
                      "senior": df["senior"].astype(float)})
    if with_community:
        X = X.join(pd.get_dummies(df["community"], prefix="C", drop_first=True).astype(float))
    X.insert(0, "const", 1.0)
    y = z(df["D_lsa"]).to_numpy()
    beta = np.linalg.lstsq(X.to_numpy(), y, rcond=None)[0]
    boot = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(df), len(df))
        boot.append(np.linalg.lstsq(X.to_numpy()[i], y[i], rcond=None)[0][1])
    r2 = 1 - np.sum((y - X.to_numpy() @ beta) ** 2) / np.sum((y - y.mean()) ** 2)
    return dict(zip(X.columns, beta)), np.quantile(boot, [0.025, 0.975]), r2


for with_comm in (False, True):
    coef, ci, r2 = regression(d, with_comm)
    label = "D ~ P + log(received) + senior" + (" + own community" if with_comm else "")
    print(f"{label}")
    print(f"   P: {coef['P']:+.3f} SD of D per SD of P, 95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]; "
          f"log(received): {coef['log_received']:+.3f}; senior: {coef['senior']:+.3f}; R² = {r2:.2f}")
    results.append({"test": f"regression: {label}", "rho": coef["P"], "ci_low": ci[0], "ci_high": ci[1]})

# ---------------------------------------------------------------------------
title("4. Alternative measures (same shuffle within seniority groups)")
for xcol, ycol in [("constraint", "D_lsa"), ("outside_share", "D_lsa"), ("P", "D_lda"), ("constraint", "D_lda")]:
    r, pv, _ = permutation_test(d[xcol].to_numpy(), d[ycol].to_numpy(), strata=senior)
    print(f"   {xcol:13s} vs {ycol}: rho = {r:+.3f}, p = {pv:.4f}")
    results.append({"test": f"{xcol} vs {ycol}, shuffle within seniority", "rho": r, "p": pv})

pd.DataFrame(results).to_csv(OUT / "h1_results.csv", index=False)

# ---------------------------------------------------------------------------
# Figure 2, as two separate files without titles (the caption is written in the report).
# Sized for one column of a two-column paper (8.7 cm = 3.4 inch wide).
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#ffffff"
COL = {True: "#2a78d6", False: "#eb6834"}
plt.rcParams.update({"font.family": "sans-serif", "font.size": 7, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})
FIG.mkdir(parents=True, exist_ok=True)

# (1) fig2_p_vs_d: P against D, one dot per person; bigger dot = more usable emails received
fig, ax = plt.subplots(figsize=(3.4, 2.7))
for s, label in [(False, "not senior"), (True, "senior (VP and above)")]:
    g = d[d["senior"] == s]
    ax.scatter(g["P"], g["D_lsa"], s=4 + 2.2 * np.sqrt(g["received_usable"]), color=COL[s],
               edgecolor=SURFACE, linewidth=0.6, alpha=0.9, label=label, zorder=3)
show = set(d["P"].nlargest(3).index) | set(d["D_lsa"].nsmallest(2).index) | set(d["D_lsa"].nlargest(2).index)
for i in show:
    ax.annotate(d.loc[i, "name"].split("-")[0].capitalize(), (d.loc[i, "P"], d.loc[i, "D_lsa"]),
                xytext=(3, 2), textcoords="offset points", fontsize=6, color=INK2)
ax.set_xlabel("Bridging P (participation coefficient)")
ax.set_ylabel("Information diversity D")
ax.set_xlim(-0.04, 0.86)
ax.grid(color=GRID, lw=0.5)
ax.set_axisbelow(True)
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
legend = ax.legend(frameon=False, fontsize=6.5, labelcolor=INK2, loc="lower right", bbox_to_anchor=(1.0, 0.15),
                   handletextpad=0.2)
for handle in legend.legend_handles:
    handle.set_sizes([18])  # type: ignore
fig.tight_layout(pad=0.3)
fig.savefig(FIG / "fig2_p_vs_d.png", dpi=300)
fig.savefig(FIG / "fig2_p_vs_d.pdf")

# (2) fig2b_h1_null: the 5,000 shuffled correlations of the primary test, and the real value
fig, ax = plt.subplots(figsize=(3.4, 2.0))
ax.hist(null, bins=40, color="#9ec5f4", edgecolor=SURFACE, linewidth=0.4)
ax.axvline(rho, color=INK, lw=1.2)
ax.set_xlim(-0.35, 0.5)
ax.text(rho - 0.01, ax.get_ylim()[1] * 0.95, f"real data\nρ = {rho:.2f}", color=INK, fontsize=6.5,
        va="top", ha="right")
ax.set_xlabel(f"Spearman ρ with D shuffled within seniority groups ({N_PERM:,} shuffles)")
ax.set_yticks([])
for side in ["top", "right", "left"]:
    ax.spines[side].set_visible(False)
fig.tight_layout(pad=0.3)
fig.savefig(FIG / "fig2b_h1_null.png", dpi=300)
print(f"\nsaved h1_results.csv, h1_null.csv to {OUT} and fig2_p_vs_d.png/.pdf, fig2b_h1_null.png to {FIG}")
