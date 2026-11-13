import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT
            p.name,
            COUNT(*) AS email_count
        FROM emails e
        JOIN people p ON e.sender_id = p.person_id
        GROUP BY p.person_id
        ORDER BY email_count DESC
        LIMIT 5;
    """).fetchall()

    for row in rows:
        print(f"{row['name']}: {row['email_count']} emails sent")