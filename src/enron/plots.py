"""Figures for the paper. Each function takes analysis results and writes a PNG."""

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# Categorical colours in a fixed order: community 1 always gets the first colour.
# A 9th community onwards is drawn grey as "other".
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
           "#e87ba4", "#008300", "#6250d6", "#e34948"]
OTHER_GREY = "#b4b2a9"
INK = "#1f1e1c"
INK_SECONDARY = "#5f5e5a"
LINK_GREY = "#c9c7bf"
OWN_GREY = "#5f5e5a"      # aggregate bars: own community
REST_GREY = "#d3d1c7"     # aggregate bars: other communities

# One quiet style for every figure: small type, no top/right frame, left-aligned titles
matplotlib.rcParams.update({
    "font.size": 7, "axes.titlesize": 7.5, "axes.titlelocation": "left",
    "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": INK_SECONDARY, "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY, "axes.labelcolor": INK, "text.color": INK,
})

def save(fig, path_stem: Path) -> None:
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_stem.with_suffix(".png"), bbox_inches="tight", dpi=300)
    plt.close(fig)


def network_layout(H: nx.Graph, strength: dict | None = None, seed: int = 42) -> dict:
    """ForceAtlas2 layout (log weights), the classic layout for social network figures.

    Gravity keeps outlying groups close to the core; passing `strength` makes the
    layout leave room for big nodes so circles do not overlap. Separate parts of
    the graph (if any) are each laid out on their own and placed in a row underneath.
    """
    def fa2(G):
        for _, _, d in G.edges(data=True):
            d["lw"] = np.log1p(d["weight"])
        sizes = None
        if strength:
            smax = max(strength[n] for n in G) or 1
            sizes = {n: 0.5 + 2 * np.sqrt(strength[n] / smax) for n in G}
        if G.number_of_nodes() < 3:
            return nx.spring_layout(G, seed=seed)
        return nx.forceatlas2_layout(G, weight="lw", seed=seed, max_iter=3000,
                                     gravity=8.0, scaling_ratio=5.0, node_size=sizes)

    parts = sorted(nx.connected_components(H), key=lambda p: (-len(p), min(p)))
    pos = {n: np.asarray(p, dtype=float) for n, p in fa2(H.subgraph(parts[0]).copy()).items()}
    if len(parts) > 1:
        xs = np.array([p[0] for p in pos.values()])
        ys = np.array([p[1] for p in pos.values()])
        width, height = xs.max() - xs.min(), ys.max() - ys.min()
        x, y = xs.min(), ys.min() - 0.14 * height
        for part in parts[1:]:
            local = fa2(H.subgraph(part).copy()) if len(part) > 1 else {next(iter(part)): (0, 0)}
            pts = np.array([np.asarray(p, dtype=float) for p in local.values()])
            span = np.ptp(pts, axis=0).max() or 1
            r = 0.03 * width * np.sqrt(len(part))
            for n, p in local.items():
                pos[n] = np.array([x + r + r * (p[0] - pts[:, 0].mean()) / span,
                                   y + r * (p[1] - pts[:, 1].mean()) / span])
            x += 2 * r + 0.11 * width
            if x > xs.max():
                x, y = xs.min(), y - 0.1 * height
    return pos


def community_colours(communities) -> dict:
    return {c: (PALETTE[c - 1] if c <= len(PALETTE) else OTHER_GREY)
            for c in set(communities)}


def place_labels(ax, fig, points: dict, texts: dict, fontsize: float = 7) -> None:
    """Name nodes, trying positions around each so names overlap as little as possible."""
    offsets = [(5, 4), (5, -10), (-5, 4), (-5, -10), (0, 9), (0, -15), (9, -3), (-9, -3),
               (12, 12), (12, -18), (-12, 12), (-12, -18), (0, 18), (0, -24)]
    renderer = fig.canvas.get_renderer()
    placed = []

    def overlap(box):
        return sum(max(0, min(box.x1, o.x1) - max(box.x0, o.x0)) *
                   max(0, min(box.y1, o.y1) - max(box.y0, o.y0)) for o in placed)

    for n, text in texts.items():
        best = None
        for dx, dy in offsets:
            leader = ({"arrowstyle": "-", "lw": 0.4, "color": INK_SECONDARY,
                       "shrinkA": 0, "shrinkB": 2} if abs(dx) + abs(dy) > 14 else None)
            ann = ax.annotate(text, points[n], xytext=(dx, dy), textcoords="offset points",
                              ha="left" if dx >= 0 else "right", va="center", fontsize=fontsize,
                              color=INK, zorder=5, arrowprops=leader,
                              bbox={"boxstyle": "round,pad=0.15", "fc": "white",
                                    "ec": "none", "alpha": 0.85})
            box = ann.get_window_extent(renderer)
            score = overlap(box)
            if best is None or score < best[0]:
                if best is not None:
                    best[1].remove()
                best = (score, ann, box)
            else:
                ann.remove()
            if score == 0:
                break
        placed.append(best[2])


def plot_community_network(H: nx.Graph, backbone: nx.Graph, members: pd.DataFrame,
                           group_names: dict, path_stem: Path, n_labels: int = 10,
                           seed: int = 42) -> None:
    """Network drawn by the course's five rules (week 4).

    1. backbone first (computed by the caller), 2. layout of the backbone (ForceAtlas2),
    3. colour = community found on the full graph, groups named in the legend,
    4. size = strength (emails sent and received), 5. the most important people named.

    members: index = node, columns community, full_name, strength.
    group_names: community number -> short name shown in the legend.
    """
    strength = members["strength"].to_dict()
    pos = network_layout(backbone, strength=strength, seed=seed)
    comm_of = members["community"].to_dict()
    sizes = Counter(members["community"])
    colour = community_colours(sizes)
    smax = max(strength.values()) or 1

    fig, ax = plt.subplots(figsize=(7.2, 7.4))

    widths = np.array([np.log1p(d["weight"]) for _, _, d in backbone.edges(data=True)])
    nx.draw_networkx_edges(backbone, pos, ax=ax, edge_color=LINK_GREY, alpha=0.8,
                           width=0.3 + 1.2 * widths / (widths.max() if len(widths) else 1))

    order = sorted(members.index, key=lambda n: strength[n])  # big nodes drawn on top
    ax.scatter([pos[n][0] for n in order], [pos[n][1] for n in order],
               s=[12 + 260 * np.sqrt(strength[n] / smax) for n in order],
               c=[colour[comm_of[n]] for n in order],
               edgecolors="white", linewidths=0.8, zorder=3)

    top = members["strength"].nlargest(n_labels).index
    place_labels(ax, fig, pos, {n: str(members.at[n, "full_name"]) for n in top})

    handles = [Line2D([], [], marker="o", ls="", markersize=7, markerfacecolor=colour[c],
                      markeredgecolor="white",
                      label=f"C{c} {group_names.get(c, '')} ({sizes[c]})".replace("  ", " "))
               for c in sorted(sizes) if c <= len(PALETTE)]
    n_other = sum(v for c, v in sizes.items() if c > len(PALETTE))
    if n_other:
        handles.append(Line2D([], [], marker="o", ls="", markersize=7,
                              markerfacecolor=OTHER_GREY, markeredgecolor="white",
                              label=f"Other ({n_other})"))
    ax.legend(handles=handles, title="Community (people)", loc="upper center",
              bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=7.5,
              title_fontsize=8, columnspacing=1.5)
    ax.set_axis_off()
    fig.tight_layout()
    save(fig, path_stem)


# ------------------------------------------------- report figure helpers ---
REPORT_FONT = 7


# ------------------------------------------- 2c: emails between communities ---
def community_tint(colour_hex: str, share: float) -> tuple:
    """The community colour, lighter for small shares (0 = almost white, 1 = full)."""
    rgb = np.array(matplotlib.colors.to_rgb(colour_hex))
    return tuple(1 - (1 - rgb) * (0.12 + 0.88 * share))


def _colour_tick_labels(labels, communities, colour) -> None:
    for t, c in zip(labels, communities):
        t.set_color(colour[c])
        t.set_fontweight("bold")


def plot_email_between(M: pd.DataFrame, total: float, path_stem: Path) -> None:
    """Emails between communities as numbers (diagonal = inside a community, bold).

    M: symmetric community x community email counts. Each row is shaded in its
    community's colour; darker = larger share of that community's email.
    """
    comms = list(M.index)
    colour = community_colours(comms)
    row_total = M.sum(axis=1)
    fig, ax = plt.subplots(figsize=(3.6, 3.1))
    for i, a in enumerate(comms):
        for j, b in enumerate(comms):
            v = int(M.loc[a, b])
            share = M.loc[a, b] / row_total[a]
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, lw=0,
                                       color=community_tint(colour[a], share) if v else "white"))
            ax.text(j, i, f"{v:,}" if v else "–", ha="center", va="center",
                    fontsize=REPORT_FONT - 1, color="white" if share > 0.6 else INK,
                    fontweight="bold" if a == b else "normal")
        ax.text(len(comms) - 0.3, i, f"{int(row_total[a]):,}", ha="left", va="center",
                fontsize=REPORT_FONT - 1, color=INK_SECONDARY)
    ax.text(len(comms) - 0.3, -1, "Total", ha="left", va="center", fontsize=REPORT_FONT - 1,
            color=INK_SECONDARY)
    ax.set_xlim(-0.5, len(comms) - 0.5)
    ax.set_ylim(len(comms) - 0.5, -0.5)
    ax.set_xticks(range(len(comms)))
    ax.set_xticklabels([f"C{c}" for c in comms], fontsize=REPORT_FONT)
    ax.set_yticks(range(len(comms)))
    ax.set_yticklabels([f"C{c}" for c in comms], fontsize=REPORT_FONT)
    _colour_tick_labels(ax.get_xticklabels(), comms, colour)
    _colour_tick_labels(ax.get_yticklabels(), comms, colour)
    ax.xaxis.set_ticks_position("top")
    ax.tick_params(length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    inside = np.trace(M.to_numpy()) / total
    ax.text(-0.5, len(comms) + 0.1, f"{inside:.0%} of {int(total):,} emails stay inside a community",
            fontsize=REPORT_FONT - 1, color=INK_SECONDARY, va="top")
    fig.tight_layout(pad=0.3)
    save(fig, path_stem)


# ------------------------------------------------ 2c: community x labels ---
def diagonal_order(table: pd.DataFrame) -> list:
    """Columns ordered so each sits under the row where it is most common."""
    best_row = table.idxmax(axis=0)
    share = table.max(axis=0)
    return sorted(table.columns, key=lambda c: (list(table.index).index(best_row[c]), -share[c]))


def _count_table(ax, counts: pd.DataFrame, title: str) -> None:
    colour = community_colours(counts.index)
    share = counts.div(counts.sum(axis=1), axis=0)
    for i, a in enumerate(counts.index):
        for j in range(counts.shape[1]):
            v = counts.iat[i, j]
            if not v:
                continue
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, lw=0,
                                       color=community_tint(colour[a], share.iat[i, j])))
            ax.text(j, i, str(v), ha="center", va="center", fontsize=REPORT_FONT - 1,
                    color="white" if share.iat[i, j] > 0.6 else INK)
    ax.set_xlim(-0.5, counts.shape[1] - 0.5)
    ax.set_ylim(counts.shape[0] - 0.5, -0.5)
    ax.set_xticks(range(counts.shape[1]))
    ax.set_xticklabels(counts.columns, rotation=45, ha="right", fontsize=REPORT_FONT - 1,
                       rotation_mode="anchor")
    ax.set_yticks(range(counts.shape[0]))
    ax.set_yticklabels([f"C{c}" for c in counts.index], fontsize=REPORT_FONT)
    _colour_tick_labels(ax.get_yticklabels(), counts.index, colour)
    ax.tick_params(length=0, pad=2)
    ax.set_title(title, fontsize=REPORT_FONT, loc="left", pad=4)
    for sp in ax.spines.values():
        sp.set_visible(False)


def plot_community_heatmap(dept_counts: pd.DataFrame, role_counts: pd.DataFrame,
                           dept_title: str, role_title: str, path_stem: Path) -> None:
    """People per community and department (left) and role (right).
    Numbers = people; each row in its community's colour, darker = larger share
    of the community."""
    dept_counts = dept_counts[diagonal_order(dept_counts.div(dept_counts.sum(axis=1), axis=0))]
    role_counts = role_counts[diagonal_order(role_counts.div(role_counts.sum(axis=1), axis=0))]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.0, 2.9),
        gridspec_kw={"width_ratios": [dept_counts.shape[1], role_counts.shape[1]], "wspace": 0.08})
    _count_table(ax1, dept_counts, dept_title)
    _count_table(ax2, role_counts, role_title)
    ax2.set_yticklabels([])
    fig.subplots_adjust(left=0.05, right=0.99, bottom=0.3, top=0.9, wspace=0.08)
    save(fig, path_stem)


# --------------------------------------------------- 2c: mixing (SI) ---
def plot_mixing_matrix(ratio: pd.DataFrame, path_stem: Path) -> None:
    """Observed / expected email between communities, as numbers.
    Above 1 (more than chance) is shaded; the diagonal is within-community email."""
    vals = ratio.to_numpy()
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    shade = np.where(vals > 1, np.log10(np.clip(vals, 1, None)), 0)
    ax.imshow(shade, cmap="Greys", vmin=0, vmax=np.log10(vals.max()) * 1.6)
    for (r, c), v in np.ndenumerate(vals):
        ax.text(c, r, f"{v:.1f}" if v >= 0.95 else f"{v:.2f}".lstrip("0") if v > 0 else "0",
                ha="center", va="center", fontsize=REPORT_FONT - 1,
                color=INK if v > 1 or r == c else INK_SECONDARY,
                fontweight="bold" if r == c else "normal")
    labels = [f"C{c}" for c in ratio.index]
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=REPORT_FONT)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=REPORT_FONT)
    ax.xaxis.set_ticks_position("top")
    ax.tick_params(length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.tight_layout(pad=0.3)
    save(fig, path_stem)


# ------------------------------------------------ 2a: named people's reach ---
def plot_named_reach(shares: pd.DataFrame, own: dict, P: dict, groups: list,
                     reference: dict, path_stem: Path) -> None:
    """Where selected people send their email: one 100% bar per person.

    shares: rows = people (labels), columns = community numbers, values = share
    of the person's email to that community (rows sum to 1).
    own: label -> own community; P: label -> participation coefficient.
    groups: [(group title, number of rows), ...] in the order of `shares`.
    reference: {"label", "own_share", "P"} for a grey reference bar (e.g. the
    median of everyone else), drawn last under the heading "Everyone else".
    Own community first, outlined; segments of 12% or more are labelled.
    """
    from matplotlib.patches import Patch
    comms = list(shares.columns)
    colour = community_colours(comms)
    layout, people = [], iter(shares.index)
    for title, n in groups:
        layout.append(("header", title))
        layout += [("person", next(people)) for _ in range(n)]
    layout += [("header", "Everyone else"), ("reference", reference["label"])]

    fig, ax = plt.subplots(figsize=(3.6, 0.5 + 0.2 * len(layout)))
    height = 0.68
    right = ax.get_yaxis_transform()
    for y, (kind, name) in enumerate(layout):
        if kind == "header":
            ax.text(-0.02, y + 0.15, name, transform=right, ha="right", va="center",
                    fontsize=REPORT_FONT - 0.5, fontweight="bold", color=INK)
            continue
        if kind == "reference":
            v = reference["own_share"]
            ax.barh(y, v, height=height, color="#8a8880", edgecolor="white", lw=0.5)
            ax.barh(y, 1 - v, left=v, height=height, color="#d6d4cd", edgecolor="white", lw=0.5)
            ax.text(v / 2, y, f"{v:.0%}", ha="center", va="center", fontsize=REPORT_FONT - 1.5,
                    color="white")
            ax.text(1.02, y, f"{reference['P']:.2f}", transform=right, va="center",
                    ha="left", fontsize=REPORT_FONT - 1, color=INK)
            continue
        row = shares.loc[name]
        left = 0.0
        for c in [own[name]] + [c for c in comms if c != own[name]]:
            v = row[c]
            if v <= 0:
                continue
            ax.barh(y, v, left=left, height=height, color=colour[c], edgecolor="white", lw=0.5)
            if v >= 0.12:
                ax.text(left + v / 2, y, f"{v:.0%}", ha="center", va="center",
                        fontsize=REPORT_FONT - 1.5, color="white")
            left += v
        ax.barh(y, row[own[name]], height=height, fill=False, edgecolor=INK, lw=0.7)
        ax.text(1.02, y, f"{P[name]:.2f}", transform=right, va="center", ha="left",
                fontsize=REPORT_FONT - 1, color=INK)

    bar_y = [y for y, (k, _) in enumerate(layout) if k != "header"]
    ax.set_yticks(bar_y)
    ax.set_yticklabels([layout[y][1] for y in bar_y], fontsize=REPORT_FONT - 0.5)
    ax.set_ylim(len(layout) - 0.5, -0.9)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["0%", "50%", "100%"], fontsize=REPORT_FONT - 1)
    ax.set_xlabel("Share of the person's email, own community first (outlined)",
                  fontsize=REPORT_FONT - 1)
    ax.text(1.02, -0.6, "P", transform=right, ha="left", va="center",
            fontsize=REPORT_FONT - 1, fontweight="bold", color=INK)
    ax.tick_params(length=0, pad=2)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.4)
    ax.legend(handles=[Patch(color=colour[c], label=f"C{c}") for c in comms], ncol=len(comms),
              loc="lower center", bbox_to_anchor=(0.45, 1.0), frameon=False,
              fontsize=REPORT_FONT - 1, handlelength=0.9, columnspacing=0.7, handletextpad=0.3)
    fig.tight_layout(pad=0.3)
    save(fig, path_stem)


# --------------------------------------------------------- 2a: z-P (SI) ---
def plot_zp_scatter(table: pd.DataFrame, path_stem: Path, n_extra: int = 0) -> None:
    """Participation coefficient P (x) against within-community degree z (y), for
    everyone. Colour = community; ring = named in Congress; lines = SD over runs.
    Names: the people named in Congress (n_extra adds the top unnamed bridges)."""
    colour = community_colours(table["community"])
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    ax.errorbar(table["P"], table["z"], xerr=table["P_sd"], yerr=table["z_sd"], fmt="none",
                ecolor=LINK_GREY, elinewidth=0.4, zorder=1)
    for named, kw in [(False, {"edgecolors": "white", "linewidths": 0.4, "zorder": 2}),
                      (True, {"edgecolors": INK, "linewidths": 0.9, "zorder": 3})]:
        sub = table[table["named"] == named]
        ax.scatter(sub["P"], sub["z"], s=10 if not named else 16,
                   c=[colour[c] for c in sub["community"]], **kw)
    label_ids = list(table.index[table["named"]])
    label_ids += list(table[~table["named"] & (table["degree"] >= 5)]["P"].nlargest(n_extra).index)
    points = {n: (table.at[n, "P"], table.at[n, "z"]) for n in label_ids}
    place_labels(ax, fig, points, {n: str(table.at[n, "full_name"]) for n in label_ids},
                 fontsize=REPORT_FONT - 1.5)
    ax.set_xlabel("Participation coefficient P", fontsize=REPORT_FONT)
    ax.set_ylabel("Within-community degree z", fontsize=REPORT_FONT)
    ax.tick_params(labelsize=REPORT_FONT - 1, length=2)
    ax.spines[["top", "right"]].set_visible(False)
    for sp in ax.spines.values():
        sp.set_linewidth(0.5)
    fig.tight_layout(pad=0.3)
    save(fig, path_stem)


# ----------------------------------------- Analysis 3: plain-style figures ---
GREY_LIGHT, GREY_MID, GREY_DARK = "0.9", "0.6", "0.35"


def _plain(ax) -> None:
    """Plain axes: left and bottom spines only, thin lines, report font."""
    ax.spines[["top", "right"]].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_linewidth(0.6)
    ax.tick_params(labelsize=REPORT_FONT, width=0.6, length=3)


def plot_visibility(roles: pd.DataFrame, named_pct: pd.Series, others_pct: pd.Series,
                    auc_text: str, path_stem: Path) -> None:
    """a: share of each role named in Congress. b: each named person's centrality
    percentile, against the median and middle 50% of everyone else.

    roles: index = role (in display order), columns people, named.
    named_pct: index = names, values = percentile (100 = most central).
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.3),
                               gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.55})
    y = np.arange(len(roles))
    share = 100 * roles["named"] / roles["people"]
    a.barh(y, share, height=0.6,
           color=["black" if r == "Executive" else GREY_MID for r in roles.index])
    for i, (role, row) in enumerate(roles.iterrows()):
        a.text(share[role] + 1.5, i, f"{int(row['named'])}/{int(row['people'])}", va="center",
               fontsize=REPORT_FONT - 1)
    a.set_yticks(y)
    a.set_yticklabels(roles.index)
    a.invert_yaxis()
    a.set_xlim(0, max(50, share.max() + 10))
    a.set_xlabel("Named in Congress (% of role)", fontsize=REPORT_FONT)
    a.set_title("a", loc="left", fontweight="bold", fontsize=REPORT_FONT + 1)
    _plain(a)

    named_pct = named_pct.sort_values()
    q1, median, q3 = np.percentile(others_pct, [25, 50, 75])
    yb = np.arange(len(named_pct))
    b.axvspan(q1, q3, color=GREY_LIGHT, lw=0)
    b.axvline(median, color=GREY_MID, lw=0.8)
    b.hlines(yb, 0, named_pct, color="0.8", lw=0.6)
    b.scatter(named_pct, yb, s=16, color="black", zorder=3)
    b.set_yticks(yb)
    b.set_yticklabels(named_pct.index)
    b.set_xlim(0, 100)
    b.set_ylim(-0.7, len(named_pct) - 0.3)
    b.set_xlabel("PageRank percentile in the email network (100 = most central)",
                 fontsize=REPORT_FONT)
    b.text(median, len(named_pct) - 0.15, "Others: median and middle 50%", ha="center",
           va="bottom", fontsize=REPORT_FONT - 1.5, color=GREY_DARK)
    b.text(100, -0.65, auc_text, ha="right", va="bottom", fontsize=REPORT_FONT - 1)
    b.set_title("b", loc="left", fontweight="bold", fontsize=REPORT_FONT + 1)
    _plain(b)
    save(fig, path_stem)


def plot_brokers(brokers: pd.DataFrame, z_min: float, path_stem: Path) -> None:
    """Brokers by betweenness z-score; people named in Congress in black.

    brokers: index = names, columns broker_z, named.
    """
    brokers = brokers.sort_values("broker_z")
    y = np.arange(len(brokers))
    fig, ax = plt.subplots(figsize=(3.4, 0.45 + 0.16 * len(brokers)))
    ax.barh(y, brokers["broker_z"], height=0.6,
            color=["black" if n else GREY_MID for n in brokers["named"]])
    for i, z in enumerate(brokers["broker_z"]):
        ax.text(z + 0.1, i, f"{z:.1f}", va="center", fontsize=REPORT_FONT - 1)
    ax.axvline(z_min, color=GREY_DARK, lw=0.6, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{name} (named)" if named else name
                        for name, named in zip(brokers.index, brokers["named"])])
    ax.set_xlabel("Betweenness z-score against shuffled graphs", fontsize=REPORT_FONT)
    _plain(ax)
    ax.tick_params(axis="y", length=0)
    save(fig, path_stem)


def plot_named_ranks(ranks: pd.DataFrame, tests: pd.DataFrame, n_people: int,
                     path_stem: Path) -> None:
    """Rank (1 = most central) of each named person on each measure, with the AUC
    test underneath. Darker grey = more central.

    ranks: index = names, columns = measures; tests: rows per measure with AUC, p_text.
    """
    measures = list(ranks.columns)
    fig, ax = plt.subplots(figsize=(4.0, 0.6 + 0.22 * (len(ranks) + 2)))
    for i, name in enumerate(ranks.index):
        for j, m in enumerate(measures):
            r = ranks.at[name, m]
            centrality = 1 - (r - 1) / (n_people - 1)
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, lw=0,
                                       color=str(1 - 0.75 * centrality ** 2)))
            ax.text(j, i, str(r), ha="center", va="center", fontsize=REPORT_FONT - 1,
                    color="white" if centrality > 0.8 else INK)
    n = len(ranks)
    ax.axhline(n - 0.5, color=INK, lw=0.5)
    for j, row in enumerate(tests.itertuples()):
        ax.text(j, n + 0.1, f"{row.AUC:.2f}", ha="center", va="center",
                fontsize=REPORT_FONT - 1, fontweight="bold")
        ax.text(j, n + 0.75, f"p {row.p_text}", ha="center", va="center",
                fontsize=REPORT_FONT - 2, color=GREY_DARK)
    ax.set_xlim(-0.5, len(measures) - 0.5)
    ax.set_ylim(n + 1.1, -0.5)
    ax.set_xticks(range(len(measures)))
    ax.set_xticklabels([m.replace(" ", "\n") for m in measures], fontsize=REPORT_FONT - 1)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(list(range(n)) + [n + 0.1])
    ax.set_yticklabels(list(ranks.index) + ["AUC"], fontsize=REPORT_FONT - 0.5)
    ax.tick_params(length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    save(fig, path_stem)


def plot_rank_agreement(ours: pd.Series, theirs: pd.Series, named: pd.Series,
                        names: pd.Series, rho: float, path_stem: Path) -> None:
    """PageRank rank in this graph (x) against the full-corpus network (y); named
    people in black and labelled. 1 = most central, at the top right."""
    both = pd.concat({"ours": ours, "theirs": theirs}, axis=1, join="inner").dropna()
    rx = both["ours"].rank(ascending=False)
    ry = both["theirs"].rank(ascending=False)
    is_named = named.reindex(both.index).fillna(False).astype(bool)
    fig, ax = plt.subplots(figsize=(3.2, 3.0))
    ax.plot([1, len(both)], [1, len(both)], color="0.85", lw=0.6, zorder=0)
    ax.scatter(rx[~is_named], ry[~is_named], s=8, color=GREY_MID, linewidths=0)
    ax.scatter(rx[is_named], ry[is_named], s=14, color="black", linewidths=0)
    place_labels(ax, fig, {i: (rx[i], ry[i]) for i in both.index[is_named]},
                 {i: str(names[i]) for i in both.index[is_named]}, fontsize=REPORT_FONT - 1.5)
    ax.invert_xaxis()
    ax.invert_yaxis()
    ax.set_xlabel("PageRank rank, 148-person graph", fontsize=REPORT_FONT)
    ax.set_ylabel("PageRank rank, full-corpus network", fontsize=REPORT_FONT)
    ax.set_title(f"{len(both)} people in both; Spearman ρ = {rho:.2f}", fontsize=REPORT_FONT - 1,
                 loc="left", color=GREY_DARK)
    _plain(ax)
    save(fig, path_stem)


# ------------------------------------------- Analysis 1: network basics ---
def plot_role_mixing(ratio: pd.DataFrame, path_stem: Path) -> None:
    """Emails from each role (rows) to each role (columns), as observed over
    expected from the row and column totals. Every cell shows its ratio; cells
    above 1 (more email than chance) are shaded, darker = more."""
    k = len(ratio)
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    top = max(4.0, float(np.nanmax(ratio.to_numpy())))
    for i in range(k):
        for j in range(k):
            r = ratio.iat[i, j]
            shade = 0.0 if r <= 1 else min(1.0, np.log(r) / np.log(top))
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, lw=0.4, ec="white",
                                       color=str(1 - 0.8 * shade)))
            ax.text(j, i, f"{r:.1f}", ha="center", va="center", fontsize=REPORT_FONT - 1,
                    color="white" if shade > 0.6 else (INK if r > 1 else GREY_MID),
                    fontweight="bold" if i == j else "normal")
    ax.set_xlim(-0.5, k - 0.5)
    ax.set_ylim(k - 0.5, -0.5)
    ax.set_xticks(range(k))
    ax.set_xticklabels(ratio.columns, rotation=40, ha="left", fontsize=REPORT_FONT - 1)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(k))
    ax.set_yticklabels(ratio.index, fontsize=REPORT_FONT - 1)
    ax.set_ylabel("Sender's role", fontsize=REPORT_FONT)
    ax.set_xlabel("Recipient's role  (1.0 = as much email as chance)", fontsize=REPORT_FONT)
    ax.tick_params(length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    save(fig, path_stem)


def plot_null_models(table: pd.DataFrame, nulls: dict, path_stem: Path) -> None:
    """One panel per statistic: values in shuffled graphs (dark grey), in random
    graphs with the same size (light grey), and the email network (black line)."""
    stats = list(table["statistic"])
    fig, axes = plt.subplots(1, len(stats), figsize=(7.0, 1.45),
                             gridspec_kw={"wspace": 0.35})
    for ax, row in zip(axes, table.itertuples()):
        sh, rnd = nulls["shuffled"][row.statistic], nulls["random"][row.statistic]
        lo = min(sh.min(), rnd.min(), row.observed)
        hi = max(sh.max(), rnd.max(), row.observed)
        bins = np.linspace(lo - 0.05 * (hi - lo), hi + 0.05 * (hi - lo), 50)
        ax.hist(rnd, bins=bins, color=GREY_LIGHT, lw=0)
        ax.hist(sh, bins=bins, color=GREY_MID, lw=0)
        ax.axvline(row.observed, color="black", lw=1)
        z = f"{row.z:.0f}" if abs(row.z) >= 10 else f"{row.z:.1f}"
        ax.set_title(row.statistic, fontsize=REPORT_FONT, loc="left", pad=9)
        ax.text(0, 1.02, f"z = {z}", transform=ax.transAxes, ha="left", va="bottom",
                fontsize=REPORT_FONT - 1, color=GREY_DARK)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        _plain(ax)
        ax.tick_params(axis="x", labelsize=REPORT_FONT - 1.5)
    axes[0].text(0, -0.42, "Black line: email network.  Dark grey: shuffled graphs, same "
                 "degrees.  Light grey: random graphs, same size.", transform=axes[0].transAxes,
                 fontsize=REPORT_FONT - 1, color=GREY_DARK)
    save(fig, path_stem)


def plot_rich_club(rich: pd.DataFrame, path_stem: Path) -> None:
    """Rich-club ratio rho(k): link density among people with more than k contacts,
    over the same in shuffled graphs; grey band = 95% of shuffled graphs."""
    k = rich.index.to_numpy()
    fig, ax = plt.subplots(figsize=(3.2, 2.1))
    ax.fill_between(k, rich.null_lo / rich.null_mean, rich.null_hi / rich.null_mean,
                    color=GREY_LIGHT, lw=0, step="mid")
    ax.axhline(1, color=GREY_MID, lw=0.6)
    ax.plot(k, rich.rho, color="black", lw=1, drawstyle="steps-mid")
    ax.set_xlabel("Contacts k (people with more than k contacts)", fontsize=REPORT_FONT)
    ax.set_ylabel("Rich-club ratio ρ(k)", fontsize=REPORT_FONT)
    top = ax.secondary_xaxis("top", functions=(lambda x: x, lambda x: x))
    ticks = [t for t in ax.get_xticks() if k.min() <= t <= k.max()]
    top.set_xticks(ticks)
    top.set_xticklabels([str(int(rich.people_above_k.reindex([int(t)], method="nearest").iloc[0]))
                         for t in ticks], fontsize=REPORT_FONT - 1.5)
    top.set_xlabel("people above k", fontsize=REPORT_FONT - 1, color=GREY_DARK)
    top.tick_params(length=2, width=0.6)
    top.spines["top"].set_linewidth(0.6)
    _plain(ax)
    save(fig, path_stem)


def plot_send_receive(table: pd.DataFrame, path_stem: Path, n_labels: int = 8) -> None:
    """Emails sent against received per person (log scales); the people furthest
    from the diagonal on each side are labelled."""
    t = table[(table.sent > 0) & (table.received > 0)].copy()
    t["imbalance"] = np.log10(t.sent / t.received)
    fig, ax = plt.subplots(figsize=(3.2, 3.0))
    lim = [1, 10 ** np.ceil(np.log10(max(t.sent.max(), t.received.max())))]
    ax.plot(lim, lim, color="0.85", lw=0.6, zorder=0)
    ax.scatter(t.received, t.sent, s=8, color=GREY_MID, linewidths=0)
    big = t[t.sent + t.received >= t.sent.add(t.received).quantile(0.5)]
    picks = pd.concat([big.nlargest(n_labels // 2, "imbalance"),
                       big.nsmallest(n_labels // 2, "imbalance")])
    ax.scatter(picks.received, picks.sent, s=12, color="black", linewidths=0)
    place_labels(ax, fig, {i: (picks.received[i], picks.sent[i]) for i in picks.index},
                 {i: picks.full_name[i] for i in picks.index}, fontsize=REPORT_FONT - 1.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("Emails received", fontsize=REPORT_FONT)
    ax.set_ylabel("Emails sent", fontsize=REPORT_FONT)
    ax.text(1.4, lim[1] / 1.4, "sends more\nthan receives", ha="left", va="top",
            fontsize=REPORT_FONT - 1, color=GREY_DARK)
    ax.text(lim[1] / 1.4, 1.4, "receives more\nthan sends", ha="right", va="bottom",
            fontsize=REPORT_FONT - 1, color=GREY_DARK)
    _plain(ax)
    save(fig, path_stem)
