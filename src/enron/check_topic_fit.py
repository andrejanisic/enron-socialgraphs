"""Score the yes/no hand check of the Congress topics.

Reads data/topic_fit_congress.csv (a copy of
results/congress_text/topic_fit_template.csv with `fits` filled in: yes or no)
and results/congress_text/topic_fit_key.csv (which passages were the strongest
for their topic and which were random), and reports the share that fit, per
topic and for the strongest and random passages separately.

Usage (from the project root):
    uv run python -m enron.check_topic_fit
    uv run python -m enron.check_topic_fit --labels data/topic_fit_congress_2.csv

Output: results/congress_text/topic_fit.md
"""

import argparse
from pathlib import Path

import pandas as pd

from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table

OUT = RESULTS_DIR / "congress_text"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, default=DATA_DIR / "topic_fit_congress.csv",
                    help="filled-in template (default data/topic_fit_congress.csv)")
    return ap.parse_args()


def main():
    args = parse_args()
    judged = pd.read_csv(args.labels)
    judged["fit"] = judged["fits"].astype(str).str.strip().str.lower().map({"yes": 1, "y": 1, "no": 0, "n": 0})
    judged = judged.dropna(subset=["fit"])
    table = judged.merge(pd.read_csv(OUT / "topic_fit_key.csv"), on=["item", "topic"])

    overall = (table.groupby("kind")["fit"].agg(["count", "mean"])
               .rename(columns={"count": "passages", "mean": "share fitting"}).reset_index())
    overall.loc[len(overall)] = ["all", len(table), table["fit"].mean()]
    per_topic = (table.groupby(["topic", "topic_name"], dropna=False)["fit"].agg(["count", "sum"])
                 .rename(columns={"count": "judged", "sum": "fit"}).reset_index())
    misfits = table[table["fit"] == 0]

    lines = [f"# Do the passages fit their topic? ({args.labels.name})", "",
             f"{len(table)} passages judged; 'strongest' = the topic's highest-weight passages, "
             "'random' = a random passage with the topic as its main topic.", "",
             md_table(overall, 2), "", "Per topic:", "", md_table(per_topic), "",
             "Passages judged not to fit:", ""]
    lines += [f"- item {r.item} (topic {r.topic}, {r.kind}): {r.text[:220]}..." for r in misfits.itertuples()]
    (OUT / "topic_fit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(overall.round(2).to_string(index=False))
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/topic_fit.md")


if __name__ == "__main__":
    main()
