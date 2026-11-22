import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np
import spacy
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer


# ==================================================
# CONFIGURATION
# ==================================================

# This assumes the script is in a directory three levels below the project root,
# matching the location of the previous script. Adjust if you move it.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"
MEMBERS_PATH = PROJECT_ROOT / "results" / "communities" / "members.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "nmf"

N_TOPICS = 15
TOP_TERMS = 15
REPRESENTATIVE_EMAILS = 5

MIN_DF = 5
MAX_DF = 0.4
MAX_FEATURES = 20_000
RANDOM_STATE = 42

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
      AND (
          e.message_type IS NULL
          OR e.message_type NOT IN ('automated', 'generated')
      )
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
    fyi claudia kim perlingiere shackleton carol jeff
""".split())


# ==================================================
# LOAD COMMUNITIES AND EMAILS
# ==================================================

def load_communities():
    """Return {community_id: set(person_ids)} and {person_id: community_id}."""
    community_members = defaultdict(set)

    with MEMBERS_PATH.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            person_id = int(row["person_id"])
            community_id = int(row["community"])
            community_members[community_id].add(person_id)

    person_to_community = {
        person_id: community_id
        for community_id, members in community_members.items()
        for person_id in members
    }

    print(f"Loaded {len(community_members)} communities.")
    for community_id, members in sorted(community_members.items()):
        print(f"  Community {community_id}: {len(members)} members")

    return community_members, person_to_community


def load_emails():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(QUERY).fetchall()


# ==================================================
# PREPROCESSING
# ==================================================

def clean_raw_text(text):
    text = (text or "").lower()

    # Email addresses
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", " ", text)

    # URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Phone numbers
    text = re.sub(r"\+?\d[\d\s().-]{7,}\d", " ", text)

    # Standalone numbers
    text = re.sub(r"\b\d+\b", " ", text)

    return text


def preprocess_emails(rows, person_to_community, nlp):
    documents = []
    metadata = []

    texts = [clean_raw_text(row[1]) for row in rows]
    print("  Lemmatizing emails...")

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
            "community_id": person_to_community.get(sender_id),
            "body": body,
        })

    return documents, metadata


# ==================================================
# GLOBAL TF-IDF + NMF
# ==================================================

def build_tfidf(documents):
    print("  Building global TF-IDF matrix...")

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

    print(f"  TF-IDF matrix: {X.shape}")
    print(f"  Non-zero entries: {X.nnz:,}")
    print(f"  Vocabulary size: {len(vectorizer.get_feature_names_out()):,}")

    return X, vectorizer


def fit_nmf(X):
    print(f"  Fitting ONE global NMF model with {N_TOPICS} topics...")

    model = NMF(
        n_components=N_TOPICS,
        init="nndsvda",
        random_state=RANDOM_STATE,
        max_iter=400,
    )

    W = model.fit_transform(X)
    H = model.components_

    print(f"  Reconstruction error: {model.reconstruction_err_:.4f}")
    print(f"  Iterations: {model.n_iter_}")

    return model, W, H


def normalize_topic_weights(W):
    """
    Convert each email's NMF row into a relative topic mixture.
    NMF scores themselves are not probabilities.
    """
    row_sums = W.sum(axis=1, keepdims=True)
    return np.divide(W, row_sums, out=np.zeros_like(W), where=row_sums != 0)


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
                "community_id": item["community_id"],
                "subject_body_preview": (item["body"] or "").replace("\n", " ")[:300],
            })

    return results


# ==================================================
# COMMUNITY TOPIC MIXTURES
# ==================================================

def calculate_community_topic_mix(P, metadata):
    """
    Average normalized email-topic mixtures for each sender community.
    Emails from senders absent from members.csv are excluded from this
    aggregation, but they remain in the global NMF model.
    """
    community_rows = defaultdict(list)

    for idx, item in enumerate(metadata):
        community_id = item["community_id"]
        if community_id is not None:
            community_rows[community_id].append(P[idx])

    wide_rows = []
    long_rows = []

    for community_id in sorted(community_rows):
        matrix = np.vstack(community_rows[community_id])
        mean_mix = matrix.mean(axis=0)
        email_count = len(matrix)

        row = {
            "community_id": community_id,
            "email_count": email_count,
        }

        for topic_id, value in enumerate(mean_mix):
            row[f"topic_{topic_id}"] = float(value)

            long_rows.append({
                "community_id": community_id,
                "email_count": email_count,
                "topic_id": topic_id,
                "mean_topic_weight": float(value),
                "percentage": float(value * 100),
            })

        wide_rows.append(row)

    return wide_rows, long_rows


# ==================================================
# CSV / MATRIX EXPORTS
# ==================================================

def write_csv(path, rows, fieldnames=None):
    if not rows:
        print(f"  No rows to write: {path.name}")
        return

    if fieldnames is None:
        fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_email_topics(W, P, metadata):
    rows = []

    for idx, item in enumerate(metadata):
        raw_scores = W[idx]
        proportions = P[idx]
        dominant = int(np.argmax(proportions))

        row = {
            "email_id": item["email_id"],
            "date": item["date"],
            "sender_id": item["sender_id"],
            "sender_name": item["sender_name"],
            "community_id": item["community_id"],
            "dominant_topic": dominant,
            "dominant_topic_percentage": float(proportions[dominant] * 100),
        }

        for topic_id in range(N_TOPICS):
            row[f"topic_{topic_id}"] = float(proportions[topic_id])
            row[f"raw_topic_{topic_id}"] = float(raw_scores[topic_id])

        rows.append(row)

    write_csv(OUTPUT_DIR / "email_topics.csv", rows)


def export_matrices(X, W, P, H, vectorizer, metadata):
    np.savez_compressed(
        OUTPUT_DIR / "nmf_matrices.npz",
        W=W,
        P=P,
        H=H,
        vocabulary=vectorizer.get_feature_names_out(),
        email_ids=np.array([m["email_id"] for m in metadata]),
        community_ids=np.array([
            -1 if m["community_id"] is None else m["community_id"]
            for m in metadata
        ]),
    )


def export_report(topic_terms, representative_emails, model, metadata,
                  community_mix):
    path = OUTPUT_DIR / "topic_report.txt"

    lines = [
        "ENRON GLOBAL NMF TOPIC MODEL",
        "=" * 65,
        f"Topics: {N_TOPICS}",
        f"Usable emails: {len(metadata):,}",
        f"Reconstruction error: {model.reconstruction_err_:.4f}",
        f"Iterations: {model.n_iter_}",
        "",
    ]

    for topic_id in range(N_TOPICS):
        lines.extend([
            "=" * 65,
            f"TOPIC {topic_id}",
            "-" * 65,
        ])

        terms = [
            r["term"] for r in topic_terms
            if r["topic_id"] == topic_id
        ]
        lines.append("Terms: " + ", ".join(terms))
        lines.append("Representative emails:")

        for item in representative_emails:
            if item["topic_id"] != topic_id:
                continue

            lines.append(
                f"  Email {item['email_id']} | {item['sender_name']} | "
                f"community={item['community_id']} | score={item['score']:.3f}"
            )
            lines.append(f"  {item['subject_body_preview']}")

        lines.append("")

    lines.extend([
        "=" * 65,
        "COMMUNITY TOPIC MIXTURES",
        "=" * 65,
        "Values are mean normalized topic weights (percentages).",
        "",
    ])

    for row in community_mix:
        community_id = row["community_id"]
        email_count = row["email_count"]
        topic_values = [
            (topic_id, row[f"topic_{topic_id}"])
            for topic_id in range(N_TOPICS)
        ]
        top_topics = sorted(topic_values, key=lambda x: x[1], reverse=True)[:5]

        lines.append(
            f"Community {community_id} ({email_count:,} emails): "
            + ", ".join(
                f"Topic {topic_id}={value * 100:.1f}%"
                for topic_id, value in top_topics
            )
        )

    path.write_text("\n".join(lines), encoding="utf-8")


# ==================================================
# MAIN
# ==================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading communities...")
    community_members, person_to_community = load_communities()

    print("\nLoading database...")
    rows = load_emails()
    print(f"Loaded {len(rows):,} emails for the global corpus.")

    print("\nLoading spaCy model...")
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])

    print("\nPreprocessing the GLOBAL corpus...")
    documents, metadata = preprocess_emails(rows, person_to_community, nlp)
    print(f"Usable emails: {len(documents):,}")

    if len(documents) < N_TOPICS:
        raise RuntimeError(
            f"Only {len(documents)} usable emails for {N_TOPICS} topics."
        )

    print("\nBuilding global TF-IDF...")
    X, vectorizer = build_tfidf(documents)

    if min(X.shape) < N_TOPICS:
        raise RuntimeError(
            f"TF-IDF matrix dimensions {X.shape} are insufficient "
            f"for {N_TOPICS} topics."
        )

    print("\nFitting global NMF...")
    model, W, H = fit_nmf(X)

    # Normalize each email's topic scores so its topic mixture sums to 1.
    P = normalize_topic_weights(W)

    terms = vectorizer.get_feature_names_out()
    topic_terms = get_topic_terms(H, terms)
    representative_emails = get_representative_emails(W, metadata)

    print("\nCalculating community topic mixtures...")
    community_mix, community_mix_long = calculate_community_topic_mix(
        P, metadata
    )

    assigned_emails = sum(
        1 for item in metadata if item["community_id"] is not None
    )
    print(f"Emails assigned to a community: {assigned_emails:,}")
    print(f"Communities with usable emails: {len(community_mix):,}")

    print("\nExporting results...")
    write_csv(OUTPUT_DIR / "topic_terms.csv", topic_terms)
    write_csv(
        OUTPUT_DIR / "representative_emails.csv",
        representative_emails,
    )
    export_email_topics(W, P, metadata)
    write_csv(
        OUTPUT_DIR / "community_topic_mix.csv",
        community_mix,
    )
    write_csv(
        OUTPUT_DIR / "community_topic_mix_long.csv",
        community_mix_long,
    )
    export_matrices(X, W, P, H, vectorizer, metadata)
    export_report(
        topic_terms,
        representative_emails,
        model,
        metadata,
        community_mix,
    )

    print("\nDone.")
    print(f"Results saved in: {OUTPUT_DIR}")
    print("Key file: community_topic_mix.csv")


if __name__ == "__main__":
    main()
