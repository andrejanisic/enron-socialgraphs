import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"

# Compile regexes once for speed (case-insensitive)
LINE_NOISE_PATTERNS = [
    re.compile(r"<[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}>"),  # <name@domain.com>
]

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode = WAL;")
conn.execute("PRAGMA synchronous = NORMAL;")
cursor = conn.cursor()

# Coarse SQL pre-filter (fast scan) so Python only inspects candidate rows
cursor.execute("""
    SELECT email_id, body_clean
    FROM emails
    WHERE body_clean LIKE '%@%'
       OR body_clean LIKE '%HOU/ECT%'
       OR body_clean LIKE '%Forwarded by%'
""")
rows = cursor.fetchall()
print(f"Inspecting {len(rows):,} candidate emails...")

updates = []
for email_id, body in rows:
    if not body:
        continue

    cleaned_lines = [
        line for line in body.split("\n")
        if not any(pattern.search(line) for pattern in LINE_NOISE_PATTERNS)
    ]
    new_body = "\n".join(cleaned_lines)

    if new_body != body:
        updates.append((new_body, email_id))

with conn:
    conn.executemany(
        "UPDATE emails SET body_clean = ? WHERE email_id = ?",
        updates,
    )

print(f"Updated {len(updates):,} emails.")
conn.close()