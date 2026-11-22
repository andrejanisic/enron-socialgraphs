"""Everyone named in the Congress documents, and whether they are among the 148.

Person names come from spaCy's named-entity recogniser (label PERSON) run on every
paragraph, plus the hearing speaker labels ("Mr. Skilling", "Senator Boxer").
Variants of one name are merged: titles and middle initials are dropped, nicknames
mapped to one first name (Jeff = Jeffrey), and surname-only mentions ("Mr. Fastow")
given to the full name when the surname belongs to one person only. A name is matched
to the 148 only with its first name; a surname alone that one of the 148 shares is
marked unclear ("Mrs. Jones" is a member of Congress, not Tana Jones).
"""

import re
from collections import Counter, defaultdict

import pandas as pd

TITLES = re.compile(
    r"^(?:(?:mr|ms|mrs|dr|sen|senator|chairman|chairwoman|congressman|congresswoman|"
    r"representative|rep|judge|professor|prof|governor|gov|president|secretary|"
    r"commissioner|dean|treasurer|former|ceo|cfo|vice|chief|messrs)\.?\s+)+", re.IGNORECASE)
SUFFIX = re.compile(r",?\s+(?:jr|sr|ii|iii|iv)\.?$", re.IGNORECASE)
POSSESSIVE = re.compile(r"['’]s$")
TITLE_WORD = re.compile(r"\b(Mr|Ms|Mrs|Dr|Senator|Chairman|Chairwoman|Congressman|"
                        r"Congresswoman|Representative)\.?\s+$")
# Same first name written two ways
NICKNAMES = {
    "jeff": "jeffrey", "jeffery": "jeffrey", "ken": "kenneth", "kenny": "kenneth",
    "rick": "richard", "dick": "richard", "rich": "richard", "andy": "andrew",
    "ben": "benjamin", "mike": "michael", "bill": "william", "will": "william",
    "jim": "james", "jimmy": "james", "steve": "steven", "stephen": "steven",
    "bob": "robert", "rob": "robert", "tom": "thomas", "dave": "david", "dan": "daniel",
    "joe": "joseph", "chuck": "charles", "charlie": "charles", "greg": "gregory",
    "tony": "anthony", "chris": "christopher", "pat": "patrick", "ed": "edward",
    "larry": "lawrence", "fred": "frederick", "sam": "samuel", "matt": "matthew",
    "cindy": "cynthia", "sherry": "sherron", "vince": "vincent", "lou": "louis",
}
# Entities the recogniser often tags as people that are not people
NOT_PEOPLE = {
    "enron", "raptor", "raptors", "ljm", "ljm1", "ljm2", "chewco", "jedi", "whitewing",
    "talon", "osprey", "marlin", "andersen", "arthur andersen", "dynegy", "moody",
    "aicpa", "fasb", "gaap", "chair", "chairman", "pro-forma", "berkshire hathaway",
    "pfizer", "financial officers", "southampton", "condor", "braveheart",
    "hrg", "clerk", "reg", "fitch", "rhythms", "standard", "poor", "powers report",
    "global crossing", "hearing record", "arthur anderson", "fast andy",
}
# Committee rosters put a state next to the name ("Vermont FERGUSON")
STATES = re.compile(
    r"^(?:Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|"
    r"Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|"
    r"Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|"
    r"New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|"
    r"Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|"
    r"Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\s+")


def clean_name(text: str) -> str | None:
    """A person name without titles, middle initials, suffixes or possessive 's;
    None when it does not look like a name."""
    name = re.sub(r"\s+", " ", text).strip(" .,;:()[]\"'")
    name = STATES.sub("", TITLES.sub("", name))
    name = POSSESSIVE.sub("", SUFFIX.sub("", name)).strip(" .,")
    if not name or re.search(r"[\d@/&=_]", name) or len(name) < 3:
        return None
    letters = [c for c in name if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:      # JOHN McCAIN
        name = " ".join(w.capitalize() if not w.lower().startswith("mc") else
                        "Mc" + w[2:].capitalize() for w in name.split())
    words = [w for w in name.split() if not re.fullmatch(r"[A-Z]\.?", w)]   # middle initials
    if not words or not all(w[0].isupper() for w in words) or len(words) > 4:
        return None
    if " ".join(words).lower() in NOT_PEOPLE:
        return None
    return " ".join(words)


def first_key(first: str) -> str:
    first = first.lower().rstrip(".")
    return NICKNAMES.get(first, first)


def find_mentions(paragraphs: pd.DataFrame, nlp) -> pd.DataFrame:
    """One row per PERSON entity: doc_id, para_id, name (cleaned), title (the title
    word just before it, if any), and a short context. The speaker's name opening a
    speaking turn is left out (counted as a turn, not a mention)."""
    rows = []
    texts = paragraphs["text"].fillna("").tolist()
    # a speaking turn opens with the speaker's name ("Mr. Skilling. ..."): not a mention
    label_end = [len(str(sp)) + 2 if ex == 1 and isinstance(sp, str) else 0
                 for sp, ex in zip(paragraphs["speaker"], paragraphs["explicit"])]
    rows_in = paragraphs[["doc_id", "para_id", "text"]].itertuples(index=False)
    for (doc_id, para_id, text), skip, doc in zip(rows_in, label_end, nlp.pipe(texts, batch_size=64)):
        for ent in doc.ents:
            if ent.label_ != "PERSON" or ent.start_char < skip:
                continue
            name = clean_name(ent.text)
            if not name:
                continue
            before = text[max(0, ent.start_char - 16):ent.start_char]
            title = TITLE_WORD.search(before)
            title = title.group(1) if title else ""
            if not title:          # the recogniser often keeps the title inside the name
                inside = re.match(r"(Mr|Ms|Mrs|Dr|Senator|Chairman|Congressman|Representative)\b", ent.text)
                title = inside.group(1) if inside else ""
            context = text[max(0, ent.start_char - 120):ent.end_char + 120].replace("\n", " ")
            rows.append((doc_id, para_id, name, title, context))
    return pd.DataFrame(rows, columns=["doc_id", "para_id", "name", "title", "context"])


def speaker_turns(paragraphs: pd.DataFrame) -> Counter:
    """Speaking turns per cleaned speaker name (usually a surname with a title)."""
    turns = Counter()
    for speaker in paragraphs["speaker"].dropna():
        name = clean_name(speaker)
        if name:
            turns[name] += 1
    return turns


def canonical_names(mentions: pd.DataFrame, turns: Counter, min_share: float = 0.8) -> dict:
    """Map every cleaned name (full or surname only) to one canonical 'First Last'.

    Full names are grouped by surname and first name (nicknames merged). A surname
    alone goes to the full name with that surname when one first name has at least
    `min_share` of the full-name mentions; otherwise it stays as the surname alone."""
    full = Counter()
    for name in mentions["name"]:
        words = name.split()
        if len(words) >= 2:
            full[(words[-1].lower(), first_key(words[0]))] += 1
    # the most common spelling of each (surname, first name) pair
    spelling = defaultdict(Counter)
    for name in mentions["name"]:
        words = name.split()
        if len(words) >= 2:
            spelling[(words[-1].lower(), first_key(words[0]))][f"{words[0]} {words[-1]}"] += 1
    by_surname = defaultdict(Counter)
    for (surname, first), n in full.items():
        by_surname[surname][first] += n
    mapping = {}
    for name in set(mentions["name"]) | set(turns):
        words = name.split()
        surname = words[-1].lower()
        if len(words) >= 2:
            seen = spelling[(surname, first_key(words[0]))].most_common(1)
            mapping[name] = seen[0][0] if seen else f"{words[0]} {words[-1]}"
        else:
            firsts = by_surname.get(surname)
            if firsts and firsts.most_common(1)[0][1] / sum(firsts.values()) >= min_share:
                top = firsts.most_common(1)[0][0]
                mapping[name] = spelling[(surname, top)].most_common(1)[0][0]
            else:
                mapping[name] = words[-1]
    return mapping


def people_table(mentions: pd.DataFrame, turns: Counter, people: pd.DataFrame,
                 min_mentions: int = 3) -> pd.DataFrame:
    """One row per canonical name: mentions, documents, speaking turns, the title most
    often used, and the matching person among the 148 (same surname and first name,
    nicknames merged; the first initial when only a surname is known)."""
    mapping = canonical_names(mentions, turns)
    # a lone first name ("Sherron", "Joe") that is never a surname or a speaker
    firsts = {n.split()[0].lower() for n in mentions["name"] if len(n.split()) >= 2}
    surnames = {n.split()[-1].lower() for n in mentions["name"] if len(n.split()) >= 2}
    speakers = {n.split()[-1].lower() for n in turns}
    lone_first = {n for n in mapping if len(n.split()) == 1 and n.lower() in firsts
                  and n.lower() not in surnames and n.lower() not in speakers}
    mentions = mentions[~mentions["name"].isin(lone_first)]
    mentions = mentions.assign(canonical=mentions["name"].map(mapping))
    turns_by = Counter()
    for name, n in turns.items():
        turns_by[mapping.get(name, name)] += n

    index = defaultdict(list)          # surname -> [(first key, person_id)]
    for pid, full_name in people["full_name"].items():
        words = str(full_name).replace(".", " ").split()
        if len(words) >= 2:
            index[words[-1].lower()].append((first_key(words[0]), pid))

    def match(name):
        """(person_id or None, in_148): 'yes', 'no', or 'unclear' for a surname alone
        that one of the 148 shares (the text never gives the first name)."""
        words = name.split()
        candidates = index.get(words[-1].lower(), [])
        if len(words) == 1:
            return None, ("unclear (surname only)" if candidates else "no")
        hits = [pid for first, pid in candidates if first == first_key(words[0])]
        return (hits[0], "yes") if len(hits) == 1 else (None, "no")

    rows = []
    for name, group in mentions.groupby("canonical"):
        titles = group.loc[group["title"] != "", "title"]
        pid, in_148 = match(name)
        rows.append({
            "name": name,
            "mentions": len(group),
            "documents": group["doc_id"].nunique(),
            "speaking_turns": turns_by.get(name, 0),
            "title_used": titles.mode().iloc[0] if len(titles) else "",
            "spellings": "; ".join(sorted(set(group["name"]))[:6]),
            "in_148": in_148,
            "person_id": pid,
            "name_in_148": people.loc[pid, "full_name"] if pid is not None else "",
            "role_in_148": people.loc[pid, "role"] if pid is not None else "",
            "example": group["context"].iloc[len(group) // 2][:240],
        })
    table = pd.DataFrame(rows)
    table["person_id"] = table["person_id"].astype("Int64")
    keep = (table["mentions"] + table["speaking_turns"]) >= min_mentions
    return table[keep].sort_values(["mentions", "speaking_turns"], ascending=False).reset_index(drop=True)
