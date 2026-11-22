"""What the bosses wrote about, and whether they email each other.

Groups: the finance core (Fastow, Causey, Glisan, Kopper, McMahon, Watkins, Mintz,
imported without a mailbox), the executives among the 148, and everyone else.
Compares their own-word emails on the Congress themes, on the emails' own topics,
and on their most typical words, and counts the emails between the bosses.

Usage (from the project root, after run_email_themes and run_email_topics):
    uv run python -m enron.run_boss_emails

Outputs: results/boss_emails/
    summary.md               all tables below, with notes
    groups.csv               the people in each group
    group_summary.csv        emails written, Congress-theme and energy shares, theme counts
    topic_mix.csv            share of each email topic per group
    distinctive_words.csv    the words most typical of each boss group (log-odds z)
    group_links.csv          email deliveries between the groups
    boss_links.csv           per boss: deliveries sent and received, to and from bosses
"""

import sys

import pandas as pd

from enron import boss_emails as be
from enron import themes as th
from enron.congress_text import PROCEDURE_WORDS
from enron.loaders import load_emails, load_people
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table
from enron.run_email_themes import EMAIL_WORDS, people_names
from enron.text import lemmatise, load_nlp

OUT = RESULTS_DIR / "boss_emails"
CLEAN = RESULTS_DIR / "email_themes" / "emails_clean.csv"
TAGS = RESULTS_DIR / "email_themes" / "email_themes.csv"
TOPICS = RESULTS_DIR / "email_topics" / "email_topics.csv"
TOPIC_NAMES = DATA_DIR / "topic_names_emails.csv"


def main():
    for path, script in [(CLEAN, "run_email_themes"), (TAGS, "run_email_themes"), (TOPICS, "run_email_topics")]:
        if not path.exists():
            sys.exit(f"{path.relative_to(PROJECT_ROOT)} is missing: run `uv run python -m enron.{script}` first.")
    OUT.mkdir(parents=True, exist_ok=True)

    people = load_people()
    groups = be.boss_groups(people)
    names = people["full_name"]
    bosses = list(groups[groups != "Other employees"].index)
    groups[groups != "Other employees"].rename("group").to_frame() \
        .assign(name=names).to_csv(OUT / "groups.csv")

    print("1/3 Themes and topics per group ...", flush=True)
    emails = pd.read_csv(CLEAN).merge(pd.read_csv(TAGS).drop(columns=["sender_id", "date", "n_words"]),
                                      on="email_id")
    emails = emails.merge(pd.read_csv(TOPICS)[["email_id", "topic"]], on="email_id", how="left")
    emails["group"] = emails["sender_id"].map(groups).fillna("Other employees")
    theme_names = th.theme_names(th.load_themes(DATA_DIR / "themes.csv"))
    summary = be.group_summary(emails, theme_names)
    summary.to_csv(OUT / "group_summary.csv", index=False)
    topic_names = (pd.read_csv(TOPIC_NAMES).set_index("topic")["name"].to_dict()
                   if TOPIC_NAMES.exists() else {})
    mix = be.topic_mix(emails, topic_names)
    mix.to_csv(OUT / "topic_mix.csv")

    print("2/3 Typical words per group (lemmatising) ...", flush=True)
    stop = PROCEDURE_WORDS | EMAIL_WORDS | people_names(people)
    emails["tokens"] = lemmatise(emails["text"].tolist(), load_nlp(), stop)
    words = []
    for group, min_count in [("Finance core", 3), ("Executives", 8)]:
        inside = emails["group"] == group
        table = be.log_odds(emails.loc[inside, "tokens"], emails.loc[~inside, "tokens"], min_count=min_count)
        words.append(table.assign(group=group))
    words = pd.concat(words)[["group", "word", "count in group", "count elsewhere", "z"]]
    words.to_csv(OUT / "distinctive_words.csv", index=False)

    print("3/3 Emails between the bosses ...", flush=True)
    pairs = be.deliveries(load_emails())
    links = be.group_links(pairs, groups)
    links.to_csv(OUT / "group_links.csv")
    per_boss = be.person_links(pairs, bosses, names)
    per_boss.to_csv(OUT / "boss_links.csv", index=False)

    finance_words = ", ".join(words.loc[words["group"] == "Finance core", "word"].head(15))
    executive_words = ", ".join(words.loc[words["group"] == "Executives", "word"].head(15))
    lines = [
        "# What the bosses wrote about", "",
        "Finance core = the seven finance and legal people imported without a mailbox (Fastow, Causey, "
        "Glisan, Kopper, McMahon, Watkins, Mintz); executives = role Executive among the 148. Emails = "
        "the sender's own words (`results/email_themes/emails_clean.csv`); themes = term lists; topics = "
        "the emails' own NMF topics (`run_email_topics`). The finance core wrote too few emails to fit a "
        "topic model of its own.", "",
        "## Congress themes and energy", "", md_table(summary), "",
        "## Email topics (% of each group's emails with at least 20 words)", "",
        "The email topics were fitted mostly on traders' emails and fit the finance core's emails "
        "less well; read them together with the typical words.", "",
        md_table(mix.reset_index()), "",
        "## Most typical words (weighted log-odds against all other emails)", "",
        f"Finance core: {finance_words}", "",
        f"Executives: {executive_words}", "",
        "Full lists with counts and z-scores: `distinctive_words.csv`.", "",
        "## Do the bosses email each other? (deliveries; rows = sender's group)", "",
        md_table(links.reset_index().rename(columns={"sender": "from"})), "",
        "The database holds only emails that involve at least one of the 148: emails among the finance "
        "core alone were never collected, so their links to each other are mostly invisible. Per boss:", "",
        md_table(per_boss), "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print(links.to_string())
    print(f"Finance core words: {finance_words}")
    print(f"Executive words: {executive_words}")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
