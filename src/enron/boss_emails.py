"""What the bosses wrote about, and whether they email each other.

Two groups of bosses: the finance core (the seven finance and legal people Congress
investigated, imported without a mailbox: Fastow, Causey, Glisan, Kopper, McMahon,
Watkins, Mintz) and the executives among the 148. Their own-word emails are compared
with everyone else's on the Congress themes (term lists), on the emails' own NMF
topics, and on the words most typical of each group (weighted log-odds, Monroe et al.
2008). Too few finance-core emails exist (about 76) to fit a topic model of their own.

The database holds only emails that involve at least one of the 148, so emails among
the finance core alone are not in it: their links to each other are mostly invisible.
"""

from collections import Counter

import numpy as np
import pandas as pd

FINANCE_CORE = list(range(149, 156))      # person_ids added by import_new_people
GROUP_ORDER = ["Finance core", "Executives", "Other employees"]


def boss_groups(people: pd.DataFrame) -> pd.Series:
    """Group of every person: finance core, executives (role Executive), or others."""
    groups = pd.Series("Other employees", index=people.index)
    groups[people["role"] == "Executive"] = "Executives"
    groups[groups.index.isin(FINANCE_CORE)] = "Finance core"
    return groups


def group_summary(emails: pd.DataFrame, names: pd.Series) -> pd.DataFrame:
    """Per group: emails written, share with any Congress theme (1-7), share on energy (8),
    and the number of emails tagged with each Congress theme."""
    congress = [f"terms_{t}" for t in range(1, 8)]
    rows = []
    for group in GROUP_ORDER:
        g = emails[emails["group"] == group]
        row = {"group": group, "emails written": len(g),
               "Congress-theme emails": int(g[congress].any(axis=1).sum()),
               "Congress-theme share (%)": round(100 * g[congress].any(axis=1).mean(), 1) if len(g) else 0,
               "energy share (%)": round(100 * g["terms_8"].mean(), 1) if len(g) else 0}
        row.update({names[t]: int(g[f"terms_{t}"].sum()) for t in range(1, 8)})
        rows.append(row)
    return pd.DataFrame(rows)


def topic_mix(emails: pd.DataFrame, topic_names: dict) -> pd.DataFrame:
    """Share (%) of each group's emails (at least 20 words) in each email topic."""
    with_topic = emails[emails["topic"].notna()].copy()
    with_topic["topic"] = with_topic["topic"].astype(int).map(lambda t: topic_names.get(t, f"topic {t}"))
    table = pd.crosstab(with_topic["group"], with_topic["topic"], normalize="index").mul(100).round(1)
    table.insert(0, "emails with a topic", with_topic["group"].value_counts())
    return table.reindex([g for g in GROUP_ORDER if g in table.index])


def log_odds(tokens_a, tokens_b, prior: float = 0.01, min_count: int = 3, top: int = 25) -> pd.DataFrame:
    """Words most typical of texts A against texts B: weighted log-odds ratio with an
    informative Dirichlet prior (Monroe, Colaresi and Quinn 2008), as a z-score."""
    a = Counter(t for ts in tokens_a for t in ts)
    b = Counter(t for ts in tokens_b for t in ts)
    total = a + b
    n_all = sum(total.values())
    n_a, n_b, a0 = sum(a.values()), sum(b.values()), prior * n_all
    rows = []
    for word, count in a.items():
        if count < min_count:
            continue
        aw = a0 * total[word] / n_all
        delta = (np.log((count + aw) / (n_a + a0 - count - aw))
                 - np.log((b[word] + aw) / (n_b + a0 - b[word] - aw)))
        rows.append((word, count, b[word], delta / np.sqrt(1 / (count + aw) + 1 / (b[word] + aw))))
    table = pd.DataFrame(rows, columns=["word", "count in group", "count elsewhere", "z"])
    return table.sort_values("z", ascending=False).head(top).round({"z": 2}).reset_index(drop=True)


def deliveries(raw_emails: pd.DataFrame) -> pd.DataFrame:
    """One row per sender-recipient delivery (recipients without the sender)."""
    return pd.DataFrame([(e.sender_id, r) for e in raw_emails.itertuples() for r in e.others],
                        columns=["sender", "recipient"])


def group_links(pairs: pd.DataFrame, groups: pd.Series) -> pd.DataFrame:
    """Deliveries from each group to each group (rows: sender's group)."""
    table = pd.crosstab(pairs["sender"].map(groups), pairs["recipient"].map(groups))
    return table.reindex(index=GROUP_ORDER, columns=GROUP_ORDER, fill_value=0)


def person_links(pairs: pd.DataFrame, bosses: list, names: pd.Series) -> pd.DataFrame:
    """Per boss: deliveries sent and received, and how many of them go to or come from bosses."""
    rows = []
    for person in bosses:
        sent, received = pairs[pairs["sender"] == person], pairs[pairs["recipient"] == person]
        rows.append({"person": names[person], "sent": len(sent),
                     "sent to bosses": int(sent["recipient"].isin(bosses).sum()),
                     "received": len(received),
                     "received from bosses": int(received["sender"].isin(bosses).sum())})
    return pd.DataFrame(rows)
