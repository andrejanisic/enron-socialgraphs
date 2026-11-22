"""The Congress themes in both texts: term lists, retrieval, and the hand-check sample.

A theme (data/themes.csv) has unambiguous `name` terms (LJM, Raptor, Andersen) and
`general` terms that also turn up in everyday business (hedge, audit, bonus). A
text gets a theme when it holds one name term, or two different general terms.
`exclude` terms mark another subject that shares the general words (the California
energy crisis, which shares words such as "board" and "rating"): when one is
present, general terms do not
count, name terms still do.

Retrieval, the second method, compares meaning instead of terms: sentence
embeddings of the email and of the theme's Congress passages (enron.embeddings),
a threshold per theme set among the emails (the top 1% most similar), the rule that
the theme must be the email's most similar one, and the same exclude terms as the
term list.

Term syntax: case is ignored; `*` at the end of a word allows any ending
(`audit*` = audit, auditor, auditing); a space also matches a hyphen; a term
starting with `re:` is a regular expression.
"""

import re
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score


# ------------------------------------------------------------ term lists ---
def term_pattern(term: str) -> re.Pattern:
    if term.startswith("re:"):
        return re.compile(term[3:], re.IGNORECASE)
    words = []
    for word in term.split():
        star = word.endswith("*")
        word = re.escape(word.rstrip("*"))
        words.append(word + (r"\w*" if star else ""))
    body = r"[\s\-]+".join(words)
    # \b only next to word characters, so terms such as "PG&E" still match
    left = r"\b" if re.match(r"\w", term) else ""
    right = r"\b" if re.search(r"[\w*]$", term) else ""
    return re.compile(left + body + right, re.IGNORECASE)


def load_themes(path) -> pd.DataFrame:
    """The theme list with a compiled pattern per term."""
    themes = pd.read_csv(path)
    themes["pattern"] = themes["term"].map(term_pattern)
    return themes


def theme_names(themes: pd.DataFrame) -> pd.Series:
    return themes.drop_duplicates("theme_id").set_index("theme_id")["theme"]


def tag_terms(texts, themes: pd.DataFrame) -> pd.DataFrame:
    """One row per text, one boolean column per theme id: one name term, or two
    different general terms in a text without any of the theme's exclude terms."""
    texts = list(texts)
    tags = {}
    for theme_id, group in themes.groupby("theme_id"):
        kinds = {k: [p for p, kk in zip(group["pattern"], group["kind"]) if kk == k]
                 for k in ("name", "general", "exclude")}

        def has_theme(t):
            if any(p.search(t) for p in kinds["name"]):
                return True
            if any(p.search(t) for p in kinds["exclude"]):
                return False
            return sum(bool(p.search(t)) for p in kinds["general"]) >= 2

        tags[theme_id] = [has_theme(t) for t in texts]
    return pd.DataFrame(tags)


def matched_terms(text: str, themes: pd.DataFrame, theme_id: int) -> str:
    """The terms of one theme found in a text (for reading the hand-check emails)."""
    group = themes[(themes["theme_id"] == theme_id) & (themes["kind"] != "exclude")]
    return ", ".join(t for t, p in zip(group["term"], group["pattern"]) if p.search(text))


# ------------------------------------------------------------- retrieval ---
# ------------------------------------------------------------- retrieval ---
def theme_topics(themes: pd.DataFrame) -> dict:
    """For each theme id, the Congress (LDA) topics it was built from."""
    first = themes.drop_duplicates("theme_id").set_index("theme_id")["topics"]
    return {theme_id: [int(t) for t in str(topics).split(";")] for theme_id, topics in first.items()}


def theme_profiles(passage_vectors: np.ndarray, passage_topics, themes: pd.DataFrame) -> pd.DataFrame:
    """One unit vector per theme (rows, indexed by theme id): the mean embedding of the
    Congress passages whose main LDA topic is one of the theme's topics."""
    topics = np.asarray(passage_topics)
    rows = {}
    for theme_id, wanted in theme_topics(themes).items():
        mean = passage_vectors[np.isin(topics, wanted)].mean(axis=0)
        rows[theme_id] = mean / (np.linalg.norm(mean) or 1)
    return pd.DataFrame(rows).T


def email_thresholds(similarity: pd.DataFrame, scored, percentile: float = 99) -> pd.Series:
    """For each theme, the similarity that only (100 - percentile)% of the scored emails
    reach. Set among the emails themselves, because emails and hearings are written so
    differently that a threshold set among the Congress passages is out of reach for
    any email (even for energy, the emails' most common subject)."""
    scored = np.asarray(scored)
    return pd.Series({t: float(np.percentile(similarity.loc[scored, t], percentile))
                      for t in similarity.columns})


def has_exclude_terms(texts, themes: pd.DataFrame) -> pd.DataFrame:
    """One row per text, one boolean column per theme id: does the text hold any of
    the theme's exclude terms (the California energy crisis, ISDA agreements)?"""
    texts = list(texts)
    out = {}
    for theme_id, group in themes.groupby("theme_id"):
        patterns = list(group.loc[group["kind"] == "exclude", "pattern"])
        out[theme_id] = [any(p.search(t) for p in patterns) for t in texts]
    return pd.DataFrame(out)


def retrieval_tags(similarity: pd.DataFrame, thresholds: pd.Series, excluded: pd.DataFrame,
                   n_words, min_words: int = 30) -> pd.DataFrame:
    """Emails tagged by similarity: at or above the theme's threshold, more similar to
    this theme than to any other, at least `min_words` words long, and without any of
    the theme's exclude terms (the same rule as the term list). A theme can get no
    emails at all."""
    long_enough = np.asarray(n_words) >= min_words
    best = similarity.idxmax(axis=1).to_numpy()
    tags = {theme_id: (similarity[theme_id].to_numpy() >= thresholds[theme_id]) & (best == theme_id)
            & long_enough & ~excluded[theme_id].to_numpy()
            for theme_id in similarity.columns}
    return pd.DataFrame(tags, index=similarity.index)


def _kappa(a, b) -> float:
    """Cohen's kappa, or NaN when a method tags no email (kappa is undefined then)."""
    if not a.any() or not b.any():
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cohen_kappa_score(a, b)


def method_agreement(term_tags: pd.DataFrame, retrieval_tags: pd.DataFrame, names: pd.Series) -> pd.DataFrame:
    """How far the two tagging methods pick the same emails, per theme.

    Columns: emails tagged by the term list; emails tagged by similarity to the theme's
    Congress passages (above the theme's threshold); emails tagged by both;
    the share of term-list emails that similarity also finds; overlap = both / either
    (Jaccard); and Cohen's kappa (agreement beyond chance, 0 = chance, 1 = identical)."""
    rows = []
    for theme_id in term_tags:
        a, b = term_tags[theme_id], retrieval_tags[theme_id]
        both = int((a & b).sum())
        rows.append({"theme": names[theme_id],
                     "emails tagged by term list": int(a.sum()),
                     "emails tagged by similarity": int(b.sum()),
                     "emails tagged by both": both,
                     "term-list emails also found by similarity (%)": 100 * both / max(int(a.sum()), 1),
                     "overlap, both / either (Jaccard)": both / max(int((a | b).sum()), 1),
                     "agreement beyond chance (Cohen's kappa)": _kappa(a, b)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ hand check ---
def hand_check_sample(term_tags: pd.DataFrame, retrieval_tags: pd.DataFrame, n_terms: int = 7,
                      n_retrieval: int = 3, n_none: int = 30, seed: int = 2026) -> pd.DataFrame:
    """Emails to judge by hand: per theme, `n_terms` random emails tagged by the term
    list and `n_retrieval` found only by retrieval; and `n_none` random emails with no
    theme from either method. Rows shuffled; `row` indexes the email table."""
    rng = np.random.default_rng(seed)
    rows, used = [], set()

    def pick(pool, n):
        pool = [i for i in pool if i not in used]
        chosen = list(rng.choice(pool, size=min(n, len(pool)), replace=False)) if pool else []
        used.update(chosen)
        return chosen

    for theme_id in term_tags:
        a, b = term_tags[theme_id].to_numpy(), retrieval_tags[theme_id].to_numpy()
        rows += [{"theme_id": theme_id, "row": i, "source": "term list"} for i in pick(np.flatnonzero(a), n_terms)]
        rows += [{"theme_id": theme_id, "row": i, "source": "retrieval only"}
                 for i in pick(np.flatnonzero(b & ~a), n_retrieval)]
    none = np.flatnonzero(~(term_tags.to_numpy().any(axis=1) | retrieval_tags.to_numpy().any(axis=1)))
    rows += [{"theme_id": 0, "row": i, "source": "no theme"} for i in pick(none, n_none)]
    sample = pd.DataFrame(rows, columns=["theme_id", "row", "source"]) \
        .sample(frac=1, random_state=seed).reset_index(drop=True)
    sample.insert(0, "item", np.arange(1, len(sample) + 1))
    return sample
