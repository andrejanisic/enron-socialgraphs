"""Preparing and describing text (course weeks 5 and 6).

Shared by the Congress texts and, later, the emails: tokens and lemmas with
spaCy, vocabulary and Zipf counts, collocations with NLTK, concordance lines
and TF-IDF "fingerprints".
"""

import re
from collections import Counter

import numpy as np
import pandas as pd
from nltk.collocations import (BigramAssocMeasures, BigramCollocationFinder,
                               TrigramAssocMeasures, TrigramCollocationFinder)
from sklearn.feature_extraction.text import TfidfVectorizer

# A kept token: starts with a letter, letters/digits/hyphens inside, at least 2 characters
TOKEN = re.compile(r"^[a-z][a-z0-9\-]*[a-z0-9]$")


# ------------------------------------------------------------ preparation ---
def load_nlp(entities: bool = False):
    """spaCy's small English model without the parser; the entity step (names of
    people, organisations) only when `entities` is True (not needed for lemmas)."""
    import spacy
    if entities:
        return spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    return spacy.load("en_core_web_sm", disable=["parser", "ner"])


def lemmatise(texts, nlp, extra_stopwords=frozenset(), batch_size=200) -> list[list[str]]:
    """Lowercased lemmas per text, without punctuation, numbers and stopwords
    (spaCy's list plus `extra_stopwords`)."""
    out = []
    for doc in nlp.pipe(texts, batch_size=batch_size):
        tokens = []
        for t in doc:
            if t.is_punct or t.is_space or t.is_stop or t.like_num:
                continue
            lemma = t.lemma_.lower()
            if TOKEN.match(lemma) and lemma not in extra_stopwords and not nlp.vocab[lemma].is_stop:
                tokens.append(lemma)
        out.append(tokens)
    return out


# ------------------------------------------------------------- vocabulary ---
def vocabulary(token_lists) -> tuple[dict, pd.DataFrame]:
    """Token, type and hapax counts, and every word with its count and relative frequency."""
    counts = Counter(t for tokens in token_lists for t in tokens)
    n = sum(counts.values())
    words = pd.DataFrame(counts.most_common(), columns=["word", "count"])
    words["per_10k"] = 10_000 * words["count"] / n
    words.index = np.arange(1, len(words) + 1)
    words.index.name = "rank"
    stats = {"tokens": n, "types": len(counts), "hapax": sum(c == 1 for c in counts.values())}
    return stats, words


def zipf_slope(words: pd.DataFrame, low: int = 10, high: int = 1000) -> float:
    """Slope of log(count) against log(rank) between two ranks (about -1 for Zipf's law)."""
    part = words.loc[low:high]
    return float(np.polyfit(np.log10(part.index), np.log10(part["count"]), 1)[0])


# ----------------------------------------------------------- collocations ---
def collocations(token_lists, n: int = 2, min_freq: int = 10, top: int = 40,
                 rank_by: str = "likelihood_ratio") -> pd.DataFrame:
    """Bigrams (n = 2) or trigrams (n = 3) that occur together more than chance.

    Scored by likelihood ratio (frequent, reliable pairs) and PMI (strongly tied
    pairs); phrases do not run across text boundaries. The table keeps the `top`
    phrases by `rank_by` ("likelihood_ratio", "pmi" or "count"). For trigrams,
    count ranks best: the likelihood ratio puts any word next to a strong pair
    ("arthur andersen X") at the top, and PMI favours rare fixed fragments.
    """
    finder_cls, measures = ((BigramCollocationFinder, BigramAssocMeasures()) if n == 2
                            else (TrigramCollocationFinder, TrigramAssocMeasures()))
    finder = finder_cls.from_documents(token_lists)
    finder.apply_freq_filter(min_freq)
    llr = dict(finder.score_ngrams(measures.likelihood_ratio))
    pmi = dict(finder.score_ngrams(measures.pmi))
    rows = [{"phrase": " ".join(g), "count": finder.ngram_fd[g], "likelihood_ratio": s, "pmi": pmi[g]}
            for g, s in llr.items()]
    return (pd.DataFrame(rows).sort_values(rank_by, ascending=False)
            .head(top).reset_index(drop=True))


def concordance(texts, phrase: str, width: int = 70, max_lines: int = 5) -> list[str]:
    """Keyword-in-context lines for a lemmatised phrase found in the original texts.

    Each word matches its inflected forms ("entity" also finds "entities").
    """
    stems = [re.escape(w[:max(4, len(w) - 2)]) + r"\w*" for w in phrase.split()]
    pattern = re.compile(r"\b" + r"\W+".join(stems) + r"\b", re.IGNORECASE)
    lines = []
    for text in texts:
        for m in pattern.finditer(text):
            left = text[max(0, m.start() - width):m.start()].rjust(width)
            lines.append(f"{left} [{m.group(0)}] {text[m.end():m.end() + width]}")
            if len(lines) >= max_lines:
                return lines
    return lines


# ----------------------------------------------------------- fingerprints ---
def tfidf_fingerprints(groups: dict, top: int = 12, max_df: float = 0.8) -> pd.DataFrame:
    """The words with the highest TF-IDF weight in each group, treating each group
    (a document, a speaker) as one document. groups: name -> list of tokens.

    Words used by more than `max_df` of the groups ("enron", "company") are left
    out: they cannot tell the groups apart, but their counts would top every list.
    """
    names = list(groups)
    vectoriser = TfidfVectorizer(analyzer=lambda tokens: tokens, max_df=max_df)
    X = vectoriser.fit_transform([groups[n] for n in names])
    vocab = np.array(vectoriser.get_feature_names_out())
    rows = []
    for i, name in enumerate(names):
        row = X[i].toarray().ravel()
        for rank, j in enumerate(np.argsort(row)[::-1][:top], start=1):
            rows.append({"group": name, "rank": rank, "word": vocab[j], "tfidf": row[j]})
    return pd.DataFrame(rows)


# ------------------------------------------------------ comparing corpora ---
def compare_rates(tokens_a, tokens_b, min_count: int = 20) -> pd.DataFrame:
    """Each word's rate per 10,000 words in corpus A and in corpus B, as Scattertext
    plots them (course week 6), with the log2 ratio of the rates (A over B, each
    count + 1). Words used fewer than `min_count` times in total are left out."""
    a = Counter(t for tokens in tokens_a for t in tokens)
    b = Counter(t for tokens in tokens_b for t in tokens)
    na, nb = sum(a.values()), sum(b.values())
    words = [w for w in set(a) | set(b) if a[w] + b[w] >= min_count]
    table = pd.DataFrame({"word": words, "count_a": [a[w] for w in words], "count_b": [b[w] for w in words]})
    table["per_10k_a"] = 10_000 * table["count_a"] / na
    table["per_10k_b"] = 10_000 * table["count_b"] / nb
    table["log2_ratio"] = np.log2(((table["count_a"] + 1) / na) / ((table["count_b"] + 1) / nb))
    return table.sort_values("log2_ratio", ascending=False).reset_index(drop=True)


def term_rates(texts, themes: pd.DataFrame) -> pd.Series:
    """Matches of each theme's terms per 10,000 words of text (independent of how long
    the single texts are). `themes` as loaded by enron.themes.load_themes."""
    texts = list(texts)
    words = sum(len(t.split()) for t in texts)
    counted = themes[themes["kind"] != "exclude"]
    hits = {theme_id: sum(len(p.findall(t)) for p in group["pattern"] for t in texts)
            for theme_id, group in counted.groupby("theme_id")}
    return pd.Series({k: 10_000 * v / words for k, v in hits.items()})


def join_phrases(token_lists, phrases) -> list[list[str]]:
    """Join two-word names into one token ("el", "paso" -> "el paso"), so they are
    counted as one word. phrases: iterable of (first, second) lemma pairs."""
    pairs = {tuple(p): " ".join(p) for p in phrases}
    out = []
    for tokens in token_lists:
        joined, i = [], 0
        while i < len(tokens):
            if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) in pairs:
                joined.append(pairs[(tokens[i], tokens[i + 1])])
                i += 2
            else:
                joined.append(tokens[i])
                i += 1
        out.append(joined)
    return out


def written_forms(texts, words) -> dict:
    """For each lowercased word or phrase, the spelling most often used in the texts
    ("mmbtu" -> "MMBtu", "el paso" -> "El Paso"); words not found keep their form."""
    joined = "\n".join(texts)
    forms = {}
    for word in words:
        pattern = re.compile(r"\b" + r"\W+".join(map(re.escape, word.split())) + r"\b", re.IGNORECASE)
        found = Counter(m.group(0) for m in pattern.finditer(joined))
        forms[word] = re.sub(r"\s+", " ", found.most_common(1)[0][0]) if found else word
    return forms
