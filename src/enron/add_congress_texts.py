"""Add the full Congress texts to the external database, one row per paragraph.

Reads the pages saved by `download_congress.py` (data/external/congress/) and
writes the table congress_paragraphs to data/enron_external.sqlite, replacing
it if it exists. Nothing else in the database is changed.

The pages are plain text. A paragraph starts after a blank line, on a line that
is indented more than the line before it, or on an indented line that opens
with a speaker's name (short turns in a hearing sit at the same indent). In the hearings a speaker's
turn opens with a name and a full stop ("Mr. Powers. I cannot ..."); the
paragraphs that follow without a name belong to the same speaker, until the
next name or a heading.

Usage (from the project root, after `uv run python -m enron.download_congress`):
    uv run python -m enron.add_congress_texts

Checks printed: text length per document against n_chars in
congress_documents (a few percent shorter, since repeated spaces are collapsed),
and the share of the mention snippets in congress_mentions found in the text.
"""

import html
import re
import sqlite3
from contextlib import closing

import pandas as pd

from enron.paths import DATA_DIR, EXTERNAL_DB

PAGES = DATA_DIR / "external" / "congress"

SPEAKER = re.compile(r"^((?:Mr|Ms|Mrs|Dr|Senator|Chairman|Representative)\.? [A-Z][A-Za-z'\-]+"
                     r"|The Chairman|The Chair|Chairman)\.\s")
PAGE_MARKER = re.compile(r"^\s*\[\[Page [^\]]*\]\]\s*$")
SCHEMA = """
CREATE TABLE congress_paragraphs (
    doc_id   TEXT NOT NULL REFERENCES congress_documents(doc_id),
    para_id  INTEGER NOT NULL,      -- position in the document, from 0
    speaker  TEXT,                  -- hearings only: who is speaking, e.g. 'Mr. Powers'
    explicit INTEGER NOT NULL,      -- 1 if the paragraph opens with the speaker's name
    text     TEXT NOT NULL,
    PRIMARY KEY (doc_id, para_id)
);
CREATE INDEX idx_paragraphs_speaker ON congress_paragraphs(speaker);
"""


def page_lines(raw: str) -> list[str]:
    """Text lines of a govinfo page: tags removed, entities decoded, page markers dropped."""
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    return [line.rstrip() for line in text.split("\n") if not PAGE_MARKER.match(line)]


def indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def split_paragraphs(lines: list[str]) -> list[str]:
    """Join lines into paragraphs: a new one after a blank line, at a deeper indent,
    or at an indented line that opens with a speaker's name."""
    paragraphs, current, previous = [], [], None
    for line in lines:
        if not line.strip():
            if current:
                paragraphs.append(" ".join(current))
            current, previous = [], None
            continue
        new_turn = indent(line) > 0 and SPEAKER.match(line.strip())
        if current and previous is not None and (indent(line) > previous or new_turn):
            paragraphs.append(" ".join(current))
            current = []
        current.append(line.strip())
        previous = indent(line)
    if current:
        paragraphs.append(" ".join(current))
    return [re.sub(r"\s+", " ", p).strip() for p in paragraphs]


def is_heading(paragraph: str) -> bool:
    """Short all-capital lines (section titles, 'PREPARED STATEMENT OF ...')."""
    letters = [c for c in paragraph if c.isalpha()]
    return len(paragraph) < 200 and len(letters) > 3 and all(c.isupper() for c in letters)


def with_speakers(paragraphs: list[str], is_hearing: bool) -> list[tuple]:
    """(speaker, explicit, text) per paragraph; speakers carry on until a new name or heading."""
    rows, speaker = [], None
    for p in paragraphs:
        match = SPEAKER.match(p) if is_hearing else None
        if match:
            speaker = match.group(1)
        elif is_heading(p):
            speaker = None
        rows.append((speaker, int(bool(match)), p))
    return rows


def snippet_found(snippet: str, text: str) -> bool:
    """Is the middle half of a mention snippet in the document text? (Snippets are
    fixed-width windows, so they often run across two paragraphs.)"""
    core = re.sub(r"\s+", " ", snippet).strip()
    return core[len(core) // 4: 3 * len(core) // 4] in text


def main():
    with closing(sqlite3.connect(EXTERNAL_DB)) as conn:
        docs = pd.read_sql("SELECT doc_id, doc_type, title, n_chars FROM congress_documents", conn)
        mentions = pd.read_sql("SELECT doc_id, context_snippet FROM congress_mentions", conn)

    rows, checks = [], []
    for doc in docs.itertuples():
        path = PAGES / f"{doc.doc_id}.htm"
        if not path.exists():
            raise SystemExit(f"Missing {path}: run `uv run python -m enron.download_congress` first")
        paragraphs = split_paragraphs(page_lines(path.read_text(encoding="utf-8")))
        for i, (speaker, explicit, text) in enumerate(with_speakers(paragraphs, doc.doc_type == "hearing")):
            rows.append((doc.doc_id, i, speaker, explicit, text))
        full_text = " ".join(paragraphs)
        snippets = mentions.loc[mentions.doc_id == doc.doc_id, "context_snippet"].dropna()
        found = sum(snippet_found(s, full_text) for s in snippets)
        checks.append({"doc_id": doc.doc_id, "paragraphs": len(paragraphs),
                       "characters": sum(map(len, paragraphs)), "expected": doc.n_chars,
                       "snippets": len(snippets), "found": found})

    table = pd.DataFrame(rows, columns=["doc_id", "para_id", "speaker", "explicit", "text"])
    with closing(sqlite3.connect(EXTERNAL_DB)) as conn:
        conn.execute("DROP TABLE IF EXISTS congress_paragraphs")
        conn.executescript(SCHEMA)
        table.to_sql("congress_paragraphs", conn, if_exists="append", index=False)
        conn.commit()

    checks = pd.DataFrame(checks)
    checks["difference"] = (100 * (checks.characters - checks.expected) / checks.expected).map("{:+.1f}%".format)
    print(checks.to_string(index=False))
    print(f"\n{len(table):,} paragraphs; {table.speaker.notna().sum():,} with a speaker; "
          f"snippets found: {checks.found.sum()} of {checks.snippets.sum()}")
    print(f"Wrote congress_paragraphs to {EXTERNAL_DB.name}")


if __name__ == "__main__":
    main()
