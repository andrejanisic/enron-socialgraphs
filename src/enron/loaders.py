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
def load_email_graph(path: Path = GRAPH_PATH) -> nx.DiGraph:
    """The directed email graph: node = person_id, edge weight = emails sent."""
    with Path(path).open("rb") as f:
        return pickle.load(f)


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
    """
    with closing(connect()) as conn:
        people = pd.read_sql("""
            SELECT p.person_id,
                   p.name                         AS folder,
                   COALESCE(i.full_name, p.name)  AS full_name,
                   COALESCE(i.role, 'Unknown')    AS role,
                   i.jse_department               AS department,
                   f.community                    AS full_corpus_community
            FROM people p
            LEFT JOIN ext.person_info i USING (person_id)
            LEFT JOIN ext.full_network_metrics f USING (person_id)
        """, conn)
    return people.set_index("person_id")


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
