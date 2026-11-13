"""Who bridges communities (Analysis 2a).

Node roles relative to the communities (Guimera & Amaral 2005), classic broker
measures, and tests of whether the people named in Congress are bridges.
Pure analysis functions; the script that runs them is `enron.run_brokers`.
"""

from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

# role groups for the seniority-controlled permutation test
ROLE_STRATA = {"Executive": "senior", "VP / Director": "senior", "Trading": "trading",
               "Legal": "legal"}


# ------------------------------------------------- Guimera-Amaral roles ---
def participation_coefficient(H: nx.Graph, comm_of: dict, weighted: bool = True) -> dict:
    """P_i = 1 - sum_s (k_is / k_i)^2, where k_is = person i's links (or email
    weight) to community s. 0 = all email inside one community."""
    P = {}
    for i in H:
        to_comm = defaultdict(float)
        for j, d in H[i].items():
            to_comm[comm_of[j]] += d["weight"] if weighted else 1.0
        k = sum(to_comm.values())
        P[i] = 1.0 - sum((v / k) ** 2 for v in to_comm.values()) if k else 0.0
    return P


def within_community_z(H: nx.Graph, comm_of: dict, weighted: bool = True) -> dict:
    """z_i = (k_i,own - mean of own community) / SD of own community, where
    k_i,own = person i's links (or email weight) inside their own community."""
    inside = {}
    for i in H:
        inside[i] = sum((d["weight"] if weighted else 1.0)
                        for j, d in H[i].items() if comm_of[j] == comm_of[i])
    by_comm = defaultdict(list)
    for i, v in inside.items():
        by_comm[comm_of[i]].append(v)
    z = {}
    for i, v in inside.items():
        vals = np.array(by_comm[comm_of[i]])
        sd = vals.std()
        z[i] = float((v - vals.mean()) / sd) if sd > 0 else 0.0
    return z


def community_shares(H: nx.Graph, comm_of: dict) -> pd.DataFrame:
    """Share of each person's email that goes to each community (rows sum to 1)."""
    rows = {}
    for i in H:
        to_comm = defaultdict(float)
        for j, d in H[i].items():
            to_comm[comm_of[j]] += d["weight"]
        total = sum(to_comm.values())
        rows[i] = {c: v / total for c, v in to_comm.items()} if total else {}
    shares = pd.DataFrame.from_dict(rows, orient="index").fillna(0.0)
    shares = shares[sorted(shares.columns)]
    shares.index.name = "person_id"
    return shares


def roles_over_seeds(H: nx.Graph, partitions: pd.DataFrame) -> pd.DataFrame:
    """Mean and SD of P and z over every Louvain run, weighted and unweighted.

    partitions: index = person, one column per seed (as from
    communities.seed_partitions); the 'community' column is ignored.
    """
    runs = partitions.drop(columns="community")
    records = defaultdict(lambda: defaultdict(list))
    for col in runs.columns:
        comm_of = runs[col].to_dict()
        for weighted, tag in [(True, "w"), (False, "u")]:
            P = participation_coefficient(H, comm_of, weighted)
            z = within_community_z(H, comm_of, weighted)
            for n in H:
                records[n][f"P_{tag}"].append(P[n])
                records[n][f"z_{tag}"].append(z[n])
    rows = []
    for n, vals in records.items():
        row = {"person_id": n}
        for key, values in vals.items():
            row[f"{key}_mean"] = float(np.mean(values))
            row[f"{key}_sd"] = float(np.std(values))
        rows.append(row)
    return pd.DataFrame(rows).set_index("person_id")


# ------------------------------------------------------- broker measures ---
def broker_measures(H: nx.Graph) -> pd.DataFrame:
    """Degree, strength, weighted betweenness (distance = 1/emails) and Burt's
    constraint and effective size (weighted)."""
    G = H.copy()
    for _, _, d in G.edges(data=True):
        d["distance"] = 1.0 / d["weight"]
    return pd.DataFrame({
        "degree": dict(G.degree()),
        "strength": dict(G.degree(weight="weight")),
        "betweenness": nx.betweenness_centrality(G, weight="distance", normalized=True),
        "constraint": nx.constraint(G, weight="weight"),
        "effective_size": nx.effective_size(G, weight="weight"),
    }).rename_axis("person_id")


# --------------------------------------------------------- visibility tests ---
def spearman_permutation(x: np.ndarray, y: np.ndarray, n_perm: int, rng) -> dict:
    """Spearman correlation with a two-sided permutation p-value."""
    rho = stats.spearmanr(x, y).statistic
    null = np.array([stats.spearmanr(x, rng.permutation(y)).statistic for _ in range(n_perm)])
    p = (np.sum(np.abs(null) >= abs(rho)) + 1) / (n_perm + 1)
    return {"rho": float(rho), "p": float(p)}


def visibility_correlations(table: pd.DataFrame, measures, n_perm: int, rng) -> pd.DataFrame:
    """Correlation between Congress mentions and each broker measure."""
    rows = []
    for m in measures:
        res = spearman_permutation(table[m].to_numpy(), table["mentions"].to_numpy(), n_perm, rng)
        rows.append({"measure": m, **res})
    return pd.DataFrame(rows)


def named_vs_not(table: pd.DataFrame, measure: str) -> dict:
    """Mann-Whitney test of a measure for people named in Congress vs never named."""
    named = table.loc[table["named"], measure]
    other = table.loc[~table["named"], measure]
    res = stats.mannwhitneyu(named, other, alternative="two-sided")
    return {"measure": measure, "named_n": len(named), "named_median": float(named.median()),
            "others_median": float(other.median()), "U": float(res.statistic),
            "p": float(res.pvalue)}


def stratified_permutation(table: pd.DataFrame, measure: str, n_perm: int, rng) -> dict:
    """Is the mean of `measure` among named people higher than chance, when the
    'named' label is shuffled only within role groups (controls for seniority)?"""
    strata = table["role"].map(ROLE_STRATA).fillna("other").to_numpy()
    named = table["named"].to_numpy()
    values = table[measure].to_numpy()
    observed = values[named].mean()
    null = np.empty(n_perm)
    for k in range(n_perm):
        shuffled = named.copy()
        for s in np.unique(strata):
            idx = np.where(strata == s)[0]
            shuffled[idx] = rng.permutation(named[idx])
        null[k] = values[shuffled].mean()
    return {"measure": measure, "named_mean": float(observed),
            "null_mean": float(null.mean()),
            "p_greater": float((np.sum(null >= observed) + 1) / (n_perm + 1))}


def visibility_by_community(table: pd.DataFrame) -> pd.DataFrame:
    """Named people per community vs chance (hypergeometric), Benjamini-Hochberg corrected."""
    N, K = len(table), int(table["named"].sum())
    rows = []
    for c, grp in table.groupby("community"):
        n, k = len(grp), int(grp["named"].sum())
        rows.append({"community": f"C{c}", "people": n, "named": k,
                     "expected": n * K / N,
                     "mentions": int(grp["mentions"].sum()),
                     "p_more_than_chance": float(stats.hypergeom.sf(k - 1, N, K, n))})
    out = pd.DataFrame(rows)
    out["p_BH"] = stats.false_discovery_control(out["p_more_than_chance"].to_numpy())
    return out
