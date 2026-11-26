"""
Step 5: information about people that later steps need, and checks that it can be trusted.

Input:  data/enron_external.sqlite (person_info: names, titles, departments, made by a teammate)
        data/enron_main_characters.sqlite (people: the email address each mailbox was built from)
        pipeline/output/communities.csv, emails_clean.csv (Steps 2 and 4)
Output: pipeline/output/people.csv  one row per person: name, titles, senior yes/no, department

Checks and decisions:
  1. Identity: does person_info describe the person whose emails we have? Two kinds of evidence:
     the mailbox's own email address, and the first name people use in their own emails
     (sign-off, 'Forwarded by Name/Unit/Org' lines). Wrong rows are corrected by hand (CORRECTIONS).
  2. Seniority (M): senior = a title of VP or higher (VP, Vice President, President, Managing
     Director, CEO/COO/CFO/CTO/CRO, Chief ..., General Counsel, Chairman). 'Director' alone is NOT
     senior: at Enron it was a middle rank ('Dir Trading' is an ordinary trader title).
     (N) Senior if EITHER title list says so; disagreements are printed.
  3. Departments: checked for everyone with evidence, at business-unit level (ETS / EES /
     ENA and corporate), using the Lotus Notes address in their own emails ('Name/HOU/ECT').
     Desks inside ENA (Gas West, Gas East, ...) cannot be checked this way.

Run from the project root:
    uv run python pipeline/step5_people.py
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"

SENIOR = re.compile(r"\bvp\b|vice president|president|managing director|mng dir|\bceo\b|\bcoo\b|"
                    r"\bcfo\b|\bcto\b|\bcro\b|chief|general counsel|chairman", re.IGNORECASE)

# Rows of person_info that describe a DIFFERENT person than the one whose emails we have
# (found by the identity check below; evidence read by hand on 18 Nov 2026).
CORRECTIONS = {
    97: {   # mcconnell-m
        "full_name": "Mark McConnell", "department": "ETS", "jse_title": None, "edo_title": None,
        "why": "emails come from mark.mcconnell@enron.com and are signed 'Mark McConnell, Transwestern "
               "Pipeline Company'; person_info describes Mike McConnell (EGM President & CEO)"},
    137: {  # hodge-j
        "full_name": "Jeffrey T. Hodge", "department": "ENA Legal", "jse_title": None, "edo_title": None,
        "why": "emails come from t..hodge@enron.com, are signed 'Jeff', Notes address 'Jeffrey T Hodge/HOU/ECT', "
               "written to Legal colleagues; person_info describes John Hodge (gas trader)"},
}

# Mailboxes that MIX two different people: we cannot split their emails, so later steps keep them
# in the network but leave them out of the person-level tests (H1, H2b).
MIXED = {
    83: "campbell-l: its own emails are from Larry F. Campbell (ETS, Transwestern environmental work), "
        "but 32 of the 54 emails it receives come from Don Baughman's East Power real-time desk "
        "('24 Hour Group', 'PJM schedule') and were meant for a different Larry Campbell, a trader",
}

con = sqlite3.connect(ROOT / "data" / "enron_main_characters.sqlite")
con.execute(f"ATTACH DATABASE '{ROOT / 'data' / 'enron_external.sqlite'}' AS ext")
info = pd.read_sql("""SELECT p.person_id, p.mail AS mailbox_address, i.email AS info_address,
                             i.full_name, i.jse_title, i.edo_title, i.jse_department AS department
                      FROM people p JOIN ext.person_info i USING (person_id)""", con).set_index("person_id")
con.close()
comm = pd.read_csv(OUT / "communities.csv", index_col="person_id")
people = comm[["name", "community"]].join(info)  # only the 147 people in the network
emails = pd.read_csv(OUT / "emails_clean.csv", usecols=["email_id", "sender_id", "body_clean"])
emails["body_clean"] = emails["body_clean"].fillna("")

CUT = re.compile(r"-{3,}\s*(?:Original Message|Forwarded by)|^\s*From:", re.MULTILINE)
NOTES = re.compile(r"Forwarded by ([A-Z][A-Za-z .'-]+?)/([A-Za-z&]+/[A-Za-z&]+)")


def title(text):
    print("\n" + "=" * 75)
    print(text)
    print("=" * 75)


def own_evidence(pid, surname):
    """First names and Notes units a person uses in their OWN sent emails."""
    sign, notes = {}, []
    for body in emails.loc[emails["sender_id"] == pid, "body_clean"]:
        lines = [ln.strip(" -,") for ln in CUT.split(body)[0].splitlines() if ln.strip()]
        if lines and re.fullmatch(r"[A-Za-z]{2,12}", lines[-1]):       # one-word sign-off, e.g. 'Jeff'
            sign[lines[-1].lower()] = sign.get(lines[-1].lower(), 0) + 1
        notes += [(n, unit) for n, unit in NOTES.findall(body)           # 'Forwarded by Kim Ward/HOU/ECT'
                  if surname in n.lower().replace(" ", "")]
    return sign, notes


evidence = {}
for pid, p in people.iterrows():
    evidence[pid] = own_evidence(pid, p["name"].split("-")[0].lower()[:5])

# ---------------------------------------------------------------------------
title("1. Identity: does person_info describe the person whose emails we have?")
print("a) the mailbox address and person_info's address use different first names:")
for pid, p in people.iterrows():
    a = p["mailbox_address"].split("@")[0].split(".")[0]
    b = str(p["info_address"]).split("@")[0].split(".")[0]
    if len(a) >= 3 and len(b) >= 3 and a[:2] != b[:2]:
        print(f"   {p['name']:22s} mailbox {p['mailbox_address']:28s} person_info {p['info_address']}")

print("\nb) the first name used in own emails (sign-off 3+ times, or Notes address) differs from person_info:")
for pid, p in people.iterrows():
    first = str(p["full_name"]).split()[0].lower()
    sign, notes = evidence[pid]
    used = [w for w, n in sign.items() if n >= 3 and w not in {"thanks", "fyi", "regards"}]
    used += [n.split()[0].lower() for n, _ in notes]
    if used and all(u[:2] != first[:2] for u in used):
        print(f"   {p['name']:22s} person_info: {p['full_name']:24s} own emails: {sorted(set(used))}")
print("\n(nicknames such as Bill/William, Jim/James, Tom/Thomas and initials are fine; "
      "the real mismatches were read by hand)")

print("\ncorrections applied:")
for pid, fix in CORRECTIONS.items():
    print(f"   {people.loc[pid, 'name']}: {people.loc[pid, 'full_name']} -> {fix['full_name']}. {fix['why']}")
    for field in ["full_name", "department", "jse_title", "edo_title"]:
        people.loc[pid, field] = fix[field]

print("\nmailboxes that mix two people (kept in the network, left out of person-level tests):")
for pid, why in MIXED.items():
    print(f"   {why}")
people["mixed_identity"] = people.index.isin(list(MIXED))

# ---------------------------------------------------------------------------
title("2. Seniority from job titles (rule M: VP and above; rule N: either list)")


def is_senior(t):
    return None if pd.isna(t) else bool(SENIOR.search(t))


people["senior_jse"] = people["jse_title"].map(is_senior)
people["senior_edo"] = people["edo_title"].map(is_senior)
people["senior"] = (people["senior_jse"] == True) | (people["senior_edo"] == True)  # noqa: E712
no_title = people["jse_title"].isna() & people["edo_title"].isna()
print(f"senior: {people['senior'].sum()} of {len(people)} people "
      f"(no title at all for {no_title.sum()}: {', '.join(people.loc[no_title, 'name'])} -> counted as not senior)")
print("\nall senior people:")
for _, p in people[people["senior"]].sort_values("name").iterrows():
    edo = p["edo_title"] if pd.notna(p["edo_title"]) else "-"
    print(f"   {p['full_name']:22s} JSE: {str(p['jse_title']):26s} EDO: {edo}")

both = people[people["senior_jse"].notna() & people["senior_edo"].notna()]
disagree = both[both["senior_jse"] != both["senior_edo"]]
print(f"\nthe two lists disagree on seniority for {len(disagree)} of {len(both)} people with both titles:")
for _, p in disagree.iterrows():
    print(f"   {p['full_name']:22s} JSE: {p['jse_title']:26s} EDO: {p['edo_title']}")

# ---------------------------------------------------------------------------
title("3. Departments, checked at business-unit level with own Notes addresses")


def unit_of_address(unit):
    if any(x in unit for x in ["ET&S", "FGT", "GPGFIN", "NPNG"]):
        return "ETS"
    return "EES" if "EES" in unit else "ENA/corporate"


def unit_of_label(dept):
    if pd.isna(dept):
        return "unknown"
    return dept if dept in ("ETS", "EES") else "ENA/corporate"


people["notes_unit"] = [pd.Series([u for _, u in evidence[pid][1]]).value_counts().index[0]
                        if evidence[pid][1] else None for pid in people.index]
has = people["notes_unit"].notna()
people["unit_from_label"] = people["department"].map(unit_of_label)
people["unit_from_notes"] = people["notes_unit"].map(lambda u: unit_of_address(u) if pd.notna(u) else None)
print(f"people with their own Notes address in their emails: {has.sum()} of {len(people)}")
print(pd.crosstab(people.loc[has, "unit_from_label"], people.loc[has, "unit_from_notes"],
                  rownames=["label says"], colnames=["own address says"]).to_string())
clash = people[has & (people["unit_from_label"] != people["unit_from_notes"])]
print(f"\ndisagreements ({len(clash)}):")
for _, p in clash.iterrows():
    print(f"   {p['full_name']:22s} label: {str(p['department']):34s} own address: {p['notes_unit']}")
print("\nWest Power desks are in Portland (PDX):",
      people.loc[has & people["department"].str.contains("West Power", na=False), "notes_unit"]
      .value_counts().to_dict())

people["department_checked"] = (has & (people["unit_from_label"] == people["unit_from_notes"])) | \
                               people.index.isin(list(CORRECTIONS))
people[["name", "full_name", "community", "jse_title", "edo_title", "senior", "department",
         "notes_unit", "department_checked", "mixed_identity"]].to_csv(OUT / "people.csv")
print(f"\nsaved people.csv to {OUT}")
