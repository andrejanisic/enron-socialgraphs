import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"

# Define all unwanted line-level substrings in one place
NOISE_PHRASES = [
    "HOU/ECT",
    "ENRON@enronXgate",
    "LON/ECT",
    "Communications@Enron"
]

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode = WAL;")
conn.execute("PRAGMA synchronous = NORMAL;")
cursor = conn.cursor()

# 1. Dynamically build the WHERE clause from NOISE_PHRASES
where_clause = " OR ".join("body_clean LIKE ?" for _ in NOISE_PHRASES)
params = [f"%{phrase}%" for phrase in NOISE_PHRASES]

cursor.execute(
    f"SELECT email_id, body_clean FROM emails WHERE {where_clause}",
    params,
)
rows = cursor.fetchall()
print(f"Found {len(rows)} matching emails.")

# 2. Drop any line containing ANY of the phrases
updates = []
for email_id, body in rows:
    if body is None:
        continue
    cleaned_lines = [
        line for line in body.split("\n")
        if not any(phrase in line for phrase in NOISE_PHRASES)
    ]
    new_body = "\n".join(cleaned_lines)
    if new_body != body:  # Only write rows that actually changed
        updates.append((new_body, email_id))

# 3. Bulk update in a single transaction
with conn:
    conn.executemany(
        "UPDATE emails SET body_clean = ? WHERE email_id = ?",
        updates,
    )

print(f"Updated {len(updates)} emails.")
conn.close()