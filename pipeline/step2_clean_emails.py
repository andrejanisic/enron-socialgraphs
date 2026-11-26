"""
Step 2: clean the email data (decisions made after Step 1).

Input:  data/enron_main_characters.sqlite
Output: pipeline/output/emails_clean.csv      one row per email we keep
        pipeline/output/recipients_clean.csv  one row per (email, recipient) arrow
        pipeline/output/cleaning_log.csv      how many rows each rule removed

Decisions:
  D. drop emails with broken dates (before 1999)
  B. drop machine-generated emails, found by OUR OWN subject rules (see Step 2b:
     the teammate's 'automated' label misses system emails and also marks
     human emails as automated, so we do not use it)
  A. drop duplicate copies: same sender, subject, recipients and body (ignoring
     whitespace), sent at the same moment or a whole number of hours apart
     (at most 12 h, a time-zone copy). Copies further apart are kept as real resends.
  C. drop recipient rows where the sender emails themself, then drop emails
     that have no recipient left
  E. mass emails (5+ recipients) are KEPT; we test their effect later.

Run from the project root:
    uv run python pipeline/step2_clean_emails.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "enron_main_characters.sqlite"
OUT = ROOT / "pipeline" / "output"
OUT.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(DB)
emails = pd.read_sql("SELECT * FROM emails", con)
recipients = pd.read_sql("SELECT * FROM recipients", con)
con.close()

emails["date"] = pd.to_datetime(emails["date"], utc=True)
emails["subject"] = emails["subject"].fillna("")
emails["body_clean"] = emails["body_clean"].fillna("")

log = []


def record(rule):
    """Remember how many emails and arrows are left after each rule."""
    rec = recipients[recipients["email_id"].isin(emails["email_id"])]
    log.append({"rule": rule, "emails": len(emails), "recipient_rows": len(rec)})
    print(f"{rule:45s} emails {len(emails):6d}   recipient rows {len(rec):6d}")


record("start")

# D. broken dates ----------------------------------------------------------
emails = emails[emails["date"].dt.year >= 1999]
record("D. drop dates before 1999")

# B. machine-generated emails ------------------------------------------------
# A subject pattern for each kind of system email we found in Step 2b.
MACHINE_SUBJECTS = [
    r"TRV Notification", r"ERV Notification",       # risk-report system
    r"^Request (?:Submitted|Closed)",                # IT access-request system
    r"Synchronization Log",                          # Outlook sync log
    r"AutoReply|Auto Reply|is out of the office",    # automatic out-of-office replies
    r"^Commissioner\.COM",                           # fantasy-football website notices
]
machine = emails["subject"].str.contains("|".join(MACHINE_SUBJECTS), case=False, regex=True)
print("\n   our rule vs the teammate's label (rows: their label, columns: our rule says machine?)")
print(pd.crosstab(emails["message_type"], machine).to_string().replace("\n", "\n   "))
print()
emails = emails[~machine]
record("B. drop machine-generated (our subject rules)")

# A. duplicate copies ------------------------------------------------------
recipient_set = recipients.groupby("email_id")["recipient_id"].apply(lambda s: tuple(sorted(s)))
emails["recipient_set"] = emails["email_id"].map(recipient_set)
emails["body_key"] = emails["body_clean"].str.split().str.join(" ")  # ignore spaces and line breaks

KEY = ["sender_id", "subject", "recipient_set", "body_key"]
duplicate_ids = []
example = None
for _, group in emails.sort_values("date").groupby(KEY):
    if len(group) == 1:
        continue
    kept_times = []  # times of the copies we keep in this group
    for email_id, t in zip(group["email_id"], group["date"]):
        is_copy = False
        for k in kept_times:
            seconds = abs((t - k).total_seconds())
            if seconds <= 12 * 3600 and seconds % 3600 == 0:  # 0, 1, 2, ... 12 whole hours apart
                is_copy = True
        if is_copy:
            duplicate_ids.append(email_id)
        else:
            kept_times.append(t)
    if example is None and len(group) >= 2 and len(kept_times) < len(group):
        example = group

emails = emails[~emails["email_id"].isin(duplicate_ids)]
record("A. drop duplicate copies")

if example is not None:
    print("\n   example of one duplicate group (same email found twice):")
    print(example[["email_id", "date", "source_path"]].to_string(index=False))
    print()

# C. emails to oneself -----------------------------------------------------
recipients = recipients[recipients["email_id"].isin(emails["email_id"])]
sender_of = emails.set_index("email_id")["sender_id"]
recipients = recipients[recipients["recipient_id"] != recipients["email_id"].map(sender_of)]
record("C1. drop recipient rows sender = recipient")
emails = emails[emails["email_id"].isin(recipients["email_id"])]
record("C2. drop emails with no recipient left")

# save -----------------------------------------------------------------------
keep = ["email_id", "date", "sender_id", "subject", "body_clean", "message_type",
        "human_probability", "source_path"]
emails[keep].to_csv(OUT / "emails_clean.csv", index=False)
recipients.to_csv(OUT / "recipients_clean.csv", index=False)
pd.DataFrame(log).to_csv(OUT / "cleaning_log.csv", index=False)

# a few facts about the cleaned data ----------------------------------------
n_rec = recipients.groupby("email_id").size()
print(f"\nsaved {len(emails)} emails and {len(recipients)} recipient rows to {OUT}")
print(f"senders: {emails['sender_id'].nunique()}, recipients: {recipients['recipient_id'].nunique()}")
print(f"dates: {emails['date'].min():%Y-%m-%d} to {emails['date'].max():%Y-%m-%d}")
print(f"emails to 5+ people: {(n_rec >= 5).sum()} ({(n_rec >= 5).mean():.1%} of emails), "
      f"giving {n_rec[n_rec >= 5].sum() / n_rec.sum():.1%} of recipient rows")
