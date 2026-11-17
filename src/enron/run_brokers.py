"""Analysis 2a: who bridges communities, and are they the people named in Congress?

Uses the 50 Louvain runs saved by `enron.run_communities`
(results/communities/seed_partitions.csv), so run that first.

Steps:
  1. participation coefficient P and within-community degree z for every person
     in every run (weighted by emails and unweighted), averaged over runs
  2. weighted betweenness (distance = 1/emails), Burt's constraint, effective size
  3. Congress mentions per person; Spearman correlations with permutation p-values,
     Mann-Whitney named vs not named, a seniority-controlled permutation test,
     and named people per community (hypergeometric, Benjamini-Hochberg)
  4. figures: where the named people's email goes (stacked bars, main text) and
     the z-P scatter for everyone (supplement)

Usage (from the project root):
    uv run python -m enron.run_brokers
    uv run python -m enron.run_brokers --perms 10000

Outputs: results/brokers/ (summary.md + CSV tables) and figures/ (.png):
fig_named_reach (main text), fig_si_brokers_zp (supplement)
"""

import argparse

import numpy as np
import pandas as pd

from enron import brokers as br
from enron import communities as cm
from enron.loaders import load_congress_mentions, load_email_graph, load_people, to_undirected
from enron.paths import FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import plot_named_reach, plot_zp_scatter
from enron.reporting import fmt_p, md_table

OUT = RESULTS_DIR / "brokers"
PARTITIONS = RESULTS_DIR / "communities" / "seed_partitions.csv"
MEASURES = ["P_main", "z_main", "betweenness", "constraint", "effective_size", "strength"]
MIN_DEGREE = 5


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perms", type=int, default=10000, help="permutations (default 10000)")
    return ap.parse_args()


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    if not PARTITIONS.exists():
        raise SystemExit("Run `uv run python -m enron.run_communities` first "
                         f"(needs {PARTITIONS.relative_to(PROJECT_ROOT)})")

    # data: same graph and the same Louvain runs as Analysis 2
    people = load_people()
    H, _ = cm.split_isolates(to_undirected(load_email_graph()))
    partitions = pd.read_csv(PARTITIONS, index_col="person_id")
    partitions = partitions.loc[sorted(H.nodes())]
    mentions = load_congress_mentions()

    # 1-2. roles (averaged over runs, and in the main partition) and broker measures
    roles = br.roles_over_seeds(H, partitions)
    measures = br.broker_measures(H)
    main_comm = partitions["community"].to_dict()
    table = (people.loc[roles.index, ["full_name", "role", "department"]]
             .join(partitions["community"]).join(roles).join(measures))
    table["P_main"] = pd.Series(br.participation_coefficient(H, main_comm))
    table["z_main"] = pd.Series(br.within_community_z(H, main_comm))
    shares = br.community_shares(H, main_comm)
    shares.to_csv(OUT / "community_shares.csv")
    table["mentions"] = mentions.reindex(table.index).fillna(0).astype(int)
    table["named"] = table["mentions"] > 0
    table["low_degree"] = table["degree"] < MIN_DEGREE
    table = table.sort_values("P_main", ascending=False)
    table.to_csv(OUT / "brokers.csv")
    print(f"{len(table)} people; {int(table['named'].sum())} named in Congress; "
          f"{int(table['low_degree'].sum())} with fewer than {MIN_DEGREE} links")

    # correlation between the measures themselves
    corr = table[MEASURES].corr(method="spearman").round(2)

    # top bridges (people with enough links for P to mean something)
    top = table[~table["low_degree"]].head(10)[
        ["full_name", "community", "role", "department", "P_main", "P_w_mean", "P_w_sd",
         "z_main", "betweenness", "constraint", "mentions"]]

    # 3. visibility tests
    vis_corr = br.visibility_correlations(table, MEASURES, args.perms, rng)
    vis_corr["p"] = [fmt_p(p, args.perms) for p in vis_corr["p"]]
    mw = pd.DataFrame([br.named_vs_not(table, m) for m in ["P_main", "z_main",
                                                           "betweenness", "strength"]])
    strat = pd.DataFrame([br.stratified_permutation(table, m, args.perms, rng)
                          for m in ["P_main", "z_main", "betweenness", "strength"]])
    strat["p_greater"] = [fmt_p(p, args.perms) for p in strat["p_greater"]]
    by_comm = br.visibility_by_community(table)
    named = table[table["named"]][["full_name", "community", "role", "mentions",
                                   "P_main", "P_w_mean", "z_main", "betweenness"]]
    named = named.sort_values("mentions", ascending=False)
    for name, df in [("visibility_correlations", vis_corr), ("named_vs_not", mw),
                     ("seniority_controlled", strat), ("visibility_by_community", by_comm),
                     ("measure_correlations", corr.reset_index())]:
        df.to_csv(OUT / f"{name}.csv", index=False)
    print(vis_corr.to_string(index=False))

    # 4. figures: where the named people and the strongest unnamed bridges send email
    others = table[~table["named"]]
    named_ids = list(table[table["named"]].sort_values("P_main", ascending=False).index)
    hidden = list(others[~others["low_degree"]].sort_values("P_main", ascending=False).index[:3])
    rows = named_ids + hidden
    labels = {i: str(table.at[i, "full_name"]) for i in rows}
    own_shares = pd.Series({i: shares.at[i, main_comm[i]] for i in others.index})
    plot_named_reach(shares.loc[rows].rename(index=labels),
                     own={labels[i]: main_comm[i] for i in rows},
                     P={labels[i]: table.at[i, "P_main"] for i in rows},
                     groups=[("Named in Congress", len(named_ids)),
                             ("Strongest bridges, never named", len(hidden))],
                     reference={"label": f"Median of {len(others)} others",
                                "own_share": float(own_shares.median()),
                                "P": float(others["P_main"].median())},
                     path_stem=FIGURES_DIR / "fig_named_reach")
    plot_table = table.rename(columns={"P_w_mean": "P", "P_w_sd": "P_sd",
                                       "z_w_mean": "z", "z_w_sd": "z_sd"})
    plot_zp_scatter(plot_table, FIGURES_DIR / "fig_si_brokers_zp")

    # summary
    unweighted_agree = table[["P_w_mean", "P_u_mean"]].corr(method="spearman").iat[0, 1]
    text = f"""# Analysis 2a: who bridges communities?

{len(table)} people with links; P and z averaged over the {partitions.shape[1] - 1} Louvain runs
(`P_w_mean`) and from the main partition (`P_main`). The two can differ for
people in unstable communities (C7, parts of C1), where other runs split the
community differently; report `P_main` in the text. Runs saved by run_communities.
P = 1 - sum over communities of (share of a person's
email to that community)^2; 0 = all email inside one community, at most 0.875
with 8 communities. z = email inside one's own community, in SDs above the
community average. Weighted = email counts; unweighted = links only (Spearman
agreement between weighted and unweighted P: {unweighted_agree:.2f}).
People with fewer than {MIN_DEGREE} links are flagged (`low_degree`) and left out of
the top list. Betweenness uses distance = 1 / emails.

## Top 10 bridges (highest P, at least {MIN_DEGREE} links)

{md_table(top.reset_index(drop=True), digits=3)}

## How the measures relate (Spearman)

{md_table(corr.reset_index().rename(columns={"index": "measure"}), digits=2)}

## Are the people named in Congress the bridges?

People named in Congress (mentions hand-checked as wrong left out):

{md_table(named.reset_index(drop=True), digits=3)}

Spearman correlation between mention count and each measure
({args.perms} permutations, two-sided):

{md_table(vis_corr, digits=3)}

Named vs never named (Mann-Whitney):

{md_table(mw, digits=3)}

Seniority controlled: mean of each measure among named people, with the
'named' label shuffled only within role groups (executives and VPs / traders /
lawyers / others):

{md_table(strat, digits=3)}

Named people per community vs chance (hypergeometric, Benjamini-Hochberg):

{md_table(by_comm, digits=3)}

Few people are named, so treat these tests as descriptive.

## Figures

- `fig_named_reach` (main text): one 100% bar per person showing where their
  email goes, coloured by community, own community first (outlined); P (main
  partition) on the right. Rows: the people named in Congress, the 3 strongest
  bridges who were never named, and a grey reference bar for the median of
  everyone else (share kept inside their own community, and median P).
- `fig_si_brokers_zp` (supplement): P (x) against within-community degree z (y)
  for everyone, averaged over runs with SD lines; colour = community, ring =
  named in Congress; the named people are labelled.
"""
    (OUT / "summary.md").write_text(text, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_named_reach, fig_si_brokers_zp")


if __name__ == "__main__":
    main()
