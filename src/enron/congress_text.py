"""What the Congress documents say: cleaning, passages, and topics (course weeks 6 and 7).

Topics are found twice, with LDA on word counts and NMF on TF-IDF weights, and
each is checked for stability across random seeds.
"""

import re

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import normalized_mutual_info_score

# People the documents investigate who have no mailbox in our data; their surnames
# stay in the text even when they also spoke in a hearing
DISCUSSED_OUTSIDERS = ["Andrew Fastow", "Sherron Watkins", "Michael Kopper", "Ben Glisan",
                       "David Duncan", "Herbert Winokur", "Robert Jaedicke"]

# Words of hearing procedure and conversation that say nothing about the subject
PROCEDURE_WORDS = frozenset("""
chairman chairwoman committee subcommittee senator congressman congresswoman gentleman
gentlelady gentlewoman member hearing testimony witness question answer thank yield
minute time today yes okay sir ask tell think know believe want like look come let hear
good right way thing lot sure mean say go get make try point really little bit
chair recognize opening expire cong hrg clerk aye nay swear hon interview
senate governmental affairs permanent investigations
""".split())

SPEAKER_LABEL = re.compile(r"^(?:(?:Mr|Ms|Mrs|Dr|Senator|Chairman|Representative)\.? [A-Z][A-Za-z'\-]+"
                           r"|The Chairman|The Chair|Chairman)\.\s+")
LEADER_DOTS = re.compile(r"\.{5,}")
NOISE = re.compile(r"\[GRAPHIC\]|TIFF OMITTED|^[_=\-\s]+$|Government (?:Printing|Publishing) Office",
                   re.IGNORECASE)
FOOTNOTE_MARK = re.compile(r"\\\d+\\")          # \413\ in the text
SEPARATOR = re.compile(r"-{5,}|_{5,}")            # lines that set footnotes apart


DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                  r" (\d{1,2}), (\d{4})", re.IGNORECASE)
KIND = re.compile(r"\[(House|Senate) (Hearing|Prints?)")


def document_labels(paragraphs: pd.DataFrame, title_chars: int = 32) -> pd.DataFrame:
    """Date, chamber and a short label per document, read from its front matter.

    Label example: '5 Feb 2002 · House hearing · Financial collapse of Enron'.
    """
    rows = []
    for doc_id, doc in paragraphs.groupby("doc_id", sort=False):
        head = " ".join(doc.sort_values("para_id")["text"].head(40))
        date = pd.to_datetime(" ".join(DATE.search(head).groups()), format="%B %d %Y")
        chamber, kind = KIND.search(head).groups()
        kind = "hearing" if kind == "Hearing" else "report"
        title = re.sub(r"^THE ", "", doc["title"].iloc[0].strip(" -")).capitalize().replace("enron", "Enron")
        title = title if len(title) <= title_chars else title[:title_chars].rstrip(" ,:") + "…"
        rows.append({"doc_id": doc_id, "date": date,
                     "label": f"{date.day} {date:%b %Y} · {chamber} {kind} · {title}"})
    return pd.DataFrame(rows).sort_values("date").set_index("doc_id")


def is_heading(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return len(text) < 200 and len(letters) > 3 and all(c.isupper() for c in letters)


def drop_footnotes(text: str) -> str:
    """Remove footnotes (citations such as "\\413\\ John Emshwiller ... Wall Street Journal")
    and footnote markers, keeping any ordinary text around them.

    A footnote runs from its marker to the next separator line; a paragraph can
    hold footnotes and ordinary text on either side of such a line.
    """
    segments = [s for s in SEPARATOR.split(text) if not re.match(r"\s*\\\d+\\", s)]
    return re.sub(r"\s+", " ", FOOTNOTE_MARK.sub("", " ".join(segments))).strip()


def clean_paragraphs(paragraphs: pd.DataFrame, min_words: int = 5) -> pd.DataFrame:
    """Drop front matter, contents pages, footnotes, headings, image placeholders and
    very short paragraphs.

    Front matter of a hearing = everything before the first speaker's name; of a
    report = everything up to the last line of its table of contents.
    """
    keep = []
    for doc_id, doc in paragraphs.groupby("doc_id", sort=False):
        doc = doc.sort_values("para_id")
        if (doc["doc_type"] == "hearing").all() and doc["explicit"].any():
            doc = doc[doc["para_id"] >= doc.loc[doc["explicit"] == 1, "para_id"].min()]
        else:
            contents = doc.head(200)["text"].str.contains(LEADER_DOTS)
            if contents.any():
                doc = doc[doc["para_id"] > doc.head(200).loc[contents, "para_id"].max()]
        keep.append(doc)
    out = pd.concat(keep)
    out["text"] = out["text"].map(drop_footnotes)
    bad = (out["text"].str.contains(LEADER_DOTS) | out["text"].str.contains(NOISE)
           | out["text"].map(is_heading) | (out["text"].str.split().str.len() < min_words))
    return out[~bad].reset_index(drop=True)


def strip_speaker_labels(paragraphs: pd.DataFrame) -> pd.DataFrame:
    """Remove the name that opens a speaker's turn ("Mr. Greenwood. ..."): it is who
    speaks, not what is said, and the speaker stays in the `speaker` column."""
    out = paragraphs.copy()
    out["text"] = out["text"].str.replace(SPEAKER_LABEL, "", regex=True)
    return out


def name_stopwords(paragraphs: pd.DataFrame, discussed_names) -> frozenset:
    """Surnames of speakers (mostly members of Congress), except people the documents
    discuss by name (`discussed_names`, e.g. Skilling, Fastow, Watkins)."""
    keep = {n.split()[-1].lower() for n in discussed_names if isinstance(n, str)}
    surnames = {s.split()[-1].lower() for s in paragraphs["speaker"].dropna().unique()}
    return frozenset(surnames - keep)


def build_passages(paragraphs: pd.DataFrame, target: int = 180, longest: int = 360) -> pd.DataFrame:
    """Join consecutive paragraphs of a document into passages of about `target` words.

    An exchange of questions and answers stays together; a paragraph longer than
    `longest` words is cut into pieces of `target` words.
    """
    rows = []

    def flush(doc_id, words, speakers, first):
        if words:
            rows.append({"doc_id": doc_id, "first_para": first, "speakers": "; ".join(dict.fromkeys(speakers)),
                         "text": " ".join(words)})

    for doc_id, doc in paragraphs.groupby("doc_id", sort=False):
        words, speakers, first = [], [], None
        for p in doc.sort_values("para_id").itertuples():
            pieces = p.text.split()
            chunks = ([pieces[i:i + target] for i in range(0, len(pieces), target)]
                      if len(pieces) > longest else [pieces])
            for chunk in chunks:
                if first is None:
                    first = p.para_id
                words += chunk
                if isinstance(p.speaker, str):
                    speakers.append(p.speaker)
                if len(words) >= target:
                    flush(doc_id, words, speakers, first)
                    words, speakers, first = [], [], None
        flush(doc_id, words, speakers, first)
    passages = pd.DataFrame(rows)
    passages.index.name = "passage_id"
    return passages.reset_index()


# ----------------------------------------------------------------- topics ---
def document_term(token_lists, min_df: int = 5, max_df: float = 0.5):
    """Word counts and TF-IDF weights over the same vocabulary (words in at least
    `min_df` passages and at most `max_df` of them)."""
    counts = CountVectorizer(analyzer=lambda t: t, min_df=min_df, max_df=max_df)
    C = counts.fit_transform(token_lists)
    vocab = counts.get_feature_names_out()
    tfidf = TfidfVectorizer(analyzer=lambda t: t, vocabulary=vocab)
    return C, tfidf.fit_transform(token_lists), np.array(vocab)


def fit_topics(method: str, X, k: int, seed: int):
    """Document-topic weights (rows sum to 1) and topic-word weights."""
    if method == "lda":
        model = LatentDirichletAllocation(n_components=k, learning_method="batch", max_iter=50,
                                          random_state=seed)
    else:
        # random start, so that the seed matters and stability across seeds means something
        model = NMF(n_components=k, init="random", random_state=seed, max_iter=500)
    W = model.fit_transform(X)
    W = W / np.clip(W.sum(axis=1, keepdims=True), 1e-12, None)
    return W, model.components_


def top_words(H, vocab, n: int = 12) -> list[list[str]]:
    return [list(vocab[np.argsort(row)[::-1][:n]]) for row in H]


def stability(method: str, X, k: int, seeds) -> float:
    """Mean NMI between the main topic of each passage across runs with different seeds."""
    labels = [fit_topics(method, X, k, s)[0].argmax(axis=1) for s in seeds]
    pairs = [normalized_mutual_info_score(labels[i], labels[j])
             for i in range(len(labels)) for j in range(i + 1, len(labels))]
    return float(np.mean(pairs))


def topic_table(W, H, vocab, n_words: int = 12) -> pd.DataFrame:
    """One row per topic: its top words and its share of all passage weight."""
    words = top_words(H, vocab, n_words)
    return pd.DataFrame({"topic": np.arange(1, len(H) + 1),
                         "share": W.sum(axis=0) / W.sum(),
                         "passages_main": np.bincount(W.argmax(axis=1), minlength=len(H)),
                         "top_words": [", ".join(w) for w in words]})


def match_topics(W_a, W_b) -> dict:
    """For each topic in A, the topic in B its passages most often have as main topic."""
    a, b = W_a.argmax(axis=1), W_b.argmax(axis=1)
    return {int(t) + 1: int(np.bincount(b[a == t], minlength=W_b.shape[1]).argmax()) + 1
            for t in np.unique(a)}


def shares_by_document(W, doc_ids) -> pd.DataFrame:
    """Mean topic weight of the passages in each document (rows: topics, columns: documents)."""
    frame = pd.DataFrame(W, columns=np.arange(1, W.shape[1] + 1))
    frame["doc_id"] = list(doc_ids)
    return frame.groupby("doc_id", sort=False).mean().T


def example_passages(W, passages: pd.DataFrame, n: int = 3, chars: int = 400) -> pd.DataFrame:
    """The `n` passages with the highest weight on each topic, for reading and labelling."""
    rows = []
    for t in range(W.shape[1]):
        for i in np.argsort(W[:, t])[::-1][:n]:
            rows.append({"topic": t + 1, "weight": W[i, t], "doc_id": passages.doc_id.iloc[i],
                         "speakers": passages.speakers.iloc[i], "text": passages.text.iloc[i][:chars]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ hand check ---
def nmf_to_lda(passages: pd.DataFrame) -> dict:
    """For each NMF topic, the LDA topic its passages most often have, so NMF can be
    compared with labels written in LDA's numbering."""
    return passages.groupby("nmf_topic")["lda_topic"].agg(lambda s: s.value_counts().idxmax()).to_dict()


def label_agreement(human: pd.Series, model: pd.Series, second: pd.Series | None = None) -> dict:
    """Agreement between hand labels and a model's main topic, same passages.

    strict: the model's topic is the hand label; lenient: it is the hand label or
    the optional second choice; kappa: Cohen's kappa on the strict labels.
    Passages labelled 0 (none of the topics) count as disagreements.
    """
    from sklearn.metrics import cohen_kappa_score
    strict = human == model
    lenient = strict | (second == model) if second is not None else strict
    return {"passages": len(human), "strict": strict.mean(), "lenient": lenient.mean(),
            "kappa": cohen_kappa_score(human, model),
            "labelled_none": int((human == 0).sum())}


def fit_check_sample(W, n_strong: int = 2, n_random: int = 1, seed: int = 2026) -> pd.DataFrame:
    """Passages to judge by hand per topic: its `n_strong` highest-weight passages and
    `n_random` random passages that have it as main topic (the strongest ones are the
    easy cases, so the random ones keep the check honest). Rows come shuffled."""
    rng = np.random.default_rng(seed)
    main = W.argmax(axis=1)
    rows = []
    for t in range(W.shape[1]):
        strong = list(np.argsort(W[:, t])[::-1][:n_strong])
        pool = [i for i in np.flatnonzero(main == t) if i not in strong]
        picks = list(rng.choice(pool, size=min(n_random, len(pool)), replace=False))
        rows += [{"topic": t + 1, "row": i, "kind": "strongest"} for i in strong]
        rows += [{"topic": t + 1, "row": i, "kind": "random"} for i in picks]
    sample = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    sample.insert(0, "item", np.arange(1, len(sample) + 1))
    return sample
