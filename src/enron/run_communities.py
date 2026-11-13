"""Analysis 2: email communities vs the org chart.

Steps (course week 4):
  1. undirected email graph, weight = emails in both directions; self-emails
     dropped; people with no links set aside
  2. Louvain with many seeds: modularity Q and stability (NMI between runs)
  3. Q against degree-preserving shuffled graphs
  4. NMI / AMI between communities and department, and role, against label shuffles
  5. a profile of each community
  6. second methods: Leiden and greedy modularity
  7. agreement with the earlier full-corpus communities
  + resolution sweep, and the network figure
  + Analysis 2c: emails between communities, community x department / role
    tables, consensus (how often pairs share a community across runs), and the
    community mixing matrix

Usage (from the project root):
    uv run python -m enron.run_communities
    uv run python -m enron.run_communities --seeds 50 --nulls 100 --perms 1000

Outputs: results/communities/ (summary.md + CSV tables, including
seed_partitions.csv used by run_brokers) and figures/ (.png):
main text: fig_communities, fig_email_matrix, fig_community_heatmap;
supplement: fig_si_community_mixing
"""

import argparse

import numpy as np
import pandas as pd

from enron import communities as cm
from enron.loaders import load_email_graph, load_people, to_undirected
from enron.paths import FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import (plot_community_heatmap, plot_community_network,
                         plot_email_between, plot_mixing_matrix)
from enron.reporting import fmt_p, md_table

OUT = RESULTS_DIR / "communities"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=50, help="Louvain runs (default 50)")
    ap.add_argument("--nulls", type=int, default=100, help="shuffled graphs for Q (default 100)")
    ap.add_argument("--perms", type=int, default=1000, help="label shuffles for NMI (default 1000)")
    return ap.parse_args()


def write_summary(path, *, H, isolates, people, args, best, stability, null, tests,
                  profiles, methods, sweep, earlier_nmi, backbone, matrix_stats, mixing):
    isolate_names = ", ".join(str(people.at[n, "full_name"]) for n in isolates) or "none"
    stats = pd.DataFrame([
        ("Communities (best run)", best["k"]),
        ("Modularity Q (best run)", f"{best['q']:.3f}"),
        ("Q across seeds, min to max", f"{stability['q_min']:.3f} to {stability['q_max']:.3f}"),
        ("NMI between seed runs, mean (min)",
         f"{stability['nmi_mean']:.3f} ({stability['nmi_min']:.3f})"),
        ("Q in shuffled graphs, mean ± sd", f"{null['mean']:.3f} ± {null['sd']:.3f}"),
        ("Q vs shuffled graphs, z (p)", f"{null['z']:.1f} ({fmt_p(null['p'], args.nulls)})"),
        ("NMI with full-corpus communities", f"{earlier_nmi:.3f}"),
        ("Backbone: links kept", f"{backbone.number_of_edges()} of {H.number_of_edges()}"),
        ("Backbone: kept by filter / strongest link / reconnect",
         " / ".join(str(cm.backbone_counts(backbone).get(k, 0))
                    for k in ("filter", "strongest", "reconnect"))),
        ("Backbone: people kept", f"{backbone.number_of_nodes()} of {H.number_of_nodes()}"),
    ], columns=["measure", "value"])
    tests = tests.assign(p=[fmt_p(p, args.perms) for p in tests["p"]])

    text = f"""# Analysis 2: communities vs the org chart

Graph: {H.number_of_nodes()} people with at least one link, {H.number_of_edges()} undirected
links (weight = emails in both directions, emails to oneself left out).
Left out for having no links to anyone else: {isolate_names}.
Louvain was run with {args.seeds} seeds; the run with the highest Q is used.
Communities are numbered by size (C1 = largest).

## Louvain and its checks

{md_table(stats)}

## Do communities follow the org chart?

NMI = 0 means no relation, 1 = communities and labels are the same grouping.
AMI corrects NMI for chance. The null is {args.perms} shuffles of the labels.
Role leaves out people labelled Unknown; department leaves out people with none.

{md_table(tests[["compared with", "people", "groups", "nmi", "ami", "null_mean", "z", "p"]])}

## Communities

{md_table(profiles)}

`emails_inside_share` = share of the community's email weight that stays inside it.

## Second methods

{md_table(methods)}

## Resolution sweep

{md_table(sweep)}

## The org-chart match (Analysis 2c)

- Email weight inside communities: {matrix_stats['inside']:.1%} (chance given each
  community's total email: {matrix_stats['expected']:.1%}).
- Pairs of people who are together in some Louvain runs but not others
  (0.1 < share < 0.9): {matrix_stats['unstable']:.1%} of all pairs.

How often members of each community end up together across the {args.seeds} runs
(1 = always):

{md_table(matrix_stats['together'])}

Observed / expected email between communities (1 = chance; diagonal = within):

{md_table(mixing.round(2).reset_index().rename(columns={"index": "community"}), digits=2)}

Figures:
- `fig_email_matrix` (main): emails between communities as numbers (diagonal,
  bold = inside a community; right = each community's total); each row shaded
  in its community's colour, darker = larger share of its email.
- `fig_community_heatmap` (main): people per community and department / role;
  numbers = people, each row in its community's colour, darker = larger share.
- `fig_si_community_mixing` (supplement): the observed / expected table above.

## Figure

`figures/fig_communities.png`, drawn by the course's five rules (week 4):
1. backbone = disparity filter (α = 0.05), plus each person's strongest link, plus
   the strongest link joining any group the filter cut off from the main network;
2. ForceAtlas2 layout of the backbone; 3. colour = Louvain community found on the
full graph, each named in the legend by its most common department;
4. size = emails sent and received; 5. the 10 people with most emails named.
"""
    path.write_text(text, encoding="utf-8")


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)

    # 1. data
    people = load_people()
    H_all = to_undirected(load_email_graph())
    H, isolates = cm.split_isolates(H_all)
    nodes = sorted(H.nodes())
    missing = [n for n in nodes if n not in people.index]
    if missing:
        raise SystemExit(f"{len(missing)} graph nodes are not in the people table: {missing[:5]}")
    print(f"{H.number_of_nodes()} people with links, {H.number_of_edges()} links; "
          f"{len(isolates)} without links set aside")

    # 2. Louvain over seeds
    runs = cm.run_louvain(H, nodes, args.seeds)
    best = cm.best_run(runs)
    comm = cm.relabel_by_size(best["labels"])
    stability = cm.seed_stability(runs)
    print(f"Louvain: Q = {best['q']:.3f}, {best['k']} communities, "
          f"NMI between runs = {stability['nmi_mean']:.3f}")

    # 3. null model for Q
    null = cm.modularity_null(H, best["q"], args.nulls)
    print(f"Shuffled graphs: Q = {null['mean']:.3f} ± {null['sd']:.3f} (z = {null['z']:.1f})")

    # 4. org chart
    tests = cm.compare_with_attributes(nodes, comm, people, args.perms, rng)
    print(tests[["compared with", "nmi", "ami", "z"]].to_string(index=False))

    # 5. profiles
    members = cm.community_members(H, nodes, comm, people)
    profiles = cm.community_profiles(H, members)

    # 6-7. other methods, earlier communities, resolution
    methods = cm.compare_methods(H, nodes, comm, best["q"], best["k"])
    earlier_nmi = cm.agreement_with(comm, people.loc[nodes, "full_corpus_community"])
    sweep = cm.resolution_sweep(H, nodes, people, seeds=args.seeds)

    # figure
    names = cm.group_names(members)
    backbone = cm.disparity_backbone(H)
    plot_community_network(H, backbone, members, names, FIGURES_DIR / "fig_communities")

    # 2c: ordered email matrix + consensus matrix
    partitions = cm.seed_partitions(runs, nodes, comm)
    D_all = pd.DataFrame(cm.consensus_matrix(partitions), index=nodes, columns=nodes)
    order = cm.consensus_order(D_all, members)      # community, then who groups together
    D = D_all.loc[order, order].to_numpy()
    together = cm.consensus_by_community(D_all, members)
    comm_of = members["community"].to_dict()
    share = cm.inside_share(H, comm_of)
    matrix_stats = {"inside": share["observed"], "expected": share["expected"],
                    "unstable": cm.unstable_pair_share(D), "together": together}
    between, total_emails = cm.community_weight_totals(H, comm_of)
    plot_email_between(between, total_emails, FIGURES_DIR / "fig_email_matrix")

    # 2c: community x department / role
    dept = tests.set_index("compared with").loc["department"]
    role = tests.set_index("compared with").loc["role"]
    dept_counts = pd.crosstab(members["community"], members["department"].fillna("(none)"))
    role_counts = pd.crosstab(members["community"], members["role"])
    plot_community_heatmap(
        dept_counts, role_counts,
        f"a  Department (NMI {dept['nmi']:.2f}, AMI {dept['ami']:.2f}; "
        f"shuffled 95%: {dept['null_p95']:.2f})",
        f"b  Role (NMI {role['nmi']:.2f}; shuffled 95%: {role['null_p95']:.2f})",
        FIGURES_DIR / "fig_community_heatmap")

    # 2c: community mixing
    mixing = cm.mixing_matrix(H, comm_of)
    plot_mixing_matrix(mixing, FIGURES_DIR / "fig_si_community_mixing")

    # save
    members.to_csv(OUT / "members.csv")
    profiles.to_csv(OUT / "profiles.csv", index=False)
    pd.crosstab(members["community"], members["department"].fillna("(none)")).to_csv(
        OUT / "community_x_department.csv")
    pd.crosstab(members["community"], members["role"]).to_csv(OUT / "community_x_role.csv")
    pd.DataFrame([{k: v for k, v in r.items() if k != "labels"} for r in runs]).to_csv(
        OUT / "seed_runs.csv", index=False)
    pd.DataFrame({"null_q": null["null_q"]}).to_csv(OUT / "null_q.csv", index=False)
    tests.to_csv(OUT / "org_chart_tests.csv", index=False)
    methods.to_csv(OUT / "methods.csv", index=False)
    sweep.to_csv(OUT / "resolution_sweep.csv", index=False)
    partitions.to_csv(OUT / "seed_partitions.csv")
    D_all.to_csv(OUT / "consensus_matrix.csv")
    mixing.to_csv(OUT / "mixing_matrix.csv")
    between.astype(int).to_csv(OUT / "emails_between_communities.csv")
    together.to_csv(OUT / "consensus_by_community.csv", index=False)
    write_summary(OUT / "summary.md", H=H, isolates=isolates, people=people, args=args,
                  best=best, stability=stability, null=null, tests=tests, profiles=profiles,
                  methods=methods, sweep=sweep, earlier_nmi=earlier_nmi, backbone=backbone,
                  matrix_stats=matrix_stats, mixing=mixing)
    print(f"Email inside communities: {share['observed']:.1%} (chance {share['expected']:.1%}); "
          f"unstable pairs {matrix_stats['unstable']:.1%}")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_*.png")


if __name__ == "__main__":
    main()
