"""Loading the email graph and the database tables.

Every analysis loads its data through these functions, so file locations and
table joins are defined in one place.
"""

import pickle
import sqlite3
from contextlib import closing
from pathlib import Path

import networkx as nx
import pandas as pd

from enron.paths import EXTERNAL_DB, GRAPH_PATH, MAIN_DB


# ------------------------------------------------------------------ graph ---
LAST_MAILBOX_ID = 148      # person_ids 1-148 have a mailbox; 149-155 were imported without one


def load_email_graph(path: Path = GRAPH_PATH, mailboxes_only: bool = True) -> nx.DiGraph:
    """The directed email graph: node = person_id, edge weight = emails sent.

    By default only the 148 people with a mailbox: the people imported without one
    (Fastow, Causey, ...) are seen only through their email with the 148, so their
    links and centrality would be partial. Use mailboxes_only=False to keep them."""
    with Path(path).open("rb") as f:
        G = pickle.load(f)
    if mailboxes_only:
        G = G.subgraph([n for n in G if n <= LAST_MAILBOX_ID]).copy()
    return G


def to_undirected(G: nx.DiGraph, drop_self_loops: bool = True) -> nx.Graph:
    """Undirected copy where each link's weight = emails in both directions.

    Self-loops (emails to oneself) are dropped by default. Every node is kept,
    including people left with no links.
    """
    H = nx.Graph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, d in G.edges(data=True):
        if drop_self_loops and u == v:
            continue
        w = d.get("weight", 1)
        if H.has_edge(u, v):
            H[u][v]["weight"] += w
        else:
            H.add_edge(u, v, weight=w)
    return H


def to_directed(G: nx.DiGraph, nodes=None) -> nx.DiGraph:
    """Directed copy without self-loops (emails to oneself), weight = emails sent.

    nodes: keep only these people (e.g. those with at least one link); default all.
    """
    keep = set(G) if nodes is None else set(nodes)
    D = nx.DiGraph()
    D.add_nodes_from(n for n in G if n in keep)
    D.add_weighted_edges_from((u, v, d.get("weight", 1)) for u, v, d in G.edges(data=True)
                              if u != v and u in keep and v in keep)
    return D


# --------------------------------------------------------------- database ---
def connect(attach_external: bool = True) -> sqlite3.Connection:
    """Connection to the main database, with the external one attached as `ext`."""
    conn = sqlite3.connect(MAIN_DB)
    if attach_external:
        conn.execute(f"ATTACH DATABASE '{EXTERNAL_DB.as_posix()}' AS ext")
    return conn


def load_people() -> pd.DataFrame:
    """One row per person (index = person_id) with name, role and department.

    Columns: folder, full_name, role ('Unknown' when missing), department,
    full_corpus_community (community in the earlier full-corpus analysis).
    People added later without a record in person_info (e.g. Andrew Fastow, added
    from other people's mailboxes) get a name made from their address.
    """
    with closing(connect()) as conn:
        people = pd.read_sql("""
            SELECT p.person_id,
                   p.name                         AS folder,
                   COALESCE(i.full_name, p.name)  AS full_name,
                   p.mail                         AS mail,
                   i.full_name IS NULL            AS no_info,
                   COALESCE(i.role, 'Unknown')    AS role,
                   i.jse_department               AS department,
                   f.community                    AS full_corpus_community
            FROM people p
            LEFT JOIN ext.person_info i USING (person_id)
            LEFT JOIN ext.full_network_metrics f USING (person_id)
        """, conn)
    from_mail = people["mail"].fillna("").str.split("@").str[0].str.replace(".", " ").str.title()
    people.loc[people["no_info"].astype(bool) & (from_mail != ""), "full_name"] = from_mail
    return people.drop(columns=["mail", "no_info"]).set_index("person_id")


def load_congress_mentions() -> pd.Series:
    """Number of times each person is named in the Congress documents.

    Index = person_id (people outside the main database are left out); mentions
    hand-checked as the wrong person are not counted.
    """
    with closing(connect()) as conn:
        counts = pd.read_sql("""
            SELECT person_id, COUNT(*) AS mentions
            FROM ext.congress_mentions
            WHERE person_id IS NOT NULL AND COALESCE(hand_correct, 1) = 1
            GROUP BY person_id
        """, conn)
    return counts.set_index("person_id")["mentions"]


def load_full_corpus_metrics() -> pd.DataFrame:
    """Results of the earlier full-corpus network analysis for people in `people`.

    Index = person_id; columns pagerank, betweenness, group_label, community.
    """
    with closing(connect()) as conn:
        metrics = pd.read_sql("""
            SELECT person_id, pagerank, betweenness, group_label, community
            FROM ext.full_network_metrics
            WHERE person_id IS NOT NULL
        """, conn)
    return metrics.set_index("person_id")


def load_congress_paragraphs() -> pd.DataFrame:
    """Full Congress texts, one row per paragraph (from `add_congress_texts`).

    Columns: doc_id, para_id, speaker (hearings only), explicit (1 if the paragraph
    opens with the speaker's name), text, title, doc_type.
    """
    with closing(connect()) as conn:
        return pd.read_sql("""
            SELECT p.doc_id, p.para_id, p.speaker, p.explicit, p.text, d.title, d.doc_type
            FROM ext.congress_paragraphs p
            JOIN ext.congress_documents d USING (doc_id)
            ORDER BY p.doc_id, p.para_id
        """, conn)


def load_mentioned_names() -> list[str]:
    """Names of everyone matched in the Congress documents, inside or outside the 148
    (e.g. Kenneth Lay, Andrew Fastow), without matches hand-checked as wrong."""
    with closing(connect()) as conn:
        names = pd.read_sql("""
            SELECT DISTINCT person_name FROM ext.congress_mentions
            WHERE COALESCE(hand_correct, 1) = 1
        """, conn)
    return names["person_name"].dropna().tolist()


def load_emails() -> pd.DataFrame:
    """Every email between the 148 people with its recipients (a list of person_ids).

    Columns: email_id, date (datetime, UTC), sender_id, subject, body_clean,
    body_raw, message_type, human_probability, recipients, and three for analyses of
    who received what:
      date_known    False for the placeholder date 1 January 1980 (date unknown)
      others        the recipients without the sender (people often cc themselves)
      n_recipients  the number of `others`

    body_clean has signatures and the headers of forwarded messages removed (see
    remove_forwarded_by and database_updates.sql); body_raw is the text before that,
    with the "Forwarded by" lines that show where forwarded text starts. Older copies
    of the database have no body_raw; it is then a copy of body_clean.
    """
    with closing(connect(attach_external=False)) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(emails)")}
        raw = "COALESCE(body_raw, body_clean)" if "body_raw" in columns else "body_clean"
        emails = pd.read_sql(f"""
            SELECT email_id, date, sender_id, subject, body_clean, {raw} AS body_raw,
                   message_type, human_probability
            FROM emails
        """, conn)
        recipients = pd.read_sql("SELECT email_id, recipient_id FROM recipients", conn)
    emails["date"] = pd.to_datetime(emails["date"], utc=True, errors="coerce")
    emails["date_known"] = emails["date"].dt.year > 1980
    lists = recipients.groupby("email_id")["recipient_id"].agg(list)
    emails["recipients"] = emails["email_id"].map(lists).apply(lambda r: r if isinstance(r, list) else [])
    emails["others"] = [[r for r in rs if r != s] for rs, s in zip(emails["recipients"], emails["sender_id"])]
    emails["n_recipients"] = emails["others"].str.len()
    return emails
