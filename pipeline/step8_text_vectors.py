"""
Step 8: turn every usable email into a vector of numbers that describes its topic.

Input:  pipeline/output/text_clean.csv (Step 6: content words per email, usable yes/no)
Output: pipeline/output/vectors_index.csv  the email_id of each row of the vector files
        pipeline/output/lsa_100.npy        LSA vector per email (100 numbers, length 1)
        pipeline/output/lda_k20.npy        LDA topic mix per email (20 numbers that sum to 1), seed 0
        pipeline/output/lda_k20_seed0..4.npy the same for all 5 seeds (LDA is unstable, so we average)
        pipeline/output/lda_k20_topics.csv the 12 top words of each LDA topic

Decisions:
  V1. TF-IDF (Week 6): a word gets a high weight in an email if it is frequent there but rare in
      other emails. Words in fewer than 5 emails or in more than half of all emails are dropped;
      counts are dampened (1 + log count) so one word repeated 10 times does not dominate.
  V2. LSA (main): TF-IDF -> 100 dimensions with TruncatedSVD (words that appear together are merged
      into shared dimensions), then every vector is scaled to length 1, so cosine = dot product.
  V3. LDA (second method, Week 6): 20 topics; an email is a MIX of topics. Checked for stability
      across 5 seeds and against 10 and 30 topics. LDA is known to struggle with short texts.
  V4. Checks: how much information 50/100/200 LSA dimensions keep; nearest words in LSA space;
      top words of every LDA topic; do LSA and LDA agree on which emails are similar?

Run from the project root (takes a few minutes because of LDA):
    uv run python pipeline/step8_text_vectors.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.decomposition import LatentDirichletAllocation, TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import normalized_mutual_info_score as nmi
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"

text = pd.read_csv(OUT / "text_clean.csv")
docs = text[text["usable"]].reset_index(drop=True)


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


# ---------------------------------------------------------------------------
title("1. TF-IDF (V1)")
tfidf = TfidfVectorizer(token_pattern=r"[a-z]{3,}", min_df=5, max_df=0.5, sublinear_tf=True)
X = tfidf.fit_transform(docs["text"])
words = tfidf.get_feature_names_out()
empty = np.asarray(X.sum(axis=1)).ravel() == 0
print(f"emails: {X.shape[0]}, vocabulary: {X.shape[1]} words, "
      f"words per email in the vocabulary: median {np.median(np.diff(X.indptr)):.0f}")
print(f"emails left with no vocabulary word at all (dropped): {empty.sum()}")
X, docs = X[~empty], docs[~empty].reset_index(drop=True)

# ---------------------------------------------------------------------------
title("2. LSA: how many dimensions? (V2)")
svd = TruncatedSVD(n_components=200, random_state=0)
Z200 = svd.fit_transform(X)
kept = np.cumsum(svd.explained_variance_ratio_)
for k in (50, 100, 200):
    print(f"   {k:3d} dimensions keep {kept[k - 1]:.0%} of the TF-IDF variance")
lsa = normalize(Z200[:, :100])          # main: 100 dimensions, length 1

print("\nnearest words in LSA space (do related words end up close?):")
# a word's LSA vector = its loadings on the dimensions, each weighted by how important the
# dimension is (its singular value); without the weights, weak noisy dimensions count as much as strong ones
word_vecs = normalize(svd.components_[:100].T * svd.singular_values_[:100])
for q in ["isda", "california", "capacity", "ercot", "curve", "interview"]:
    if q in tfidf.vocabulary_:
        sims = word_vecs @ word_vecs[tfidf.vocabulary_[q]]
        print(f"   {q:11s} -> " + ", ".join(words[i] for i in np.argsort(-sims)[1:8]))

# ---------------------------------------------------------------------------
title("3. LDA: 20 topics, 5 seeds (V3)")
counts = CountVectorizer(vocabulary=tfidf.vocabulary_, token_pattern=r"[a-z]{3,}").fit_transform(docs["text"])


def fit_lda(k, seed):
    lda = LatentDirichletAllocation(n_components=k, random_state=seed, max_iter=25, learning_method="batch")
    theta = lda.fit_transform(counts)
    topics = lda.components_ / lda.components_.sum(axis=1, keepdims=True)
    return theta, topics


def matched_similarity(t1, t2):
    """Pair the topics of two runs one-to-one so that they are as similar as possible
    (Hungarian matching on cosine similarity) and return the mean similarity of the pairs."""
    sim = normalize(t1) @ normalize(t2).T
    rows, cols = linear_sum_assignment(-sim)
    return sim[rows, cols].mean()


runs = {seed: fit_lda(20, seed) for seed in range(5)}
theta, topics = runs[0]
for s in range(1, 5):
    same_dominant = nmi(theta.argmax(axis=1), runs[s][0].argmax(axis=1))
    print(f"   seed 0 vs seed {s}: matched topic similarity {matched_similarity(topics, runs[s][1]):.2f}, "
          f"NMI of each email's main topic {same_dominant:.2f}")

print("\ntop words of each topic (seed 0) and share of emails whose main topic it is:")
main = pd.Series(theta.argmax(axis=1)).value_counts(normalize=True)
top_words = []
for t in range(20):
    tw = ", ".join(words[i] for i in np.argsort(-topics[t])[:12])
    top_words.append(tw)
    print(f"   T{t:02d} ({main.get(t, 0):4.0%}): {tw}")

print("\nother numbers of topics (2 seeds each): matched topic similarity between the seeds")
for k in (10, 30):
    a, b = fit_lda(k, 0), fit_lda(k, 1)
    print(f"   {k} topics: {matched_similarity(a[1], b[1]):.2f}")

# ---------------------------------------------------------------------------
title("4. Do LSA and LDA agree on which emails are similar? (V4)")
rng = np.random.default_rng(0)
i, j = rng.integers(0, len(docs), 20000), rng.integers(0, len(docs), 20000)
pairs = i != j
lsa_sim = np.einsum("ij,ij->i", lsa[i[pairs]], lsa[j[pairs]])
th = normalize(theta)
lda_sim = np.einsum("ij,ij->i", th[i[pairs]], th[j[pairs]])
print(f"Spearman between LSA cosine and LDA cosine over {pairs.sum()} random pairs of emails: "
      f"{spearmanr(lsa_sim, lda_sim).statistic:.2f}")
print(f"LSA cosine of random pairs: median {np.median(lsa_sim):.2f}  "
      f"(near 0 = unrelated emails look unrelated)")

# example: the 3 most similar emails to one email, to read by hand
example = int(rng.integers(0, len(docs)))
nearest = np.argsort(-(lsa @ lsa[example]))[1:4]
print(f"\nexample email {docs.loc[example, 'email_id']}: {docs.loc[example, 'text'][:110]}")
for n in nearest:
    print(f"   cos {lsa[n] @ lsa[example]:.2f}  email {docs.loc[n, 'email_id']}: {docs.loc[n, 'text'][:95]}")

# ---------------------------------------------------------------------------
docs[["email_id"]].to_csv(OUT / "vectors_index.csv", index=False)
np.save(OUT / "lsa_100.npy", lsa.astype(np.float32))
np.save(OUT / "lda_k20.npy", theta.astype(np.float32))
for s, (th_s, _) in runs.items():      # all 5 seeds, so the LDA diversity can be averaged over seeds
    np.save(OUT / f"lda_k20_seed{s}.npy", th_s.astype(np.float32))
pd.DataFrame({"topic": [f"T{t:02d}" for t in range(20)], "top_words": top_words}).to_csv(
    OUT / "lda_k20_topics.csv", index=False)
print(f"\nsaved vectors_index.csv, lsa_100.npy, lda_k20.npy, lda_k20_topics.csv to {OUT}")
