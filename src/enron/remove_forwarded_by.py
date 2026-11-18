
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"

def clean_forwarding_lines(text):
    lines = text.splitlines()
    result = []
    skip = 0

    for line in lines:
        if skip:
            skip -= 1
            continue

        if "forwarded by" in line.lower():
            skip = 4
            continue

        result.append(line)

    return "\n".join(result)


def main():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT email_id, body_clean
            FROM emails
            WHERE body_clean LIKE '%Forwarded by%'
        """).fetchall()

        print(f"Found {len(rows)} emails containing forwarding markers.")

        updates = [
            (clean_forwarding_lines(body), email_id)
            for email_id, body in rows
        ]

        conn.executemany("""
            UPDATE emails
            SET body_clean = ?
            WHERE email_id = ?
        """, updates)

        conn.commit()

        print(f"Updated {len(updates)} emails.")


if __name__ == "__main__":
    main()
