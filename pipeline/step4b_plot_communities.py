"""
Step 4b: two figures to LOOK at the communities from Step 4 (no new analysis).

Input:  pipeline/output/edges_undirected.csv, communities.csv, partitions_louvain.csv
Output: pipeline/figures/fig_consensus.png  who ends up together across the 50 runs,
                                             and the people who move most
        pipeline/figures/fig_network.png    the email network (backbone), coloured by community

Drawing rules from Week 4:
  1. backbone first, with a stated method and parameter (disparity filter, alpha = 0.05,
     plus each person's strongest link so nobody is cut off); report what was removed
  2. layout computed on the backbone
  3. colour = community found on the FULL network (Step 4), with a label on each group
  4. size = number of emails (strength)
  5. labels: community labels on the plot, members named in the legend

Run from the project root:
    uv run python pipeline/step4b_plot_communities.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
FIG = ROOT / "pipeline" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# colours: categorical slots in fixed order (8 hues); the 9th community gets neutral grey,
# and every community is also labelled on the plot, so identity never relies on colour alone
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948", "#898781"]
INK, INK2, MUTED, EDGE, SURFACE = "#0b0b0b", "#52514e", "#898781", "#c3c2b7", "#fcfcfb"
BLUES = LinearSegmentedColormap.from_list(
    "blues", [SURFACE, "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9, "axes.edgecolor": EDGE,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})

edges = pd.read_csv(OUT / "edges_undirected.csv")
people = pd.read_csv(OUT / "communities.csv", index_col="person_id")
parts = pd.read_csv(OUT / "partitions_louvain.csv", index_col="person_id")
U = nx.Graph()
for a, b, w in zip(edges["a"], edges["b"], edges["emails"]):
    U.add_edge(a, b, weight=int(w))
strength = pd.Series(dict(U.degree(weight="weight")))
k = people["community"].max()

# short description of each community: its main department and its two biggest emailers
describe = {}
for c in range(1, k + 1):
    members = people[people["community"] == c]
    dept = members["department"].value_counts()
    top = strength[members.index].sort_values(ascending=False).head(2).index
    who = ", ".join(people.loc[top, "name"].str.split("-").str[0].str.capitalize())
    describe[c] = f"C{c} ({len(members)}): {dept.index[0]} {dept.iloc[0]}/{len(members)}; {who}"

# ---------------------------------------------------------------------------
# Figure A: consensus matrix + the people who move most
order = people.sort_values(["community", "stability"], ascending=[True, False]).index
L = parts.loc[order].to_numpy()
together = (L[:, None, :] == L[None, :, :]).mean(axis=2)  # share of runs in which i and j are together

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 5.2), gridspec_kw={"width_ratios": [1.25, 1]})
im = ax.imshow(together, cmap=BLUES, vmin=0, vmax=1, interpolation="nearest")
sizes = people.loc[order, "community"].value_counts().sort_index()
edges_pos = np.cumsum(sizes.to_numpy())
for pos in edges_pos[:-1]:
    ax.axhline(pos - 0.5, color=MUTED, lw=0.6)
    ax.axvline(pos - 0.5, color=MUTED, lw=0.6)
centres = edges_pos - sizes.to_numpy() / 2 - 0.5
ax.set_xticks(centres, [f"C{c}" for c in sizes.index], fontsize=8)
ax.set_yticks(centres, [f"C{c}" for c in sizes.index], fontsize=8)
ax.tick_params(length=0)
for side in ax.spines.values():
    side.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
cb.set_label("share of the 50 runs in which two people\nare in the same community", color=INK2)
cb.outline.set_visible(False)
ax.set_title("Who ends up together across 50 Louvain runs", loc="left", color=INK, fontsize=10)

movers = people.sort_values("stability").head(12)
y = np.arange(len(movers))[::-1]
ax2.hlines(y, 0, movers["stability"], color=EDGE, lw=2)
ax2.scatter(movers["stability"], y, s=40, color=[SLOTS[c - 1] for c in movers["community"]],
            edgecolor=SURFACE, linewidth=1.5, zorder=3)
ax2.set_yticks(y, [f"{n}  (C{c})" for n, c in zip(movers["name"], movers["community"])])
ax2.set_xlim(0, 1)
ax2.set_xlabel("share of runs together with their own (best-run) community")
ax2.tick_params(length=0)
ax2.grid(axis="x", color="#e1e0d9", lw=0.6)
ax2.set_axisbelow(True)
for side in ["top", "right", "left"]:
    ax2.spines[side].set_visible(False)
ax2.set_title("The 12 people whose community changes most", loc="left", color=INK, fontsize=10)
fig.tight_layout()
fig.savefig(FIG / "fig_consensus.png", dpi=200)
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure B: network backbone coloured by community
ALPHA = 0.05
keep = set()
for i in U:
    deg = U.degree(i)
    s_i = strength[i]
    for j, d in U[i].items():
        # disparity filter: is this link stronger than expected if i's emails were spread
        # at random over its deg links? (Serrano, Boguna & Vespignani 2009)
        if deg > 1 and (1 - d["weight"] / s_i) ** (deg - 1) < ALPHA:
            keep.add(frozenset((i, j)))
n_filter = len(keep)
for i in U:  # each person's strongest link, so nobody is cut off
    j = max(U[i], key=lambda x: U[i][x]["weight"])
    keep.add(frozenset((i, j)))
B = nx.Graph()
B.add_nodes_from(U)
for link in keep:
    a, b = tuple(link)
    B.add_edge(a, b, weight=U[a][b]["weight"])
kept_weight = B.size(weight="weight") / U.size(weight="weight")
print(f"backbone: {B.number_of_edges()} of {U.number_of_edges()} links kept "
      f"({n_filter} by the filter, {B.number_of_edges() - n_filter} as someone's strongest link), "
      f"carrying {kept_weight:.0%} of all emails; connected pieces: {nx.number_connected_components(B)}")

pos = nx.forceatlas2_layout(B, max_iter=1000, scaling_ratio=4.0, gravity=1.0, seed=1)
community = people["community"]
fig, ax = plt.subplots(figsize=(10, 7))
nx.draw_networkx_edges(B, pos, ax=ax, edge_color=EDGE, width=0.5, alpha=0.8)
nodes = list(B.nodes())
size = 15 + 400 * np.sqrt(strength[nodes] / strength.max())
moving = people.loc[nodes, "stability"] < 0.5
ax.scatter([pos[p][0] for p in nodes], [pos[p][1] for p in nodes], s=size,
           c=[SLOTS[community[p] - 1] for p in nodes],
           edgecolor=[INK if m else SURFACE for m in moving], linewidth=[1.4 if m else 0.8 for m in moving],
           zorder=3)
for c in range(1, k + 1):
    # put the label at the member closest to all other members (the medoid), not at the
    # average position, which can fall between two parts of a community
    X = np.array([pos[p] for p in nodes if community[p] == c])
    xy = X[np.argmin([np.linalg.norm(X - x, axis=1).sum() for x in X])]
    ax.text(xy[0], xy[1], f"C{c}", fontsize=12, fontweight="bold", color=INK, ha="center", va="center",
            zorder=4, path_effects=[pe.withStroke(linewidth=3, foreground=SURFACE)])
handles = [plt.Line2D([], [], marker="o", ls="", markersize=7, markerfacecolor=SLOTS[c - 1],
                      markeredgecolor=SURFACE, label=describe[c]) for c in range(1, k + 1)]
handles.append(plt.Line2D([], [], marker="o", ls="", markersize=7, markerfacecolor=SURFACE,
                          markeredgecolor=INK, markeredgewidth=1.4,
                          label="black ring: together with own community in < 50% of runs"))
leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=8,
                labelcolor=INK2, title="community (people): main department; biggest emailers",
                title_fontsize=8)
leg.get_title().set_color(INK)
ax.set_title(f"Email network of {B.number_of_nodes()} Enron custodians: backbone of {B.number_of_edges()} links, "
             f"coloured by Louvain community (best of 50 runs)", loc="left", color=INK, fontsize=10)
ax.text(0, -0.02, f"Backbone: disparity filter alpha = {ALPHA} plus each person's strongest link; "
        f"keeps {kept_weight:.0%} of emails. Communities found on the full network. Size = emails.",
        transform=ax.transAxes, fontsize=7.5, color=MUTED, va="top")
ax.axis("off")
fig.tight_layout()
fig.savefig(FIG / "fig_network.png", dpi=200)
plt.close(fig)
print(f"saved fig_consensus.png and fig_network.png to {FIG}")
