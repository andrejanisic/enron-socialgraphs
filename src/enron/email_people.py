"""Who wrote and who received the emails on what Congress investigated.

People are put in four groups by their place in the email network and in the
Congress record (named by Congress, central core, brokers, others). The question is
whether the emails carrying a Congress theme (themes 1-7, pooled) came from, or went
to, any group more often than chance. Chance = the same number of theme emails spread
at random over all emails, which keeps every person's number of emails fixed.
"""

import networkx as nx
import numpy as np
import pandas as pd

GROUP_ORDER = ["Named by Congress", "Central core", "Brokers", "Others"]


# ------------------------------------------------------------- the groups ---
def betweenness_z(H: nx.Graph, n_null: int, weighted: bool, seed: int = 0) -> pd.Series:
    """Betweenness against degree-preserving shuffles of the graph (z-score).

    weighted=True uses distance = 1 / emails (many emails = close); False counts links.
    The shuffles keep each person's number of links; with weights, the email counts
    travel with the swapped links."""
    def score(G):
        if weighted:
            for _, _, d in G.edges(data=True):
                d["distance"] = 1.0 / d["weight"]
            return pd.Series(nx.betweenness_centrality(G, weight="distance"))
        return pd.Series(nx.betweenness_centrality(G))

    observed = score(H.copy())
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_null):
        G = H.copy()
        nx.double_edge_swap(G, nswap=2 * G.number_of_edges(), max_tries=200 * G.number_of_edges(),
                            seed=int(rng.integers(1 << 31)))
        for u, v, d in G.edges(data=True):
            d.setdefault("weight", 1)
        null.append(score(G))
    null = pd.concat(null, axis=1)
    return ((observed - null.mean(axis=1)) / null.std(axis=1).replace(0, np.nan)).fillna(0)


def assign_groups(people: pd.DataFrame, named: pd.Series, central: pd.Series,
                  broker: pd.Series) -> pd.Series:
    """One group per person, in this order: named by Congress, central core,
    brokers, others."""
    group = np.select([named, central, broker], GROUP_ORDER[:3], GROUP_ORDER[3])
    return pd.Series(group, index=people.index, name="group")


# ------------------------------------------------------- emails per person ---
def person_counts(emails: pd.DataFrame, flag: str, people_index) -> pd.DataFrame:
    """Per person: emails written, emails written with `flag`, emails received
    (counting each email once per recipient, and weighted 1 / number of recipients)
    and the same for emails with `flag`."""
    written = emails.groupby("sender_id").size()
    written_flag = emails[emails[flag]].groupby("sender_id").size()
    rows = emails[["others", "n_recipients", flag]].explode("others").dropna(subset=["others"])
    rows["w"] = 1.0 / rows["n_recipients"]
    received = rows.groupby("others").size()
    received_w = rows.groupby("others")["w"].sum()
    received_flag = rows[rows[flag]].groupby("others").size()
    received_flag_w = rows[rows[flag]].groupby("others")["w"].sum()
    out = pd.DataFrame({"written": written, "written_theme": written_flag,
                        "received": received, "received_theme": received_flag,
                        "received_w": received_w, "received_theme_w": received_flag_w},
                       index=people_index).fillna(0)
    return out


# ------------------------------------------------------------------- tests ---
def _recipient_matrix(emails: pd.DataFrame, groups: pd.Series, weighted: bool) -> np.ndarray:
    """emails x groups: how much of each email each group received."""
    col = {g: i for i, g in enumerate(GROUP_ORDER)}
    M = np.zeros((len(emails), len(GROUP_ORDER)))
    for k, (others, n) in enumerate(zip(emails["others"], emails["n_recipients"])):
        for r in others:
            g = groups.get(r)
            if g is not None:
                M[k, col[g]] += (1.0 / n) if weighted else 1.0
    return M


def group_test(emails: pd.DataFrame, groups: pd.Series, flag: str, n_perm: int = 10000,
               weighted: bool = True, seed: int = 2026) -> pd.DataFrame:
    """For each group: theme emails written and received, against chance.

    Chance: the flag is shuffled over all emails n_perm times (every email keeps its
    sender and recipients). `expected` = mean over shuffles, `chance_low` /
    `chance_high` = the range holding 95% of the shuffles, `ratio` = observed /
    expected, `p_high` / `p_low` = share of shuffles at least as high / as low as
    observed (one-sided; +1 smoothing)."""
    rng = np.random.default_rng(seed)
    col = {g: i for i, g in enumerate(GROUP_ORDER)}
    sender_group = emails["sender_id"].map(groups).map(col).to_numpy()
    S = np.zeros((len(emails), len(GROUP_ORDER)))
    S[np.arange(len(emails)), sender_group] = 1
    R = _recipient_matrix(emails, groups, weighted)
    flag_v = emails[flag].to_numpy().astype(float)
    obs = {"written": flag_v @ S, "received": flag_v @ R}
    null = {"written": np.empty((n_perm, len(GROUP_ORDER))), "received": np.empty((n_perm, len(GROUP_ORDER)))}
    for b in range(n_perm):
        f = rng.permutation(flag_v)
        null["written"][b] = f @ S
        null["received"][b] = f @ R
    rows = []
    for side in ("written", "received"):
        for g, i in col.items():
            o, n = obs[side][i], null[side][:, i]
            rows.append({"side": side, "group": g, "observed": o, "expected": n.mean(),
                         "chance_low": np.percentile(n, 2.5), "chance_high": np.percentile(n, 97.5),
                         "ratio": o / n.mean() if n.mean() > 0 else np.nan,
                         "p_high": (1 + (n >= o).sum()) / (n_perm + 1),
                         "p_low": (1 + (n <= o).sum()) / (n_perm + 1)})
    return pd.DataFrame(rows)


def timeline(emails: pd.DataFrame, flag: str) -> pd.DataFrame:
    """Theme emails and all emails per month (emails with a known date)."""
    known = emails[emails["date_known"]]
    month = known["date"].dt.tz_localize(None).dt.to_period("M")
    return pd.DataFrame({"emails": known.groupby(month).size(),
                         "theme_emails": known[known[flag]].groupby(month).size()}).fillna(0).astype(int)
