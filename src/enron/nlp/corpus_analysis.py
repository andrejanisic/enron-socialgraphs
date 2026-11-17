
import sqlite3
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"
OUTPUT_DIR = PROJECT_ROOT / "reports"
OUTPUT_FILE = OUTPUT_DIR / "corpus_analysis.txt"

TOP_N = 60

# Change this query to analyze a different subset.
# It must return body_clean, date, and sender_id.
QUERY = """
    SELECT body_clean, date, sender_id
    FROM emails
    WHERE body_clean IS NOT NULL
      AND TRIM(body_clean) != ''
    AND NOT message_type = 'generated'
    -- AND human_probability > 0.5
"""


# Basic English stopwords. Keep this list simple for now.
STOPWORDS = set("""
    a an the and or but if while is am are was were be been being
    have has had do does did will would shall should can could may
    might must to of in on at by for with from into about against
    between through during before after above below up down out off
    over under again further then once here there when where why how
    all any both each few more most other some such no nor not only
    own same so than too very s t don now
    i me my we our you your he she it they them his her its their
    this that these those what which who whom as
    also just like get got one two
""".split())


# --------------------------------------------------
# Text processing
# --------------------------------------------------

def tokenize(text):
    text = text.lower()

    # Remove email addresses
    text = re.sub(r'\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b', ' ', text)

    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)

    # Remove standalone email/header artifacts
    text = re.sub(r'\b(?:ect|enron|com|hou)\b', ' ', text)

    # Extract words, excluding single-character fragments
    return re.findall(r'\b[a-z]{2,}\b', text)


def content_tokens(text):
    """Tokens without common stopwords."""
    return [word for word in tokenize(text) if word not in STOPWORDS]


def make_ngrams(tokens, n):
    return zip(*(tokens[i:] for i in range(n)))


# --------------------------------------------------
# Load emails
# --------------------------------------------------

def load_emails():
    conn = sqlite3.connect(DB_PATH)

    try:
        rows = conn.execute(QUERY).fetchall()
    finally:
        conn.close()

    return rows


# --------------------------------------------------
# Analysis
# --------------------------------------------------

def analyze(rows):
    all_tokens = []
    content_word_counts = Counter()
    ngram_counts = {2: Counter(), 3: Counter()}

    email_lengths = []
    sender_stats = defaultdict(lambda: {
        "emails": 0,
        "words": 0
    })

    monthly_counts = Counter()

    for body, date, sender_id in rows:
        body = body or ""

        tokens = tokenize(body)
        filtered = [w for w in tokens if w not in STOPWORDS]

        all_tokens.extend(tokens)
        content_word_counts.update(filtered)

        email_lengths.append(len(tokens))

        for n in (2, 3):
            ngram_counts[n].update(make_ngrams(filtered, n))

        sender_stats[sender_id]["emails"] += 1
        sender_stats[sender_id]["words"] += len(tokens)

        if date:
            month = str(date)[:7]
            if re.fullmatch(r"\d{4}-\d{2}", month):
                monthly_counts[month] += 1

    total_words = len(all_tokens)
    vocabulary = set(all_tokens)

    return {
        "email_count": len(rows),
        "total_words": total_words,
        "vocabulary_size": len(vocabulary),
        "email_lengths": email_lengths,
        "word_counts": content_word_counts,
        "ngram_counts": ngram_counts,
        "sender_stats": sender_stats,
        "monthly_counts": monthly_counts,
    }


# --------------------------------------------------
# Report
# --------------------------------------------------

def generate_report(results):
    lengths = results["email_lengths"]

    lines = []

    def section(title):
        lines.append("")
        lines.append("=" * 60)
        lines.append(title.upper())
        lines.append("=" * 60)

    def add(text=""):
        lines.append(str(text))

    # General statistics
    section("Corpus overview")

    add(f"Emails:             {results['email_count']:,}")
    add(f"Total words:        {results['total_words']:,}")
    add(f"Unique vocabulary:  {results['vocabulary_size']:,}")

    if lengths:
        add(f"Average email:      {statistics.mean(lengths):,.1f} words")
        add(f"Median email:       {statistics.median(lengths):,.1f} words")
        add(f"Shortest email:     {min(lengths):,} words")
        add(f"Longest email:      {max(lengths):,} words")

    # Vocabulary
    section("Most frequent words (stopwords removed)")

    for word, count in results["word_counts"].most_common(TOP_N):
        add(f"{word:<25} {count:>10,}")

    # N-grams
    for n in (2, 3):
        section(f"Most frequent {n}-grams (stopwords removed)")

        for gram, count in results["ngram_counts"][n].most_common(TOP_N):
            phrase = " ".join(gram)
            add(f"{phrase:<35} {count:>10,}")

    # Sender statistics
    section("Most active senders")

    senders = sorted(
        results["sender_stats"].items(),
        key=lambda x: x[1]["emails"],
        reverse=True
    )

    add(f"{'Person ID':<15} {'Emails':>10} {'Words':>12} {'Avg words/email':>18}")

    for sender_id, stats in senders[:20]:
        avg = stats["words"] / stats["emails"]
        add(
            f"{str(sender_id):<15} "
            f"{stats['emails']:>10,} "
            f"{stats['words']:>12,} "
            f"{avg:>18.1f}"
        )

    # Monthly distribution
    section("Emails per month")

    for month, count in sorted(results["monthly_counts"].items()):
        add(f"{month:<15} {count:>10,}")

    return "\n".join(lines)


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    print(f"Database: {DB_PATH}")
    print("Loading emails...")

    rows = load_emails()

    print(f"Loaded {len(rows):,} emails.")
    print("Analyzing corpus...")

    results = analyze(rows)
    report = generate_report(results)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nReport saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
