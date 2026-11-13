import pickle
import networkx as nx
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = PROJECT_ROOT / "data" / "main_characters_graph.pkl"

with GRAPH_PATH.open("rb") as f:
    G = pickle.load(f)

print("Graph loaded from main_characters_graph.pkl")
print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")
print("Each edge might contain more than one email, if the same sender sent more than one email to this recipient.")

# Inspect all emails from person A to person B
emails = G[68][123]["emails"]

print(f"Example emails from {G.nodes[68]['name']} to {G.nodes[123]['name']}:")
for email in emails:
    print(email["date"])
    print(email["subject"])
    print(email["body_clean"])
    print("-" * 50)

metrics = {}

metrics["in_degree"] = dict(G.in_degree())
metrics["out_degree"] = dict(G.out_degree())
metrics["total_degree"] = dict(G.degree())

metrics["in_strength"] = dict(G.in_degree(weight="weight"))
metrics["out_strength"] = dict(G.out_degree(weight="weight"))
metrics["total_strength"] = dict(G.degree(weight="weight"))

n = G.number_of_nodes()

if n > 1:
    metrics["in_degree_centrality"] = nx.in_degree_centrality(G)
    metrics["out_degree_centrality"] = nx.out_degree_centrality(G)

    # Normalized by the maximum possible total directed degree.
    metrics["total_degree_centrality"] = {
        node: G.degree(node) / (2 * (n - 1))
        for node in G.nodes()
    }


# --------------------------------------------------
# 3. Betweenness centrality
# --------------------------------------------------

metrics["betweenness"] = nx.betweenness_centrality(
    G,
    normalized=True
)

metrics["weighted_betweenness"] = nx.betweenness_centrality(
    G,
    normalized=True,
    weight="distance"
)


# --------------------------------------------------
# 4. Closeness centrality
# --------------------------------------------------

# NetworkX's directed closeness measures how easily
# other nodes can reach a given node.

metrics["in_closeness"] = nx.closeness_centrality(G)

# Reverse the graph to measure how easily a person
# can reach everyone else.
metrics["out_closeness"] = nx.closeness_centrality(G.reverse())

metrics["weighted_in_closeness"] = nx.closeness_centrality(
    G,
    distance="distance"
)

metrics["weighted_out_closeness"] = nx.closeness_centrality(
    G.reverse(),
    distance="distance"
)


# --------------------------------------------------
# 5. Eigenvector centrality
# --------------------------------------------------

# Incoming eigenvector centrality:
# important if you receive communication from important people.

try:
    metrics["eigenvector_in"] = nx.eigenvector_centrality(
        G,
        max_iter=2000,
        weight="weight"
    )
except nx.PowerIterationFailedConvergence:
    print("Warning: incoming eigenvector centrality did not converge.")

# Outgoing version:
# important if you communicate with important people.

try:
    metrics["eigenvector_out"] = nx.eigenvector_centrality(
        G.reverse(),
        max_iter=2000,
        weight="weight"
    )
except nx.PowerIterationFailedConvergence:
    print("Warning: outgoing eigenvector centrality did not converge.")


# --------------------------------------------------
# 6. PageRank
# --------------------------------------------------

metrics["pagerank"] = nx.pagerank(
    G,
    weight="weight"
)


# --------------------------------------------------
# 7. HITS: hubs and authorities
# --------------------------------------------------

try:
    hubs, authorities = nx.hits(
        G,
        max_iter=2000,
        normalized=True
    )

    metrics["hub_score"] = hubs
    metrics["authority_score"] = authorities

except nx.PowerIterationFailedConvergence:
    print("Warning: HITS did not converge.")


# --------------------------------------------------
# 8. Clustering coefficient
# --------------------------------------------------

metrics["clustering"] = nx.clustering(
    G,
    weight="weight"
)


# --------------------------------------------------
# 9. Print top 5 for every metric
# --------------------------------------------------

for metric_name, values in metrics.items():

    print(f"\n{'=' * 60}")
    print(f"TOP 5 — {metric_name.upper()}")
    print(f"{'=' * 60}")

    top5 = sorted(
        values.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    for rank, (node, value) in enumerate(top5, start=1):
        person = G.nodes[node]

        print(
            f"{rank}. {person['name']:<30} "
            f"{value:.6f}"
        )