
import sqlite3
import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"
NAMES_PATH = PROJECT_ROOT / "data" / "temp_names.csv"
MAILS_PATH = PROJECT_ROOT / "data" / "temp_mails.csv"

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)


def extract_addresses(text):
    if not text:
        return set()

    return {
        address.lower()
        for address in EMAIL_PATTERN.findall(text)
    }


def main():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # 1. Import people
        with open(NAMES_PATH, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row["name"].strip()
                mail = row["mail"].strip().lower()

                conn.execute("""
                    INSERT OR IGNORE INTO people (name, mail)
                    VALUES (?, ?)
                """, (name, mail))

        # Build complete address -> person_id mapping.
        people = {
            mail.lower(): person_id
            for person_id, mail in conn.execute(
                "SELECT person_id, mail FROM people"
            )
        }

        print("People loaded.")

        # 2. Import emails
        imported = 0
        skipped_sender = 0
        skipped_duplicate = 0
        recipient_links = 0

        with open(MAILS_PATH, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                sender = (row.get("sender") or "").strip().lower()
                sender_id = people.get(sender)

                if sender_id is None:
                    skipped_sender += 1
                    continue

                source_path = row.get("path")

                # Avoid importing existing emails.
                if source_path and conn.execute("""
                    SELECT 1 FROM emails WHERE source_path = ?
                """, (source_path,)).fetchone():
                    skipped_duplicate += 1
                    continue

                cursor = conn.execute("""
                    INSERT INTO emails (
                        date,
                        sender_id,
                        subject,
                        body_clean,
                        message_type,
                        human_probability,
                        source_path
                    )
                    VALUES (?, ?, ?, ?, 'human', NULL, ?)
                """, (
                    row.get("date"),
                    sender_id,
                    row.get("subject"),
                    row.get("body_clean"),
                    source_path
                ))

                email_id = cursor.lastrowid
                imported += 1

                # 3. Import known recipients.
                addresses = extract_addresses(row.get("recipients"))

                for address in addresses:
                    recipient_id = people.get(address)

                    if recipient_id is None:
                        continue

                    result = conn.execute("""
                        INSERT OR IGNORE INTO recipients (
                            email_id,
                            recipient_id
                        )
                        VALUES (?, ?)
                    """, (email_id, recipient_id))

                    recipient_links += result.rowcount

        conn.commit()

        print("\nImport completed.")
        print(f"Emails imported:           {imported:,}")
        print(f"Duplicate emails skipped:  {skipped_duplicate:,}")
        print(f"Unknown senders skipped:   {skipped_sender:,}")
        print(f"Recipient links inserted:  {recipient_links:,}")


if __name__ == "__main__":
    main()
