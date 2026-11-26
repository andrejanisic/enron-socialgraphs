"""
Step 10: information diversity D of every person: how varied are the topics of the emails they receive?

Input:  pipeline/output/vectors_index.csv, lsa_100.npy, lda_k20_seed0..4.npy (Step 8)
        recipients_clean.csv (Step 2), bridge_measures.csv (Step 7: who is in the test)
Output: pipeline/output/diversity.csv  one row per person in the test

How D is measured:
  The inbox of a person = the usable emails they received (the same emails P was computed from).
  D1/D2. Draw 20 of these emails at random and compute D; repeat 200 times and average.
         Everyone is measured on the same number of emails (rarefaction), so people who simply
         receive more email do not automatically look more varied.
  LSA:   every email is a vector of length 1. Average the 20 vectors:
         D_lsa = 1 - (length of the average vector)
         0 = all 20 emails point the same way (same topic); close to 1 = they point in many directions.
         (This equals the average of 1 - cos(email, centre of the 20 emails).)
  LDA:   every email is a mix of 20 topics. D_lda = [H(average mix) - average H(each email's mix)] / log(20),
         where H is entropy: how much MORE spread the 20 emails are together than each one alone
         (0 = all emails have the same topic mix). Averaged over the 5 LDA seeds (D3), as LDA is unstable.
  D4. Checks: D vs email volume (rarefaction should remove this), the same D without rarefaction
      (to see why rarefaction is needed), D_lsa vs D_lda across people (alternative method),
      LDA seeds against each other, repeat with another random seed, 10 and 40 emails instead of 20.
  D5. The P-D relation is NOT looked at here; it is the main test (Step 11).

Run from the project root:
    uv run python pipeline/step10_diversity.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "output"
N, DRAWS = 20, 200

index = pd.read_csv(OUT / "vectors_index.csv")
row_of = pd.Series(np.arange(len(index)), index=index["email_id"])   # email_id -> row in the vector files
lsa = np.load(OUT / "lsa_100.npy")
ldas = [np.load(OUT / f"lda_k20_seed{s}.npy") for s in range(5)]
recipients = pd.read_csv(OUT / "recipients_clean.csv")
bridge = pd.read_csv(OUT / "bridge_measures.csv", index_col="person_id")

# inbox: for every person, the vector rows of the usable emails they received
arrows = recipients[recipients["email_id"].isin(row_of.index)]
inbox = arrows.groupby("recipient_id")["email_id"].apply(lambda ids: row_of[ids].to_numpy())
people = bridge.index[bridge["in_test"]]


def title(t):
    print("\n" + "=" * 75)
    print(t)
    print("=" * 75)


def d_lsa(rows):
    return 1 - np.linalg.norm(lsa[rows].mean(axis=0))


def entropy(p):
    p = np.clip(p, 1e-12, 1)
    return -(p * np.log(p)).sum(axis=-1)


def d_lda(theta, rows):
    t = theta[rows]
    return (entropy(t.mean(axis=0)) - entropy(t).mean()) / np.log(t.shape[1])


def rarefied(rows, n, rng):
    """Average D over DRAWS random samples of n emails (the same samples for LSA and every LDA seed)."""
    samples = [rng.choice(rows, size=n, replace=False) for _ in range(DRAWS)]
    lsa_value = np.mean([d_lsa(s) for s in samples])
    lda_values = [np.mean([d_lda(theta, s) for s in samples]) for theta in ldas]
    return lsa_value, lda_values


rng = np.random.default_rng(0)
rows = []
for p in people:
    r = inbox[p]
    lsa20, lda20 = rarefied(r, N, rng)
    row = {"person_id": p, "received_usable": len(r), "D_lsa": lsa20, "D_lda": np.mean(lda20),
           "D_lsa_all_emails": d_lsa(r),
           "D_lsa_n10": rarefied(r, 10, rng)[0],
           "D_lsa_n40": rarefied(r, 40, rng)[0] if len(r) >= 40 else np.nan,
           "D_lsa_other_seed": rarefied(r, N, np.random.default_rng(p + 1000))[0]}
    row.update({f"D_lda_seed{s}": v for s, v in enumerate(lda20)})
    rows.append(row)
d = pd.DataFrame(rows).set_index("person_id")
d.insert(0, "name", bridge.loc[d.index, "name"])
d.insert(1, "community", bridge.loc[d.index, "community"])
d.insert(2, "senior", bridge.loc[d.index, "senior"])


def rho(a, b):
    ok = d[a].notna() & d[b].notna()
    return spearmanr(d.loc[ok, a], d.loc[ok, b]).statistic, ok.sum()


# ---------------------------------------------------------------------------
title(f"1. D for {len(d)} people (20 emails, 200 draws)")
for col in ["D_lsa", "D_lda"]:
    print(f"   {col}: median {d[col].median():.3f}, min {d[col].min():.3f}, max {d[col].max():.3f}")

title("2. Is D just email volume? (why we draw 20 emails instead of using all of them)")
r_raw, _ = rho("D_lsa_all_emails", "received_usable")
r_rare, _ = rho("D_lsa", "received_usable")
print(f"   D from ALL received emails vs emails received:  rho = {r_raw:+.2f}")
print(f"   D from 20 emails (rarefied) vs emails received: rho = {r_rare:+.2f}")

title("3. Do LSA and LDA agree on who has a varied inbox? (alternative method)")
r, n = rho("D_lsa", "D_lda")
print(f"   D_lsa vs D_lda (LDA averaged over 5 seeds): rho = {r:+.2f} (n = {n})")
seed_cols = [f"D_lda_seed{s}" for s in range(5)]
pairs = [spearmanr(d[a], d[b]).statistic for i, a in enumerate(seed_cols) for b in seed_cols[i + 1:]]
print(f"   D_lda from different LDA seeds against each other: rho {min(pairs):.2f} to {max(pairs):.2f}")

title("4. Is D stable? (other random draws; 10 or 40 emails instead of 20)")
for col, label in [("D_lsa_other_seed", "another random seed for the 200 draws"),
                   ("D_lsa_n10", "10 emails per draw"), ("D_lsa_n40", "40 emails per draw (people with 40+)")]:
    r, n = rho("D_lsa", col)
    print(f"   D_lsa vs {label:40s} rho = {r:+.3f} (n = {n})")

title("5. Who has the most and the least varied inbox? (D_lsa)")
cols = ["name", "community", "senior", "received_usable", "D_lsa", "D_lda"]
print("most varied:")
print(d.sort_values("D_lsa", ascending=False)[cols].head(8).round(3).to_string())
print("\nleast varied:")
print(d.sort_values("D_lsa")[cols].head(8).round(3).to_string())
print("\nmedian D_lsa per community:")
print(d.groupby("community")["D_lsa"].agg(["count", "median"]).round(3).T.to_string())

d.to_csv(OUT / "diversity.csv")
print(f"\nsaved diversity.csv to {OUT}")
