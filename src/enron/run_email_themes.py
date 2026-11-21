"""Phases A-D: the emails against the Congress themes.

Steps:
  A. prepare the emails: human-written only, the sender's own words (forwarded and
     quoted messages cut), repeated signature lines dropped, one copy of duplicates
  B. load the theme list (data/themes.csv): 8 themes taken from the Congress topics
  C. Congress against email language: word rates per 10,000 words in each (as
     Scattertext plots them) and theme coverage in both texts
  D. tag each email with themes by two methods (term lists, and TF-IDF similarity
     to each theme's Congress passages), measure how far they agree, and write a
     sample of emails to judge by hand

Usage (from the project root, after `uv run python -m enron.run_congress_text`):
    uv run python -m enron.run_email_themes
    uv run python -m enron.run_email_themes --threshold 0.9

Pasted news articles (bylines, news agencies) are set aside and counted separately.

Outputs: results/email_themes/ (summary.md + CSV tables, theme_table.csv for the
paper) and figures/ (.png): fig_theme_coverage (main), fig_si_word_comparison
(supplement: typical words).

Once data/hand_check_emails.csv holds answers, the hand-check key and template are
kept as they are, so the answers keep matching them (--new-hand-check draws a new sample).
"""

import argparse

import pandas as pd

from enron import themes as th
from enron.congress_text import PROCEDURE_WORDS
from enron.emails import prepare_emails
from enron.loaders import load_emails, load_people
from enron.paths import DATA_DIR, FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import plot_theme_coverage, plot_typical_words
from enron.reporting import md_table
from enron.text import compare_rates, join_phrases, lemmatise, load_nlp, term_rates, written_forms

OUT = RESULTS_DIR / "email_themes"
PASSAGES = RESULTS_DIR / "congress_text" / "passages.csv"
THEMES = DATA_DIR / "themes.csv"
# Email words that say nothing about the subject
EMAIL_WORDS = frozenset("""
enron ena ect hou com corp cc fw fwd fyi re subject email mail message attach attached please
thanks info regards hi hello pm am week day tomorrow call need let know get like want go think look
""".split())
# Two-word names counted as one word
PHRASES = [("el", "paso"), ("san", "juan"), ("wall", "street")]
GLOSSARY = DATA_DIR / "glossary.csv"        # term, written (optional), meaning: explains figure terms
N_WORDS, MIN_COUNT = 15, 30       # typical-words figure
LABELS = DATA_DIR / "hand_check_emails.csv"   # the filled-in hand check
# Short theme names for the figure
SHORT_NAMES = {1: "Partnerships (LJM, Fastow)", 2: "Special purpose entities",
               3: "Andersen and the auditing", 4: "Board and executive pay",
               5: "Employees' stock and 401(k)", 6: "Analysts and rating agencies",
               7: "Collapse and layoffs", 8: "Energy markets and trading"}


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=0.8,
                    help="lowest human_probability kept for emails marked uncertain (default 0.8)")
    ap.add_argument("--new-hand-check", action="store_true",
                    help="draw a new hand-check sample even though data/hand_check_emails.csv "
                         "already holds answers (they would no longer match the key)")
    return ap.parse_args()


def labels_started() -> bool:
    """True when data/hand_check_emails.csv exists and holds at least one answer."""
    if not LABELS.exists():
        return False
    answers = pd.read_csv(LABELS, dtype={"about_theme": str})["about_theme"]
    return bool(answers.fillna("").str.strip().ne("").any())


def theme_table(coverage: pd.DataFrame) -> pd.DataFrame:
    """The table for the paper: per theme, shares of texts, rates per 10,000 words,
    how many times more often Congress uses the terms, and emails tagged."""
    return pd.DataFrame({
        "theme": coverage["theme"],
        "Congress passages with theme (%)": coverage["Congress texts with theme (%)"].round(1),
        "emails with theme (%)": coverage["emails with theme (%)"].round(2),
        "Congress terms per 10k words": coverage["Congress terms per 10k words"].round(1),
        "email terms per 10k words": coverage["email terms per 10k words"].round(2),
        "Congress / emails": (coverage["Congress terms per 10k words"]
                              / coverage["email terms per 10k words"]).round(1),
        "emails tagged": coverage["emails with theme"],
    })


def people_names(people: pd.DataFrame) -> frozenset:
    """First and last names of the 148 people, so names do not dominate word lists."""
    parts = " ".join(people["full_name"].dropna()).lower().replace(".", " ").split()
    return frozenset(p for p in parts if len(p) > 2)


def typical_words(words: pd.DataFrame) -> list:
    """The words the typical-words figure shows (same selection as the plot)."""
    congress = words[words["count_a"] >= MIN_COUNT].head(N_WORDS)
    emails = words[words["count_b"] >= MIN_COUNT].tail(N_WORDS)
    return list(congress["word"]) + list(emails["word"])


def reading_sample(raw: pd.DataFrame, clean: pd.DataFrame, n: int = 30) -> str:
    """Cleaned emails next to their original bodies, for checking the preparation by eye."""
    lines = ["# Cleaned emails next to the originals", ""]
    sample = clean.sample(n, random_state=2026)
    originals = raw.set_index("email_id")["body_raw"]
    for row in sample.itertuples():
        lines += [f"## Email {row.email_id}", "", "Kept:", "", "```", row.text[:800], "```", "",
                  "Original:", "", "```", (originals[row.email_id] or "")[:1500], "```", ""]
    return "\n".join(lines)


def write_summary(steps, coverage, agreement, words, n_hand, args) -> None:
    lines = [
        "# The emails against the Congress themes", "",
        "## A. Preparing the emails", "", md_table(steps), "",
        "Thirty cleaned emails next to their originals: `cleaning_check.md`.", "",
        "## C. Theme coverage", "",
        "Share of texts with the theme (one name term or two general terms), and theme terms "
        "per 10,000 words (independent of text length). Congress texts = passages of about "
        "180 words; emails = the sender's own words, without pasted news articles. "
        "'incl. forwarded text' also counts forwarded and quoted text (what people passed on "
        "or replied to); 'pasted articles' counts the news articles set aside "
        "(`press_emails.csv`).", "",
        md_table(coverage, 2), "",
        "`theme_table.csv` holds the same numbers rounded for the paper; `Congress / emails` "
        "is how many times more often Congress uses the theme's terms.", "",
        "Words most typical of each side (rates per 10,000 words):", "",
        "Congress: " + ", ".join(words.head(20)["word"]), "",
        "Emails: " + ", ".join(words.tail(20)["word"][::-1]), "",
        "## D. Two methods for tagging emails", "",
        "Method 1, term list: the theme's terms (one name term, or two general terms). "
        "Method 2, similarity: the emails whose words are most similar (TF-IDF) to the theme's "
        "Congress passages (emails of at least 30 words); it tags as many emails as the term "
        "list, and at least 10, so the "
        "question is whether the two pick the same emails. With fewer than about 10 tagged "
        "emails, overlap and kappa rest on a handful of emails and say little.", "",
        md_table(agreement, 2), "",
        "## Hand check", "",
        f"`hand_check_template.csv` holds {n_hand} emails. Copy it to "
        "`data/hand_check_emails.csv`, fill in `about_theme` (yes/no; for rows asking about any "
        "theme, the theme number or 0), then run `uv run python -m enron.check_email_themes`.", "",
        "## Figures", "",
        "- `fig_theme_coverage`: how many times more often Congress uses each theme's terms than "
        "the emails (main)",
        "- `fig_si_word_comparison`: the words most typical of each text (supplement)",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    # A. prepare the emails
    raw = load_emails()
    emails, steps = prepare_emails(raw, threshold=args.threshold)
    # pasted news articles are counted apart: passed on, not written
    press = emails[emails["press"]].reset_index(drop=True)
    emails = emails[~emails["press"]].reset_index(drop=True)
    # exposure: the same emails with forwarded and quoted text kept
    full_text = emails["body_clean"].fillna("")     # forwarded text kept, headers removed
    steps.to_csv(OUT / "preparation_steps.csv", index=False)
    (OUT / "cleaning_check.md").write_text(reading_sample(raw, emails), encoding="utf-8")
    print(steps.to_string(index=False))

    # B. the theme list
    themes = th.load_themes(THEMES)
    names = th.theme_names(themes)

    # lemmas for both texts, with the same stopwords
    passages = pd.read_csv(PASSAGES)
    stop = PROCEDURE_WORDS | EMAIL_WORDS | people_names(load_people())
    nlp = load_nlp()
    print(f"Lemmatising {len(emails):,} emails and {len(passages):,} Congress passages ...")
    email_tokens = join_phrases(lemmatise(emails["text"].tolist(), nlp, stop), PHRASES)
    passage_tokens = join_phrases(lemmatise(passages["text"].tolist(), nlp, stop), PHRASES)

    # C. Congress against email language
    words = compare_rates(passage_tokens, email_tokens)
    words.to_csv(OUT / "word_comparison.csv", index=False)
    term_tags = th.tag_terms(emails["text"], themes)
    congress_tags = th.tag_terms(passages["text"], themes)
    coverage = pd.DataFrame({
        "theme": names,
        "Congress texts with theme (%)": 100 * congress_tags.mean(),
        "emails with theme (%)": 100 * term_tags.mean(),
        "Congress terms per 10k words": term_rates(passages["text"], themes),
        "email terms per 10k words": term_rates(emails["text"], themes),
        "emails with theme": term_tags.sum(),
        "emails with theme incl. forwarded text": th.tag_terms(full_text, themes).sum(),
        "pasted articles with theme": th.tag_terms(press["text"], themes).sum(),
    })
    coverage.to_csv(OUT / "theme_coverage.csv", index=False)
    print(coverage.round(2).to_string(index=False))

    # D. two tagging methods and the hand-check sample
    similarity = th.theme_similarity(email_tokens, passage_tokens, passages["lda_topic"], themes,
                                     emails["n_words"])
    retrieval_tags = th.rank_matched(similarity, term_tags)
    agreement = th.method_agreement(term_tags, retrieval_tags, names)
    agreement.to_csv(OUT / "method_agreement.csv", index=False)
    tags = emails[["email_id", "sender_id", "date", "n_words"]].copy()
    for theme_id in names.index:
        tags[f"terms_{theme_id}"] = term_tags[theme_id].to_numpy()
        tags[f"retrieval_{theme_id}"] = retrieval_tags[theme_id].to_numpy()
        tags[f"similarity_{theme_id}"] = similarity[theme_id].round(4).to_numpy()
    tags.to_csv(OUT / "email_themes.csv", index=False)
    emails[["email_id", "sender_id", "date", "n_words", "text"]].to_csv(OUT / "emails_clean.csv", index=False)
    press_tags = th.tag_terms(press["text"], themes).set_axis([f"terms_{i}" for i in names.index], axis=1)
    pd.concat([press[["email_id", "sender_id", "date", "n_words"]], press_tags.astype(int)], axis=1) \
        .to_csv(OUT / "press_emails.csv", index=False)

    sample = th.hand_check_sample(term_tags, retrieval_tags)
    keep_key = labels_started() and (OUT / "hand_check_key.csv").exists() and not args.new_hand_check
    if keep_key:
        print(f"\nKept the hand-check key and template: {LABELS.relative_to(PROJECT_ROOT)} already "
              "holds answers for them (use --new-hand-check for a new sample).")
    else:
        sample["email_id"] = emails["email_id"].iloc[sample["row"]].to_numpy()
        sample[["item", "theme_id", "email_id", "source"]].to_csv(OUT / "hand_check_key.csv", index=False)
        question = sample["theme_id"].map(names).fillna("Any of the 8 themes? Write its number, or 0")
        pd.DataFrame({"item": sample["item"], "theme_id": sample["theme_id"].replace(0, ""),
                      "theme": question, "about_theme": "",
                      "text": emails["text"].iloc[sample["row"]].str[:1500].to_numpy()}) \
            .to_csv(OUT / "hand_check_template.csv", index=False)

    table = theme_table(coverage)
    table.to_csv(OUT / "theme_table.csv", index=False)
    plot_theme_coverage(pd.DataFrame({
        "congress": coverage["Congress terms per 10k words"].to_numpy(),
        "emails": coverage["email terms per 10k words"].to_numpy(),
        "n_emails": coverage["emails with theme"].to_numpy()},
        index=[SHORT_NAMES.get(i, n) for i, n in names.items()]), FIGURES_DIR / "fig_theme_coverage")
    shown = typical_words(words)
    forms = written_forms(list(emails["text"]) + list(passages["text"]), shown)
    glossary = {}
    if GLOSSARY.exists():
        entries = pd.read_csv(GLOSSARY).set_index("term")
        glossary = entries["meaning"].to_dict()
        forms.update(entries["written"].dropna().to_dict())   # spellings set by hand win
    plot_typical_words(words, N_WORDS, MIN_COUNT, forms, glossary, FIGURES_DIR / "fig_si_word_comparison")
    write_summary(steps, coverage, agreement, words, len(sample), args)
    print("\nTwo tagging methods (columns = theme number, as in the table above):")
    print(agreement.drop(columns="theme").set_axis(range(1, len(agreement) + 1)).round(2).T.to_string())
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_theme_coverage, fig_si_word_comparison")


if __name__ == "__main__":
    main()
