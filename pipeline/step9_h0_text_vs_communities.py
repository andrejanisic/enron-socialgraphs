"""
Step 9: H0, the precondition. Do different communities write about different things?
If they do not, being a bridge between communities cannot bring more varied information,
and the research question stops here.

Input:  pipeline/output/text_clean.csv, emails_clean.csv (sender), communities.csv (community of the
        best Louvain run), people.csv (mixed mailbox), vectors_index.csv + lsa_100.npy (Step 8)
Output: pipeline/output/h0_summary.csv           the main numbers
        pipeline/output/h0_null_classifier.csv   the shuffled-label results (for Figure 1c)
        pipeline/output/h0_cluster_table.csv     text clusters x communities
        pipeline/output/h0_distinctive_words.csv top words per community (for Figure 1b)

Tests (one unit = one usable email, labelled with its SENDER's community):
  H0a. Can a text classifier (TF-IDF + logistic regression, Week 7) predict the sender's community?
       Trained and tested on DIFFERENT senders (5 folds split by sender), so it cannot just learn
       one person's writing style. Main number: balanced accuracy (each community counts equally).
  H0b. Do text clusters follow communities? KMeans with 9 clusters on the LSA vectors, NMI with
       the sender's community, and the cluster x community table (Week 7).
  H0c. Which words are typical for each community? Log-odds with an informative prior
       (Monroe et al. 2008, the method behind Scattertext, Week 6).
  Null model for H0a and H0b: the community labels are shuffled BETWEEN SENDERS. Every sender keeps
       all of their emails together but gets a random community. This keeps the fact that one
       person's emails resemble each other, which a shuffle of single emails would destroy.
  Left out: the sent emails of the mixed mailbox (Step 5), whose community label is unreliable.

Run from the project root (a few minutes: the classifier is trained 5 x 101 times):
    uv run python pipeline/step9_h0_text_vs_communities.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.metrics import normalized_mutual_info_score as nmi
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
N_NULL_CLASSIFIER = 100
N_NULL_CLUSTERS = 1000
rng = np.random.default_rng(0)

text = pd.read_csv(OUT / "text_clean.csv")
community = pd.read_csv(OUT / "communities.csv", index_col="person_id")["community"]
people = pd.read_csv(OUT / "people.csv", index_col="person_id")
index = pd.read_csv(OUT / "vectors_index.csv")
lsa = np.load(OUT / "lsa_100.npy")

# usable emails in the same row order as the LSA vectors, without the mixed mailbox
docs = index.merge(text[["email_id", "sender_id", "text"]], on="email_id", how="left")
keep = ~docs["sender_id"].map(people["mixed_identity"]).to_numpy()
docs, lsa = docs[keep].reset_index(drop=True), lsa[keep]
senders = docs["sender_id"].to_numpy()
y = docs["sender_id"].map(community).to_numpy()


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


def shuffled_labels():
    """Give every sender a random community (sender-level shuffle); returns one label per email."""
    unique = np.unique(senders)
    new = dict(zip(unique, rng.permutation(community[unique].to_numpy())))
    return np.array([new[s] for s in senders])


def p_value(null, observed):
    return (1 + np.sum(np.array(null) >= observed)) / (1 + len(null))


title("0. Data")
print(f"usable emails: {len(docs)} from {len(np.unique(senders))} senders")
counts = pd.Series(y).value_counts().sort_index()
print("emails per sender community:", counts.to_dict())
top_share = docs.groupby(y)["sender_id"].agg(lambda s: s.value_counts(normalize=True).iloc[0])
print("share of each community's emails written by its single most active sender:",
      top_share.round(2).to_dict())

# ---------------------------------------------------------------------------
title("1. H0a: can text predict the sender's community, for senders never seen in training?")
model = make_pipeline(
    TfidfVectorizer(token_pattern=r"[a-z]{3,}", min_df=5, max_df=0.5, sublinear_tf=True),
    LogisticRegression(max_iter=2000))
folds = GroupKFold(n_splits=5)


def classify(labels):
    pred = cross_val_predict(model, docs["text"], labels, groups=senders, cv=folds, n_jobs=-1)
    return accuracy_score(labels, pred), balanced_accuracy_score(labels, pred), pred


acc, bal, pred = classify(y)
print(f"accuracy {acc:.3f} (always guessing the largest community: {counts.max() / counts.sum():.3f})")
print(f"balanced accuracy {bal:.3f} (each community counts equally; pure guessing: {1 / len(counts):.3f})")
recall = pd.Series(pred == y).groupby(y).mean()
print("share of each community's emails classified correctly:", recall.round(2).to_dict())

null_bal = []
for k in range(N_NULL_CLASSIFIER):
    null_bal.append(classify(shuffled_labels())[1])
null_bal = np.array(null_bal)
print(f"\nsender-level shuffles ({N_NULL_CLASSIFIER}): balanced accuracy {null_bal.mean():.3f} ± {null_bal.std():.3f}, "
      f"95% below {np.quantile(null_bal, 0.95):.3f}")
print(f"observed {bal:.3f}: {np.sum(null_bal >= bal)} of {N_NULL_CLASSIFIER} shuffles reach it, "
      f"p = {p_value(null_bal, bal):.3f}")

# ---------------------------------------------------------------------------
title("2. H0b: do text clusters (KMeans on LSA) follow the sender's community?")
clusters = KMeans(n_clusters=len(counts), n_init=10, random_state=0).fit_predict(lsa)
observed_nmi = nmi(y, clusters)
null_nmi = np.array([nmi(shuffled_labels(), clusters) for _ in range(N_NULL_CLUSTERS)])
print(f"NMI(text clusters, sender community) = {observed_nmi:.3f}")
print(f"sender-level shuffles ({N_NULL_CLUSTERS}): {null_nmi.mean():.3f} ± {null_nmi.std():.3f}, "
      f"95% below {np.quantile(null_nmi, 0.95):.3f}; p = {p_value(null_nmi, observed_nmi):.3f}")
table = pd.crosstab(pd.Series(y, name="community"), pd.Series(clusters, name="cluster"))
print("\nshare of each community's emails in each text cluster (rows sum to 1):")
print(table.div(table.sum(axis=1), axis=0).round(2).to_string())

# ---------------------------------------------------------------------------
title("3. H0c: the most typical words of each community (log-odds with informative prior)")
# counts = number of emails that contain the word (so one long email cannot dominate)
cv = CountVectorizer(token_pattern=r"[a-z]{3,}", min_df=5, binary=True)
B = cv.fit_transform(docs["text"])
vocab = cv.get_feature_names_out()
total = np.asarray(B.sum(axis=0)).ravel()
prior = total / total.sum() * 1000          # prior: overall word frequencies, worth 1000 'pseudo-emails'
rows = []
for c in counts.index:
    inside = np.asarray(B[y == c].sum(axis=0)).ravel()
    outside = total - inside
    n_in, n_out, a0 = inside.sum(), outside.sum(), prior.sum()
    delta = (np.log((inside + prior) / (n_in + a0 - inside - prior))
             - np.log((outside + prior) / (n_out + a0 - outside - prior)))
    z = delta / np.sqrt(1 / (inside + prior) + 1 / (outside + prior))
    top = np.argsort(-z)[:15]
    rows += [{"community": c, "rank": r + 1, "word": vocab[i], "z": round(z[i], 1)} for r, i in enumerate(top)]
    print(f"   C{c}: " + ", ".join(vocab[i] for i in top[:12]))
words = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
pd.DataFrame([
    {"test": "H0a balanced accuracy", "observed": bal, "null_mean": null_bal.mean(),
     "null_95": np.quantile(null_bal, 0.95), "p": p_value(null_bal, bal)},
    {"test": "H0a accuracy", "observed": acc, "null_mean": np.nan, "null_95": np.nan, "p": np.nan},
    {"test": "H0b NMI clusters vs community", "observed": observed_nmi, "null_mean": null_nmi.mean(),
     "null_95": np.quantile(null_nmi, 0.95), "p": p_value(null_nmi, observed_nmi)},
]).to_csv(OUT / "h0_summary.csv", index=False)
pd.DataFrame({"balanced_accuracy": null_bal}).to_csv(OUT / "h0_null_classifier.csv", index=False)
table.to_csv(OUT / "h0_cluster_table.csv")
words.to_csv(OUT / "h0_distinctive_words.csv", index=False)
print(f"\nsaved h0_summary.csv, h0_null_classifier.csv, h0_cluster_table.csv, h0_distinctive_words.csv to {OUT}")
