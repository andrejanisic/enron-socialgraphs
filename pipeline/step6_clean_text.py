"""
Step 6: clean the email text, so that it describes WHAT an email is about, not WHO wrote it.

Input:  pipeline/output/emails_clean.csv, recipients_clean.csv, people.csv, communities.csv
Output: pipeline/output/text_clean.csv        one row per email: content words, usable yes/no
        pipeline/output/review_20_emails.txt  20 random emails before and after cleaning (read them!)

Decisions:
  T1. The text of an email = subject + the words its sender wrote. The body is cut at the first
      'Forwarded by' / 'Original Message' / quoted header ('From:' or 'To:' at the start of a line).
      Forwarded content was written by someone else; it is only used in a robustness check later.
  T2. Removed: greeting line ('Kim,'), everything from the closing on ('Thanks, Jeff'), signature,
      address and disclaimer lines, email addresses, Lotus Notes addresses, URLs and numbers.
  T3. Names removed: (a) every name token of the 148 custodians plus common nicknames,
      (b) every PERSON that spaCy finds (Week 7, named-entity recognition).
      A few names are also everyday trading words (Rick BUY, Michelle CASH, 'mark to market');
      those words are PROTECTED and kept.
  T4. An email is 'usable' for text analysis if at least 50 characters of content words are left.
      Unusable emails stay in the network; they are only left out of the text analysis.
  T5. Checks: what was removed, no custodian name left in the vocabulary, top words per community,
      and 20 random emails to read by hand.

Run from the project root (takes about a minute because of spaCy):
    uv run python pipeline/step6_clean_text.py
"""
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import spacy
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"

emails = pd.read_csv(OUT / "emails_clean.csv")
emails["subject"] = emails["subject"].fillna("")
emails["body_clean"] = emails["body_clean"].fillna("")
recipients = pd.read_csv(OUT / "recipients_clean.csv")
people = pd.read_csv(OUT / "people.csv", index_col="person_id")
community = pd.read_csv(OUT / "communities.csv", index_col="person_id")["community"]


def title(text):
    print("\n" + "=" * 75)
    print(text)
    print("=" * 75)


# ---------------------------------------------------------------------------
# T1 + T2: the sender's own words, without greeting, closing and signature
PREFIX = re.compile(r"^\s*(?:(?:re|fw|fwd)\s*:\s*)+", re.IGNORECASE)
# start of a forwarded or quoted part (a memo that itself STARTS with 'To:' / 'From:' is not cut, see below)
CUT = re.compile(r"-{3,}\s*(?:Original Message|Forwarded by|Inline attachment follows)|^\s*(?:From|To):\s",
                 re.IGNORECASE | re.MULTILINE)
GREETING = re.compile(r"^[\w .&'-]{1,30}[,:]$")            # a short first line like 'Kim,' or 'Hi John:'
# a line that is ONLY a closing, maybe with a name: 'Thanks,'  'Thanks, Jeff'  'Best regards'
CLOSING = re.compile(r"^(?:thanks|thank you|thx|regards|best regards|best|cheers|sincerely|take care|rgds)"
                     r"[\s,.!-]*(?:[A-Za-z]+\.?\s*){0,2}$", re.IGNORECASE)
# signature and address lines are SHORT lines; a long paragraph that mentions 'phone' is content
SIGNATURE = re.compile("|".join([
    r"\d{3}[\s.)/-]+\d{3}[\s.-]+\d{4}",                   # phone and fax numbers
    r"\b(?:phone|fax|tel|cell|mobile|pager)\b",
    r"smith street|louisiana st|\bsuite\b|houston,? (?:tx|texas)|portland,? or|\b77002\b|\beb ?\d{3,4}",
    r"enron north america corp|enron wholesale services|legal department",
    r"sent from my blackberry",
]), re.IGNORECASE)
DISCLAIMER = re.compile(r"^(?:this e-?mail|this message|the information (?:contained|in this)|confidentiality notice)"
                        r"|intended only for the use|if you are not the intended recipient", re.IGNORECASE)
ADDRESS = re.compile(r"\S+@\S+|https?://\S+|www\.\S+|"                    # email addresses, URLs
                     r"[\w.'-]+(?: [\w.'-]+)*/[A-Za-z&]+/[A-Za-z&]+(?:@[A-Za-z&]+)?")  # Notes 'Kim Ward/HOU/ECT'

removed = Counter()       # how often each kind of removal happened
signature_lines = Counter()


def own_words(subject, body):
    body = body.strip()
    first = CUT.search(body)
    if first and first.start() == 0 and re.match(r"(?:From|To):", body, re.IGNORECASE):
        first = CUT.search(body, 1)            # a memo that starts with 'To:/From:' lines is the sender's own text
    if first:
        body = body[:first.start()]
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if lines and GREETING.match(lines[0]):
        lines = lines[1:]
        removed["greeting line"] += 1
    for i in range(max(0, len(lines) - 6), len(lines)):        # closing within the last 6 lines
        if len(lines[i]) <= 30 and CLOSING.match(lines[i]):
            removed["closing and everything after"] += 1
            lines = lines[:i]
            break
    kept = []
    for ln in lines:
        if len(ln) <= 80 and SIGNATURE.search(ln):
            signature_lines[ln[:60]] += 1
            removed["signature/address line"] += 1
        elif DISCLAIMER.search(ln):
            removed["disclaimer paragraph"] += 1
        else:
            kept.append(ln)
    text = PREFIX.sub("", subject) + "\n" + "\n".join(kept)
    return ADDRESS.sub(" ", text)


emails["had_forward"] = emails["body_clean"].str.contains(CUT)
emails["own_text"] = [own_words(s, b) for s, b in zip(emails["subject"], emails["body_clean"])]

# ---------------------------------------------------------------------------
# T3: names
NICKNAMES = {"tom", "bert", "bill", "jim", "greg", "jeff", "mike", "steve", "chris", "dave", "dan", "rick",
             "rob", "bob", "ben", "matt", "joe", "phil", "andy", "doug", "liz", "kate", "vince", "larry",
             "harry", "jay", "geoff", "brad", "sam", "tim", "pat", "jerry", "sue", "deb", "kim", "tana",
             "sara", "dutch", "errol", "vladi", "jmf", "dana"}
PROTECT = {"buy", "cash", "south", "white", "love", "heard", "lay", "mark", "bill", "may", "will", "price"}
name_tokens = set(NICKNAMES)
for full, folder in zip(people["full_name"].fillna(""), people["name"]):
    name_tokens |= {t.lower() for t in re.findall(r"[A-Za-z]+", f"{full} {folder}") if len(t) >= 3}
name_tokens -= PROTECT

# spaCy finds PERSON names. Rule: a word that spaCy calls a person in MOST of the emails where it
# appears (and in at least 3 emails) is a name and is removed everywhere. spaCy is a general-purpose
# model and calls some energy jargon a person, so these 16 words were checked by hand and are kept
# (from the list of all 149 such words used in 10+ emails, read on 18 Nov 2026):
JARGON = {"edison", "mmbtu", "waha", "perm", "frontera", "tues", "fri", "aquila", "treasurer", "oneok",
          "rsvp", "crestar", "tenn", "assemblyman", "max", "devon"}
nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "tagger", "attribute_ruler"])
person_words = Counter()          # in how many emails spaCy put a word inside a PERSON name
for doc in nlp.pipe(emails["own_text"], batch_size=256):
    person_words.update({w.lower() for e in doc.ents if e.label_ == "PERSON"
                         for w in re.findall(r"[A-Za-z]+", e.text)})
all_words = Counter(w for s in emails["own_text"] for w in set(re.findall(r"[a-z]+", s.lower())))
person_share = {w: person_words[w] / all_words[w] for w in person_words if all_words[w]}
spacy_names = {w for w, s in person_share.items() if s >= 0.5 and person_words[w] >= 3} - JARGON - PROTECT

# T4: content words (lowercase, 3+ letters, no stop words, no names)
EMAIL_WORDS = {"enron", "ect", "hou", "corp", "ees", "ena", "cc", "pm", "am", "subject", "re", "fw", "fwd",
               "forwarded", "original", "message", "sent", "com", "www", "http", "https", "mailto", "thanks",
               "thank", "email", "mail", "nbsp", "amp", "quot"}
STOP = set(ENGLISH_STOP_WORDS) | EMAIL_WORDS


DROP = STOP | name_tokens | spacy_names
emails["text"] = [" ".join(t for t in re.findall(r"[a-z]{3,}", s.lower()) if t not in DROP)
                  for s in emails["own_text"]]
emails["n_words"] = emails["text"].str.split().str.len()
emails["usable"] = emails["text"].str.len() >= 50

# ---------------------------------------------------------------------------
title("1. The sender's own words (T1)")
print(f"emails: {len(emails)}; with a forwarded or quoted part: {emails['had_forward'].mean():.1%}")
pure_forward = emails["had_forward"] & (emails["n_words"] < 3)
print(f"pure forwards (sender added fewer than 3 content words): {pure_forward.sum()}")

title("2. What was removed (T2)")
for kind, n in removed.most_common():
    print(f"   {kind:38s} {n:6d} times")
print("\nmost frequent removed signature/address/disclaimer lines:")
for ln, n in signature_lines.most_common(10):
    print(f"   {n:4d} x  {ln}")

title("3. Names (T3)")
print(f"custodian name tokens + nicknames removed everywhere: {len(name_tokens)}")
print(f"protected (names that are also everyday words, kept): {sorted(PROTECT)}")
extra = sorted(spacy_names - name_tokens, key=lambda w: -person_words[w])
print(f"extra names found by spaCy and removed everywhere: {len(extra)}; most frequent:")
print("   " + ", ".join(f"{w} ({person_words[w]})" for w in extra[:30]))
print(f"business words spaCy mistakes for names, KEPT (hand-checked): {sorted(JARGON)}")
sometimes = sorted((w for w, s in person_share.items() if 0.2 <= s < 0.5 and all_words[w] >= 30
                    and w not in STOP and len(w) >= 3), key=lambda w: -all_words[w])
print("tagged as a person in only 20-50% of their emails, so KEPT (most common):")
print("   " + ", ".join(f"{w} ({person_share[w]:.0%})" for w in sometimes[:20]))

title("4. Which emails are usable for text analysis (T4)")
print(f"usable: {emails['usable'].sum()} of {len(emails)} ({emails['usable'].mean():.1%}); "
      f"content words per usable email: median {emails.loc[emails['usable'], 'n_words'].median():.0f}")
emails["sender_community"] = emails["sender_id"].map(community)
print("usable emails by sender community:", emails[emails["usable"]].groupby("sender_community").size().to_dict())
arrows = recipients.merge(emails[["email_id", "usable"]], on="email_id")
usable_received = arrows[arrows["usable"]].groupby("recipient_id").size().reindex(people.index, fill_value=0)
ok = (usable_received >= 20) & ~people["mixed_identity"]
print(f"people with >= 20 usable received emails (mixed mailbox left out): {ok.sum()} of {len(people)}")
print(f"   (these are the people in the main test H1; median usable received: {usable_received[ok].median():.0f})")

title("5. Vocabulary check (T5)")
vec = CountVectorizer(min_df=5, token_pattern=r"[a-z]{3,}")
X = vec.fit_transform(emails.loc[emails["usable"], "text"])
vocab = set(vec.get_feature_names_out())
print(f"vocabulary (words in 5+ usable emails): {len(vocab)} words")
print(f"custodian name tokens left in the vocabulary: {sorted(vocab & name_tokens) or 'none'}")
print(f"spaCy names left in the vocabulary: {sorted(vocab & spacy_names) or 'none'}")

title("6. Most typical words per sender community (share of the community's emails minus elsewhere)")
usable = emails[emails["usable"]]
has_word = pd.DataFrame.sparse.from_spmatrix(X > 0, columns=vec.get_feature_names_out()).astype(float)
for c in sorted(usable["sender_community"].dropna().unique()):
    inside = (usable["sender_community"] == c).to_numpy()
    diff = has_word[inside].mean() - has_word[~inside].mean()
    print(f"   C{int(c)}: " + ", ".join(diff.sort_values(ascending=False).head(12).index))

# ---------------------------------------------------------------------------
sample = emails.sample(20, random_state=11)
with open(OUT / "review_20_emails.txt", "w") as f:
    for _, e in sample.iterrows():
        f.write(f"===== email {e['email_id']} from {people.loc[e['sender_id'], 'name']}, usable: {e['usable']}\n")
        f.write("--- BEFORE (subject + body, first 700 characters)\n")
        f.write(f"{e['subject']}\n{e['body_clean'][:700]}\n")
        f.write(f"--- AFTER ({e['n_words']} content words)\n{e['text']}\n\n")
emails[["email_id", "sender_id", "text", "n_words", "usable", "had_forward"]].to_csv(
    OUT / "text_clean.csv", index=False)
print(f"\nsaved text_clean.csv and review_20_emails.txt to {OUT}")
