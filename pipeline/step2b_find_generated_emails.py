"""
Step 2b: are there machine-generated emails left after Step 2?

Idea: a machine writes the same thing again and again. So we look for
  1. subjects that repeat many times (after replacing numbers and dates by '#')
  2. bodies that repeat many times
  3. typical system phrases (sync logs, out-of-office replies, calendar replies)
and we read examples. This script only prints; it changes nothing.

Run from the project root:
    uv run python pipeline/step2b_find_generated_emails.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"

emails = pd.read_csv(OUT / "emails_clean.csv")
recipients = pd.read_csv(OUT / "recipients_clean.csv")
emails["subject"] = emails["subject"].fillna("")
emails["body_clean"] = emails["body_clean"].fillna("")
emails["n_recipients"] = emails["email_id"].map(recipients.groupby("email_id").size())


def subject_pattern(s):
    """'RE: EOL Report 10/03/00' -> 'eol report #/#/#'"""
    s = s.lower()
    s = pd.Series(s).str.replace(r"^((re|fw|fwd)\s*:\s*)+", "", regex=True)[0]
    s = pd.Series(s).str.replace(r"\d+", "#", regex=True)[0]
    return " ".join(s.split())


emails["pattern"] = emails["subject"].map(subject_pattern)

print("=" * 75)
print("1. Every subject pattern used 10+ times (numbers replaced by #)")
print("   A machine repeats itself, so any large group of system emails shows up here.")
print("=" * 75)
top = (emails.groupby("pattern")
       .agg(emails=("email_id", "size"), senders=("sender_id", "nunique"),
            mean_recipients=("n_recipients", "mean"))
       .sort_values("emails", ascending=False))
print(top[top["emails"] >= 10].round(1).to_string())

print("\n" + "=" * 75)
print("2. Most repeated bodies (same first 200 characters)")
print("=" * 75)
emails["body_start"] = emails["body_clean"].str.split().str.join(" ").str[:200]
body_counts = emails[emails["body_start"].str.len() > 30]["body_start"].value_counts()
for text, n in body_counts.head(10).items():
    print(f"{n:4d} x  {text[:110]}")

print("\n" + "=" * 75)
print("3. Typical system phrases")
print("=" * 75)
phrases = {
    "sync log": r"synchronization log",
    "trv/erv report": r"[te]rv notification",
    "auto-reply": r"auto.?reply|is out of the office",
    "out of office": r"out of (?:the )?office",
    "calendar reply": r"^(?:accepted|declined|tentative|updated|invitation)\s*:",
    "delivery failure": r"undeliverable|delivery status|mail delivery",
    "do not reply": r"do not reply",
}
text = (emails["subject"] + " " + emails["body_clean"].str[:300]).str.lower()
for name, pat in phrases.items():
    hit = text.str.contains(pat, regex=True)
    print(f"{name:17s} {hit.sum():5d}   e.g. {emails.loc[hit, 'subject'].head(2).tolist()}")

print("\n" + "=" * 75)
print("4. The teammate's human_probability for 'uncertain' emails")
print("=" * 75)
p = emails.loc[emails["message_type"] == "uncertain", "human_probability"]
print(pd.cut(p, [0, 0.2, 0.4, 0.6, 0.8, 1.0]).value_counts().sort_index().to_string())
print("\nfive 'uncertain' emails with the LOWEST human_probability:")
for _, e in emails[emails["message_type"] == "uncertain"].nsmallest(5, "human_probability").iterrows():
    print(f"  p={e['human_probability']:.2f}  {e['subject'][:50]!r:52s} {e['body_start'][:70]!r}")
