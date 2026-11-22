"""Phase F: did the central people write about what Congress investigated?

Steps:
  1. groups from the email network and the Congress record, one per person:
     named by Congress (named at least once, hand-checked), central core (top 20% by
     PageRank, not named), brokers (betweenness z >= 2 against degree-preserving
     shuffles with both email-weighted and links-only betweenness, at least 5 links;
     not named or central), others
  2. per person: own-word emails written and received, and how many carry a Congress
     theme (themes 1-7 pooled) or the energy theme (8)
  3. tests: theme emails written and received by each group against chance (the theme
     flags shuffled over all emails, so every person keeps their number of emails);
     receiving counts the recipients without the sender, each email weighted
     1 / number of recipients
  4. when: theme emails per month, and the Congress-theme emails written before
     October 2001 for close reading
  5. robustness: central = top 20% by links; receiving unweighted; forwarded text
     included; "named" = named at least 10 times
  + people outside the email network (no mailbox: Fastow, Causey and others added
    from other people's mailboxes) are left out of the group tests, because only
    their emails with the 148 are seen; their emails are reported apart

Usage (from the project root, after run_visibility, run_email_themes and
run_congress_people):
    uv run python -m enron.run_email_people
    uv run python -m enron.run_email_people --nulls 200 --perms 10000

Outputs: results/email_people/ (summary.md + CSV tables) and figures/ (.png):
fig_email_people (main: Congress-theme emails written and received by each group
against the range expected by chance), fig_si_email_people_ratio (supplement:
observed / expected for the Congress themes and, as a contrast, energy)
"""

import argparse

import numpy as np
import pandas as pd

from enron import email_people as ep
from enron import themes as th
from enron import visibility as vis
from enron.loaders import (load_congress_mentions, load_email_graph, load_emails, load_people,
                           to_directed, to_undirected)
from enron.paths import DATA_DIR, FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import plot_group_chance, plot_group_ratio
from enron.reporting import md_table

OUT = RESULTS_DIR / "email_people"
TAGS = RESULTS_DIR / "email_themes" / "email_themes.csv"
CLEAN = RESULTS_DIR / "email_themes" / "emails_clean.csv"
NAMED_NEW = RESULTS_DIR / "congress_people" / "people_named.csv"
THEMES = DATA_DIR / "themes.csv"
CONGRESS_THEMES = [1, 2, 3, 4, 5, 6, 7]
ENERGY_THEME = 8
CENTRAL_SHARE, Z_MIN, MIN_DEGREE = 0.2, 2.0, 5
PUBLIC = pd.Timestamp("2001-10-01", tz="UTC")     # Enron's losses and the partnerships in the news


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nulls", type=int, default=200, help="shuffled graphs for broker z-scores (default 200)")
    ap.add_argument("--perms", type=int, default=10000, help="shuffles of the theme flags (default 10000)")
    return ap.parse_args()


def network_table(people: pd.DataFrame, n_null: int) -> pd.DataFrame:
    """PageRank, links, and betweenness z-scores (email-weighted and links-only)."""
    G = load_email_graph()
    D, H = to_directed(G), to_undirected(G)
    table = vis.centrality_measures(D, H).reindex(people.index)
    table["degree"] = pd.Series(dict(H.degree())).reindex(people.index).fillna(0)
    table["z_weighted"] = ep.betweenness_z(H, n_null, weighted=True).reindex(people.index).fillna(0)
    table["z_links"] = ep.betweenness_z(H, n_null, weighted=False, seed=1).reindex(people.index).fillna(0)
    return table


def central_by(table: pd.DataFrame, measure: str) -> pd.Series:
    return table[measure].fillna(0) >= table[measure].fillna(0).quantile(1 - CENTRAL_SHARE)


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    everyone = load_people()
    in_network = everyone.index.isin(list(load_email_graph().nodes()))
    people, outside = everyone[in_network], everyone[~in_network]

    # 1. groups
    print(f"1/5 Network position: betweenness in {2 * args.nulls} shuffled networks (about a minute) ...",
          flush=True)
    net = network_table(people, args.nulls)
    mentions = load_congress_mentions().reindex(people.index).fillna(0)
    named = mentions > 0
    central = central_by(net, "PageRank")
    broker = ((net["z_weighted"] >= Z_MIN) & (net["z_links"] >= Z_MIN) & (net["degree"] >= MIN_DEGREE))
    groups = ep.assign_groups(people, named, central, broker)

    print("    groups: " + ", ".join(f"{g} {n}" for g, n in groups.value_counts()
                                     .reindex(ep.GROUP_ORDER).items()), flush=True)

    # 2. emails: own words, theme flags
    print("2/5 Emails and theme tags ...", flush=True)
    tags = pd.read_csv(TAGS)
    emails = load_emails().set_index("email_id")
    emails = emails.loc[tags["email_id"]].reset_index()
    tags = tags.reset_index(drop=True)
    emails["text"] = emails["email_id"].map(pd.read_csv(CLEAN).set_index("email_id")["text"])
    emails["congress"] = tags[[f"terms_{t}" for t in CONGRESS_THEMES]].astype(bool).any(axis=1).to_numpy()
    emails["energy"] = tags[f"terms_{ENERGY_THEME}"].astype(bool).to_numpy()
    emails["themes"] = [",".join(str(t) for t in CONGRESS_THEMES if row[f"terms_{t}"])
                        for _, row in tags.iterrows()]
    themes = th.load_themes(THEMES)
    full = th.tag_terms(emails["body_clean"].fillna(""), themes)    # forwarded text included
    emails["congress_full"] = full[CONGRESS_THEMES].any(axis=1).to_numpy()
    all_emails = emails
    emails = emails[emails["sender_id"].isin(people.index)].reset_index(drop=True)
    outsiders = outside_table(all_emails, outside)
    if len(outsiders):
        outsiders.to_csv(OUT / "outside_network.csv")

    counts = ep.person_counts(emails, "congress", people.index)
    energy = ep.person_counts(emails, "energy", people.index)
    person = people[["full_name", "role", "department"]].join(groups).assign(
        congress_mentions=mentions.astype(int), pagerank_rank=net["PageRank"].rank(ascending=False).astype(int),
        degree=net["degree"].astype(int), z_weighted=net["z_weighted"].round(2), z_links=net["z_links"].round(2),
        written=counts["written"].astype(int), written_congress=counts["written_theme"].astype(int),
        written_energy=energy["written_theme"].astype(int), received=counts["received"].astype(int),
        received_congress=counts["received_theme"].astype(int))
    person = person.sort_values(["group", "pagerank_rank"], key=lambda s: s.map(
        {g: i for i, g in enumerate(ep.GROUP_ORDER)}) if s.name == "group" else s)
    person.to_csv(OUT / "people.csv")

    sizes = person.groupby("group").agg(
        people=("full_name", "size"), emails_written=("written", "sum"),
        congress_written=("written_congress", "sum"), energy_written=("written_energy", "sum"),
        members=("full_name", lambda s: "; ".join(s.head(12)))).reindex(ep.GROUP_ORDER)
    sizes.to_csv(OUT / "groups.csv")

    # 3. tests
    print(f"3/5 Tests: {args.perms:,} shuffles of the theme flags ...", flush=True)
    tests = pd.concat([ep.group_test(emails, groups, "congress", args.perms).assign(theme="Congress themes 1-7"),
                       ep.group_test(emails, groups, "energy", args.perms).assign(theme="Energy (8)")])
    tests = tests[["theme", "side", "group", "observed", "expected", "chance_low", "chance_high",
                   "ratio", "p_high", "p_low"]]
    tests.to_csv(OUT / "tests.csv", index=False)
    plot_group_chance(tests[tests["theme"].str.startswith("Congress")], FIGURES_DIR / "fig_email_people")
    plot_group_ratio(tests, FIGURES_DIR / "fig_si_email_people_ratio")

    print("4/5 Timeline and the emails written before October 2001 ...", flush=True)
    # 4. when
    monthly = ep.timeline(emails, "congress").join(
        ep.timeline(emails, "energy")["theme_emails"].rename("energy_emails"))
    monthly.to_csv(OUT / "timeline.csv")
    flagged = emails[emails["congress"]].copy()
    flagged["sender"] = flagged["sender_id"].map(people["full_name"])
    flagged["group"] = flagged["sender_id"].map(groups)
    flagged["recipients"] = flagged["others"].apply(lambda r: "; ".join(everyone.loc[x, "full_name"] for x in r))
    flagged["start"] = flagged["text"].str.replace(r"\s+", " ", regex=True).str[:220]
    show = ["email_id", "date", "sender", "group", "themes", "recipients", "start"]
    flagged = flagged.sort_values("date")
    flagged[show].to_csv(OUT / "congress_emails.csv", index=False)
    early = flagged[flagged["date_known"] & (flagged["date"] < PUBLIC)]
    early[show].to_csv(OUT / "early_emails.csv", index=False)

    # 5. robustness: the central core's share of Congress-theme emails written and received
    print("5/5 Robustness checks ...", flush=True)
    variants = []
    def central_row(label, grp, flag="congress", weighted=True):
        t = ep.group_test(emails, grp, flag, max(2000, args.perms // 5), weighted)
        for side in ("written", "received"):
            r = t[(t["side"] == side) & (t["group"] == "Central core")].iloc[0]
            n = t[(t["side"] == side) & (t["group"] == "Named by Congress")].iloc[0]
            variants.append({"variant": label, "side": side,
                             "central core: observed": r["observed"], "expected": r["expected"],
                             "ratio": r["ratio"], "p_low": r["p_low"], "p_high": r["p_high"],
                             "named: observed": n["observed"], "named: expected": n["expected"],
                             "named: p_high": n["p_high"]})
    central_row("main (PageRank top 20%, weighted receiving)", groups)
    central_row("central = top 20% by links", ep.assign_groups(people, named, central_by(net, "degree"), broker))
    central_row("receiving unweighted", groups, weighted=False)
    central_row("forwarded text included", groups, flag="congress_full")
    if NAMED_NEW.exists():
        new = pd.read_csv(NAMED_NEW).dropna(subset=["person_id"])
        often = people.index.isin(new.loc[new["mentions"] >= 10, "person_id"].astype(int))
        central_row("named = named 10+ times", ep.assign_groups(people, pd.Series(often, index=people.index),
                                                                central, broker))
    robust = pd.DataFrame(variants)
    robust.to_csv(OUT / "robustness.csv", index=False)

    write_summary(sizes, tests, monthly, flagged, early, robust, outsiders, args)
    print(md_table(tests[tests["theme"].str.startswith("Congress")].round(3)))
    print(f"\nWrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_email_people, fig_si_email_people_ratio")


def outside_table(emails: pd.DataFrame, outside: pd.DataFrame) -> pd.DataFrame:
    """Emails written and received by people outside the network (seen only through
    the mailboxes of the 148), with their Congress mentions when known."""
    if outside.empty:
        return pd.DataFrame()
    congress = ep.person_counts(emails, "congress", outside.index)
    energy = ep.person_counts(emails, "energy", outside.index)
    table = outside[["full_name"]].assign(
        written=congress["written"].astype(int), written_congress=congress["written_theme"].astype(int),
        written_energy=energy["written_theme"].astype(int), received=congress["received"].astype(int),
        received_congress=congress["received_theme"].astype(int))
    if NAMED_NEW.exists():
        named = pd.read_csv(NAMED_NEW)
        key = lambda n: (str(n).split()[-1].lower(), str(n)[:1].lower())
        mentions = named.groupby(named["name"].map(key))["mentions"].max()
        table["congress_mentions"] = [int(mentions.get(key(n), 0)) for n in table["full_name"]]
    return table


def write_summary(sizes, tests, monthly, flagged, early, robust, outsiders, args) -> None:
    def pick(theme, side):
        t = tests[(tests["theme"].str.startswith(theme)) & (tests["side"] == side)]
        return t.drop(columns=["theme", "side"]).round({"expected": 1, "ratio": 2, "p_high": 4, "p_low": 4})
    before = int((flagged["date_known"] & (flagged["date"] < PUBLIC)).sum())
    lines = [
        "# Did the central people write about what Congress investigated?", "",
        "Congress-theme emails = own-word emails tagged with any of themes 1-7 by the term "
        f"lists ({int(flagged.shape[0])} emails). Chance = the theme flags shuffled over all "
        f"own-word emails {args.perms:,} times; every email keeps its sender and recipients, so "
        "people who write a lot are expected to write more theme emails. `ratio` = observed / "
        "expected; `p_high` = share of shuffles at least as high as observed, `p_low` = at least "
        "as low.", "",
        "## Groups", "",
        "One group per person, in this order: named by Congress (named at least once in the "
        "hand-checked Congress mentions); central core (top 20% by PageRank); brokers "
        "(betweenness z >= 2 against degree-preserving shuffles, with both email-weighted and "
        "links-only betweenness, and at least 5 links); others.", "",
        md_table(sizes.reset_index()), "",
        "## Who wrote the Congress-theme emails", "", md_table(pick("Congress", "written")), "",
        "## Who received them", "",
        "Recipients without the sender; each email weighted 1 / number of recipients.", "",
        md_table(pick("Congress", "received")), "",
        "## For contrast: energy emails", "", "Written:", "", md_table(pick("Energy", "written")), "",
        "Received:", "", md_table(pick("Energy", "received")), "",
        "## When", "",
        f"{before} of the {int(flagged.shape[0])} Congress-theme emails were written before "
        "October 2001 (`early_emails.csv`); all of them, with sender, group and first words, are in "
        "`congress_emails.csv`. Per month: `timeline.csv`.", "",
        md_table(monthly[monthly["theme_emails"] > 0].reset_index().astype(str)), "",
        "## Robustness (central core and named people)", "", md_table(robust.round(3)), "",
    ]
    if len(outsiders):
        lines += [
            "## People outside the email network", "",
            "Added from other people's mailboxes (they have no mailbox of their own), so only "
            "their emails with the 148 are seen and they are left out of the group tests above. "
            "Own-word emails they wrote and received:", "",
            md_table(outsiders.reset_index(drop=True)), "",
        ]
    lines += [
        "Figures: `fig_email_people` (main): Congress-theme emails written and received by each "
        "group against the range expected by chance; `fig_si_email_people_ratio` (supplement): "
        "observed / expected for the Congress themes and energy.", "",
        "Files: `people.csv` (every person: group, network position, emails written and "
        "received), `groups.csv`, `tests.csv`, `timeline.csv`, `congress_emails.csv`, "
        "`early_emails.csv`, `robustness.csv`.",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
