"""Remove the "Forwarded by" lines and the header of each forwarded message from
emails.body_clean, keeping the forwarded text itself.

A forwarded message starts with a marker line ("---- Forwarded by Jeff Dasovich/NA/Enron
on 12/26/2000 11:14 AM ----", sometimes wrapped onto a second line) followed by its
header: sender, date, To:, cc: (often over several lines of addresses) and Subject:.
Only the marker and that header are removed; the first line that is not part of the
header, and everything after it, is kept. (An earlier version removed a fixed 4 lines
after the marker, which cut real text when the header was shorter and left address
lines when it was longer.)

Before the first change the original text is copied to a new column, body_raw, so
analyses can still tell a sender's own words from what they forwarded.

Usage (from the project root, on the database before this clean-up):
    uv run python -m enron.remove_forwarded_by
"""

import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"

MARKER = re.compile(r"forwarded by", re.IGNORECASE)
BLANK = re.compile(r"^\s*$")
# the end of a marker wrapped onto the next line: "PM ---------------------------"
MARKER_TAIL = re.compile(r"^\s*(?:\d{1,2}:\d{2})?\s*(?:AM|PM)?\s*-{3,}\s*$")
FIELD = re.compile(r"^\s*(?:From|To|cc|bcc|Sent(?: by)?|Date)\s*:", re.IGNORECASE)
SUBJECT = re.compile(r"^\s*Subject\s*:", re.IGNORECASE)
DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}")
# a line of addresses: user@host, <address>, or Notes names such as Mary Hain/HOU/ECT
ADDRESS = re.compile(r"@|<[^>]+>|/(?:HOU|NA|Corp|ECT|ENRON|Enron|PDX|CAL|EES|EU|LON|SF|OTS|GCO|ENRON_DEVELOPMENT)\b")
# a sender's name on its own line: a few words, no full stop at the end
NAME = re.compile(r"^\s*\"?[A-Z][\w.'\-]*(?:[ ,]+\(?[A-Za-z][\w.'\-()]*\)?){0,4}\"?\s*(?:<[^>]+>)?\s*$")


def header_end(lines: list[str], start: int) -> int:
    """Index of the first line after the header that begins at `start` (the line after
    a marker). Returns `start` (nothing removed) when no header follows."""
    i = start
    while i < len(lines) and (BLANK.match(lines[i]) or MARKER_TAIL.match(lines[i])):
        i += 1                                         # wrapped marker end, blank lines
    j, seen_field, seen_date, in_addresses = i, False, False, False
    while j < len(lines):
        line = lines[j]
        if SUBJECT.match(line):                        # the header ends with Subject:
            j += 1
            while j < len(lines) and BLANK.match(lines[j]):
                j += 1
            return j
        if FIELD.match(line):
            seen_field, in_addresses = True, True
        elif BLANK.match(line):
            in_addresses = False
        elif DATE.search(line):
            seen_date = True
        elif in_addresses and ADDRESS.search(line):
            pass                                       # To:/cc: continued on this line
        elif not seen_field and (ADDRESS.search(line) or NAME.match(line)) and _date_follows(lines, j):
            pass                                       # the sender, just above the date
        else:
            break                                      # real text starts here
        j += 1
    return j if (seen_field or seen_date) else i


def _date_follows(lines: list[str], j: int) -> bool:
    """True when the next non-blank line after j holds a date or a header field."""
    for line in lines[j + 1:j + 3]:
        if BLANK.match(line):
            continue
        return bool(DATE.search(line) or FIELD.match(line) or SUBJECT.match(line))
    return False


def clean_forwarding(text: str) -> str:
    """The text without "Forwarded by" lines and the headers of forwarded messages."""
    lines = (text or "").split("\n")
    kept, i = [], 0
    while i < len(lines):
        if MARKER.search(lines[i]):
            i = header_end(lines, i + 1)
            continue
        kept.append(lines[i])
        i += 1
    return "\n".join(kept)


def keep_raw_copy(conn: sqlite3.Connection) -> None:
    """Add emails.body_raw with the text as it is now, unless the column exists."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(emails)")}
    if "body_raw" not in columns:
        conn.execute("ALTER TABLE emails ADD COLUMN body_raw TEXT")
        conn.execute("UPDATE emails SET body_raw = body_clean")
        print("Copied the original text to emails.body_raw.")


def main():
    with sqlite3.connect(DB_PATH) as conn:
        keep_raw_copy(conn)
        rows = conn.execute("""
            SELECT email_id, body_clean FROM emails WHERE body_clean LIKE '%Forwarded by%'
        """).fetchall()
        print(f"Found {len(rows)} emails containing forwarding markers.")
        updates = [(clean_forwarding(body), email_id) for email_id, body in rows]
        conn.executemany("UPDATE emails SET body_clean = ? WHERE email_id = ?", updates)
        conn.commit()
        print(f"Updated {len(updates)} emails.")


if __name__ == "__main__":
    main()
