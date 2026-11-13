"""Build data/enron_external.sqlite: the external data (custodian titles, roles,
US Congress documents and mentions, network results), linked to the people in
Christos's data/enron_main_characters.sqlite.

Christos's database is only read, never changed. The new tables live in their
own file, and data/schema_external.sql documents them (like data/schema.sql
does for his tables).

Usage (from the project root):
    uv add pandas
    uv run python src/enron/add_external_data.py --tables data/external

--tables is the folder where you unzipped enron_tables.zip. Files are found by
name anywhere under it, so the zip's own data/ and results/ folders are fine.

Tables created (person_id always means people.person_id in the main database):
    person_info         one row per person in `people`: full name, email, titles, role
    email_addresses     every known email ADDRESS of a person -> person_id
                        (not messages: those are in the main database's `emails`)
    congress_documents  the 10 US Congress hearings / committee prints that were searched
    congress_mentions   each place a person is named in those documents, with hand checks
    full_network_metrics per-person results of the RQ1/RQ2 analysis
                        (full-corpus network, 1,892 people, k = 10; NOT the 148-person graph)

Rows about people outside the 148 keep person_id = NULL instead of being dropped.

To query both databases together:
    conn = sqlite3.connect("data/enron_main_characters.sqlite")
    conn.execute("ATTACH DATABASE 'data/enron_external.sqlite' AS ext")
    conn.execute("SELECT p.name, i.full_name FROM people p JOIN ext.person_info i USING (person_id)")
"""

import argparse
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "enron_main_characters.sqlite"
DEFAULT_OUT = PROJECT_ROOT / "data" / "enron_external.sqlite"
DEFAULT_SCHEMA = PROJECT_ROOT / "data" / "schema_external.sql"
DEFAULT_TABLES = PROJECT_ROOT / "data" / "external"

# JSE spreadsheet folder names that differ from the real maildir folder names
JSE_FOLDER_FIXES = {"crandell-s": "crandall-s"}

# govinfo collection prefix -> document type
DOC_TYPES = {"CHRG": "hearing", "CPRT": "committee print"}

SCHEMA = """
CREATE TABLE person_info (
    person_id INTEGER PRIMARY KEY,      -- people.person_id in the main database
    full_name TEXT,
    email TEXT,                         -- main address, e.g. jeff.dasovich@enron.com
    folder TEXT,                        -- maildir folder, same as people.name
    edo_title TEXT,                     -- job title from the EDO custodian list
    jse_department TEXT,                -- department from the JSE employee sheet
    jse_title TEXT,                     -- job title from the JSE employee sheet
    role TEXT                           -- hand-checked role group used in RQ2
);

CREATE TABLE email_addresses (
    address TEXT PRIMARY KEY,           -- one email address (not a message)
    person_id INTEGER,                  -- people.person_id in the main database
    main_address TEXT,                  -- the person's main address
    match_method TEXT                   -- custodian / sent-folder / same-name
);

CREATE TABLE congress_documents (
    doc_id TEXT PRIMARY KEY,            -- govinfo package id, e.g. CHRG-107hhrg77985
    doc_type TEXT,                      -- hearing / committee print
    title TEXT,
    n_chars INTEGER,                    -- length of the document text
    enron_count INTEGER,                -- times the word 'Enron' appears
    kept INTEGER,                       -- 1 = used in the analysis (>= 10 'Enron')
    source TEXT
);

CREATE TABLE congress_mentions (
    mention_id INTEGER PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES congress_documents(doc_id),
    person_id INTEGER,                  -- NULL if the person is not in `people`
    email TEXT NOT NULL,                -- the person's main address
    person_name TEXT,
    matched_text TEXT,                  -- how the name was written, e.g. 'Mr. Skilling'
    context_snippet TEXT,               -- text around the mention
    hand_correct INTEGER,               -- 1 right person, 0 wrong, NULL not checked
    hand_note TEXT
);

CREATE INDEX idx_mentions_person ON congress_mentions(person_id);
CREATE INDEX idx_mentions_doc ON congress_mentions(doc_id);
CREATE INDEX idx_addresses_person ON email_addresses(person_id);
"""


def find(tables_dir: Path, filename: str) -> Path:
    hits = sorted(tables_dir.rglob(filename))
    if not hits:
        raise SystemExit(f"Could not find {filename} under {tables_dir}")
    return hits[0]


def norm(text) -> str:
    """Lower-case, NFKC-normalised (fixes ligatures like 'ﬃ'), single spaces."""
    if pd.isna(text):
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(text)).lower().split())


def load_custodians(tables_dir: Path) -> pd.DataFrame:
    """EDO custodian list: maildir folder, main email address, full name, title."""
    edo = pd.read_csv(find(tables_dir, "edo_enron-custodians-data.tsv"), sep="\t",
                      header=None, names=["folder", "email", "full_name", "edo_title"])
    edo["edo_title"] = edo["edo_title"].replace("", pd.NA)
    return edo


def load_jse(tables_dir: Path, edo: pd.DataFrame) -> pd.DataFrame:
    """JSE employee sheet -> one row per folder, with department and title.

    Some JSE folders list two names ('panus-s, phanis-s') and some folders are
    shared by two different people (e.g. two Susan Scotts). For shared folders
    the row whose name matches the EDO full name wins; if that is still
    ambiguous the folder gets no JSE data rather than a wrong guess.
    """
    jse = pd.read_csv(find(tables_dir, "jse_employees.csv"))
    jse = jse.rename(columns={"Name": "jse_name", "Department": "jse_department",
                              "Title": "jse_title", "Folder": "folder"})
    jse["folder"] = jse["folder"].map(norm).str.split(",")
    jse = jse.explode("folder")
    jse["folder"] = jse["folder"].str.strip().replace(JSE_FOLDER_FIXES)

    edo_names = dict(zip(edo["folder"], edo["full_name"].map(norm)))
    rows = []
    for folder, cands in jse.groupby("folder"):
        if len(cands) == 1:
            rows.append(cands.iloc[0])
            continue
        target = edo_names.get(folder, "")
        exact = cands[cands["jse_name"].map(norm) == target]
        if len(exact) == 1:
            rows.append(exact.iloc[0])
            continue
        first = target.split(" ")[0] if target else ""
        same_first = cands[cands["jse_name"].map(lambda n: norm(n).split(" ")[0]) == first]
        if len(same_first) == 1:
            rows.append(same_first.iloc[0])
        # otherwise ambiguous: leave this folder without JSE data
    return pd.DataFrame(rows)[["folder", "jse_name", "jse_department", "jse_title"]]


def map_people(main_db: Path, edo: pd.DataFrame, aliases: pd.DataFrame) -> dict[str, int]:
    """Return {main email address -> person_id} for everyone in `people`.

    people.name holds the maildir folder (e.g. 'dasovich-j'), so match on the
    folder first, then on people.mail against the EDO address and all aliases.
    """
    with sqlite3.connect(f"file:{main_db.as_posix()}?mode=ro", uri=True) as conn:
        people = pd.read_sql("SELECT person_id, name, mail FROM people", conn)
    by_folder = dict(zip(people["name"].map(norm), people["person_id"]))
    by_mail = dict(zip(people["mail"].map(norm), people["person_id"]))
    alias_groups = aliases.groupby("canonical")["address"].apply(list).to_dict()

    email_to_pid = {}
    for row in edo.itertuples():
        pid = by_folder.get(norm(row.folder))
        if pid is None:
            for addr in [row.email, *alias_groups.get(row.email, [])]:
                pid = by_mail.get(norm(addr))
                if pid is not None:
                    break
        if pid is not None:
            email_to_pid[row.email] = int(pid)

    unmatched = sorted(set(people["person_id"]) - set(email_to_pid.values()))
    print(f"Matched {len(email_to_pid)} of {len(people)} people to the custodian list.")
    if unmatched:
        print("  Not matched (check these by hand):")
        print(people[people["person_id"].isin(unmatched)].to_string(index=False))
    return email_to_pid


def bools_to_int(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == bool:
            df[col] = df[col].astype(int)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="Christos's database (read only)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="new database to write")
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="schema file to write")
    ap.add_argument("--tables", type=Path, default=DEFAULT_TABLES,
                    help="folder where enron_tables.zip was unzipped")
    args = ap.parse_args()

    if not args.db.exists():
        raise SystemExit(f"Main database not found: {args.db}")

    t = args.tables
    edo = load_custodians(t)
    jse = load_jse(t, edo)
    aliases = pd.read_csv(find(t, "aliases.csv"))
    docs = pd.read_csv(find(t, "congress_docs.csv"))
    mentions = pd.read_csv(find(t, "congress_mentions_all.csv"))
    roles = pd.read_csv(find(t, "roles.csv"))
    rq = pd.read_csv(find(t, "rq2_people.csv"))
    check_m = pd.read_csv(find(t, "hand_check_mentions.csv"))
    check_p = pd.read_csv(find(t, "hand_check_people.csv"))

    email_to_pid = map_people(args.db, edo, aliases)
    addr_to_pid = {a: email_to_pid.get(c) for a, c in zip(aliases["address"], aliases["canonical"])}
    addr_to_pid.update(email_to_pid)

    def pid_of(addr):
        pid = addr_to_pid.get(addr)
        return None if pid is None else int(pid)

    # ---- person_info ----------------------------------------------------------
    role_by_node = rq.set_index("node")["role"].to_dict()
    role_by_node.update(roles.set_index("node")["role"].to_dict())  # hand-checked wins
    info = edo.merge(jse, on="folder", how="left")
    info["person_id"] = info["email"].map(email_to_pid)
    info = info.dropna(subset=["person_id"])
    info["person_id"] = info["person_id"].astype(int)
    info["role"] = info["email"].map(role_by_node)
    info = info[["person_id", "full_name", "email", "folder", "edo_title",
                 "jse_department", "jse_title", "role"]]

    # ---- email_addresses --------------------------------------------------------
    addresses = aliases.rename(columns={"canonical": "main_address", "how": "match_method"})
    addresses["person_id"] = addresses["address"].map(pid_of)
    addresses = addresses[["address", "person_id", "main_address", "match_method"]]

    # ---- congress_documents -----------------------------------------------------
    docs = docs.rename(columns={"n_enron": "enron_count"})
    docs["doc_type"] = docs["doc_id"].str.split("-").str[0].map(DOC_TYPES)
    docs["title"] = docs["title"].str.lstrip("- ").str.strip()
    docs["kept"] = docs["kept"].astype(int)
    docs["source"] = "US Congress via govinfo.gov"
    docs = docs[["doc_id", "doc_type", "title", "n_chars", "enron_count", "kept", "source"]]

    # ---- congress_mentions, with both hand checks attached ----------------------
    mentions = mentions.rename(columns={"name": "person_name"})
    hm = check_m.rename(columns={"name": "person_name"})[
        ["doc_id", "node", "matched", "context", "correct", "note"]]
    hp = check_p.rename(columns={"name": "person_name"})[
        ["doc_id", "person_name", "matched", "context", "correct", "note"]]
    mentions = mentions.merge(hm, on=["doc_id", "node", "matched", "context"], how="left")
    mentions = mentions.merge(hp, on=["doc_id", "person_name", "matched", "context"],
                              how="left", suffixes=("", "_p"))
    mentions["hand_correct"] = mentions["correct"].fillna(mentions["correct_p"])
    mentions["hand_note"] = mentions["note"].fillna(mentions["note_p"])
    mentions["person_id"] = mentions["node"].map(pid_of)
    mentions = mentions.rename(columns={"node": "email", "matched": "matched_text",
                                        "context": "context_snippet"})
    mentions = mentions[["doc_id", "person_id", "email", "person_name", "matched_text",
                         "context_snippet", "hand_correct", "hand_note"]].drop_duplicates()

    # ---- full_network_metrics ---------------------------------------------------
    rq = bools_to_int(rq.rename(columns={"group": "group_label", "node": "email"}))
    rq.insert(1, "person_id", rq["email"].map(pid_of))
    rq.insert(2, "k_threshold", 10)

    # ---- write a fresh external database ----------------------------------------
    args.out.unlink(missing_ok=True)
    conn = sqlite3.connect(args.out)
    conn.execute("PRAGMA foreign_keys = ON")
    with conn:
        conn.executescript(SCHEMA)
        info.to_sql("person_info", conn, if_exists="append", index=False)
        addresses.to_sql("email_addresses", conn, if_exists="append", index=False)
        docs.to_sql("congress_documents", conn, if_exists="append", index=False)
        mentions.to_sql("congress_mentions", conn, if_exists="append", index=False)
        rq.to_sql("full_network_metrics", conn, index=False)
        conn.execute("CREATE INDEX idx_fullnet_person ON full_network_metrics(person_id)")

    # schema file, in the same spirit as data/schema.sql
    ddl = [r[0] for r in conn.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
        "ORDER BY type = 'index', name")]
    args.schema.write_text(
        "-- Schema of data/enron_external.sqlite (written by src/enron/add_external_data.py)\n"
        "-- person_id = people.person_id in data/enron_main_characters.sqlite\n\n"
        + ";\n\n".join(ddl) + ";\n", encoding="utf-8")

    print(f"\nWrote {args.out.name} and {args.schema.name}:")
    for name in ["person_info", "email_addresses", "congress_documents",
                 "congress_mentions", "full_network_metrics"]:
        if name == "congress_documents":
            total = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  {name:<21} {total:>5} rows")
            continue
        total, linked = conn.execute(
            f"SELECT COUNT(*), COUNT(person_id) FROM {name}").fetchone()
        print(f"  {name:<21} {total:>5} rows, {linked:>5} linked to people")
    conn.close()


if __name__ == "__main__":
    main()
