"""Analysis 1: network basics and null models.

Steps:
  1. directed email graph (emails to oneself left out) and its undirected copy;
     the one person with no links is described, then left out of the tests
  2. describe: size, density, reciprocity, degrees, components, clustering,
     path length; who mostly sends and who mostly receives
  3. null models: reciprocity, clustering, transitivity, path length and degree
     assortativity against degree-preserving shuffles (z-scores) and random
     graphs of the same size
  4. mixing: assortativity by role and by department (links and email-weighted),
     against label shuffles; role-by-role email matrix (observed / expected)
  5. rich club: link density among the best-connected people against the
     shuffled graphs; do executives email each other more than chance?

Usage (from the project root):
    uv run python -m enron.run_network_basics
    uv run python -m enron.run_network_basics --nulls 200 --perms 1000

Outputs: results/network_basics/ (summary.md + CSV tables) and figures/ (.png):
main text: fig_role_mixing; supplement: fig_si_null_models, fig_si_rich_club,
fig_si_send_receive
"""

import argparse

import networkx as nx
import numpy as np
import pandas as pd

from enron import network_basics as nb
from enron.loaders import load_email_graph, load_people, to_directed, to_undirected
from enron.paths import FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import plot_null_models, plot_rich_club, plot_role_mixing, plot_send_receive
from enron.reporting import fmt_p, md_table

OUT = RESULTS_DIR / "network_basics"
ROLES = ["Executive", "Legal", "VP / Director", "Gov. & regulatory", "Trading",
         "Manager / staff", "Unknown"]


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nulls", type=int, default=1000,
                    help="shuffled and random graphs (default 1000; a few minutes)")
    ap.add_argument("--perms", type=int, default=5000,
                    help="label shuffles for assortativity and the executive test (default 5000)")
    return ap.parse_args()


def null_table_text(table: pd.DataFrame, n_null: int) -> pd.DataFrame:
    """Table 1 layout: observed, random, shuffled mean ± SD, z, p."""
    return pd.DataFrame({
        "Statistic": table.statistic,
        "Email network": table.observed.map("{:.3f}".format),
        "Random graphs": table.random_mean.map("{:.3f}".format),
        "Shuffled graphs": [f"{m:.3f} ± {s:.3f}" for m, s in zip(table.shuffled_mean, table.shuffled_sd)],
        "z": table.z.map("{:.1f}".format),
        "p": [fmt_p(p, n_null) for p in table.p],
    })


def write_summary(describe, null_text, assort, execs, rich, senders, args) -> None:
    peak = rich.loc[rich.rho.idxmax()]
    lines = [
        "# Analysis 1: network basics and null models", "",
        f"Shuffled graphs: {args.nulls} (degree-preserving edge swaps); random graphs: "
        f"{args.nulls} with the same number of people and links; label shuffles: {args.perms}.", "",
        "## The network", "", md_table(describe), "",
        "## Against null models (Table 1)", "",
        "z and p are against the shuffled graphs, which keep every person's number of "
        "contacts; p is two-sided.", "", md_table(null_text), "",
        "## Mixing by role and department", "",
        "Assortativity r: 0 = links ignore the attribute, 1 = links only within groups. "
        "'emails' weights each link by its number of emails.", "", md_table(assort), "",
        "## Rich club", "",
        f"Highest rich-club ratio: rho = {peak.rho:.2f} for the {int(peak.people_above_k)} people "
        f"with more than {int(peak.name)} contacts (shuffled graphs: 95% between "
        f"{peak.null_lo / peak.null_mean:.2f} and {peak.null_hi / peak.null_mean:.2f}).", "",
        "Executives emailing each other:", "", md_table(execs), "",
        "## Who mostly sends, who mostly receives", "",
        "People with at least 100 emails, by share of their email that they sent.", "",
        md_table(senders), "",
        "## Figures", "",
        "- `fig_role_mixing`: emails between roles, observed / expected (main text)",
        "- `fig_si_null_models`: each statistic against both null models (supplement)",
        "- `fig_si_rich_club`: rich-club ratio by number of contacts (supplement)",
        "- `fig_si_send_receive`: emails sent against received per person (supplement)",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)

    # 1. graphs
    G = load_email_graph()
    people = load_people()
    D_all, H_all = to_directed(G), to_undirected(G)
    linked = [n for n in H_all if H_all.degree(n) > 0]
    D, H = D_all.subgraph(linked).copy(), H_all.subgraph(linked).copy()
    role = people.role.to_dict()
    department = people.department.to_dict()

    # 2. describe
    describe = nb.describe(G, D_all, H_all)
    describe.to_csv(OUT / "describe.csv", index=False)
    flows = nb.send_receive(D, people)
    flows.to_csv(OUT / "send_receive.csv")
    busy = flows[flows.sent + flows.received >= 100].sort_values("sent_share")
    senders = pd.concat([busy.head(5), busy.tail(5)])[["full_name", "role", "sent", "received", "sent_share"]]
    print(f"{D.number_of_nodes()} people, {D.number_of_edges()} directed links, "
          f"reciprocity {nx.reciprocity(D):.2f}")

    # 3. null models (also records the rich club and executive links)
    executives = {n for n in H if role.get(n) == "Executive"}
    print(f"Building {args.nulls} shuffled and {args.nulls} random graphs ...")
    nulls = nb.null_ensemble(D, H, args.nulls, executives)
    observed = {"Reciprocity": nx.reciprocity(D), **nb.undirected_stats(H)}
    table = nb.null_model_table(observed, nulls)
    table.to_csv(OUT / "null_models.csv", index=False)
    null_text = null_table_text(table, args.nulls)
    print(null_text.to_string(index=False))

    # 4. mixing by role and department
    assort = []
    for name, labels in [("Role", role), ("Department", department)]:
        for weight, kind in [(None, "links"), ("weight", "emails")]:
            res = nb.assortativity_test(H, labels, args.perms, rng, weight)
            assort.append({"attribute": name, "counted": kind, "r": res["r"],
                           "shuffled mean": res["null_mean"], "shuffled 95%": res["null_p95"],
                           "p": fmt_p(res["p"], args.perms), "groups": res["groups"]})
    assort = pd.DataFrame(assort)
    assort.to_csv(OUT / "assortativity.csv", index=False)
    print(assort.to_string(index=False))

    roles = [r for r in ROLES if r in set(role.values())]
    role_counts = nb.mixing_counts(D, role, roles, weight="weight")
    role_ratio = nb.mixing_ratio(role_counts)
    role_counts.to_csv(OUT / "role_mixing_emails.csv")
    role_ratio.to_csv(OUT / "role_mixing_ratio.csv")
    departments = sorted(d for d in set(department.values()) if pd.notna(d))
    nb.mixing_ratio(nb.mixing_counts(D, department, departments, weight="weight")) \
        .to_csv(OUT / "department_mixing_ratio.csv")

    # 5. rich club and executives
    rich = nb.rich_club_table(H, nulls["rich_club"])
    rich.to_csv(OUT / "rich_club.csv")
    club = nb.club_test(H, executives, nulls["shuffled"]["club_links"], args.perms, rng)
    execs = pd.DataFrame([{
        "executives": club["members"], "possible links": club["possible_links"],
        "links": club["observed_links"],
        "shuffled graphs": f"{club['shuffled_mean']:.1f}", "p (shuffled)": fmt_p(club["p_shuffled"], args.nulls),
        "random sets of 15": f"{club['label_mean']:.1f}", "p (random sets)": fmt_p(club["p_label"], args.perms),
    }])
    execs.to_csv(OUT / "executive_club.csv", index=False)
    print(execs.to_string(index=False))

    write_summary(describe, null_text, assort, execs, rich, senders, args)

    plot_role_mixing(role_ratio, FIGURES_DIR / "fig_role_mixing")
    plot_null_models(table, nulls, FIGURES_DIR / "fig_si_null_models")
    plot_rich_club(rich, FIGURES_DIR / "fig_si_rich_club")
    plot_send_receive(flows, FIGURES_DIR / "fig_si_send_receive")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_role_mixing, "
          "fig_si_null_models, fig_si_rich_club, fig_si_send_receive")


if __name__ == "__main__":
    main()
