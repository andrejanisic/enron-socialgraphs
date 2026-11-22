"""Preparing the emails for text analysis: each sender's own words only.

Steps: keep human-written emails (without Outlook synchronisation logs), cut
forwarded and quoted messages (found in body_raw, which keeps the "Forwarded by"
lines that body_clean no longer has), drop sign-off initials and lines
that repeat across many emails (signatures, addresses, disclaimers), and keep
one copy of emails sent more than once with the same text. Long emails that
are mostly a pasted news article (a byline, a news agency, "Published ...") are
marked `press`: they show what people passed on, not what they wrote.
"""

import re

import pandas as pd

# The first line of a forwarded or quoted message; everything from here on is
# someone else's text
QUOTE_START = re.compile(
    r"^\s*(?:-+\s*Forwarded by|-+\s*Original Message|From:\s|To:\s|Sent:\s|Subject:\s|cc:\s*$"
    r"|\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\s*$)",
    re.IGNORECASE | re.MULTILINE)
QUOTED_LINE = re.compile(r"^\s*>.*$", re.MULTILINE)
# Outlook synchronisation logs that passed the human-written filter
SYNC_LOG = re.compile(r"Synchronizing (?:Mailbox|Folder|Hierarchy|Favorites)")
# Signs of a pasted news article: bylines, news agencies, newspapers, "(Published ...)"
PRESS = re.compile(
    r"\bBYLINE\b|\bHEADLINE:|\b(?i:staff writers?)\b|\(Published\b|\bCopyright\b|©|All rights reserved"
    r"|\bDow Jones\b|\bReuters\b|\bAssociated Press\b|\(Bloomberg\)|\bBloomberg News\b|\bKnight Ridder\b"
    r"|\bNews Service\b|\b(?:Los Angeles|New York) Times\b|\bWall Street Journal\b|\bWashington Post\b"
    r"|\bSan Francisco Chronicle\b|\bSacramento Bee\b|\bMercury News\b|\bHouston Chronicle\b"
    r"|\bFinancial Times\b|\bESPN\.com\b|\bPress Release\b|FOR IMMEDIATE RELEASE|BUSINESS WIRE|PR Newswire"
    r"|Union[- ]Tribune|Orange County Register|sfgate\.com|POLITICAL WRITER|\bTimes Staff\b"
    r"|\b(?i:see (?:the )?(?:story|article) below)\b|\bInterested in subscribing\b"
    r"|^\s*By [A-Z][a-z]+(?: [A-Z]\.)? [A-Z][a-z'-]+(?:,| and |\s*$)", re.MULTILINE)
MIN_PRESS_WORDS = 150      # shorter emails that name a newspaper are not articles


def human_written(emails: pd.DataFrame, threshold: float) -> pd.Series:
    """True for emails marked human, or uncertain with human_probability >= threshold."""
    return (emails["message_type"] == "human") | (
        (emails["message_type"] == "uncertain") & (emails["human_probability"] >= threshold))


def own_text(body: str) -> str:
    """The sender's own words: the body up to the first forwarded or quoted message,
    without lines starting with '>'."""
    body = body or ""
    match = QUOTE_START.search(body)
    if match:
        body = body[:match.start()]
    return QUOTED_LINE.sub("", body).strip()


def is_press(text: str, n_words: int) -> bool:
    """True for a long email with signs of a pasted news article."""
    return n_words >= MIN_PRESS_WORDS and bool(PRESS.search(text))


def frequent_lines(texts, min_emails: int) -> set:
    """Lines (stripped) found in at least `min_emails` different emails: signatures,
    addresses, disclaimers, sign-offs such as 'Thanks,'."""
    counts = pd.Series([line for t in texts for line in {l.strip() for l in t.split("\n")} if line])
    counts = counts.value_counts()
    return set(counts[counts >= min_emails].index)


INITIALS = re.compile(r"^\W*[A-Za-z]{1,3}\W*$")   # sign-offs such as "DF" or "ds"


def drop_lines(text: str, lines: set) -> str:
    """Drop the given lines and lines that are only initials."""
    kept = [l for l in text.split("\n")
            if l.strip() and l.strip() not in lines and not INITIALS.match(l)]
    return re.sub(r"[ \t]+", " ", "\n".join(kept)).strip()


def prepare_emails(emails: pd.DataFrame, threshold: float = 0.8, min_emails: int = 15,
                   min_words: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cleaned emails (one row each, columns `text` and `press`) and the number left
    after each step. Pasted news articles stay in, marked `press`."""
    steps = [("all emails", len(emails))]
    out = emails[human_written(emails, threshold)].copy()
    steps.append((f"human-written (threshold {threshold})", len(out)))
    out = out[~out["body_raw"].fillna("").str.contains(SYNC_LOG)]
    steps.append(("not an Outlook synchronisation log", len(out)))
    out["text"] = out["body_raw"].map(own_text)      # body_raw keeps the "Forwarded by" lines
    boiler = frequent_lines(out["text"], min_emails)
    out["text"] = out["text"].map(lambda t: drop_lines(t, boiler))
    out["n_words"] = out["text"].str.split().str.len()
    out = out[out["n_words"] >= min_words]
    steps.append((f"with own text of at least {min_words} words", len(out)))
    out = out.drop_duplicates(["sender_id", "text"])
    steps.append(("one copy per sender and text", len(out)))
    out["press"] = [is_press(t, n) for t, n in zip(out["text"], out["n_words"])]
    steps.append(("own words (pasted news articles set aside)", int((~out["press"]).sum())))
    counts = pd.DataFrame(steps, columns=["step", "emails"])
    return out.reset_index(drop=True), counts
