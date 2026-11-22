import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode = WAL;")
conn.execute("PRAGMA synchronous = NORMAL;")

cursor = conn.cursor()

# 1. Select only rows that actually contain 'HOU/ECT'
cursor.execute("""
    SELECT email_id, body_clean
    FROM emails
    WHERE body_clean LIKE '%Cynthia Clark%'
""")
rows = cursor.fetchall()
print(f"Found {len(rows)} matching emails.\n")

for email_id, body_clean in rows:
    print(f"=== Email ID: {email_id} ===")
    print(body_clean)
    print("-" * 40)

conn.close()