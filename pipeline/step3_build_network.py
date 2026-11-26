"""
Step 3: build the email network from the cleaned arrows and describe it.

Input:  pipeline/output/emails_clean.csv, recipients_clean.csv (from Step 2)
        data/enron_main_characters.sqlite (only for people's folder names)
Output: pipeline/output/edges_directed.csv    sender, recipient, emails  (A -> B)
        pipeline/output/edges_undirected.csv  a, b, emails  (A->B plus B->A)

Decisions:
  F. two versions of the same network:
     - directed (who sent to whom): used for what a person RECEIVES (Step 6)
     - undirected (emails in both directions added): used for communities (Step 4)
  G. link weight = number of emails; an email to k people counts 1 for each of them
  H. compare with the group's network file (numbers only) as a check

Run from the project root:
    uv run python pipeline/step3_build_network.py
"""
import pickle
import sqlite3
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"

emails = pd.read_csv(OUT / "emails_clean.csv")
recipients = pd.read_csv(OUT / "recipients_clean.csv")
con = sqlite3.connect(ROOT / "data" / "enron_main_characters.sqlite")
name_of = pd.read_sql("SELECT person_id, name FROM people", con).set_index("person_id")["name"]
con.close()

# one row per arrow: sender -> recipient
arrows = recipients.merge(emails[["email_id", "sender_id"]], on="email_id")
arrows = arrows.rename(columns={"sender_id": "sender", "recipient_id": "recipient"})

# ---------------------------------------------------------------------------
# directed network: weight = number of emails from sender to recipient
directed = arrows.groupby(["sender", "recipient"]).size().reset_index(name="emails")
D = nx.DiGraph()
for sender, recipient, n_emails in zip(directed["sender"], directed["recipient"], directed["emails"]):
    D.add_edge(sender, recipient, weight=n_emails)

# undirected network: weight = emails A->B plus emails B->A
U = nx.Graph()
for a, b, d in D.edges(data=True):
    if U.has_edge(a, b):
        U[a][b]["weight"] += d["weight"]
    else:
        U.add_edge(a, b, weight=d["weight"])
undirected = pd.DataFrame([(a, b, d["weight"]) for a, b, d in U.edges(data=True)],
                          columns=["a", "b", "emails"])

directed.to_csv(OUT / "edges_directed.csv", index=False)
undirected.to_csv(OUT / "edges_undirected.csv", index=False)


def title(text):
    print("\n" + "=" * 75)
    print(text)
    print("=" * 75)


# ---------------------------------------------------------------------------
title("1. Size")
n = D.number_of_nodes()
print(f"people (nodes):          {n}")
print(f"directed links (A->B):   {D.number_of_edges()}   density {nx.density(D):.3f}")
print(f"undirected links (A-B):  {U.number_of_edges()}   density {nx.density(U):.3f}")
print(f"emails on links (total weight): {directed['emails'].sum()}  (= recipient rows)")
print(f"reciprocity (share of A->B links where B->A also exists): {nx.reciprocity(D):.2f}")

# ---------------------------------------------------------------------------
title("2. Link weights: how many emails per link?")
w = undirected["emails"]
print(f"emails per undirected link: median {w.median():.0f}, mean {w.mean():.1f}, max {w.max()}")
print(f"links with a single email: {(w == 1).mean():.0%}")
top10 = w.sort_values(ascending=False).head(10).sum() / w.sum()
print(f"the 10 heaviest links carry {top10:.0%} of all emails")
heaviest = undirected.sort_values("emails", ascending=False).head(5)
for a, b, n_emails in zip(heaviest["a"], heaviest["b"], heaviest["emails"]):
    print(f"   {name_of[a]:14s} - {name_of[b]:14s} {n_emails} emails")

# ---------------------------------------------------------------------------
title("3. People: contacts (degree) and emails (strength)")
degree = pd.Series(dict(U.degree()))
strength = pd.Series(dict(U.degree(weight="weight")))
received = pd.Series(dict(D.in_degree(weight="weight")))
print(f"contacts per person: median {degree.median():.0f}, min {degree.min()}, max {degree.max()}")
print(f"emails received per person: median {received.median():.0f}, "
      f"under 20: {(received < 20).sum()} people")
print("most contacts:", ", ".join(f"{name_of[i]} ({d})" for i, d in degree.nlargest(5).items()))
print("most emails:  ", ", ".join(f"{name_of[i]} ({s})" for i, s in strength.nlargest(5).items()))

# ---------------------------------------------------------------------------
title("4. Structure")
print(f"weakly connected parts: {nx.number_weakly_connected_components(D)}, "
      f"largest strongly connected part: {len(max(nx.strongly_connected_components(D), key=len))} people")
print(f"average clustering: {nx.average_clustering(U):.2f}  "
      f"(a random network with the same density would give about {nx.density(U):.2f})")
print(f"average shortest path (hops): {nx.average_shortest_path_length(U):.2f}, diameter {nx.diameter(U)}")
print(f"degree assortativity: {nx.degree_assortativity_coefficient(U):.2f}")

# ---------------------------------------------------------------------------
title("5. Check against the group's network file (data/main_characters_graph.pkl)")
with open(ROOT / "data" / "main_characters_graph.pkl", "rb") as f:
    G_group = pickle.load(f)
group = {(a, b): d["weight"] for a, b, d in G_group.edges(data=True) if a != b}  # no self-loops
ours = {(a, b): d["weight"] for a, b, d in D.edges(data=True)}
print(f"group: {len(group)} directed links, {sum(group.values())} emails (self-emails left out)")
print(f"ours:  {len(ours)} directed links, {sum(ours.values())} emails")
print(f"links in ours but not in the group's (should be 0): {len(set(ours) - set(group))}")
print(f"links that disappeared after cleaning: {len(set(group) - set(ours))}")
print(f"links where we have MORE emails than the group (should be 0): "
      f"{sum(ours[k] > group[k] for k in ours if k in group)}")
print(f"links where we have fewer emails: {sum(ours[k] < group[k] for k in ours if k in group)}")
