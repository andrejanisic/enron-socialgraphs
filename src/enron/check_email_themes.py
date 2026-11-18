"""Score the hand check of the email themes.

Reads data/hand_check_emails.csv (a copy of results/email_themes/hand_check_template.csv
with `about_theme` filled in) and results/email_themes/hand_check_key.csv (which
method chose each email). Rows naming a theme are answered yes or no; rows asking
about any theme are answered with a theme number, or 0 for none.

Reports, per theme, how many emails chosen by the term list and by retrieval alone
are really about the theme (precision), and the share of emails with no theme that
are about one after all (missed).

Usage (from the project root, after `uv run python -m enron.run_email_themes`):
    uv run python -m enron.check_email_themes
    uv run python -m enron.check_email_themes --labels data/hand_check_emails_2.csv

Output: results/email_themes/hand_check.md
"""

import argparse
from pathlib import Path

import pandas as pd

from enron import themes as th
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table

OUT = RESULTS_DIR / "email_themes"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, default=DATA_DIR / "hand_check_emails.csv",
                    help="filled-in template (default data/hand_check_emails.csv)")
    return ap.parse_args()


def main():
    args = parse_args()
    judged = pd.read_csv(args.labels, dtype={"about_theme": str})
    key = pd.read_csv(OUT / "hand_check_key.csv")
    table = judged[["item", "about_theme"]].merge(key, on="item")
    answer = table["about_theme"].fillna("").str.strip().str.lower()
    names = th.theme_names(th.load_themes(DATA_DIR / "themes.csv"))

    tagged = table[table["source"] != "no theme"].copy()
    tagged["fit"] = answer[tagged.index].map({"yes": 1, "y": 1, "no": 0, "n": 0})
    tagged = tagged.dropna(subset=["fit"])
    precision = (tagged.pivot_table(index="theme_id", columns="source", values="fit", aggfunc=["sum", "count"])
                 .fillna(0).astype(int))
    rows = []
    for theme_id in names.index:
        row = {"theme": names[theme_id]}
        for source in ["term list", "retrieval only"]:
            fit = precision.get(("sum", source), pd.Series(dtype=int)).get(theme_id, 0)
            n = precision.get(("count", source), pd.Series(dtype=int)).get(theme_id, 0)
            row[source] = f"{fit} of {n}" if n else "-"
        rows.append(row)
    per_theme = pd.DataFrame(rows)

    untagged = table[table["source"] == "no theme"].copy()
    untagged["label"] = pd.to_numeric(answer[untagged.index], errors="coerce")
    untagged = untagged.dropna(subset=["label"])
    missed = untagged[untagged["label"] > 0]

    overall = pd.DataFrame([
        {"emails": source, "judged": int((tagged["source"] == source).sum()),
         "about the theme": tagged.loc[tagged["source"] == source, "fit"].mean()}
        for source in ["term list", "retrieval only"]])
    lines = [f"# Hand check of the email themes ({args.labels.name})", "",
             md_table(overall, 2), "", "Per theme (emails about the theme, of those judged):", "",
             md_table(per_theme), "",
             f"Emails with no theme from either method: {len(missed)} of {len(untagged)} are about a "
             f"theme after all" + (f" ({', '.join(str(int(t)) for t in missed['label'])})." if len(missed) else ".")]
    (OUT / "hand_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(overall.round(2).to_string(index=False))
    print(per_theme.to_string(index=False))
    print(f"Missed: {len(missed)} of {len(untagged)} emails without a theme")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/hand_check.md")


if __name__ == "__main__":
    main()
