"""What the Congress documents say: words, phrases and topics (steps 1-5 of the plan).

Steps:
  1. prepare: drop front matter, contents pages, headings and image placeholders;
     remove the speaker's name that opens each turn; lemmas with spaCy, without
     stopwords, hearing-procedure words and the surnames of speakers (except
     people the documents investigate); passages of about 180 words
  2. vocabulary: token and type counts, top words, Zipf plot
  3. phrases: bigram and trigram collocations (likelihood ratio, PMI), with
     concordance lines to read each in context
  4. fingerprints: TF-IDF per document and per main speaker
  5. topics: LDA (word counts) and NMF (TF-IDF) on the passages; stability across
     seeds, agreement between the two, topic shares per document; for the
     hand check, 3 passages per topic to judge yes/no (topic_fit_template.csv)

Usage (from the project root, after `uv run python -m enron.add_congress_texts`):
    uv run python -m enron.run_congress_text
    uv run python -m enron.run_congress_text --topics 10 --choose-k

Outputs: results/congress_text/ (summary.md + CSV tables) and figures/ (.png):
supplement: fig_si_zipf, fig_si_congress_topics
"""

import argparse
import re

import numpy as np
import pandas as pd
from sklearn.metrics import normalized_mutual_info_score

from enron import congress_text as ct
from enron.loaders import load_congress_paragraphs, load_mentioned_names
from enron.paths import DATA_DIR, FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR
from enron.plots import plot_topics_by_document, plot_zipf
from enron.reporting import md_table
from enron.text import (collocations, concordance, lemmatise, load_nlp, tfidf_fingerprints,
                        vocabulary, zipf_slope)

OUT = RESULTS_DIR / "congress_text"
TOPIC_NAMES = DATA_DIR / "topic_names_congress.csv"   # optional: topic, name (written by hand)
K_GRID = [6, 8, 10, 12, 15]
MIN_SPEAKER_TOKENS = 1500     # speakers with fewer content words get no fingerprint
HAND_LABEL_SAMPLE = 50


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topics", type=int, default=10, help="number of topics (default 10)")
    ap.add_argument("--seeds", type=int, default=3, help="runs per method for stability (default 3)")
    ap.add_argument("--choose-k", action="store_true",
                    help=f"also compare stability for {K_GRID} topics (a few more minutes)")
    return ap.parse_args()


def topic_choice(C, T, seeds) -> pd.DataFrame:
    rows = []
    for k in K_GRID:
        W_lda, _ = ct.fit_topics("lda", C, k, seeds[0])
        W_nmf, _ = ct.fit_topics("nmf", T, k, seeds[0])
        rows.append({"topics": k, "LDA stability": ct.stability("lda", C, k, seeds),
                     "NMF stability": ct.stability("nmf", T, k, seeds),
                     "LDA vs NMF": normalized_mutual_info_score(W_lda.argmax(1), W_nmf.argmax(1))})
        print(f"  {k} topics done")
    return pd.DataFrame(rows)


def write_fit_check(W, passages: pd.DataFrame, topics: pd.DataFrame) -> None:
    """The yes/no hand check: a key (which passage, strongest or random) and a template
    without it, so the judge cannot tell the easy cases from the random ones."""
    sample = ct.fit_check_sample(W)
    sample["passage_id"] = passages["passage_id"].iloc[sample["row"]].to_numpy()
    sample[["item", "topic", "passage_id", "kind"]].to_csv(OUT / "topic_fit_key.csv", index=False)
    names = (pd.read_csv(TOPIC_NAMES).set_index("topic")["name"] if TOPIC_NAMES.exists()
             else pd.Series(dtype=str))
    words = topics.set_index("topic")["top_words"]
    # `fits` before the long text, so spreadsheet programs do not hide it under the passage
    template = pd.DataFrame({
        "item": sample["item"], "topic": sample["topic"],
        "topic_name": sample["topic"].map(names).fillna(""), "fits": "",
        "top_words": sample["topic"].map(words),
        "text": passages["text"].iloc[sample["row"]].to_numpy()})
    template.to_csv(OUT / "topic_fit_template.csv", index=False)


def write_summary(stats, slope, words, bigrams, trigrams, choice, checks, lda_table, nmf_table,
                  match, args) -> None:
    lines = [
        "# What the Congress documents say", "",
        f"{stats['paragraphs']:,} paragraphs kept of {stats['paragraphs_all']:,}; "
        f"{stats['passages']:,} passages of about 180 words.", "",
        "## Vocabulary", "",
        f"{stats['tokens']:,} content words (lemmas, stopwords removed), {stats['types']:,} distinct, "
        f"{stats['hapax']:,} used once. Zipf slope over all words: {slope:.2f}.", "",
        md_table(words.head(30).reset_index()[["rank", "word", "count", "per_10k"]], 1), "",
        "## Phrases (collocations)", "", "Bigrams:", "", md_table(bigrams.head(25), 1), "",
        "Trigrams:", "", md_table(trigrams.head(15), 1), "",
        "Concordance lines for the top phrases: `concordance.md`.", "",
        "## Fingerprints", "",
        "Top TF-IDF words per document: `fingerprints_documents.csv`; per main speaker: "
        "`fingerprints_speakers.csv`.", "",
        f"## Topics ({args.topics})", "",
        f"Stability = mean NMI between passages' main topic over {args.seeds} seeds.", "",
        md_table(checks, 2), "",
    ]
    if choice is not None:
        lines += ["Choosing the number of topics:", "", md_table(choice, 2), ""]
    lines += ["LDA topics:", "", md_table(lda_table, 3), "",
              "NMF topics:", "", md_table(nmf_table, 3), "",
              "Matching LDA topic to the NMF topic its passages most often have:", "",
              md_table(match), "",
              "## Next", "",
              f"`hand_labels_template.csv` holds {HAND_LABEL_SAMPLE} random passages. Label each with "
              "the topic it is about (from the topic tables, without looking at the model's choice), "
              "then compare with `passages.csv`.", "",
              "## Figures", "",
              "- `fig_si_zipf`: rank-frequency plot of all words (supplement)",
              "- `fig_si_congress_topics`: topic shares per document, LDA (supplement)"]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.seeds))

    # 1. prepare
    raw = load_congress_paragraphs()
    paragraphs = ct.strip_speaker_labels(ct.clean_paragraphs(raw))
    stop = ct.PROCEDURE_WORDS | ct.name_stopwords(paragraphs, load_mentioned_names() + ct.DISCUSSED_OUTSIDERS)
    passages = ct.build_passages(paragraphs)
    nlp = load_nlp()
    print(f"Lemmatising {len(paragraphs):,} paragraphs and {len(passages):,} passages ...")
    para_tokens = lemmatise(paragraphs["text"].tolist(), nlp, stop)
    pass_tokens = lemmatise(passages["text"].tolist(), nlp, stop)

    # 2. vocabulary
    stats, words = vocabulary(para_tokens)
    stats.update(paragraphs=len(paragraphs), paragraphs_all=len(raw), passages=len(passages))
    words.head(500).to_csv(OUT / "vocabulary.csv")
    all_words = pd.Series(re.findall(r"[a-z]+", " ".join(paragraphs["text"]).lower())).value_counts()
    slope = zipf_slope(pd.DataFrame({"count": all_words.to_numpy()}, index=np.arange(1, len(all_words) + 1)))
    plot_zipf(all_words, slope, FIGURES_DIR / "fig_si_zipf")

    # 3. phrases
    bigrams = collocations(para_tokens, n=2)
    trigrams = collocations(para_tokens, n=3, min_freq=10, top=25, rank_by="count")
    bigrams.to_csv(OUT / "collocations_bigrams.csv", index=False)
    trigrams.to_csv(OUT / "collocations_trigrams.csv", index=False)
    texts = paragraphs["text"].tolist()
    kwic = ["# Concordance lines for the top phrases", ""]
    for phrase in pd.concat([bigrams.phrase.head(20), trigrams.phrase.head(10)]):
        kwic += [f"## {phrase}", "", "```", *concordance(texts, phrase, max_lines=4), "```", ""]
    (OUT / "concordance.md").write_text("\n".join(kwic), encoding="utf-8")

    # 4. fingerprints
    docs = ct.document_labels(raw)
    docs.to_csv(OUT / "documents.csv")
    labels = docs["label"].to_dict()
    by_doc = {labels[d]: sum((t for t, dd in zip(para_tokens, paragraphs.doc_id) if dd == d), [])
              for d in docs.index}
    tfidf_fingerprints(by_doc).to_csv(OUT / "fingerprints_documents.csv", index=False)
    by_speaker = {}
    for tokens, speaker in zip(para_tokens, paragraphs["speaker"]):
        if isinstance(speaker, str):
            by_speaker.setdefault(speaker, []).extend(tokens)
    by_speaker = {s: t for s, t in by_speaker.items() if len(t) >= MIN_SPEAKER_TOKENS}
    tfidf_fingerprints(by_speaker).to_csv(OUT / "fingerprints_speakers.csv", index=False)

    # 5. topics
    C, T, vocab = ct.document_term(pass_tokens)
    choice = None
    if args.choose_k:
        print("Comparing numbers of topics ...")
        choice = topic_choice(C, T, seeds)
        choice.to_csv(OUT / "topic_choice.csv", index=False)
    k = args.topics
    W_lda, H_lda = ct.fit_topics("lda", C, k, seeds[0])
    W_nmf, H_nmf = ct.fit_topics("nmf", T, k, seeds[0])
    checks = pd.DataFrame([{"LDA stability": ct.stability("lda", C, k, seeds),
                            "NMF stability": ct.stability("nmf", T, k, seeds),
                            "LDA vs NMF": normalized_mutual_info_score(W_lda.argmax(1), W_nmf.argmax(1))}])
    lda_table = ct.topic_table(W_lda, H_lda, vocab)
    nmf_table = ct.topic_table(W_nmf, H_nmf, vocab)
    match = pd.DataFrame(list(ct.match_topics(W_lda, W_nmf).items()), columns=["LDA topic", "NMF topic"])
    lda_table.to_csv(OUT / "topics_lda.csv", index=False)
    nmf_table.to_csv(OUT / "topics_nmf.csv", index=False)
    match.to_csv(OUT / "topic_match.csv", index=False)
    checks.to_csv(OUT / "topic_checks.csv", index=False)
    shares = ct.shares_by_document(W_lda, passages["doc_id"])[docs.index]   # by date
    shares.columns = [labels[d] for d in shares.columns]
    shares.to_csv(OUT / "topics_by_document.csv")
    ct.example_passages(W_lda, passages).to_csv(OUT / "topic_examples.csv", index=False)
    passages.assign(lda_topic=W_lda.argmax(1) + 1, nmf_topic=W_nmf.argmax(1) + 1) \
        .to_csv(OUT / "passages.csv", index=False)
    passages.sample(HAND_LABEL_SAMPLE, random_state=2026)[["passage_id", "doc_id", "text"]] \
        .assign(your_topic="").to_csv(OUT / "hand_labels_template.csv", index=False)
    write_fit_check(W_lda, passages, lda_table)

    names = pd.read_csv(TOPIC_NAMES).set_index("topic")["name"] if TOPIC_NAMES.exists() else {}
    topic_labels = [f"{t}. {names[t]}" if t in names else f"{t}. " + ", ".join(w.split(", ")[:3])
                    for t, w in zip(lda_table.topic, lda_table.top_words)]
    plot_topics_by_document(shares.T, list(shares.columns), topic_labels, FIGURES_DIR / "fig_si_congress_topics")

    write_summary(stats, slope, words, bigrams, trigrams, choice, checks, lda_table, nmf_table, match, args)
    print(checks.round(2).to_string(index=False))
    print(lda_table[["topic", "share", "top_words"]].to_string(index=False))
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}/ and figures/fig_si_zipf, fig_si_congress_topics")


if __name__ == "__main__":
    main()
