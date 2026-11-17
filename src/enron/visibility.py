"""Hidden vs public people (Analysis 3).

Does centrality in the email network predict who was named in Congress (RQ1),
and who are the brokers nobody named (RQ2)? Pure analysis functions; the script
that runs them is `enron.run_visibility`.
"""

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

from enron.brokers import spearman_permutation
from enron.communities import shuffled_graph

CENTRALITY_MEASURES = ["PageRank", "Emails received", "Emails sent", "Betweenness",
                       "Eigenvector"]


# ------------------------------------------------------------- centrality ---
def with_distance(H: nx.Graph) -> nx.Graph:
    """Copy of H where each link also has distance = 1 / emails (for shortest paths)."""
    G = H.copy()
    for _, _, d in G.edges(data=True):
        d["distance"] = 1.0 / d["weight"]
    return G


def centrality_measures(D: nx.DiGraph, H: nx.Graph) -> pd.DataFrame:
    """Five centrality measures per person.

    D: directed graph (PageRank, emails received / sent).
    H: undirected graph (betweenness with distance = 1 / emails, eigenvector).
    """
    G = with_distance(H)
    table = pd.DataFrame({
        "PageRank": nx.pagerank(D, weight="weight"),
        "Emails received": dict(D.in_degree(weight="weight")),
        "Emails sent": dict(D.out_degree(weight="weight")),
        "Betweenness": nx.betweenness_centrality(G, weight="distance"),
        "Eigenvector": nx.eigenvector_centrality(H, weight="weight", max_iter=2000),
        "degree": dict(H.degree()),
    })
    table.index.name = "person_id"
    return table


def percentile(values: pd.Series) -> pd.Series:
    """Percentile rank, 100 = highest value."""
    return values.rank(pct=True) * 100


# --------------------------------------------------------- RQ1: visibility ---
def auc_permutation(named: np.ndarray, scores: np.ndarray, n_perm: int, rng) -> dict:
    """AUC = chance that a named person scores higher than an unnamed one
    (0.5 = no difference), with a one-sided p-value from shuffled labels."""
    auc = roc_auc_score(named, scores)
    null = np.array([roc_auc_score(rng.permutation(named), scores) for _ in range(n_perm)])
    return {"AUC": float(auc), "p_AUC": float((np.sum(null >= auc) + 1) / (n_perm + 1))}


def top_n_test(table: pd.DataFrame, measure: str, n: int = 20) -> dict:
    """Named people among the n most central, against chance (hypergeometric)."""
    top = table[measure].nlargest(n).index
    k = int(table.loc[top, "named"].sum())
    n_people, n_named = len(table), int(table["named"].sum())
    return {f"named_in_top{n}": k, f"expected_top{n}": n * n_named / n_people,
            f"p_top{n}": float(stats.hypergeom.sf(k - 1, n_people, n_named, n))}


def visibility_tests(table: pd.DataFrame, n_perm_auc: int, n_perm_rho: int,
                     rng, top_n: int = 20) -> pd.DataFrame:
    """For each centrality measure: AUC, Spearman correlation with mentions, top-n test."""
    named = table["named"].to_numpy()
    rows = []
    for measure in CENTRALITY_MEASURES:
        scores = table[measure].to_numpy()
        rho = spearman_permutation(scores, table["mentions"].to_numpy(), n_perm_rho, rng)
        rows.append({"measure": measure,
                     **auc_permutation(named, scores, n_perm_auc, rng),
                     "rho": rho["rho"], "p_rho": rho["p"],
                     **top_n_test(table, measure, top_n)})
    return pd.DataFrame(rows)


def named_ranks(table: pd.DataFrame) -> pd.DataFrame:
    """Rank (1 = most central) of each named person on every measure."""
    ranks = table[CENTRALITY_MEASURES].rank(ascending=False, method="min").astype(int)
    named = ranks.loc[table["named"]]
    return named.sort_values("PageRank")


# ------------------------------------------------------------ RQ2: brokers ---
def betweenness_zscores(H: nx.Graph, n_null: int) -> pd.DataFrame:
    """Betweenness of each person against degree-preserving shuffled graphs.

    Returns columns betweenness, null_mean, null_sd, broker_z.
    """
    observed = pd.Series(nx.betweenness_centrality(with_distance(H), weight="distance"))
    null = pd.concat([pd.Series(nx.betweenness_centrality(with_distance(shuffled_graph(H, s)),
                                                          weight="distance"))
                      for s in range(n_null)], axis=1).reindex(observed.index)
    out = pd.DataFrame({"betweenness": observed, "null_mean": null.mean(axis=1),
                        "null_sd": null.std(axis=1)})
    out["broker_z"] = (out["betweenness"] - out["null_mean"]) / out["null_sd"].replace(0, np.nan)
    out.index.name = "person_id"
    return out


def find_brokers(table: pd.DataFrame, z_min: float = 2.0, min_degree: int = 5) -> pd.Series:
    """Broker = betweenness z-score >= z_min and at least min_degree links."""
    return (table["broker_z"] >= z_min) & (table["degree"] >= min_degree)


# ------------------------------------------------------------ groups, roles ---
def visibility_groups(table: pd.DataFrame, central_share: float = 0.2,
                      measure: str = "PageRank") -> pd.Series:
    """Public faces (central, named), hidden core (central, not named), public
    only (named, not central), others. Central = top `central_share` on `measure`."""
    central = table[measure] >= table[measure].quantile(1 - central_share)
    named = table["named"]
    groups = np.select([central & named, central & ~named, ~central & named],
                       ["Public faces", "Hidden core", "Public only"], "Others")
    return pd.Series(groups, index=table.index, name="group")


def role_table(table: pd.DataFrame, roles: list) -> pd.DataFrame:
    """People and named people per role, in the given order."""
    out = table.groupby("role").agg(people=("named", "size"), named=("named", "sum"))
    out = out.reindex(roles).fillna(0).astype(int)
    out["named_share"] = out["named"] / out["people"].replace(0, np.nan)
    return out


def executive_test(table: pd.DataFrame) -> dict:
    """Fisher exact test: are executives over-represented among named people?"""
    named, executive = table["named"], table["role"] == "Executive"
    counts = [[int((named & executive).sum()), int((named & ~executive).sum())],
              [int((~named & executive).sum()), int((~named & ~executive).sum())]]
    odds, p = stats.fisher_exact(counts)
    return {"named_executives": counts[0][0], "named": int(named.sum()),
            "other_executives": counts[1][0], "others": int((~named).sum()),
            "odds_ratio": float(odds), "p": float(p)}


# ---------------------------------------------------------------- agreement ---
def rank_agreement(ours: pd.Series, theirs: pd.Series) -> dict:
    """Spearman correlation between two centrality scores for the people in both."""
    both = pd.concat([ours, theirs], axis=1, join="inner").dropna()
    rho = stats.spearmanr(both.iloc[:, 0], both.iloc[:, 1]).statistic
    return {"people": len(both), "rho": float(rho)}
