"""
Step 12b: are the channels BETWEEN groups thinner than the channels WITHIN groups? (H2a, H2c)
Step 12 looked at people; this step looks at links (H2a) and at single emails (H2c).

Input:  pipeline/output/edges_undirected.csv (Step 3), people.csv (Step 5), communities.csv (Step 4),
        emails_clean.csv, recipients_clean.csv (Step 2), text_clean.csv (Step 6)
Output: pipeline/output/h2_boundaries.csv        the main numbers
        pipeline/output/h2c_words.csv            typical words of between vs within emails
        pipeline/figures/fig3a_boundaries.png    draft figure

H2a. Do links between DEPARTMENTS carry fewer emails than links within departments?
     Departments come from outside the email data, so this is not circular (a weighted Louvain
     partition puts heavy links inside communities by construction). Also done with the
     unweighted Louvain partition. Null: email counts shuffled across links (who knows whom fixed).
H2c. Are emails sent BETWEEN communities different from emails the SAME senders send WITHIN?
     Each email is 'within' (all recipients in the sender's community), 'between' (none) or
     'mixed' (left out); best Louvain run.
     (1) Are between-emails more often forwards (someone else's text passed on)?
     (2) Are own-written between-emails shorter (content words)? All own-written emails count,
         also short ones, because short routine emails are exactly the point.
     (3) Which words are typical of between vs within emails? (log-odds as in Step 9; plain and
         with every sender weighted equally)
     For (1) and (2), every sender is compared with themself (senders with 5+ emails of each kind).
     Null: the within/between label is shuffled among each sender's own emails, 1,000 times.
Left out: links and emails that involve the mixed mailbox (Step 5).

Run from the project root:
    uv run python pipeline/step12b_boundaries.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
FIG = ROOT / "pipeline" / "figures"
N_NULL = 1000
MIN_EACH = 5
rng = np.random.default_rng(0)

edges = pd.read_csv(OUT / "edges_undirected.csv")
people = pd.read_csv(OUT / "people.csv", index_col="person_id")
comm = pd.read_csv(OUT / "communities.csv", index_col="person_id")
emails = pd.read_csv(OUT / "emails_clean.csv", usecols=["email_id", "sender_id"])
recipients = pd.read_csv(OUT / "recipients_clean.csv")
text = pd.read_csv(OUT / "text_clean.csv", usecols=["email_id", "text", "n_words", "usable", "had_forward"])
mixed = set(people.index[people["mixed_identity"]])
results = []


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


# ---------------------------------------------------------------------------
title("1. H2a: emails per link, within vs between groups")


def link_test(labels, label_name):
    e = edges[~edges["a"].isin(mixed) & ~edges["b"].isin(mixed)].copy()
    e["la"], e["lb"] = e["a"].map(labels), e["b"].map(labels)
    e = e.dropna(subset=["la", "lb"])
    within = (e["la"] == e["lb"]).to_numpy()
    w = e["emails"].to_numpy()
    ratio = w[within].mean() / w[~within].mean()
    null = []
    for _ in range(N_NULL):
        ws = rng.permutation(w)
        null.append(ws[within].mean() / ws[~within].mean())
    null = np.array(null)
    p = (1 + np.sum(np.abs(np.log(null)) >= abs(np.log(ratio)))) / (1 + N_NULL)
    print(f"{label_name}: {within.sum()} links within, {(~within).sum()} between")
    print(f"   emails per link: within mean {w[within].mean():.1f} (median {np.median(w[within]):.0f}), "
          f"between mean {w[~within].mean():.1f} (median {np.median(w[~within]):.0f})")
    print(f"   within/between ratio of means {ratio:.2f}; shuffled weights: {null.mean():.2f} "
          f"(95% {np.quantile(null, 0.025):.2f}-{np.quantile(null, 0.975):.2f}); p = {p:.3f}")
    print(f"   share of all emails that travel on between-links: {w[~within].sum() / w.sum():.0%}")
    results.append({"test": f"H2a within/between emails per link ({label_name})", "value": ratio, "null_mean": null.mean(), "p": p})
    return w, within, ratio, null


dept_w, dept_within, dept_ratio, dept_null = link_test(people["department"], "departments")
link_test(comm["community_unweighted"], "unweighted Louvain communities")

# ---------------------------------------------------------------------------
title("2. H2c: label every email within / between / mixed (best Louvain run)")
c = comm["community"]
arrows = recipients.merge(emails, on="email_id")
arrows = arrows[~arrows["email_id"].isin(arrows.loc[arrows["sender_id"].isin(mixed) |
                                                    arrows["recipient_id"].isin(mixed), "email_id"])]
arrows["same"] = arrows["recipient_id"].map(c) == arrows["sender_id"].map(c)
kind = arrows.groupby("email_id")["same"].agg(lambda s: "within" if s.all() else "between" if not s.any() else "mixed")
m = emails.merge(kind.rename("kind"), left_on="email_id", right_index=True).merge(text, on="email_id")
print(m["kind"].value_counts().to_dict())
m = m[m["kind"] != "mixed"].copy()
m["between"] = m["kind"] == "between"


def senders_with_both(df):
    counts = df.groupby(["sender_id", "between"]).size().unstack(fill_value=0)
    return counts.index[(counts.get(True, 0) >= MIN_EACH) & (counts.get(False, 0) >= MIN_EACH)]


def sender_test(df, value, agg, label, summary=np.median):
    """Every sender compared with themself: agg(value | between) - agg(value | within), summarised over
    senders with MIN_EACH+ emails of each kind (median, or mean for yes/no values, where most
    differences are exactly 0); null = labels shuffled inside every sender."""
    df = df[df["sender_id"].isin(senders_with_both(df))]
    groups = [g for _, g in df.groupby("sender_id")]

    def statistic(labels_per_sender):
        diffs = [agg(g[value].to_numpy()[lab]) - agg(g[value].to_numpy()[~lab])
                 for g, lab in zip(groups, labels_per_sender)]
        return summary(diffs), np.array(diffs)

    observed, diffs = statistic([g["between"].to_numpy() for g in groups])
    null = np.array([statistic([rng.permutation(g["between"].to_numpy()) for g in groups])[0]
                     for _ in range(N_NULL)])
    p = (1 + np.sum(np.abs(null - null.mean()) >= abs(observed - null.mean()))) / (1 + N_NULL)
    print(f"{label} ({len(groups)} senders with {MIN_EACH}+ emails of each kind):")
    print(f"   {summary.__name__} over senders of (between - within) = {observed:+.3f}; shuffled labels: {null.mean():+.3f} "
          f"(95% {np.quantile(null, 0.025):+.3f} to {np.quantile(null, 0.975):+.3f}); p = {p:.3f}")
    print(f"   senders whose between-emails score lower than their within-emails: {np.mean(diffs < 0):.0%}")
    results.append({"test": f"H2c {label}", "value": observed, "null_mean": null.mean(), "p": p})
    return diffs


title("3. H2c (1): are between-emails more often forwards?")
print(f"share that contains a forwarded part: between {m.loc[m['between'], 'had_forward'].mean():.1%}, "
      f"within {m.loc[~m['between'], 'had_forward'].mean():.1%} (all emails pooled)")
sender_test(m.assign(fw=m["had_forward"].astype(float)), "fw", np.mean, "share of forwards", summary=np.mean)

title("4. H2c (2): are own-written between-emails shorter?")
own = m[~m["had_forward"]]
print(f"content words per own-written email: between median {own.loc[own['between'], 'n_words'].median():.0f}, "
      f"within median {own.loc[~own['between'], 'n_words'].median():.0f} (all emails pooled)")
length_diffs = sender_test(own, "n_words", np.median, "content words of own-written emails")

# ---------------------------------------------------------------------------
title("5. H2c (3): which words are typical of between vs within emails? (usable own-written emails)")
u = own[own["usable"]].reset_index(drop=True)
cv = CountVectorizer(token_pattern=r"[a-z]{3,}", min_df=5, binary=True)
B = cv.fit_transform(u["text"])
vocab = cv.get_feature_names_out()
is_b = u["between"].to_numpy()


def log_odds(weights):
    inside = B[is_b].T @ weights[is_b]
    outside = B[~is_b].T @ weights[~is_b]
    total = inside + outside
    z = np.full(len(total), np.nan)                 # words that only the left-out senders use: no score
    ok = total > 0
    inside, outside, total = inside[ok], outside[ok], total[ok]
    prior = total / total.sum() * 1000
    n_in, n_out, a0 = inside.sum(), outside.sum(), prior.sum()
    delta = (np.log((inside + prior) / (n_in + a0 - inside - prior))
             - np.log((outside + prior) / (n_out + a0 - outside - prior)))
    z[ok] = delta / np.sqrt(1 / (inside + prior) + 1 / (outside + prior))
    return z


plain = log_odds(np.ones(len(u)))
# every sender's between- and within-emails weigh equally; only senders with MIN_EACH+ usable emails of
# each kind, otherwise a sender with 1-2 emails would get as much weight as one with hundreds
group_size = u.groupby(["sender_id", "between"])["email_id"].transform("size").to_numpy()
balanced = log_odds(np.where(u["sender_id"].isin(senders_with_both(u)), 1.0 / group_size, 0.0))
print(f"senders used for the sender-balanced version: {len(senders_with_both(u))}")
words = pd.DataFrame({"word": vocab, "z_plain": plain, "z_sender_balanced": balanced})
print(f"usable own-written emails: {is_b.sum()} between, {(~is_b).sum()} within")
for col in ["z_plain", "z_sender_balanced"]:
    s = words[col].dropna()
    print(f"\n{col}: largest |z| {s.abs().max():.1f}; words with |z| > 3: {(s.abs() > 3).sum()} of {len(s)}")
    print("   typical of BETWEEN: " + ", ".join(words.nlargest(15, col)["word"]))
    print("   typical of WITHIN:  " + ", ".join(words.nsmallest(15, col)["word"]))
print("\n(plain = all emails pooled, so it also reflects WHO sends between vs within; sender-balanced = every\n"
      " sender compared with themself. If only the plain version shows strong words, the difference comes\n"
      " from which people send across boundaries, not from how a person writes across boundaries.)")

# ---------------------------------------------------------------------------
pd.DataFrame(results).to_csv(OUT / "h2_boundaries.csv", index=False)
words.sort_values("z_plain").to_csv(OUT / "h2c_words.csv", index=False)

# draft figure: (a) H2a emails per link, within vs between departments, (b) H2c per-sender length difference
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
BETWEEN, WITHIN = "#e34948", "#2a78d6"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
for mask, colour, label in [(dept_within, WITHIN, "links within a department"),
                            (~dept_within, BETWEEN, "links between departments")]:
    w = np.sort(dept_w[mask])
    ax.step(w, np.arange(1, len(w) + 1) / len(w), where="post", color=colour, lw=2,
            label=f"{label} (n = {mask.sum()}, mean {w.mean():.1f})")
ax.set_xscale("log")
ax.set_xlabel("emails on the link (log scale)")
ax.set_ylabel("share of links with at most this many emails")
ax.grid(color=GRID, lw=0.6)
ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="lower right")
ax.set_title(f"(a) Links between departments carry fewer emails\n     within/between = {dept_ratio:.1f}× "
             f"(shuffled weights: {dept_null.mean():.2f}×, 95% up to {np.quantile(dept_null, 0.975):.2f}×)",
             loc="left", color=INK, fontsize=9.5)
ax2.axvline(0, color="#c3c2b7", lw=1)
ax2.scatter(length_diffs, rng.uniform(-0.3, 0.3, len(length_diffs)), s=18, color=INK2, alpha=0.7)
ax2.axvline(np.median(length_diffs), color=BETWEEN, lw=1.5)
ax2.set_yticks([])
ax2.set_xlabel("between-emails minus within-emails: content words\n(median per sender)")
ax2.set_title(f"(b) ...but a sender's between-emails are not shorter\n     (n = {len(length_diffs)} senders; "
              f"red line = median {np.median(length_diffs):+.0f} words)", loc="left", color=INK, fontsize=9.5)
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
for side in ["top", "right", "left"]:
    ax2.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig3a_boundaries.png", dpi=200)
print(f"\nsaved h2_boundaries.csv, h2c_words.csv to {OUT} and fig3a_boundaries.png to {FIG}")
