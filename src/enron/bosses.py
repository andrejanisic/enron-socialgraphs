"""The bosses: what the finance core and the executives wrote about, and whether they
email each other.

Groups: the finance core (seven finance and legal managers without a mailbox, whose
emails with the 148 were added: Fastow, Causey, Glisan, Kopper, McMahon, Watkins,
Mintz), the executives among the 148 (role Executive), and everyone else.

Caveat built into the data: the database holds only emails that involve at least one
of the 148, so emails among the finance core alone (with nobody from the 148 on them)
are missing, and their email with each other is undercounted.
"""

import csv
from collections import Counter

import numpy as np
import pandas as pd

FINANCE_CORE = {          # person_id: public title in 2001
    149: "Chief financial officer",
    150: "Chief accounting officer",
    151: "Treasurer",
    152: "Managing director, Global Finance (Fastow's aide)",
    153: "Treasurer until 2000, chief financial officer from October 2001",
    154: "Vice president, corporate development",
    155: "General counsel, Enron Global Finance",
}
GROUPS = ["Finance core", "Executives", "Others"]


def person_groups(people: pd.DataFrame) -> pd.Series:
    """Group of every person (index = person_id)."""
    groups = pd.Series("Others", index=people.index)
    groups[people["role"] == "Executive"] = "Executives"
    groups[people.index.isin(FINANCE_CORE)] = "Finance core"
    return groups


def deliveries(emails: pd.DataFrame) -> pd.DataFrame:
    """One row per sender-recipient pair of each email (emails to oneself left out)."""
    rows = [(e, s, r) for e, s, rs in zip(emails["email_id"], emails["sender_id"], emails["recipients"])
            for r in rs if r != s]
    return pd.DataFrame(rows, columns=["email_id", "sender", "recipient"])


def group_mixing(d: pd.DataFrame, groups: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deliveries from group to group (rows = senders), and observed / expected, where
    expected = (group's deliveries sent) x (other group's deliveries received) / all."""
    counts = pd.crosstab(d["sender"].map(groups), d["recipient"].map(groups)).reindex(
        index=GROUPS, columns=GROUPS, fill_value=0)
    expected = np.outer(counts.sum(axis=1), counts.sum(axis=0)) / counts.to_numpy().sum()
    return counts, (counts / expected).round(2)


def boss_pairs(d: pd.DataFrame, bosses: list, people: pd.DataFrame, groups: pd.Series) -> pd.DataFrame:
    """Every pair of bosses that exchanged email, with the deliveries in each direction."""
    sub = d[d["sender"].isin(bosses) & d["recipient"].isin(bosses)]
    pair = sub.apply(lambda r: tuple(sorted((r["sender"], r["recipient"]))), axis=1)
    rows = []
    for (a, b), g in sub.groupby(pair):
        rows.append({"person_a": people.at[a, "full_name"], "group_a": groups[a],
                     "person_b": people.at[b, "full_name"], "group_b": groups[b],
                     "a_to_b": int(((g["sender"] == a) & (g["recipient"] == b)).sum()),
                     "b_to_a": int(((g["sender"] == b) & (g["recipient"] == a)).sum())})
    table = pd.DataFrame(rows)
    if len(table):
        table["total"] = table["a_to_b"] + table["b_to_a"]
        table = table.sort_values("total", ascending=False).reset_index(drop=True)
    return table


def top_contacts(d: pd.DataFrame, person: int, people: pd.DataFrame, groups: pd.Series, n: int = 5) -> str:
    """A person's n main contacts (deliveries in both directions), as text."""
    other = pd.concat([d.loc[d["sender"] == person, "recipient"], d.loc[d["recipient"] == person, "sender"]])
    return "; ".join(f"{people.at[p, 'full_name']} ({groups[p].lower()}, {c})"
                     for p, c in other.value_counts().head(n).items())


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% interval of a proportion k/n."""
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def theme_shares(tags: pd.DataFrame, groups: pd.Series, names: pd.Series, finance: list) -> pd.DataFrame:
    """Per group: own-word emails written, the share with any finance theme and with energy,
    and the emails with each theme."""
    t = tags.assign(group=tags["sender_id"].map(groups))
    t["finance"] = t[[f"terms_{i}" for i in finance]].astype(bool).any(axis=1)
    energy = [i for i in names.index if i not in finance][0]
    rows = []
    for group in GROUPS:
        g = t[t["group"] == group]
        lo, hi = wilson(int(g["finance"].sum()), len(g))
        row = {"group": group, "own-word emails": len(g),
               "any finance theme (%)": round(100 * g["finance"].mean(), 1) if len(g) else np.nan,
               "95% CI": f"{100 * lo:.1f}-{100 * hi:.1f}" if len(g) else "",
               "energy (%)": round(100 * g[f"terms_{energy}"].astype(bool).mean(), 1) if len(g) else np.nan}
        row.update({names[i]: int(g[f"terms_{i}"].astype(bool).sum()) for i in names.index})
        rows.append(row)
    return pd.DataFrame(rows)


def load_topic_labels(path) -> pd.DataFrame:
    """The hand-written labels of the team's NMF topics (reports/nmf/topic_labels.csv:
    topic_number, long_title, short_title): index = topic number, columns short and long.

    Some long titles hold commas without quotes ("Meetings, Office Coordination and
    Scheduling"), so each row is read as: first field = number, last field = short
    title, everything between = long title."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.reader(f) if r and any(x.strip() for x in r)]
    labels = pd.DataFrame([{"topic": int(r[0]), "long": ",".join(r[1:-1]).strip(), "short": r[-1].strip()}
                           for r in rows[1:]])
    return labels.set_index("topic")[["short", "long"]].sort_index()


def load_email_topics(path, n_topics: int) -> pd.DataFrame:
    """Each email's topic mix from the team's NMF model (reports/nmf/email_topics.csv).

    The weights topic_0 ... topic_{k-1} are rescaled to sum to 1 per email (they already
    do in the file written by nmf_tf_idf_community.py), giving columns share_0 ...
    share_{k-1}. main_topic = the topic with the largest share (NaN for the few emails
    with no topic weight at all)."""
    t = pd.read_csv(path)
    cols = [f"topic_{i}" for i in range(n_topics)]
    missing = [c for c in cols if c not in t.columns]
    if missing:
        raise ValueError(f"{path} has no columns {missing}: the labels and the topic file do not match")
    w = t[cols].to_numpy(dtype=float)
    total = w.sum(axis=1, keepdims=True)
    share = np.divide(w, total, out=np.zeros_like(w), where=total > 0)
    out = pd.DataFrame(share, columns=[f"share_{i}" for i in range(n_topics)])
    out.insert(0, "email_id", t["email_id"].to_numpy())
    out.insert(1, "sender_id", t["sender_id"].to_numpy())
    out["main_topic"] = np.where(total[:, 0] > 0, share.argmax(axis=1), np.nan)
    return out


def topic_mix(topics: pd.DataFrame, sets: dict, labels: pd.DataFrame) -> pd.DataFrame:
    """Mean topic share (%) of the emails in each set, one row per topic.

    sets: {name: boolean mask over the rows of `topics`}. The mean of the emails'
    topic shares is the measure used for the communities' topic mix (reports/nmf)."""
    share_cols = [f"share_{i}" for i in labels.index]
    table = labels.rename(columns={"short": "topic", "long": "description"}).copy()
    for name, mask in sets.items():
        sub = topics.loc[mask, share_cols]
        table[f"{name} (n={len(sub)})"] = (100 * sub.mean().to_numpy()).round(1) if len(sub) else np.nan
    return table.reset_index(drop=True)


def topic_distance(topics: pd.DataFrame, a, b, n_shuffles: int = 10_000,
                   seed: int = 0) -> tuple[float, float]:
    """How different the mean topic mixes of two sets of emails are: the total variation
    distance (half the summed absolute differences of the topic shares, in percentage
    points; 0 = same mix, 100 = no topic in common), and a one-sided p-value from
    shuffling the set labels over the emails of both sets."""
    share_cols = [c for c in topics.columns if c.startswith("share_")]
    xa = topics.loc[a, share_cols].to_numpy()
    xb = topics.loc[b, share_cols].to_numpy()
    x = np.vstack([xa, xb])
    na, n = len(xa), len(xa) + len(xb)
    total = x.sum(axis=0)

    def tvd(sum_a):
        return 50 * np.abs(sum_a / na - (total - sum_a) / (n - na)).sum()

    observed = tvd(xa.sum(axis=0))
    rng = np.random.default_rng(seed)
    hits = sum(tvd(x[rng.choice(n, na, replace=False)].sum(axis=0)) >= observed for _ in range(n_shuffles))
    return observed, (hits + 1) / (n_shuffles + 1)


def contact_density(d: pd.DataFrame, people: list) -> tuple[int, int]:
    """Pairs of the given people who exchanged at least one email (either direction),
    and the number of possible pairs among those of them with any email."""
    sub = d[d["sender"].isin(people) & d["recipient"].isin(people)]
    pairs = {tuple(sorted(p)) for p in zip(sub["sender"], sub["recipient"])}
    active = set(d["sender"]) | set(d["recipient"])
    k = len(set(people) & active)
    return len(pairs), k * (k - 1) // 2


def over_represented(mix: pd.DataFrame, column: str, baseline: str, top: int = 3,
                     min_share: float = 2.0) -> list[tuple[str, float, float]]:
    """Topics with the highest ratio of `column` to `baseline` among topics with at
    least min_share % in `column`: (topic, share, ratio)."""
    m = mix[mix[column] >= min_share].assign(ratio=lambda x: x[column] / x[baseline])
    m = m.sort_values("ratio", ascending=False).head(top)
    return list(zip(m["topic"], m[column], m["ratio"]))


def person_topics(topics: pd.DataFrame, people_ids: list, labels: pd.DataFrame) -> pd.DataFrame:
    """Mean topic share (%) of each person's emails (rows = person_ids)."""
    share_cols = [f"share_{i}" for i in labels.index]
    sub = topics[topics["sender_id"].isin(people_ids)]
    table = (100 * sub.groupby("sender_id")[share_cols].mean()).round(1)
    table.columns = labels["short"].tolist()
    table.insert(0, "emails", sub.groupby("sender_id").size())
    table = table.reindex(people_ids)
    table["emails"] = table["emails"].fillna(0).astype(int)
    return table


def typical_words(tokens_a, tokens_b, top: int = 15, prior: float = 0.01, min_count: int = 3) -> pd.DataFrame:
    """Words most typical of A against B: weighted log-odds with an informative
    Dirichlet prior (Monroe, Colaresi and Quinn 2008), as z-scores."""
    a = Counter(t for ts in tokens_a for t in ts)
    b = Counter(t for ts in tokens_b for t in ts)
    total = a + b
    n, na, nb = sum(total.values()), sum(a.values()), sum(b.values())
    a0 = prior * n
    rows = []
    for w, c in a.items():
        if c < min_count:
            continue
        aw = a0 * total[w] / n
        delta = np.log((c + aw) / (na + a0 - c - aw)) - np.log((b[w] + aw) / (nb + a0 - b[w] - aw))
        rows.append((w, c, b[w], delta / np.sqrt(1 / (c + aw) + 1 / (b[w] + aw))))
    table = pd.DataFrame(rows, columns=["word", "count", "count_others", "z"])
    return table.sort_values("z", ascending=False).head(top).reset_index(drop=True)
