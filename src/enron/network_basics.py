"""Analysis 1: describing the email network and testing it against null models.

Descriptive statistics, the same statistics in randomised graphs (z-scores),
mixing by role and department (assortativity), and the rich club.
"""

import networkx as nx
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from enron.communities import empirical_p, shuffled_graph


# ------------------------------------------------------------ description ---
def describe(G: nx.DiGraph, D: nx.DiGraph, H: nx.Graph) -> pd.DataFrame:
    """Basic size, density and connectivity figures, one row per statistic.

    G: the raw graph (all people, emails to oneself included); D: directed graph
    without self-loops; H: its undirected copy. Path length and diameter are
    measured on the largest connected part of H.
    """
    n = D.number_of_nodes()
    in_deg = np.array([d for _, d in D.in_degree()])
    out_deg = np.array([d for _, d in D.out_degree()])
    giant = H.subgraph(max(nx.connected_components(H), key=len))
    scc = max(nx.strongly_connected_components(D), key=len)
    rows = [
        ("People", n),
        ("People with no links (emailed only themselves)", len(list(nx.isolates(H)))),
        ("Emails between people", int(D.size(weight="weight"))),
        ("Emails to oneself (left out)", int(sum(d.get("weight", 1) for u, v, d in G.edges(data=True) if u == v))),
        ("Directed links (who emails whom)", D.number_of_edges()),
        ("Undirected links", H.number_of_edges()),
        ("Density (directed)", nx.density(D)),
        ("Reciprocity (share of links answered)", nx.reciprocity(D)),
        ("Mean contacts emailed (out-degree)", out_deg.mean()),
        ("Max out-degree", int(out_deg.max())),
        ("Max in-degree", int(in_deg.max())),
        ("Largest connected part (undirected)", giant.number_of_nodes()),
        ("Largest strongly connected part", len(scc)),
        ("Average clustering", nx.average_clustering(H)),
        ("Average path length (steps)", nx.average_shortest_path_length(giant)),
        ("Diameter (steps)", nx.diameter(giant)),
    ]
    return pd.DataFrame(rows, columns=["statistic", "value"])


def send_receive(D: nx.DiGraph, people: pd.DataFrame) -> pd.DataFrame:
    """Emails sent and received per person, and the share of their email they sent."""
    sent = pd.Series(dict(D.out_degree(weight="weight")), name="sent")
    received = pd.Series(dict(D.in_degree(weight="weight")), name="received")
    table = pd.concat([sent, received], axis=1).fillna(0).astype(int)
    total = table.sent + table.received
    table["sent_share"] = np.where(total > 0, table.sent / total.where(total > 0, 1), np.nan)
    table = table.join(people[["full_name", "role", "department"]])
    return table.sort_values("received", ascending=False)


# ---------------------------------------------------------- null models ---
UNDIRECTED_STATS = ["Average clustering", "Transitivity", "Average path length", "Degree assortativity"]
STAT_ORDER = ["Reciprocity"] + UNDIRECTED_STATS


def undirected_stats(H: nx.Graph) -> dict:
    """Clustering, transitivity, path length (largest part) and degree assortativity."""
    giant = H.subgraph(max(nx.connected_components(H), key=len))
    return {
        "Average clustering": nx.average_clustering(H),
        "Transitivity": nx.transitivity(H),
        "Average path length": nx.average_shortest_path_length(giant),
        "Degree assortativity": nx.degree_assortativity_coefficient(H),
    }


def club_links(H: nx.Graph, members: set) -> int:
    """Number of links with both ends in `members`."""
    return sum(1 for u, v in H.edges() if u in members and v in members)


def rich_club(H: nx.Graph) -> dict:
    """Unnormalised rich-club coefficient phi(k): link density among people with degree > k."""
    return nx.rich_club_coefficient(H, normalized=False)


def _one_null(D: nx.DiGraph, H: nx.Graph, club: set, seed: int) -> tuple:
    """Statistics of one degree-preserving shuffle and one G(n, m) random graph."""
    m_dir = D.number_of_edges()
    Rd = nx.DiGraph(D.edges())
    nx.directed_edge_swap(Rd, nswap=5 * m_dir, max_tries=100 * m_dir, seed=seed)
    Ru = shuffled_graph(H, seed=seed)
    shuffled = {"Reciprocity": nx.reciprocity(Rd), **undirected_stats(Ru),
                "club_links": club_links(Ru, club)}
    n = D.number_of_nodes()
    Gd = nx.gnm_random_graph(n, m_dir, seed=seed, directed=True)
    Gu = nx.gnm_random_graph(n, H.number_of_edges(), seed=seed)
    random = {"Reciprocity": nx.reciprocity(Gd), **undirected_stats(Gu)}
    return shuffled, random, rich_club(Ru)


def null_ensemble(D: nx.DiGraph, H: nx.Graph, n_null: int, club: set, seed: int = 0,
                  n_jobs: int = -1) -> dict:
    """The statistics in `n_null` randomised graphs of two kinds, run in parallel.

    shuffled: degree-preserving edge swaps (directed swaps for reciprocity,
              undirected swaps for the rest); also records the rich-club
              coefficient and the links inside `club`.
    random:   random graphs with the same number of people and links (G(n, m)).
    Returns {"shuffled": DataFrame, "random": DataFrame, "rich_club": DataFrame}.
    """
    runs = Parallel(n_jobs=n_jobs)(delayed(_one_null)(D, H, club, seed + i)
                                   for i in range(n_null))
    shuffled, random, clubs = zip(*runs)
    return {"shuffled": pd.DataFrame(shuffled), "random": pd.DataFrame(random),
            "rich_club": pd.DataFrame(list(clubs))}


def null_model_table(observed: dict, nulls: dict) -> pd.DataFrame:
    """Observed value against both null models, with the z-score and two-sided p
    against the degree-preserving shuffles."""
    rows = []
    for stat in STAT_ORDER:
        obs, sh, rnd = observed[stat], nulls["shuffled"][stat], nulls["random"][stat]
        sd = sh.std(ddof=1)
        z = (obs - sh.mean()) / sd if sd > 0 else np.nan
        p = (1 + np.sum(np.abs(sh - sh.mean()) >= abs(obs - sh.mean()))) / (len(sh) + 1)
        rows.append({"statistic": stat, "observed": obs, "random_mean": rnd.mean(),
                     "shuffled_mean": sh.mean(), "shuffled_sd": sd, "z": z, "p": p})
    return pd.DataFrame(rows)


def rich_club_table(H: nx.Graph, null_clubs: pd.DataFrame, min_people: int = 5) -> pd.DataFrame:
    """phi(k) against the shuffled graphs; rho = phi / mean shuffled phi.

    Only degrees k with at least `min_people` people above k are kept.
    """
    phi = pd.Series(rich_club(H), name="phi")
    degrees = np.array([d for _, d in H.degree()])
    table = phi.to_frame()
    table["people_above_k"] = [int((degrees > k).sum()) for k in table.index]
    table["null_mean"] = null_clubs.reindex(columns=table.index).mean()
    table["null_lo"] = null_clubs.reindex(columns=table.index).quantile(0.025)
    table["null_hi"] = null_clubs.reindex(columns=table.index).quantile(0.975)
    table["rho"] = table.phi / table.null_mean
    table.index.name = "k"
    return table[table.people_above_k >= min_people]


def club_test(H: nx.Graph, members: set, null_links: pd.Series, n_perm: int, rng) -> dict:
    """Do the members link to each other more than chance?

    Two nulls: shuffled graphs with the members fixed (controls for their degree),
    and random sets of the same size in the real graph (label shuffle).
    """
    observed = club_links(H, members)
    nodes = list(H)
    label_null = np.array([club_links(H, set(rng.choice(nodes, len(members), replace=False)))
                           for _ in range(n_perm)])
    k = len(members)
    return {"members": k, "possible_links": k * (k - 1) // 2, "observed_links": observed,
            "shuffled_mean": null_links.mean(), "p_shuffled": empirical_p(null_links.to_numpy(), observed),
            "label_mean": label_null.mean(), "p_label": empirical_p(label_null, observed)}


# ---------------------------------------------------------- assortativity ---
def _edge_arrays(G, nodes: list, weight: str | None):
    """Endpoints of each link as positions in `nodes`, and the link weights."""
    pos = {n: i for i, n in enumerate(nodes)}
    edges = [(pos[u], pos[v], d.get(weight, 1) if weight else 1)
             for u, v, d in G.edges(data=True) if u in pos and v in pos]
    u, v, w = (np.array(x) for x in zip(*edges))
    return u, v, w.astype(float)


def _mixing(codes: np.ndarray, u, v, w, k: int, directed: bool) -> np.ndarray:
    """k x k table of link weight between label codes (both directions if undirected)."""
    M = np.zeros((k, k))
    np.add.at(M, (codes[u], codes[v]), w)
    if not directed:
        np.add.at(M, (codes[v], codes[u]), w)
    return M


def mixing_counts(G, labels: dict, order: list, weight: str | None = None) -> pd.DataFrame:
    """Links (or emails, with weight) from each label to each label.

    For an undirected graph each link is counted in both directions, so the
    table is symmetric; for a directed graph rows are senders. People whose
    label is not in `order` are left out.
    """
    nodes = [n for n in G if labels.get(n) in order]
    code = {lab: i for i, lab in enumerate(order)}
    codes = np.array([code[labels[n]] for n in nodes])
    u, v, w = _edge_arrays(G, nodes, weight)
    M = _mixing(codes, u, v, w, len(order), G.is_directed())
    return pd.DataFrame(M, index=order, columns=order)


def assortativity(M) -> float:
    """Newman's assortativity coefficient r from a mixing table (rows = from, cols = to)."""
    e = np.asarray(M, dtype=float)
    e = e / e.sum()
    expected = (e.sum(axis=1) * e.sum(axis=0)).sum()
    return (np.trace(e) - expected) / (1 - expected)


def assortativity_test(H: nx.Graph, labels: dict, n_perm: int, rng,
                       weight: str | None = None) -> dict:
    """r for a node attribute against shuffled labels (people with no label left out)."""
    nodes = [n for n in H if pd.notna(labels.get(n))]
    order = sorted({labels[n] for n in nodes})
    code = {lab: i for i, lab in enumerate(order)}
    codes = np.array([code[labels[n]] for n in nodes])
    u, v, w = _edge_arrays(H, nodes, weight)
    k = len(order)
    observed = assortativity(_mixing(codes, u, v, w, k, directed=False))
    null = np.array([assortativity(_mixing(rng.permutation(codes), u, v, w, k, directed=False))
                     for _ in range(n_perm)])
    return {"r": observed, "null_mean": null.mean(), "null_p95": np.quantile(null, 0.95),
            "p": empirical_p(null, observed), "people": len(nodes), "groups": k}


def mixing_ratio(M: pd.DataFrame) -> pd.DataFrame:
    """Observed over expected email between groups, expected from row and column totals."""
    total = M.to_numpy().sum()
    expected = np.outer(M.sum(axis=1), M.sum(axis=0)) / total
    return M / expected
