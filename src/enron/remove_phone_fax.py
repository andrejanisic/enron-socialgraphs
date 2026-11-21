import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"


# Matches a line with "Phone: <digits>" followed immediately by a line with "Fax: <digits>"
PHONE_RE = re.compile(r"^\s*Phone\s*:.*\d", re.IGNORECASE)
FAX_RE = re.compile(r"^\s*Fax\s*:.*\d", re.IGNORECASE)

LINES_ABOVE = 1
LINES_BELOW = 3


def strip_signature_block(body: str) -> str:
    lines = body.split("\n")
    to_remove = set()

    for i in range(len(lines) - 1):
        if PHONE_RE.match(lines[i]) and FAX_RE.match(lines[i + 1]):
            start = max(0, i - LINES_ABOVE)
            end = min(len(lines), i + 2 + LINES_BELOW)  # i (Phone) + i+1 (Fax) + 3 below
            to_remove.update(range(start, end))

    if not to_remove:
        return body

    cleaned_lines = [line for idx, line in enumerate(lines) if idx not in to_remove]
    return "\n".join(cleaned_lines)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    cursor = conn.cursor()

    # Fast SQL pre-filter so Python only processes candidate rows
    cursor.execute("""
        SELECT email_id, body_clean
        FROM emails
        WHERE body_clean LIKE '%Phone:%'
          AND body_clean LIKE '%Fax:%'
    """)
    rows = cursor.fetchall()
    print(f"Inspecting {len(rows):,} candidate emails...")

    updates = []
    for email_id, body in rows:
        if not body:
            continue
        new_body = strip_signature_block(body)
        if new_body != body:
            updates.append((new_body, email_id))

    with conn:
        conn.executemany(
            "UPDATE emails SET body_clean = ? WHERE email_id = ?",
            updates,
        )

    print(f"Updated {len(updates):,} emails.")
    conn.close()


if __name__ == "__main__":
    main()