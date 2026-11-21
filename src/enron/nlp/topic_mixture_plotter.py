
import re
import csv
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# --------------------------------------------------
# Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MIX_PATH = PROJECT_ROOT / "reports" / "nmf" / "community_topic_mix.csv"
LABELS_PATH = PROJECT_ROOT / "reports" / "nmf" / "topic_labels.csv"
OUTPUT_DIR = PROJECT_ROOT / "figures"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Load data
# --------------------------------------------------

df = pd.read_csv(MIX_PATH)

topics = {}

with open(LABELS_PATH, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        topic_id = int(row["topic_number"])

        topics[topic_id] = {
            "long": row["long_title"].strip(),
            "short": row["short_title"].strip(),
        }

topic_cols = [f"topic_{i}" for i in range(15)]

# Convert proportions to percentages
matrix = df.set_index("community_id")[topic_cols] * 100

# Short labels
labels = [topics[i]["short"] for i in range(15)]

community_labels = [
    f"Community {int(cid)} ({count:,} emails)"
    for cid, count in zip(df["community_id"], df["email_count"])
]

matrix.index = community_labels
matrix.columns = labels

# --------------------------------------------------
# 1. Heatmap
# --------------------------------------------------

fig, ax = plt.subplots(figsize=(20, 8))

im = ax.imshow(
    matrix.values,
    aspect="auto",
    cmap="YlOrRd",
    vmin=0,
    vmax=matrix.values.max(),
)

ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

ax.set_yticks(range(len(community_labels)))
ax.set_yticklabels(community_labels, fontsize=9)

# Annotate every cell
for i in range(matrix.shape[0]):
    for j in range(matrix.shape[1]):
        value = matrix.iloc[i, j]

        ax.text(
            j, i, f"{value:.1f}",
            ha="center",
            va="center",
            fontsize=7,
            color="black",
        )

ax.set_title("Topic Distribution Across Enron Communities", pad=18)
ax.set_xlabel("Topics")
ax.set_ylabel("Communities")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Topic weight (%)")

ax.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(community_labels), 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1)
ax.tick_params(which="minor", bottom=False, left=False)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "community_topic_heatmap.png", dpi=250)
plt.show()


# --------------------------------------------------
# 2. 100% Stacked horizontal bar chart
# --------------------------------------------------

fig, ax = plt.subplots(figsize=(16, 7))

left = np.zeros(len(matrix))

for topic_id, label in enumerate(labels):
    values = matrix.iloc[:, topic_id].values

    ax.barh(
        community_labels,
        values,
        left=left,
        label=label,
    )

    left += values

ax.set_xlim(0, 100)
ax.set_xlabel("Share of topic weight (%)")
ax.set_title("Topic Composition of Each Community")
ax.legend(
    title="Topics",
    bbox_to_anchor=(1.02, 1),
    loc="upper left",
    fontsize=8,
)

ax.invert_yaxis()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "community_topic_stacked.png", dpi=250)
plt.show()
