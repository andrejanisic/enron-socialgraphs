"""
Step 7: network position of every person: how much they BRIDGE communities.

Input:  pipeline/output/partitions_louvain.csv (Step 4), edges_undirected.csv (Step 3),
        emails_clean.csv, recipients_clean.csv (Step 2), text_clean.csv (Step 6), people.csv (Step 5)
Output: pipeline/output/bridge_measures.csv  one row per person

Measures:
  P (main)        participation coefficient of the emails a person RECEIVED:
                  P = 1 - sum over communities of (share of my received emails from that community)^2
                  = the chance that two of my received emails, picked at random, come from
                  different communities. 0 = everything from one community.
  outside share   share of my received emails that come from outside my own community
                  (the simple, course-level version of P; used as a check)
  constraint      Burt's constraint on the undirected weighted network: high when my contacts
                  are also connected to each other (no 'structural holes'). Does not use communities.
  effective size  Burt's effective size: number of contacts, minus how redundant they are
  bandwidth       emails received per contact (all received emails / number of different senders)

Decisions:
  B1. P is computed from the USABLE received emails (Step 6), so P and the text diversity D describe
      exactly the same inbox. P from ALL received emails is computed too, as a check.
      P is computed for each of the 50 Louvain runs and then averaged (communities differ between runs).
  B2. People in the test: >= 20 usable received emails, and not a mixed mailbox (Step 5).
  B3. Outside share as a course-level check of P.
  B4. Constraint and effective size from the network of all cleaned emails (structure, not text).
  B5. Bandwidth from all received emails (it describes the channel, not the text).

Run from the project root:
    uv run python pipeline/step7_bridge_measures.py
"""
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
MIN_USABLE = 20

parts = pd.read_csv(OUT / "partitions_louvain.csv", index_col="person_id")   # 147 people x 50 runs
people = pd.read_csv(OUT / "people.csv", index_col="person_id")
emails = pd.read_csv(OUT / "emails_clean.csv", usecols=["email_id", "sender_id"])
recipients = pd.read_csv(OUT / "recipients_clean.csv")
text = pd.read_csv(OUT / "text_clean.csv", usecols=["email_id", "usable"])
edges = pd.read_csv(OUT / "edges_undirected.csv")

# one row per arrow (email -> recipient), with sender and whether the email has usable text
arrows = recipients.merge(emails, on="email_id").merge(text, on="email_id")
usable_arrows = arrows[arrows["usable"]]


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


def participation(arr, run):
    """P and outside share of every recipient, for one Louvain run (a column of `parts`)."""
    comm = parts[run]
    counts = pd.crosstab(arr["recipient_id"], arr["sender_id"].map(comm))   # received emails per community
    share = counts.div(counts.sum(axis=1), axis=0)
    P = 1 - (share ** 2).sum(axis=1)
    own = pd.Series([share.loc[i, comm[i]] if comm[i] in share.columns else 0.0 for i in share.index],
                    index=share.index)
    return P, 1 - own


P_runs, P_all_runs, outside_runs = [], [], []
for run in parts.columns:
    P, outside = participation(usable_arrows, run)
    P_runs.append(P)
    outside_runs.append(outside)
    P_all_runs.append(participation(arrows, run)[0])
P_runs = pd.concat(P_runs, axis=1)

m = pd.DataFrame(index=people.index)
m["name"] = people["name"]
m["community"] = people["community"]
m["senior"] = people["senior"]
m["received_usable"] = usable_arrows.groupby("recipient_id").size().reindex(m.index, fill_value=0)
m["received_all"] = arrows.groupby("recipient_id").size().reindex(m.index, fill_value=0)
m["senders"] = arrows.groupby("recipient_id")["sender_id"].nunique().reindex(m.index, fill_value=0)
m["P"] = P_runs.mean(axis=1)
m["P_sd"] = P_runs.std(axis=1)
m["P_all_emails"] = pd.concat(P_all_runs, axis=1).mean(axis=1)
m["outside_share"] = pd.concat(outside_runs, axis=1).mean(axis=1)
m["bandwidth"] = m["received_all"] / m["senders"]

U = nx.Graph()
for a, b, w in zip(edges["a"], edges["b"], edges["emails"]):
    U.add_edge(a, b, weight=int(w))
m["constraint"] = pd.Series(nx.constraint(U, weight="weight"))
m["effective_size"] = pd.Series(nx.effective_size(U, weight="weight"))
m["in_test"] = (m["received_usable"] >= MIN_USABLE) & ~people["mixed_identity"]

# ---------------------------------------------------------------------------
title("1. Who is in the test (B2)")
print(f"people: {len(m)}; with >= {MIN_USABLE} usable received emails: {(m['received_usable'] >= MIN_USABLE).sum()}; "
      f"minus the mixed mailbox: {m['in_test'].sum()}")
t = m[m["in_test"]].copy()
print(f"usable received emails per person in the test: median {t['received_usable'].median():.0f}, "
      f"min {t['received_usable'].min()}, max {t['received_usable'].max()}")

title("2. P, the bridge score (B1)")
print(f"P: median {t['P'].median():.2f}, min {t['P'].min():.2f}, max {t['P'].max():.2f} "
      f"(0 = all email from one community; max possible with 9 communities = {1 - 1/9:.2f})")
print(f"how much P changes between the 50 Louvain runs: median SD {t['P_sd'].median():.3f}; "
      f"people with SD > 0.1: {(t['P_sd'] > 0.1).sum()}")
for i in t.sort_values("P_sd", ascending=False).head(5).index:
    print(f"   {t.loc[i, 'name']:16s} P = {t.loc[i, 'P']:.2f} ± {t.loc[i, 'P_sd']:.2f}")

title("3. Checks: does P agree with related measures? (Spearman, people in the test)")
checks = [
    ("P from ALL received emails (B1 check)", "P_all_emails", "should be close to 1"),
    ("outside share (course-level version, B3)", "outside_share", "should be close to 1"),
    ("constraint (Burt, no communities, B4)", "constraint", "should be negative"),
    ("effective size (Burt, B4)", "effective_size", "should be positive"),
    ("usable emails received (volume)", "received_usable", "should be near 0: P is not volume"),
    ("bandwidth: emails per contact (B5)", "bandwidth", "negative = bridges have thinner channels"),
]
for label, col, expect in checks:
    rho = spearmanr(t["P"], t[col]).statistic
    print(f"   {label:44s} rho = {rho:+.2f}   ({expect})")

title("4. The strongest and weakest bridges")
cols = ["name", "community", "senior", "P", "outside_share", "constraint", "received_usable", "bandwidth"]
print("top 12 by P:")
print(t.sort_values("P", ascending=False)[cols].head(12).round(2).to_string())
print("\nbottom 5 by P:")
print(t.sort_values("P")[cols].head(5).round(2).to_string())

title("5. Is P related to seniority and to community? (why the seniority control is needed)")
print(t.groupby("senior")["P"].agg(["count", "median"]).round(2).to_string())
print(f"Spearman P vs senior: {spearmanr(t['P'], t['senior']).statistic:+.2f}")
print("\nmedian P per community (best run):")
print(t.groupby("community")["P"].agg(["count", "median"]).round(2).T.to_string())

m.to_csv(OUT / "bridge_measures.csv")
print(f"\nsaved bridge_measures.csv to {OUT}")
