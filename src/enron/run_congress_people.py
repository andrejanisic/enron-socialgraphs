"""Everyone named in the Congress documents, and who of them is among the 148.

Steps:
  1. find person names in every Congress paragraph (spaCy, label PERSON) and count
     the hearing speaker labels
  2. merge variants of one name (titles, middle initials, nicknames, surname only)
  3. match each name to the 148 people (surname + first name)
  4. add a hand-made group label (Enron, board, Andersen, Congress, ...) from
     data/congress_people_groups.csv when it exists

Usage (from the project root, after `uv run python -m enron.add_congress_texts`):
    uv run python -m enron.run_congress_people
    uv run python -m enron.run_congress_people --min-mentions 5

Outputs: results/congress_people/
  people_named.csv        everyone named at least --min-mentions times (mentions + turns)
  missing_from_148.csv    the same, without the people matched to the 148
  summary.md
"""

import argparse

import pandas as pd

from enron.congress_people import find_mentions, people_table, speaker_turns
from enron.loaders import load_congress_paragraphs, load_people
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table
from enron.text import load_nlp

OUT = RESULTS_DIR / "congress_people"
GROUPS = DATA_DIR / "congress_people_groups.csv"     # name, group (filled by hand)


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-mentions", type=int, default=3,
                    help="keep names with at least this many mentions + speaking turns (default 3)")
    return ap.parse_args()


def write_summary(table: pd.DataFrame, n_mentions: int, args) -> None:
    named = table[table["in_148"] == "yes"]
    missing = table[table["in_148"] != "yes"]
    cols = ["name", "mentions", "documents", "speaking_turns", "title_used"]
    if "group" in table:
        cols.append("group")
    lines = [
        "# People named in the Congress documents", "",
        f"{n_mentions:,} person mentions (spaCy, label PERSON) in 10 documents, merged into "
        f"{len(table)} people named at least {args.min_mentions} times (mentions + speaking turns).", "",
        f"- Among the 148: {len(named)} people, {int(named['mentions'].sum()):,} mentions",
        f"- Not among the 148: {len(missing)} people, {int(missing['mentions'].sum()):,} mentions",
        f"- Unclear (surname only, shared with one of the 148): "
        f"{int(table['in_148'].str.startswith('unclear').sum())} names", "",
        "The list also holds members of Congress, witnesses from outside Enron and "
        "authors of documents; `title_used` (Senator, Chairman, Mr., Ms.) and `example` "
        "help tell them apart. Names are found automatically, so check rare names in "
        "`example` before using them.", "",
    ]
    if "group" in table:
        by_group = (table.assign(group=table["group"].replace("", "not labelled"))
                    .groupby("group").agg(people=("name", "size"), mentions=("mentions", "sum"),
                                          among_148=("in_148", lambda s: int((s == "yes").sum())))
                    .sort_values("mentions", ascending=False).reset_index())
        enron = table[table["group"].str.startswith("Enron") & (table["in_148"] != "yes")]
        lines += ["## By group", "",
                  "Groups come from `data/congress_people_groups.csv` (labelled by hand; "
                  "a draft to check). Names without a label are mostly rarely named.", "",
                  md_table(by_group), "",
                  "## Enron people Congress named who are not among the 148", "",
                  md_table(enron[cols]), ""]
    lines += [
        "## Among the 148", "", md_table(named[cols + ["name_in_148", "role_in_148"]]), "",
        "## Not among the 148 (30 most mentioned)", "", md_table(missing[cols].head(30)), "",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    paragraphs = load_congress_paragraphs()
    people = load_people()
    nlp = load_nlp(entities=True)
    print(f"Finding person names in {len(paragraphs):,} paragraphs ...")
    mentions = find_mentions(paragraphs, nlp)
    table = people_table(mentions, speaker_turns(paragraphs), people, args.min_mentions)
    if GROUPS.exists():
        groups = pd.read_csv(GROUPS).drop_duplicates("name").set_index("name")["group"]
        table.insert(table.columns.get_loc("in_148"), "group", table["name"].map(groups).fillna(""))
    table.to_csv(OUT / "people_named.csv", index=False)
    table[table["in_148"] != "yes"].to_csv(OUT / "missing_from_148.csv", index=False)
    write_summary(table, len(mentions), args)
    show = ["name", "mentions", "documents", "speaking_turns", "title_used", "in_148"]
    print(table[show].head(40).to_string(index=False))
    print(f"\n{len(table)} people; {int((table['in_148'] == 'yes').sum())} among the 148")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
