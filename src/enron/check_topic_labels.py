"""Compare hand labels of Congress passages with the topic models (the hand check).

Reads the labels from data/hand_labels_congress.csv (a copy of
results/congress_text/hand_labels_template.csv with `your_topic` filled in,
using the LDA topic numbers, 0 = none of them; an optional `second_topic`
column holds a second choice) and the models' main topics from
results/congress_text/passages.csv. NMF topics are translated to LDA numbers
through the passages both models share. Nothing is refitted.

Usage (from the project root, after `uv run python -m enron.run_congress_text`):
    uv run python -m enron.check_topic_labels
    uv run python -m enron.check_topic_labels --labels data/hand_labels_congress_2.csv

Outputs in results/congress_text/: hand_check.md (agreement, confusion table,
disagreements to read) and hand_check.csv (one row per labelled passage).
"""

import argparse
from pathlib import Path

import pandas as pd

from enron import congress_text as ct
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table

OUT = RESULTS_DIR / "congress_text"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, default=DATA_DIR / "hand_labels_congress.csv",
                    help="CSV with passage_id and your_topic (default data/hand_labels_congress.csv)")
    return ap.parse_args()


def main():
    args = parse_args()
    labels = pd.read_csv(args.labels)
    labels = labels[pd.to_numeric(labels["your_topic"], errors="coerce").notna()].copy()
    labels["your_topic"] = labels["your_topic"].astype(int)
    passages = pd.read_csv(OUT / "passages.csv")
    table = labels.merge(passages[["passage_id", "lda_topic", "nmf_topic"]], on="passage_id")
    table["nmf_as_lda"] = table["nmf_topic"].map(ct.nmf_to_lda(passages))
    second = (pd.to_numeric(table["second_topic"], errors="coerce")
              if "second_topic" in table else None)

    results = pd.DataFrame([
        {"model": "LDA", **ct.label_agreement(table["your_topic"], table["lda_topic"], second)},
        {"model": "NMF", **ct.label_agreement(table["your_topic"], table["nmf_as_lda"], second)},
    ])
    confusion = pd.crosstab(table["your_topic"], table["lda_topic"],
                            rownames=["your label"], colnames=["LDA topic"])
    wrong = table[table["your_topic"] != table["lda_topic"]]

    lines = [f"# Hand check of the Congress topics ({args.labels.name})", "",
             f"{len(table)} labelled passages. strict = the model's main topic is your label; "
             "lenient = it is your label or your second choice; kappa corrects for chance.", "",
             md_table(results, 2), "",
             "Your label (rows) against LDA's main topic (columns):", "",
             md_table(confusion.reset_index()), "",
             "Passages where you and LDA disagree:", ""]
    for row in wrong.itertuples():
        lines += [f"- passage {row.passage_id}: you {row.your_topic}, LDA {row.lda_topic}, "
                  f"NMF {row.nmf_as_lda} - {row.text[:220]}..."]
    (OUT / "hand_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    table.drop(columns="text").to_csv(OUT / "hand_check.csv", index=False)

    print(results.round(2).to_string(index=False))
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/hand_check.md and hand_check.csv")


if __name__ == "__main__":
    main()
