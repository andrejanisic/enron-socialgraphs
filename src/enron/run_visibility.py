"""Analysis 3: are the central people in the email network the people named in Congress?

Steps:
  1. directed and undirected email graphs (self-emails and people without
     links removed) and Congress mentions per person
  2. five centrality measures: PageRank, emails received, emails sent,
     betweenness (distance = 1 / emails), eigenvector
  3. RQ1: for each measure, AUC (named vs not named), Spearman correlation with
     mentions, and named people among the 20 most central
  4. RQ2: betweenness against degree-preserving shuffled graphs (z-score);
     broker = z >= 2 and at least 5 links
  5. roles: share of each role named; Fisher test for executives
  6. groups (public faces, hidden core, public only, others) and agreement with
     the earlier full-corpus network

Usage (from the project root, after `uv run python -m enron.run_communities`):
    uv run python -m enron.run_visibility
    uv run python -m enron.run_visibility --nulls 100 --perms 5000

Outputs: results/visibility/ (summary.md + CSV tables) and figures/ (.png):
main text: fig_visibility, fig_brokers; supplement: fig_si_named_ranks, fig_si_agreement
"""

import argparse

import numpy as np
import pandas as pd

from enron import communities as cm
from enron import visibility as vis
from enron.loaders import (load_congress_mentions, load_email_graph, load_full_corpus_metrics,
                           load_people, to_directed, to_undirected)
from enron.paths import FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import plot_brokers, plot_named_ranks, plot_rank_agreement, plot_visibility
from enron.reporting import fmt_p, md_table

OUT = RESULTS_DIR / "visibility"
MEMBERS = RESULTS_DIR / "communities" / "members.csv"
ROLES = ["Executive", "Legal", "VP / Director", "Gov. & regulatory", "Trading",
         "Manager / staff", "Unknown"]
Z_MIN, MIN_DEGREE, CENTRAL_SHARE, TOP_N = 2.0, 5, 0.2, 20


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nulls", type=int, default=100,
                    help="shuffled graphs for broker z-scores (default 100)")
    ap.add_argument("--perms", type=int, default=5000,
                    help="label shuffles for AUC (default 5000; Spearman uses perms / 2)")
    return ap.parse_args()


def build_table(H, D, people, mentions, members, n_null) -> pd.DataFrame:
    """One row per person: centrality, broker z-score, mentions, role, community, group."""
    table = vis.centrality_measures(D, H)
    table = table.join(vis.betweenness_zscores(H, n_null).drop(columns="betweenness"))
    table = table.join(people[["full_name", "role", "department"]])
    if members is not None:
        table = table.join(members["community"])
    table["mentions"] = mentions.reindex(table.index).fillna(0).astype(int)
    table["named"] = table["mentions"] > 0
    table["pagerank_pct"] = vis.percentile(table["PageRank"])
    table["broker"] = vis.find_brokers(table, Z_MIN, MIN_DEGREE)
    table["group"] = vis.visibility_groups(table, CENTRAL_SHARE)
    return table


def write_summary(path, *, table, tests, brokers, roles, executives, groups, agreement, args):
    named = table[table["named"]].sort_values("PageRank", ascending=False)
    named_view = named[["full_name", "role", "mentions", "pagerank_pct", "broker_z"]].rename(
        columns={"pagerank_pct": "PageRank percentile"})
    brokers_view = brokers[["full_name", "role", "community", "broker_z", "degree", "named"]]
    text = f"""# Analysis 3: hidden vs public people

{len(table)} people with links; {int(table['named'].sum())} named in Congress (mentions
hand-checked as wrong left out).

## RQ1: does centrality predict who was named?

AUC = chance that a named person is more central than an unnamed one (0.5 = no
difference; p one-sided, {args.perms} label shuffles). rho = Spearman correlation
with the number of mentions ({args.perms // 2} shuffles, two-sided). Top {TOP_N} = named
people among the {TOP_N} most central, against chance (hypergeometric).

{md_table(tests, digits=3)}

Where the named people rank (percentile 100 = most central; broker_z = betweenness
against shuffled graphs):

{md_table(named_view.reset_index(drop=True), digits=2)}

## Roles

Share of each role named in Congress:

{md_table(roles.reset_index().rename(columns={"index": "role"}), digits=2)}

Executives: {executives['named_executives']} of {executives['named']} named people vs
{executives['other_executives']} of {executives['others']} others (Fisher exact p
{fmt_p(executives['p'], 10**6)}, odds ratio {executives['odds_ratio']:.1f}).

## RQ2: brokers

Broker = betweenness z-score >= {Z_MIN} against {args.nulls} degree-preserving shuffled
graphs, and at least {MIN_DEGREE} links. {len(brokers)} brokers; {int((~brokers['named']).sum())} never
named in Congress.

{md_table(brokers_view.reset_index(drop=True), digits=2)}

## Groups (central = top {CENTRAL_SHARE:.0%} by PageRank)

{md_table(groups, digits=0)}

## Agreement with the full-corpus network

PageRank on this graph vs the full-corpus network, {agreement['people']} people in
both: Spearman rho = {agreement['rho']:.2f}.

## Figures

- `fig_visibility` (main): a, share of each role named in Congress (counts at the
  bar ends); b, each named person's PageRank percentile, against the median
  (line) and middle 50% (band) of everyone else.
- `fig_brokers` (main): the brokers by betweenness z-score; named people in black;
  dashed line = z = {Z_MIN}.
- `fig_si_named_ranks` (supplement): rank of each named person on all five
  measures (1 = most central; darker = more central), with AUC and p.
- `fig_si_agreement` (supplement): PageRank rank on this graph against the
  full-corpus network; named people in black.
"""
    path.write_text(text, encoding="utf-8")


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)

    # 1. data
    people = load_people()
    G = load_email_graph()
    H, _ = cm.split_isolates(to_undirected(G))
    D = to_directed(G, nodes=H.nodes())
    mentions = load_congress_mentions()
    members = pd.read_csv(MEMBERS, index_col=0) if MEMBERS.exists() else None
    if members is None:
        print("Note: run enron.run_communities first to add communities to the tables.")

    # 2 + 4. centrality, broker z-scores, groups
    table = build_table(H, D, people, mentions, members, args.nulls)
    print(f"{len(table)} people; {int(table['named'].sum())} named in Congress")

    # 3. RQ1 tests
    tests = vis.visibility_tests(table, args.perms, args.perms // 2, rng, TOP_N)
    tests["p_text"] = [fmt_p(p, args.perms) for p in tests["p_AUC"]]
    print(tests[["measure", "AUC", "p_AUC", "rho", "p_rho"]].round(3).to_string(index=False))

    # 4. brokers
    brokers = table[table["broker"]].sort_values("broker_z", ascending=False)
    print(f"{len(brokers)} brokers; {int((~brokers['named']).sum())} never named")

    # 5-6. roles, groups, agreement
    roles = vis.role_table(table, ROLES)
    executives = vis.executive_test(table)
    groups = pd.crosstab(table["group"], table["role"]).reindex(
        index=["Public faces", "Hidden core", "Public only", "Others"], columns=ROLES,
        fill_value=0)
    full = load_full_corpus_metrics()
    agreement = vis.rank_agreement(table["PageRank"], full["pagerank"])

    # figures
    named = table[table["named"]]
    others = table[~table["named"]]
    best = tests.set_index("measure").loc["PageRank"]
    plot_visibility(roles, named.set_index("full_name")["pagerank_pct"], others["pagerank_pct"],
                    f"AUC = {best['AUC']:.2f}, p = {best['p_text']}",
                    FIGURES_DIR / "fig_visibility")
    plot_brokers(brokers.set_index("full_name")[["broker_z", "named"]], Z_MIN,
                 FIGURES_DIR / "fig_brokers")
    ranks = vis.named_ranks(table)
    ranks.index = table.loc[ranks.index, "full_name"]
    plot_named_ranks(ranks, tests, len(table), FIGURES_DIR / "fig_si_named_ranks")
    plot_rank_agreement(table["PageRank"], full["pagerank"], table["named"], table["full_name"],
                        agreement["rho"], FIGURES_DIR / "fig_si_agreement")

    # save
    table.to_csv(OUT / "centrality.csv")
    tests.drop(columns="p_text").to_csv(OUT / "visibility_tests.csv", index=False)
    brokers.to_csv(OUT / "brokers.csv")
    roles.to_csv(OUT / "roles.csv")
    pd.DataFrame([executives]).to_csv(OUT / "executive_test.csv", index=False)
    groups.to_csv(OUT / "groups.csv")
    pd.DataFrame([agreement]).to_csv(OUT / "agreement.csv", index=False)
    write_summary(OUT / "summary.md", table=table, tests=tests.drop(columns="p_text"),
                  brokers=brokers, roles=roles, executives=executives,
                  groups=groups.reset_index(), agreement=agreement, args=args)
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_visibility, fig_brokers, "
          "fig_si_named_ranks, fig_si_agreement")


if __name__ == "__main__":
    main()
