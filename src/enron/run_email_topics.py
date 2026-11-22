"""What the emails are about on their own terms (topic model, no Congress themes).

Fits NMF topics to the sender's own words (forwarded text, quotes and pasted news
articles already removed by run_email_themes), lists each topic's top words and its
strongest emails, and, when run_email_people has been run, the topic mix of each
person group (named by Congress, central core, robust brokers, others).

Usage (from the project root, after `uv run python -m enron.run_email_themes`):
    uv run python -m enron.run_email_topics
    uv run python -m enron.run_email_topics --topics 8

Topic names: data/topic_names_emails.csv (written by hand from the top words).

Outputs: results/email_topics/
    summary.md          topics with top words, shares and example emails
    topics.csv          one row per topic
    email_topics.csv    each email's topic and weight
    topics_by_group.csv topic shares per person group (if results/email_people exists)
"""

import argparse
import sys

import pandas as pd

from enron import email_topics as et
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table

EMAILS = RESULTS_DIR / "email_themes" / "emails_clean.csv"
PEOPLE = RESULTS_DIR / "email_people" / "people.csv"
OUT = RESULTS_DIR / "email_topics"
NAMES = DATA_DIR / "topic_names_emails.csv"   # topic, name, check_words (written by hand)


def topic_names(words: list[list[str]]) -> dict:
    """Names written by hand for the topics. A name is used only while the topic's top
    words still hold one of its check words, so a refitted model with topics in another
    order does not get the wrong names (those topics keep 'topic k')."""
    if not NAMES.exists():
        return {}
    names = {}
    for row in pd.read_csv(NAMES).itertuples():
        t = int(row.topic)
        if t <= len(words) and set(str(row.check_words).split(";")) & set(words[t - 1]):
            names[t] = row.name
        else:
            print(f"  name '{row.name}' not used: topic {t} no longer has its check words")
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--topics", type=int, default=10, help="number of topics (default 10)")
    ap.add_argument("--min-words", type=int, default=et.MIN_WORDS)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if not EMAILS.exists():
        sys.exit(f"{EMAILS.relative_to(PROJECT_ROOT)} is missing: run "
                 "`uv run python -m enron.run_email_themes` first.")
    OUT.mkdir(parents=True, exist_ok=True)

    emails = pd.read_csv(EMAILS)
    emails = emails[emails["n_words"] >= args.min_words].reset_index(drop=True)
    print(f"Fitting {args.topics} topics to {len(emails)} emails (at least {args.min_words} own words)...")

    vec, model, W = et.fit_email_topics(emails["text"], args.topics, args.seed)
    words = et.top_words(vec, model)
    topics = et.assign_topics(W)

    emails["topic"] = [t + 1 if t != et.UNCLEAR else "" for t in topics]
    emails["topic_label"] = ["no clear topic" if t == et.UNCLEAR else f"topic {t + 1}" for t in topics]
    emails["weight"] = W.max(axis=1).round(4)
    emails[["email_id", "sender_id", "date", "n_words", "topic", "weight", "text"]].to_csv(
        OUT / "email_topics.csv", index=False)

    names = topic_names(words)
    table = et.topic_table(topics, words)
    table.insert(1, "name", table["topic"].map(names).fillna(""))
    table.to_csv(OUT / "topics.csv", index=False)
    ex = et.examples(emails["text"], W, topics)

    lines = [
        "# What the emails are about",
        "",
        f"NMF topic model ({args.topics} topics) on TF-IDF of the sender's own words, "
        f"{len(emails)} emails with at least {args.min_words} own words. Each email goes to its "
        f"strongest topic; below weight {et.MIN_WEIGHT} it counts as 'no clear topic'. "
        "The model gives no names: the names were written by hand from the top words and "
        "examples (`data/topic_names_emails.csv`).",
        "",
        md_table(table, digits=1),
        "",
        "## Strongest emails per topic",
        "",
    ]
    for t, texts in ex.items():
        lines.append(f"**Topic {t}{': ' + names[t] if t in names else ''}** ({', '.join(words[t - 1][:6])})")
        lines.extend(f"- {s}" for s in texts)
        lines.append("")

    if PEOPLE.exists():
        people = pd.read_csv(PEOPLE)[["person_id", "group"]]
        mixed = emails.merge(people, left_on="sender_id", right_on="person_id", how="inner")
        by_group = et.topics_by_group(mixed).rename(columns={f"topic {t}": f"{t}. {n}" for t, n in names.items()})
        by_group.to_csv(OUT / "topics_by_group.csv")
        lines += ["## Topic mix of each person group (% of the group's emails)", "",
                  md_table(by_group.reset_index(), digits=1), ""]
    else:
        lines += ["(Run `uv run python -m enron.run_email_people` to add the topic mix per person group.)", ""]

    (OUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(table.to_string(index=False, max_colwidth=80))
    print(f"\nWrote {OUT.relative_to(PROJECT_ROOT)}/ (summary.md, topics.csv, email_topics.csv"
          + (", topics_by_group.csv)" if PEOPLE.exists() else ")"))


if __name__ == "__main__":
    main()
