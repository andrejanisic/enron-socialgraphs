import csv
import re
import sqlite3
from pathlib import Path

import numpy as np
import spacy

from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer


# ==================================================
# CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "nmf"

N_TOPICS = 15
TOP_TERMS = 15
REPRESENTATIVE_EMAILS = 5

# Minimum number of emails in which a term must appear.
MIN_DF = 5

# Ignore terms appearing in more than this fraction of emails.
MAX_DF = 0.4

MAX_FEATURES = 20_000

QUERY = """
    SELECT
        e.email_id,
        e.body_clean,
        e.date,
        e.sender_id,
        p.name
    FROM emails e
    LEFT JOIN people p ON p.person_id = e.sender_id
    WHERE e.body_clean IS NOT NULL
      AND TRIM(e.body_clean) != ''
      AND NOT e.message_type = 'automated' AND NOT e.message_type = 'generated'
      -- AND e.human_probability > 0.5
    ORDER BY e.email_id
"""

CUSTOM_STOPWORDS = set("""
    ect enron com hou
    cc bcc re fw fwd
    subject sent date
    folder original message
    mail email
    www http https
    thanks thank
""".split())


# ==================================================
# DATABASE
# ==================================================

def load_emails():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(QUERY).fetchall()


# ==================================================
# PREPROCESSING
# ==================================================

def clean_raw_text(text):
    text = (text or "").lower()

    # Email addresses
    text = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
        " ",
        text
    )

    # URLs
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text
    )

    # Phone numbers
    text = re.sub(
        r"\+?\d[\d\s().-]{7,}\d",
        " ",
        text
    )

    # Standalone numbers
    text = re.sub(r"\b\d+\b", " ", text)

    return text


def preprocess_emails(rows):
    print("Loading spaCy model...")

    nlp = spacy.load(
        "en_core_web_sm",
        disable=["ner", "parser"]
    )

    documents = []
    metadata = []

    texts = [clean_raw_text(row[1]) for row in rows]

    print("Lemmatizing emails...")

    for row, doc in zip(rows, nlp.pipe(texts, batch_size=500)):
        email_id, body, date, sender_id, sender_name = row

        tokens = []

        for token in doc:
            if not token.is_alpha or len(token.text) < 2:
                continue

            if token.is_stop:
                continue

            lemma = token.lemma_.lower().strip()

            if len(lemma) < 2 or lemma in CUSTOM_STOPWORDS:
                continue

            tokens.append(lemma)

        if not tokens:
            continue

        documents.append(" ".join(tokens))

        metadata.append({
            "email_id": email_id,
            "date": date,
            "sender_id": sender_id,
            "sender_name": sender_name or str(sender_id),
            "body": body,
        })

    return documents, metadata


# ==================================================
# TF-IDF
# ==================================================

def build_tfidf(documents):
    print("Building TF-IDF matrix...")

    vectorizer = TfidfVectorizer(
        tokenizer=str.split,
        preprocessor=None,
        token_pattern=None,
        lowercase=False,
        ngram_range=(1, 2),
        min_df=MIN_DF,
        max_df=MAX_DF,
        max_features=MAX_FEATURES,
        sublinear_tf=True,
        norm="l2",
    )

    X = vectorizer.fit_transform(documents)

    print(f"TF-IDF matrix: {X.shape}")
    print(f"Non-zero entries: {X.nnz:,}")
    print(f"Vocabulary size: {len(vectorizer.get_feature_names_out()):,}")

    return X, vectorizer


# ==================================================
# NMF
# ==================================================

def fit_nmf(X):
    print(f"Fitting NMF with {N_TOPICS} topics...")

    model = NMF(
        n_components=N_TOPICS,
        init="nndsvda",
        random_state=42,
        max_iter=400,
    )

    W = model.fit_transform(X)
    H = model.components_

    print(f"Reconstruction error: {model.reconstruction_err_:.4f}")
    print(f"Iterations: {model.n_iter_}")

    return model, W, H


# ==================================================
# TOPIC INSPECTION
# ==================================================

def get_topic_terms(H, terms):
    results = []

    for topic_id, topic in enumerate(H):
        indices = topic.argsort()[-TOP_TERMS:][::-1]

        for rank, idx in enumerate(indices, start=1):
            results.append({
                "topic_id": topic_id,
                "rank": rank,
                "term": terms[idx],
                "weight": float(topic[idx]),
            })

    return results


def get_representative_emails(W, metadata):
    results = []

    for topic_id in range(W.shape[1]):
        indices = np.argsort(W[:, topic_id])[-REPRESENTATIVE_EMAILS:][::-1]

        for rank, idx in enumerate(indices, start=1):
            item = metadata[idx]

            results.append({
                "topic_id": topic_id,
                "rank": rank,
                "score": float(W[idx, topic_id]),
                "email_id": item["email_id"],
                "date": item["date"],
                "sender_id": item["sender_id"],
                "sender_name": item["sender_name"],
                "subject_body_preview": (item["body"] or "").replace("\n", " ")[:300],
            })

    return results


# ==================================================
# EXPORT
# ==================================================

def export_topic_terms(results):
    path = OUTPUT_DIR / "topic_terms.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


def export_representative_emails(results):
    path = OUTPUT_DIR / "representative_emails.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


def export_email_topics(W, metadata):
    path = OUTPUT_DIR / "email_topics.csv"

    fieldnames = [
        "email_id",
        "date",
        "sender_id",
        "sender_name",
        "dominant_topic",
        "dominant_score",
    ] + [f"topic_{i}" for i in range(N_TOPICS)]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, item in enumerate(metadata):
            scores = W[idx]
            dominant = int(np.argmax(scores))

            row = {
                "email_id": item["email_id"],
                "date": item["date"],
                "sender_id": item["sender_id"],
                "sender_name": item["sender_name"],
                "dominant_topic": dominant,
                "dominant_score": float(scores[dominant]),
            }

            for topic_id, score in enumerate(scores):
                row[f"topic_{topic_id}"] = float(score)

            writer.writerow(row)


def export_matrices(X, W, H, vectorizer, metadata):
    np.savez_compressed(
        OUTPUT_DIR / "nmf_matrices.npz",
        W=W,
        H=H,
        vocabulary=vectorizer.get_feature_names_out(),
        email_ids=np.array([m["email_id"] for m in metadata]),
    )


def export_report(topic_terms, representative_emails, model):
    path = OUTPUT_DIR / "topic_report.txt"

    lines = [
        "ENRON NMF TOPIC MODEL",
        "=" * 60,
        f"Topics: {N_TOPICS}",
        f"Reconstruction error: {model.reconstruction_err_:.4f}",
        f"Iterations: {model.n_iter_}",
        "",
    ]

    for topic_id in range(N_TOPICS):
        lines.append("=" * 60)
        lines.append(f"TOPIC {topic_id}")
        lines.append("-" * 60)

        terms = [
            r["term"]
            for r in topic_terms
            if r["topic_id"] == topic_id
        ]

        lines.append("Terms: " + ", ".join(terms))
        lines.append("Representative emails:")

        for item in representative_emails:
            if item["topic_id"] != topic_id:
                continue

            lines.append(
                f"  Email {item['email_id']} | "
                f"{item['sender_name']} | "
                f"score={item['score']:.3f}"
            )
            lines.append(
                f"  {item['subject_body_preview']}"
            )
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ==================================================
# MAIN
# ==================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading database...")
    rows = load_emails()
    print(f"Loaded {len(rows):,} emails.")

    documents, metadata = preprocess_emails(rows)

    print(f"Usable emails: {len(documents):,}")

    if len(documents) < N_TOPICS:
        raise ValueError("Not enough usable emails for the requested number of topics.")

    X, vectorizer = build_tfidf(documents)

    model, W, H = fit_nmf(X)

    terms = vectorizer.get_feature_names_out()

    topic_terms = get_topic_terms(H, terms)
    representative_emails = get_representative_emails(W, metadata)

    print("Exporting results...")

    export_topic_terms(topic_terms)
    export_representative_emails(representative_emails)
    export_email_topics(W, metadata)
    export_matrices(X, W, H, vectorizer, metadata)
    export_report(topic_terms, representative_emails, model)

    print("\nDone.")
    print(f"Results saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
