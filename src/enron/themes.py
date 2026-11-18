"""The Congress themes in both texts: term lists, retrieval, and the hand-check sample.

A theme (data/themes.csv) has unambiguous `name` terms (LJM, Raptor, Andersen) and
`general` terms that also turn up in everyday business (hedge, audit, bonus). A
text gets a theme when it holds one name term, or two different general terms.
`exclude` terms mark another subject that shares the general words (the California
energy crisis, which shares words such as "board" and "rating"): when one is
present, general terms do not
count, name terms still do.

Term syntax: case is ignored; `*` at the end of a word allows any ending
(`audit*` = audit, auditor, auditing); a space also matches a hyphen; a term
starting with `re:` is a regular expression.
"""

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
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
def theme_similarity(email_tokens, passage_tokens, passage_topics, themes: pd.DataFrame,
                     email_words=None, min_words: int = 30) -> pd.DataFrame:
    """Cosine similarity (TF-IDF, course week 7) between each email and each theme,
    a theme being the mean vector of the Congress passages whose main topic is one
    of the theme's topics. Rows: emails; columns: theme ids.

    Emails shorter than `min_words` get similarity 0: with a handful of words, one
    shared word ("research", "options") is enough for a high score."""
    vectoriser = TfidfVectorizer(analyzer=lambda tokens: tokens, min_df=3, sublinear_tf=True)
    X = vectoriser.fit_transform(list(email_tokens) + list(passage_tokens))
    E, P = X[:len(email_tokens)], X[len(email_tokens):]
    topics = np.asarray(passage_topics)
    scores = {}
    for theme_id, group in themes.groupby("theme_id"):
        wanted = [int(t) for t in str(group["topics"].iloc[0]).split(";")]
        centroid = np.asarray(P[np.isin(topics, wanted)].mean(axis=0)).ravel()
        centroid /= np.linalg.norm(centroid) or 1
        scores[theme_id] = E @ centroid
    scores = pd.DataFrame(scores)
    if email_words is not None:
        scores.loc[np.asarray(email_words) < min_words] = 0.0
    return scores


def rank_matched(similarity: pd.DataFrame, term_tags: pd.DataFrame, minimum: int = 10) -> pd.DataFrame:
    """Retrieval tags with the same number of emails per theme as the term lists
    (at least `minimum`): the most similar emails. Keeps the two methods comparable
    without choosing a similarity threshold."""
    tags = {}
    for theme_id in similarity:
        n = max(int(term_tags[theme_id].sum()), minimum)
        top = similarity[theme_id].rank(ascending=False, method="first") <= n
        tags[theme_id] = top.to_numpy()
    return pd.DataFrame(tags, index=similarity.index)


def method_agreement(term_tags: pd.DataFrame, retrieval_tags: pd.DataFrame, names: pd.Series) -> pd.DataFrame:
    """How far the two tagging methods pick the same emails, per theme.

    Columns: emails tagged by the term list; emails tagged by similarity to the theme's
    Congress passages (the same number, at least 10, by design); emails tagged by both;
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
                     "agreement beyond chance (Cohen's kappa)": cohen_kappa_score(a, b)})
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
    sample = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    sample.insert(0, "item", np.arange(1, len(sample) + 1))
    return sample
