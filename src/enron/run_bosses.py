"""The bosses: what the finance core and the executives wrote about, and whether they
email each other.

Steps:
  1. groups: finance core (Fastow, Causey, Glisan, Kopper, McMahon, Watkins, Mintz),
     executives among the 148 (role Executive), everyone else
  2. who emails whom: deliveries between the groups, observed / expected given each
     group's volume, every pair of bosses that exchanged email, each boss's main contacts
  3. what they wrote:
     - topics: the team's NMF model (15 topics, fitted on all emails;
       reports/nmf/email_topics.csv, labels in reports/nmf/topic_labels.csv). For each
       group, and for the emails bosses sent to other bosses against those they sent
       only to others: the mean topic share of the emails, as for the communities
     - Congress themes (term lists) in each group's own-word emails
     - the words most typical of each group of bosses (weighted log-odds)

Usage (from the project root, after run_email_themes and the team's topic model):
    uv run python src/enron/nlp/nmf_tf_idf_community.py      (if reports/nmf is missing)
    uv run python -m enron.run_bosses

Outputs: results/bosses/
    summary.md           everything below in one file
    bosses.csv           one row per boss: deliveries, emails, themes, main topic, contacts
    boss_topics.csv      each boss's topic mix (%)
    group_topics.csv     topic mix (%) of each group and of the emails between bosses
    topic_distances.csv  how different two topic mixes are, with a shuffle test
    group_themes.csv     Congress themes per group
    group_deliveries.csv, group_mixing.csv, boss_pairs.csv, typical_words.csv

The database holds only emails that involve at least one of the 148, so emails among the
finance core alone are missing: their email with each other is undercounted.
"""

import sys

import pandas as pd

from enron import bosses as bs
from enron import themes as th
from enron.congress_text import PROCEDURE_WORDS
from enron.loaders import load_emails, load_people
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import fmt_p, md_table
from enron.run_email_themes import EMAIL_WORDS, people_names
from enron.text import lemmatise, load_nlp

OUT = RESULTS_DIR / "bosses"
TAGS = RESULTS_DIR / "email_themes" / "email_themes.csv"
CLEAN = RESULTS_DIR / "email_themes" / "emails_clean.csv"
NMF_DIR = PROJECT_ROOT / "reports" / "nmf"
TOPICS = NMF_DIR / "email_topics.csv"        # the team's topic model: each email's topic weights
TOPIC_LABELS = NMF_DIR / "topic_labels.csv"  # its topic names, written by hand
THEMES = DATA_DIR / "themes.csv"
FINANCE_THEMES = [1, 2, 3, 4, 5, 6, 7]


def main():
    for path, how in [(TAGS, "uv run python -m enron.run_email_themes"),
                      (TOPICS, "uv run python src/enron/nlp/nmf_tf_idf_community.py"),
                      (TOPIC_LABELS, "the topic labels written by hand (topic_number, long_title, short_title)")]:
        if not path.exists():
            sys.exit(f"{path.relative_to(PROJECT_ROOT)} is missing: {how}")
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. groups
    people = load_people()
    groups = bs.person_groups(people)
    bosses = list(groups[groups != "Others"].index)
    print("1/4 Groups:", groups.value_counts().to_dict())

    # 2. who emails whom (all emails except Outlook synchronisation logs)
    emails = load_emails()
    emails = emails[emails["message_type"] != "generated"]
    d = bs.deliveries(emails)
    counts, mixing = bs.group_mixing(d, groups)
    counts.to_csv(OUT / "group_deliveries.csv")
    mixing.to_csv(OUT / "group_mixing.csv")
    pairs = bs.boss_pairs(d, bosses, people, groups)
    pairs.to_csv(OUT / "boss_pairs.csv", index=False)
    boss_links, boss_possible = bs.contact_density(d, bosses)
    all_links, all_possible = bs.contact_density(d, list(groups.index))
    print("2/4 Deliveries between groups (rows = senders):")
    print(counts.to_string())

    # 3. topics (the team's NMF model)
    labels = bs.load_topic_labels(TOPIC_LABELS)
    topics = bs.load_email_topics(TOPICS, len(labels))
    sender_group = topics["sender_id"].map(groups)
    boss_set = set(bosses)
    to_boss = topics["email_id"].map(                      # NaN = email not among the deliveries
        emails.set_index("email_id")["others"].map(lambda rs: bool(boss_set & set(rs))))
    from_boss = sender_group.isin(["Finance core", "Executives"]) & to_boss.notna()
    sets = {g: sender_group == g for g in bs.GROUPS}
    sets["Bosses to bosses"] = from_boss & to_boss.fillna(False).astype(bool)
    sets["Bosses to others only"] = from_boss & ~to_boss.fillna(True).astype(bool)
    group_topics = bs.topic_mix(topics, sets, labels)
    group_topics.to_csv(OUT / "group_topics.csv", index=False)
    col = {name: next(c for c in group_topics.columns if c.startswith(f"{name} (n=")) for name in sets}
    comparisons = [("Finance core", "Others"), ("Executives", "Others"), ("Bosses to bosses", "Bosses to others only")]
    distances = pd.DataFrame(
        [(f"{a} vs {b}", *bs.topic_distance(topics, sets[a], sets[b])) for a, b in comparisons],
        columns=["comparison", "distance (percentage points)", "p (10,000 shuffles)"])
    distances["distance (percentage points)"] = distances["distance (percentage points)"].round(1)
    distances["p (10,000 shuffles)"] = [fmt_p(x, 10_000) for x in distances["p (10,000 shuffles)"]]
    distances.to_csv(OUT / "topic_distances.csv", index=False)
    boss_topics = bs.person_topics(topics, bosses, labels)
    boss_topics.insert(0, "name", people.loc[boss_topics.index, "full_name"])
    boss_topics.insert(1, "group", groups[boss_topics.index])
    boss_topics = boss_topics.sort_values(["group", "emails"], ascending=[False, False])
    boss_topics.to_csv(OUT / "boss_topics.csv", index_label="person_id")
    print(f"3/4 Topics ({len(labels)}) of {len(topics):,} emails; mean topic share (%):")
    print(group_topics.drop(columns="description").round(1).to_string(index=False))
    print(distances.to_string(index=False))
    print(f"Pairs of bosses in contact: {boss_links}/{boss_possible}; everyone: {all_links}/{all_possible}")

    # 4. Congress themes and typical words
    themes = th.load_themes(THEMES)
    names = th.theme_names(themes)
    tags = pd.read_csv(TAGS)
    group_themes = bs.theme_shares(tags, groups, names, FINANCE_THEMES)
    group_themes.to_csv(OUT / "group_themes.csv", index=False)

    print("4/4 Typical words (lemmatising the own-word emails) ...")
    clean = pd.read_csv(CLEAN)
    clean["group"] = clean["sender_id"].map(groups)
    stop = PROCEDURE_WORDS | EMAIL_WORDS | people_names(people)
    clean["tokens"] = lemmatise(clean["text"].tolist(), load_nlp(), stop)
    others = clean.loc[clean["group"] == "Others", "tokens"]
    words = pd.concat([bs.typical_words(clean.loc[clean["group"] == g, "tokens"], others).assign(group=g)
                       for g in ["Finance core", "Executives"]])
    words.to_csv(OUT / "typical_words.csv", index=False)

    # one row per boss
    t = tags.assign(finance=tags[[f"terms_{i}" for i in FINANCE_THEMES]].astype(bool).any(axis=1))
    short = labels["short"].to_dict()
    rows = []
    for p in bosses:
        mine = t[t["sender_id"] == p]
        main = topics.loc[topics["sender_id"] == p, "main_topic"].dropna()
        other_bosses = set(d.loc[(d["sender"] == p) & d["recipient"].isin(bosses), "recipient"]) | \
            set(d.loc[(d["recipient"] == p) & d["sender"].isin(bosses), "sender"])
        rows.append({
            "name": people.at[p, "full_name"], "group": groups[p],
            "title or department": bs.FINANCE_CORE.get(p, people.at[p, "department"]),
            "deliveries sent": int((d["sender"] == p).sum()),
            "deliveries received": int((d["recipient"] == p).sum()),
            "emails with a topic": int(len(main)),
            "main topic": short[int(main.mode().iloc[0])] if len(main) else "",
            "main topic (% of emails)": round(100 * (main == main.mode().iloc[0]).mean(), 1) if len(main) else None,
            "own-word emails": len(mine),
            "finance-theme emails": int(mine["finance"].sum()),
            "energy emails": int(mine["terms_8"].astype(bool).sum()),
            "other bosses in contact": len(other_bosses - {p}),
            "main contacts": bs.top_contacts(d, p, people, groups),
        })
    table = pd.DataFrame(rows).sort_values(["group", "deliveries sent"], ascending=[False, False])
    table.to_csv(OUT / "bosses.csv", index=False)

    # summary
    def over(name):
        return "; ".join(f"{topic} ({share:.1f}%, {ratio:.1f}x)"
                         for topic, share, ratio in bs.over_represented(group_topics, col[name], col["Others"]))

    fc_internal = int(counts.loc["Finance core", "Finance core"])
    lines = [
        "# The bosses: what they wrote and whom they wrote to", "",
        "Finance core = seven finance and legal managers without a mailbox, whose emails with the "
        "148 were added; executives = role Executive among the 148. The database holds only emails "
        "that involve at least one of the 148, so email among the finance core alone is missing.", "",
        "## Who emails whom", "",
        "Deliveries (one per sender-recipient pair; rows = senders):", "",
        md_table(counts.reset_index().rename(columns={"index": "from"})), "",
        "Observed / expected given each group's volume (1 = as much as chance):", "",
        md_table(mixing.reset_index().rename(columns={"index": "from"}), 2), "",
        f"Deliveries inside the finance core: {fc_internal} (only those copied to one of the 148).", "",
        f"Pairs in contact (at least one email either way): {boss_links} of the {boss_possible} possible "
        f"pairs of bosses with any email ({100 * boss_links / boss_possible:.0f}%), against "
        f"{all_links:,} of {all_possible:,} among everyone ({100 * all_links / all_possible:.0f}%).", "",
        "Pairs of bosses who exchanged email (most first):", "",
        md_table(pairs.head(25)), "",
        "## What they wrote: topics", "",
        f"The team's NMF topic model ({len(labels)} topics, fitted once on {len(topics):,} emails from "
        "everyone; labels from `reports/nmf/topic_labels.csv`). Each email's topic weights are "
        "rescaled to sum to 1, and a set's topic share is the mean over its emails, as for the "
        "communities' topic mix. 'Bosses to bosses' = emails a boss sent with at least one other "
        "boss among the recipients; 'bosses to others only' = the rest of the bosses' emails.", "",
        "Mean topic share (%):", "",
        md_table(group_topics.drop(columns="description"), 1), "",
        "Topics most over-represented against the others (share, ratio to the others; topics "
        "with at least 2% share):", "",
        f"- Finance core: {over('Finance core')}",
        f"- Executives: {over('Executives')}",
        f"- Bosses to bosses: {over('Bosses to bosses')}", "",
        "How different the topic mixes are (total variation distance: half the summed absolute "
        "differences of the topic shares; 0 = same mix), against shuffling the emails between the "
        "two sets:", "",
        md_table(distances, 1), "",
        "Each boss's topic mix (%):", "",
        md_table(boss_topics.reset_index(drop=True), 1), "",
        "Topic labels:", "",
        md_table(labels.reset_index().rename(columns={"short": "short title", "long": "long title"})), "",
        "## What they wrote: Congress themes and typical words", "",
        "Congress themes (term lists) in each group's own-word emails:", "",
        md_table(group_themes, 1), "",
        "Words most typical of each group of bosses against everyone else (weighted log-odds z):", "",
        md_table(words[["group", "word", "count", "count_others", "z"]], 1), "",
        "## Each boss", "",
        md_table(table, 1), "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(group_themes.to_string(index=False))
    print(table.drop(columns="main contacts").to_string(index=False))
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
