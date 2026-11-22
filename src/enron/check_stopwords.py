"""Show the stopwords in use and the most frequent words that are left after them.

Builds the two stopword sets exactly as the analyses do:
  Congress texts: spaCy's English list + PROCEDURE_WORDS + speakers' surnames
                  (as in run_congress_text)
  emails:         spaCy's English list + PROCEDURE_WORDS + EMAIL_WORDS + the names of
                  the people in the database (as in run_email_themes)
then lemmatises both texts and lists the words left, most frequent first, with the
share of texts that use each word. Words that say nothing about the subject near the
top of these lists are candidates for the stopword lists.

Usage (from the project root, after run_congress_text and run_email_themes):
    uv run python -m enron.check_stopwords
    uv run python -m enron.check_stopwords --top 300

Output: results/stopwords/
    stopwords_congress.txt, stopwords_emails.txt   the extra stopwords, one per line
    remaining_words.csv                            word, text, count, share of texts (%), flag
"""

import argparse
from collections import Counter

import pandas as pd

from enron import congress_text as ct
from enron.emails import prepare_emails
from enron.loaders import load_congress_paragraphs, load_emails, load_mentioned_names, load_people
from enron.paths import PROJECT_ROOT, RESULTS_DIR
from enron.run_email_themes import EMAIL_WORDS, people_names
from enron.text import lemmatise, load_nlp

OUT = RESULTS_DIR / "stopwords"
# Words that are often noise in a word list: days, months and short first names
DATE_WORDS = frozenset("""
monday tuesday wednesday thursday friday saturday sunday january february march april may
june july august september october november december
""".split())
NICKNAMES = frozenset("steve bob tim jim mike tom dan bill joe chris kim greg jeff".split())


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=150, help="words listed per text (default 150)")
    return ap.parse_args()


def remaining(tokens, top: int) -> pd.DataFrame:
    counts = Counter(t for ts in tokens for t in ts)
    in_texts = Counter(t for ts in tokens for t in set(ts))
    rows = [{"word": w, "count": n, "share of texts (%)": round(100 * in_texts[w] / len(tokens), 1)}
            for w, n in counts.most_common(top)]
    table = pd.DataFrame(rows)
    table["flag"] = ""
    table.loc[table["share of texts (%)"] > 50, "flag"] = "in over half the texts"
    table.loc[table["word"].isin(DATE_WORDS), "flag"] = "day or month"
    table.loc[table["word"].isin(NICKNAMES), "flag"] = "first name"
    return table


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    nlp = load_nlp()

    paragraphs = ct.strip_speaker_labels(ct.clean_paragraphs(load_congress_paragraphs()))
    surnames = ct.name_stopwords(paragraphs, load_mentioned_names() + ct.DISCUSSED_OUTSIDERS)
    congress_stop = ct.PROCEDURE_WORDS | surnames
    passages = ct.build_passages(paragraphs)

    emails, _ = prepare_emails(load_emails())
    emails = emails[~emails["press"]]
    names = people_names(load_people())
    email_stop = ct.PROCEDURE_WORDS | EMAIL_WORDS | names

    print(f"spaCy stopwords: {len(nlp.Defaults.stop_words)}")
    print(f"Congress extra stopwords: {len(congress_stop)} "
          f"(procedure words {len(ct.PROCEDURE_WORDS)}, speakers' surnames {len(surnames)})")
    print(f"Email extra stopwords: {len(email_stop)} (procedure words {len(ct.PROCEDURE_WORDS)}, "
          f"email words {len(EMAIL_WORDS)}, people's names {len(names)})")
    (OUT / "stopwords_congress.txt").write_text("\n".join(sorted(congress_stop)) + "\n", encoding="utf-8")
    (OUT / "stopwords_emails.txt").write_text("\n".join(sorted(email_stop)) + "\n", encoding="utf-8")

    print(f"Lemmatising {len(passages):,} Congress passages and {len(emails):,} emails ...")
    tables = []
    for name, texts, stop in [("Congress", passages["text"], congress_stop),
                              ("emails", emails["text"], email_stop)]:
        table = remaining(lemmatise(texts.tolist(), nlp, stop), args.top)
        table.insert(1, "text", name)
        tables.append(table)
        print(f"\nMost frequent words left in the {name} (share of texts in brackets):")
        print(" ".join(f"{w}({s:.0f}%)" for w, s in zip(table["word"].head(80), table["share of texts (%)"])))
        flagged = table[table["flag"] != ""]
        if len(flagged):
            print("Flagged: " + ", ".join(f"{w} ({f})" for w, f in zip(flagged["word"], flagged["flag"])))
    pd.concat(tables).to_csv(OUT / "remaining_words.csv", index=False)
    print(f"\nWrote {OUT.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
