"""
Step 1: look at the data before doing anything with it.

Input:  data/enron_main_characters.sqlite (tables: people, emails, recipients)
Output: nothing is saved. This script only reads and prints.

Run from the project root:
    uv run python pipeline/step1_explore_data.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "enron_main_characters.sqlite"

con = sqlite3.connect(DB)
people = pd.read_sql("SELECT * FROM people", con)
emails = pd.read_sql("SELECT * FROM emails", con)
recipients = pd.read_sql("SELECT * FROM recipients", con)
con.close()

name_of = people.set_index("person_id")["name"]  # person_id -> folder name, e.g. 'dasovich-j'


def title(text):
    print("\n" + "=" * 75)
    print(text)
    print("=" * 75)


# ---------------------------------------------------------------------------
title("1. The three tables")
for table_name, df in [("people", people), ("emails", emails), ("recipients", recipients)]:
    print(f"{table_name:11s} {len(df):6d} rows   columns: {list(df.columns)}")

# ---------------------------------------------------------------------------
title("2. People (one row per mailbox owner, a 'custodian')")
print(people.head(5).to_string(index=False))
normal = people["mail"].str.match(r"^[a-z]+\.[a-z]+@enron\.com$")
print(f"\naddresses that do not look like first.last@enron.com: {(~normal).sum()} of {len(people)}")
print(people[~normal].head(6).to_string(index=False))

# ---------------------------------------------------------------------------
title("3. When were the emails sent?")
emails["date"] = pd.to_datetime(emails["date"], utc=True)
print("first:", emails["date"].min(), "   last:", emails["date"].max())
print("\nemails per year:")
print(emails["date"].dt.year.value_counts().sort_index().to_string())
month = emails["date"].dt.strftime("%Y-%m")
print("\nbusiest months:")
print(month.value_counts().head(5).to_string())

# ---------------------------------------------------------------------------
title("4. What kind of emails? (column message_type, made by a teammate)")
print(emails["message_type"].value_counts().to_string())
has_prob = emails.groupby("message_type")["human_probability"].count()
print("\nrows with a human_probability value, per type:", has_prob.to_dict())
print("\nexample subjects of 'automated' emails:")
for s in emails.loc[emails["message_type"] == "automated", "subject"].sample(5, random_state=1):
    print("   ", s)

# ---------------------------------------------------------------------------
title("5. Senders, recipients and recipients per email")
sent = emails["sender_id"].value_counts()
received = recipients["recipient_id"].value_counts()
print(f"people who sent at least one email:     {sent.size} of {len(people)}")
print(f"people who received at least one email: {received.size} of {len(people)}")
print(f"emails sent per person:     median {sent.median():.0f}, max {sent.max()} ({name_of[sent.idxmax()]})")
print(f"emails received per person: median {received.median():.0f}, max {received.max()} ({name_of[received.idxmax()]})")

n_rec = recipients.groupby("email_id").size()
print(f"\nemails with no recipient row: {(~emails['email_id'].isin(n_rec.index)).sum()}")
bins = pd.cut(n_rec, [0, 1, 4, 9, 1000], labels=["1", "2-4", "5-9", "10+"])
print("recipients (among the 148) per email:")
print(bins.value_counts().sort_index().to_string())
big = n_rec[n_rec >= 5]
print(f"share of all recipient rows that come from emails to 5+ people: {big.sum() / n_rec.sum():.1%}")

# emails that a person sent to themself
rows = recipients.merge(emails[["email_id", "sender_id"]], on="email_id")
to_self = rows[rows["recipient_id"] == rows["sender_id"]]
print(f"\nrecipient rows where sender = recipient (email to oneself): {len(to_self)}")

# ---------------------------------------------------------------------------
title("6. Email text (column body_clean)")
body = emails["body_clean"].fillna("")
length = body.str.len()
print(f"characters per body: median {length.median():.0f}, 90% below {length.quantile(0.9):.0f}")
print(f"bodies under 50 characters: {(length < 50).sum()}")
print(f"contains a forwarded block ('Forwarded by'):     {body.str.contains('Forwarded by').mean():.1%}")
print(f"contains a quoted reply ('-----Original Message'): {body.str.contains('Original Message').mean():.1%}")

print("\ntwo random emails (first 600 characters):")
for _, e in emails[emails["message_type"] != "automated"].sample(2, random_state=7).iterrows():
    print(f"\n--- from {name_of[e['sender_id']]}, {e['date']:%Y-%m-%d}, subject: {e['subject']}")
    print(e["body_clean"][:600])

# ---------------------------------------------------------------------------
title("7. Possible duplicates: same sender, subject, body and recipients")
recipient_set = recipients.groupby("email_id")["recipient_id"].apply(lambda s: tuple(sorted(s)))
emails["recipient_set"] = emails["email_id"].map(recipient_set)
key = ["sender_id", "subject", "body_clean", "recipient_set"]
dups = emails[emails.duplicated(key, keep=False)]
n_extra = emails.duplicated(key).sum()
print(f"emails that have an identical twin: {len(dups)}; extra copies: {n_extra} ({n_extra / len(emails):.1%})")

# how far apart in time are the copies? same moment = same email stored twice
gap_hours = dups.groupby(key)["date"].agg(lambda d: (d.max() - d.min()).total_seconds() / 3600)
print("time between the first and last copy (groups of identical emails):")
print(f"   same time:            {(gap_hours == 0).sum()}")
up_to_12 = gap_hours[(gap_hours > 0) & (gap_hours <= 12)]
print(f"   0 to 12 hours:        {len(up_to_12)}  (of which exact whole hours, i.e. a time-zone "
      f"shift: {(up_to_12 % 1 == 0).sum()})")
print(f"   12 hours to 1 week:   {((gap_hours > 12) & (gap_hours <= 168)).sum()}")
print(f"   more than 1 week:     {(gap_hours > 168).sum()}")

# ---------------------------------------------------------------------------
title("8. Where was each email found? (source_path = mailbox \\ folder \\ file)")
parts = emails["source_path"].str.split("\\", regex=False)
emails["mailbox"] = parts.str[0]
emails["folder"] = parts.str[1]
print(emails["folder"].value_counts().head(6).to_string())
own = emails["mailbox"] == emails["sender_id"].map(name_of)
print(f"\nfound in the sender's own mailbox: {own.mean():.1%} of emails")
