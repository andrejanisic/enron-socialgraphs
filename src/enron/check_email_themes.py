"""Score the hand check of the email themes.

Reads data/hand_check_emails.csv (a copy of results/email_themes/hand_check_template.csv
with `about_theme` filled in) and results/email_themes/hand_check_key.csv (which
method chose each email). Rows naming a theme are answered yes or no; rows asking
about any theme are answered with a theme number, or 0 for none.

Reports, per theme, how many emails chosen by the term list and by retrieval alone
are really about the theme (precision), and the share of emails with no theme that
are about one after all (missed). Emails the term list chose when the sample was
drawn but that the current data/themes.csv no longer tags are left out and listed.

Usage (from the project root, after `uv run python -m enron.run_email_themes`):
    uv run python -m enron.check_email_themes
    uv run python -m enron.check_email_themes --labels data/hand_check_retrieval.csv \
        --key results/email_themes/hand_check_retrieval_key.csv

Output: results/email_themes/hand_check.md (or <labels file name>.md for other labels)
"""

import argparse
import math
from pathlib import Path

import pandas as pd

from enron import themes as th
from enron.paths import DATA_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.reporting import md_table

OUT = RESULTS_DIR / "email_themes"


# Sources as the keys name them; "retrieval only" keys come from the earlier TF-IDF retrieval
SOURCE_NAMES = {"retrieval only": "TF-IDF retrieval only (earlier method)"}
NO_THEME = "no theme"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, default=DATA_DIR / "hand_check_emails.csv",
                    help="filled-in template (default data/hand_check_emails.csv)")
    ap.add_argument("--key", type=Path, default=OUT / "hand_check_key.csv",
                    help="the key that belongs to the template (default results/email_themes/hand_check_key.csv)")
    return ap.parse_args()


def wilson(k: int, n: int, z: float = 1.96) -> str:
    """95% Wilson interval for k of n, as text."""
    if not n:
        return "-"
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return f"{max(0, centre - half):.2f}-{min(1, centre + half):.2f}"


def main():
    args = parse_args()
    judged = pd.read_csv(args.labels, dtype={"about_theme": str})
    key = pd.read_csv(args.key)
    key["source"] = key["source"].replace(SOURCE_NAMES)
    table = judged[["item", "about_theme", "text"]].merge(key, on="item")
    answer = table["about_theme"].fillna("").str.strip().str.lower()
    themes = th.load_themes(DATA_DIR / "themes.csv")
    names = th.theme_names(themes)

    # The sample was drawn with an earlier term list: emails it chose that the
    # current term list no longer tags say nothing about the current list's precision
    current = th.tag_terms(table["text"].fillna(""), themes)
    still = [bool(current.at[i, t]) if t in current.columns else False
             for i, t in zip(table.index, table["theme_id"])]
    dropped = table[(table["source"] == "term list") & ~pd.Series(still, index=table.index)]
    table = table.drop(dropped.index)

    tagged = table[table["source"] != NO_THEME].copy()
    tagged["fit"] = answer[tagged.index].map({"yes": 1, "y": 1, "no": 0, "n": 0})
    tagged = tagged.dropna(subset=["fit"])
    sources = [s for s in ["term list"] if s in set(tagged["source"])] + \
              sorted(set(tagged["source"]) - {"term list"})
    precision = (tagged.pivot_table(index="theme_id", columns="source", values="fit", aggfunc=["sum", "count"])
                 .fillna(0).astype(int))
    rows = []
    for theme_id in names.index:
        row = {"theme": names[theme_id]}
        for source in sources:
            fit = precision.get(("sum", source), pd.Series(dtype=int)).get(theme_id, 0)
            n = precision.get(("count", source), pd.Series(dtype=int)).get(theme_id, 0)
            row[source] = f"{fit} of {n}" if n else "-"
        rows.append(row)
    per_theme = pd.DataFrame(rows)

    untagged = table[table["source"] == NO_THEME].copy()
    untagged["label"] = pd.to_numeric(answer[untagged.index], errors="coerce")
    untagged = untagged.dropna(subset=["label"])
    missed = untagged[untagged["label"] > 0]

    overall = []
    for source in sources:
        fits = tagged.loc[tagged["source"] == source, "fit"]
        overall.append({"emails": source, "judged": len(fits), "about the theme": fits.mean(),
                        "95% interval": wilson(int(fits.sum()), len(fits))})
    overall = pd.DataFrame(overall)
    lines = [f"# Hand check of the email themes ({args.labels.name}, key {args.key.name})", "",
             md_table(overall, 2), "", "Per theme (emails about the theme, of those judged):", "",
             md_table(per_theme), ""]
    if len(untagged):
        lines += [f"Emails with no theme from either method: {len(missed)} of {len(untagged)} are about "
                  f"a theme after all" + (f" ({', '.join(str(int(t)) for t in missed['label'])})."
                                          if len(missed) else "."), ""]
    if len(dropped):
        lines.append(f"Left out: {len(dropped)} emails chosen by an earlier term list that the current "
                     f"term list no longer tags (items {', '.join(map(str, dropped['item']))}).")
    out = OUT / ("hand_check.md" if args.labels.name == "hand_check_emails.csv" else f"{args.labels.stem}.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(overall.round(2).to_string(index=False))
    print(per_theme.to_string(index=False))
    if len(untagged):
        print(f"Missed: {len(missed)} of {len(untagged)} emails without a theme")
    if len(dropped):
        print(f"Left out: {len(dropped)} term-list emails no longer tagged by the current term list")
    print(f"Wrote {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
