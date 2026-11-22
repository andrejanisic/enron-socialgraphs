"""Phases A-D: the emails against the Congress themes.

Steps:
  A. prepare the emails: human-written only, the sender's own words (forwarded and
     quoted messages cut), repeated signature lines dropped, one copy of duplicates
  B. load the theme list (data/themes.csv): 8 themes taken from the Congress topics
  C. Congress against email language: word rates per 10,000 words in each (as
     Scattertext plots them) and theme coverage in both texts
  D. tag each email with themes by two methods: the term lists, and retrieval
     (sentence embeddings of ~180-word chunks, averaged per email, compared with each
     theme's Congress passages; an email is tagged when it is among the 1% of emails
     most similar to the theme, the theme is its most similar one, and it holds none
     of the theme's exclude terms). Measure how far they agree and write samples of
     emails to judge by hand

Usage (from the project root, after `uv run python -m enron.run_congress_text`):
    uv run python -m enron.run_email_themes
    uv run python -m enron.run_email_themes --threshold 0.9
    uv run python -m enron.run_email_themes --percentile 99.5 --model sentence-transformers/all-MiniLM-L6-v2

The first run downloads the embedding model and embeds all texts (minutes); the
embeddings are kept in results/email_themes/embeddings/, so later runs take seconds.

Pasted news articles (bylines, news agencies) are set aside and counted separately.

Outputs: results/email_themes/ (summary.md + CSV tables, theme_table.csv for the
paper) and figures/ (.png): fig_theme_coverage (main), fig_si_word_comparison
(supplement: typical words).

Two hand checks: hand_check_template.csv (term list, retrieval and untagged emails)
and hand_check_retrieval_template.csv (emails only the embedding retrieval tags). Once
their filled-in copies in data/ (hand_check_emails.csv, hand_check_retrieval.csv) hold
answers, the key and template are kept as they are, so the answers keep matching them
(--new-hand-check and --new-retrieval-check draw new samples).
"""

import argparse

import numpy as np
import pandas as pd

from enron import embeddings as emb
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
RETRIEVAL_LABELS = DATA_DIR / "hand_check_retrieval.csv"   # the filled-in retrieval check
MIN_RETRIEVAL_WORDS = 30      # shorter emails are not scored: too little text to place
SENSITIVITY = (98, 99.5)      # other percentiles reported for the thresholds
# Short theme names for the figures
SHORT_NAMES = {1: "LJM partnerships", 2: "SPEs and Raptors", 3: "Andersen and audits",
               4: "Board and pay", 5: "Retirement savings", 6: "Analysts and ratings",
               7: "Bankruptcy and layoffs", 8: "Energy trading"}


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=0.8,
                    help="lowest human_probability kept for emails marked uncertain (default 0.8)")
    ap.add_argument("--model", default=emb.DEFAULT_MODEL,
                    help=f"sentence-transformers model for retrieval (default {emb.DEFAULT_MODEL})")
    ap.add_argument("--percentile", type=float, default=99,
                    help="threshold per theme: the similarity this share (%%) of the emails stays "
                         "below (default 99, i.e. the top 1%%)")
    ap.add_argument("--new-hand-check", action="store_true",
                    help="draw a new hand-check sample even though data/hand_check_emails.csv "
                         "already holds answers (they would no longer match the key)")
    ap.add_argument("--new-retrieval-check", action="store_true",
                    help="draw a new retrieval-check sample even though data/hand_check_retrieval.csv "
                         "already holds answers")
    return ap.parse_args()


def labels_started(path=LABELS) -> bool:
    """True when the filled-in hand check exists and holds at least one answer."""
    if not path.exists():
        return False
    answers = pd.read_csv(path, dtype={"about_theme": str})["about_theme"]
    return bool(answers.fillna("").str.strip().ne("").any())


def write_check(sample, emails, names, key_path, template_path) -> None:
    """The key (which method chose each email) and the template to fill in (without it)."""
    sample = sample.copy()
    sample["email_id"] = emails["email_id"].iloc[sample["row"]].to_numpy()
    sample[["item", "theme_id", "email_id", "source"]].to_csv(key_path, index=False)
    question = sample["theme_id"].map(names).fillna("Any of the 8 themes? Write its number, or 0")
    pd.DataFrame({"item": sample["item"], "theme_id": sample["theme_id"].replace(0, ""),
                  "theme": question, "about_theme": "",
                  "text": emails["text"].iloc[sample["row"]].str[:1500].to_numpy()}) \
        .to_csv(template_path, index=False)


def retrieval(emails, passages, themes, term_tags, args):
    """Embedding similarity of every email to every theme, the thresholds, and the
    emails tagged. Returns (similarity, tags, table of thresholds and counts)."""
    model, cache = emb.LazyModel(args.model), OUT / "embeddings"
    p_vec, p_owner = emb.embed_chunks(passages["text"], cache, "Congress passages", args.model, model=model)
    profiles = th.theme_profiles(emb.text_vectors(p_vec, p_owner, len(passages)), passages["lda_topic"], themes)
    P = profiles.to_numpy()

    scored = (emails["n_words"] >= MIN_RETRIEVAL_WORDS).to_numpy()
    e_vec, e_owner = emb.embed_chunks(emails.loc[scored, "text"], cache, "emails", args.model, model=model)
    similarity = pd.DataFrame(0.0, index=emails.index, columns=profiles.index)
    similarity.loc[scored] = emb.mean_similarity(e_vec, e_owner, int(scored.sum()), P)

    excluded = th.has_exclude_terms(emails["text"], themes)
    thresholds = {p: th.email_thresholds(similarity, scored, p) for p in sorted({args.percentile, *SENSITIVITY})}
    tags = {p: th.retrieval_tags(similarity, t, excluded, emails["n_words"], MIN_RETRIEVAL_WORDS)
            for p, t in thresholds.items()}
    main = tags[args.percentile]
    above = similarity.ge(thresholds[args.percentile]) & scored[:, None]
    best = similarity.idxmax(axis=1).to_numpy()[:, None] == similarity.columns.to_numpy()[None, :]
    topics = np.asarray(passages["lda_topic"])
    table = pd.DataFrame({
        "theme": th.theme_names(themes),
        "Congress passages of the theme": [int(np.isin(topics, w).sum()) for w in th.theme_topics(themes).values()],
        "threshold (similarity)": thresholds[args.percentile].round(3),
        "emails at or above it": above.sum(),
        "of these, theme is the best match": (above & best).sum(),
        "emails tagged": main.sum(),
        "also tagged by the term list": (main & term_tags.to_numpy()).sum(),
        **{f"emails tagged at {p:g}th percentile": tags[p].sum() for p in SENSITIVITY if p != args.percentile},
    })
    return similarity, main, table


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


def write_summary(steps, coverage, agreement, thresholds, words, n_hand, args) -> None:
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
        "Method 1, term list: the theme's terms (one name term, or two general terms, and no "
        "exclude term). Method 2, retrieval: each text is split into chunks of about 180 words "
        f"of equal size and embedded with `{args.model}`; an email's similarity to a theme is the "
        "average cosine similarity of its chunks to the theme's profile (the mean embedding of "
        "the Congress passages whose main LDA topic belongs to the theme). An email is tagged "
        f"when it is among the {100 - args.percentile:g}% of emails most similar to the theme, the theme "
        "is the one it is most similar to, it has at least "
        f"{MIN_RETRIEVAL_WORDS} words and it holds none of the theme's exclude terms. The threshold is "
        "set among the emails because emails and hearings are written so differently that even "
        "off-topic Congress passages are more similar to a theme than almost any email. A theme can "
        "get no emails. Thresholds and counts (other percentiles as a sensitivity check):", "",
        md_table(thresholds, 3), "",
        "How far the two methods pick the same emails. With fewer than about 10 tagged emails, "
        "overlap and kappa rest on a handful of emails and say little.", "",
        md_table(agreement, 2), "",
        "## Hand checks", "",
        f"`hand_check_template.csv` holds {n_hand} emails (term list, retrieval only, no theme). "
        "Copy it to `data/hand_check_emails.csv`, fill in `about_theme` (yes/no; for rows asking "
        "about any theme, the theme number or 0), then run "
        "`uv run python -m enron.check_email_themes`.", "",
        "`hand_check_retrieval_template.csv` holds the emails only the embedding retrieval tags "
        "(up to 4 per theme). Copy it to `data/hand_check_retrieval.csv`, fill in `about_theme` "
        "(yes/no), then run `uv run python -m enron.check_email_themes --labels "
        "data/hand_check_retrieval.csv --key results/email_themes/hand_check_retrieval_key.csv`.", "",
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

    # D. two tagging methods and the hand-check samples
    print(f"Retrieval with sentence embeddings ({args.model}) ...", flush=True)
    similarity, retrieval_tags, thresholds = retrieval(emails, passages, themes, term_tags, args)
    thresholds.to_csv(OUT / "retrieval_thresholds.csv", index=False)
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
    sample["source"] = sample["source"].replace({"retrieval only": "embedding retrieval only"})
    if labels_started(LABELS) and (OUT / "hand_check_key.csv").exists() and not args.new_hand_check:
        print(f"\nKept the hand-check key and template: {LABELS.relative_to(PROJECT_ROOT)} already "
              "holds answers for them (use --new-hand-check for a new sample).")
    else:
        write_check(sample, emails, names, OUT / "hand_check_key.csv", OUT / "hand_check_template.csv")
    # the retrieval check: emails only the embedding retrieval tags, up to 4 per theme
    r_sample = th.hand_check_sample(term_tags, retrieval_tags, n_terms=0, n_retrieval=4, n_none=0, seed=2027)
    r_sample["source"] = "embedding retrieval only"
    if (labels_started(RETRIEVAL_LABELS) and (OUT / "hand_check_retrieval_key.csv").exists()
            and not args.new_retrieval_check):
        print(f"Kept the retrieval-check key and template: {RETRIEVAL_LABELS.relative_to(PROJECT_ROOT)} "
              "already holds answers (use --new-retrieval-check for a new sample).")
    else:
        write_check(r_sample, emails, names, OUT / "hand_check_retrieval_key.csv",
                    OUT / "hand_check_retrieval_template.csv")

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
    n_hand = len(pd.read_csv(OUT / "hand_check_key.csv"))     # the key in use (kept or new)
    write_summary(steps, coverage, agreement, thresholds, words, n_hand, args)
    print("\nRetrieval thresholds and emails tagged (columns = theme number):")
    print(thresholds.drop(columns="theme").set_axis(range(1, len(thresholds) + 1)).astype(object).T.to_string())
    print("\nTwo tagging methods (columns = theme number, as in the table above):")
    print(agreement.drop(columns="theme").set_axis(range(1, len(agreement) + 1)).round(2).T.to_string())
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_theme_coverage, fig_si_word_comparison")


if __name__ == "__main__":
    main()
