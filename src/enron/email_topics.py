"""What the emails are about on their own terms: a topic model (NMF on TF-IDF)
fitted to the sender's own words, without the Congress themes."""

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

# Greetings, office phrases and mail words that would otherwise form their own topics.
EMAIL_STOPWORDS = set(ENGLISH_STOP_WORDS) | set(
    "thanks thank know let need just like ll ve com enron ect hou pm am re fw fyi please "
    "would could get also will can one call send sent attached see go going want think "
    "time week day today tomorrow make sure good work new questions question look "
    "looking help said".split()
)

MIN_WORDS = 20      # emails shorter than this say too little to place in a topic
MIN_WEIGHT = 0.02   # an email's strongest topic must reach this weight, else 'no clear topic'
UNCLEAR = -1


def fit_email_topics(texts, n_topics: int = 10, seed: int = 0):
    """Fit NMF topics. Returns (vectorizer, model, document-topic weights W)."""
    vec = TfidfVectorizer(
        stop_words=list(EMAIL_STOPWORDS), min_df=5, max_df=0.3, sublinear_tf=True,
        token_pattern=r"(?u)\b[a-zA-Z]{3,}\b",
    )
    X = vec.fit_transform(texts)
    model = NMF(n_topics, init="nndsvd", random_state=seed, max_iter=600)
    W = model.fit_transform(X)
    return vec, model, W


def top_words(vec, model, n: int = 12) -> list[list[str]]:
    words = np.array(vec.get_feature_names_out())
    return [list(words[c.argsort()[::-1][:n]]) for c in model.components_]


def assign_topics(W, min_weight: float = MIN_WEIGHT) -> np.ndarray:
    """Each email's strongest topic, or UNCLEAR when no topic is strong enough."""
    best = W.argmax(axis=1)
    return np.where(W.max(axis=1) >= min_weight, best, UNCLEAR)


def topic_table(topics: np.ndarray, words: list[list[str]]) -> pd.DataFrame:
    n = len(topics)
    rows = []
    for t, w in enumerate(words):
        k = int((topics == t).sum())
        rows.append({"topic": t + 1, "emails": k, "share (%)": 100 * k / n, "top words": ", ".join(w)})
    k = int((topics == UNCLEAR).sum())
    rows.append({"topic": "no clear topic", "emails": k, "share (%)": 100 * k / n, "top words": ""})
    return pd.DataFrame(rows)


def examples(texts: pd.Series, W, topics: np.ndarray, n: int = 3, width: int = 200) -> dict:
    """The n emails that load most strongly on each topic (shortened)."""
    out = {}
    for t in range(W.shape[1]):
        idx = np.where(topics == t)[0]
        best = idx[np.argsort(-W[idx, t])[:n]]
        out[t + 1] = [" ".join(texts.iloc[i].split())[:width] for i in best]
    return out


def topics_by_group(emails: pd.DataFrame, group_col: str = "group") -> pd.DataFrame:
    """Share of each group's emails in each topic (%), with the group's email count."""
    from enron.email_people import GROUP_ORDER

    tab = pd.crosstab(emails[group_col], emails["topic_label"], normalize="index") * 100
    topic_cols = sorted((c for c in tab.columns if c.startswith("topic ")), key=lambda c: int(c.split()[1]))
    tab = tab[topic_cols + [c for c in tab.columns if c not in topic_cols]]
    tab.insert(0, "emails", emails[group_col].value_counts())
    order = [g for g in GROUP_ORDER if g in tab.index] + [g for g in tab.index if g not in GROUP_ORDER]
    return tab.loc[order]
