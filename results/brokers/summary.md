# Analysis 2a: who bridges communities?

147 people with links; P and z averaged over the 50 Louvain runs
(`P_w_mean`) and from the main partition (`P_main`). The two can differ for
people in unstable communities (C7, parts of C1), where other runs split the
community differently; report `P_main` in the text. Runs saved by run_communities.
P = 1 - sum over communities of (share of a person's
email to that community)^2; 0 = all email inside one community, at most 0.875
with 8 communities. z = email inside one's own community, in SDs above the
community average. Weighted = email counts; unweighted = links only (Spearman
agreement between weighted and unweighted P: 0.77).
People with fewer than 5 links are flagged (`low_degree`) and left out of
the top list. Betweenness uses distance = 1 / emails.

## Top 10 bridges (highest P, at least 5 links)

| full_name | community | role | department | P_main | P_w_mean | P_w_sd | z_main | betweenness | constraint | mentions |
|---|---|---|---|---|---|---|---|---|---|---|
| Kim Ward | 6 | Trading | ENA Gas West | 0.786 | 0.789 | 0.029 | -0.359 | 0.062 | 0.142 | 0 |
| Mike Swerzbin | 3 | Trading | ENA West Power | 0.749 | 0.752 | 0.007 | -0.604 | 0.000 | 0.172 | 0 |
| Kenneth Lay | 1 | Executive | Enron | 0.730 | 0.754 | 0.014 | 0.031 | 0.000 | 0.066 | 122 |
| Kevin Ruscitti | 6 | Trading | ENA Gas Central | 0.706 | 0.686 | 0.036 | -1.308 | 0.000 | 0.250 | 0 |
| Mark Haedicke | 7 | Legal | ENA Legal | 0.703 | 0.617 | 0.018 | -0.690 | 0.000 | 0.150 | 0 |
| Joe Parks | 8 | Trading | ENA Gas Central | 0.698 | 0.614 | 0.125 | -0.768 | 0.000 | 0.249 | 0 |
| Martin Cuilla | 2 | Trading | ENA Gas Central | 0.696 | 0.672 | 0.052 | -0.627 | 0.000 | 0.175 | 0 |
| Scott Neal | 8 | Trading | ENA Gas East | 0.680 | 0.694 | 0.053 | 0.133 | 0.074 | 0.130 | 0 |
| Chris Stokley | 1 | Manager / staff | ENA West Power | 0.678 | 0.678 | 0.012 | -0.808 | 0.000 | 0.217 | 0 |
| Michelle Cash | 7 | Legal | ENA Legal | 0.672 | 0.520 | 0.031 | -0.754 | 0.000 | 0.197 | 0 |

## How the measures relate (Spearman)

| measure | P_main | z_main | betweenness | constraint | effective_size | strength |
|---|---|---|---|---|---|---|
| P_main | 1.00 | -0.25 | 0.07 | -0.65 | 0.44 | -0.11 |
| z_main | -0.25 | 1.00 | 0.55 | 0.03 | 0.47 | 0.76 |
| betweenness | 0.07 | 0.55 | 1.00 | -0.22 | 0.56 | 0.65 |
| constraint | -0.65 | 0.03 | -0.22 | 1.00 | -0.62 | 0.03 |
| effective_size | 0.44 | 0.47 | 0.56 | -0.62 | 1.00 | 0.61 |
| strength | -0.11 | 0.76 | 0.65 | 0.03 | 0.61 | 1.00 |

## Are the people named in Congress the bridges?

People named in Congress (mentions hand-checked as wrong left out):

| full_name | community | role | mentions | P_main | P_w_mean | z_main | betweenness |
|---|---|---|---|---|---|---|---|
| Jeffery Skilling | 1 | Executive | 589 | 0.653 | 0.595 | -0.666 | 0.000 |
| Kenneth Lay | 1 | Executive | 122 | 0.730 | 0.754 | 0.031 | 0.000 |
| Rick Buy | 1 | Executive | 91 | 0.426 | 0.412 | -0.284 | 0.000 |
| James Derrick | 7 | Legal | 19 | 0.549 | 0.505 | -0.734 | 0.000 |
| Steven Kean | 7 | Executive | 4 | 0.490 | 0.531 | -0.437 | 0.024 |
| Louise Kitchen | 1 | Executive | 1 | 0.636 | 0.661 | 3.426 | 0.242 |
| John Lavorato | 1 | Executive | 1 | 0.503 | 0.641 | 3.014 | 0.086 |
| Richard Sanders | 7 | Legal | 1 | 0.327 | 0.618 | -0.638 | 0.000 |

Spearman correlation between mention count and each measure
(10000 permutations, two-sided):

| measure | rho | p |
|---|---|---|
| P_main | 0.229 | 0.0043 |
| z_main | 0.023 | 0.786 |
| betweenness | -0.006 | 0.948 |
| constraint | -0.239 | 0.0031 |
| effective_size | 0.200 | 0.012 |
| strength | 0.041 | 0.626 |

Named vs never named (Mann-Whitney):

| measure | named_n | named_median | others_median | U | p |
|---|---|---|---|---|---|
| P_main | 8 | 0.526 | 0.308 | 877.000 | 0.006 |
| z_main | 8 | -0.360 | -0.299 | 593.000 | 0.755 |
| betweenness | 8 | 0.000 | 0.000 | 556.000 | 1.000 |
| strength | 8 | 210.000 | 191.000 | 619.000 | 0.594 |

Seniority controlled: mean of each measure among named people, with the
'named' label shuffled only within role groups (executives and VPs / traders /
lawyers / others):

| measure | named_mean | null_mean | p_greater |
|---|---|---|---|
| P_main | 0.539 | 0.330 | 0.001 |
| z_main | 0.464 | 0.078 | 0.139 |
| betweenness | 0.044 | 0.029 | 0.208 |
| strength | 358.125 | 391.805 | 0.550 |

Named people per community vs chance (hypergeometric, Benjamini-Hochberg):

| community | people | named | expected | mentions | p_more_than_chance | p_BH |
|---|---|---|---|---|---|---|
| C1 | 48 | 5 | 2.612 | 804 | 0.075 | 0.301 |
| C2 | 23 | 0 | 1.252 | 0 | 1.000 | 1.000 |
| C3 | 18 | 0 | 0.980 | 0 | 1.000 | 1.000 |
| C4 | 17 | 0 | 0.925 | 0 | 1.000 | 1.000 |
| C5 | 11 | 0 | 0.599 | 0 | 1.000 | 1.000 |
| C6 | 11 | 0 | 0.599 | 0 | 1.000 | 1.000 |
| C7 | 10 | 3 | 0.544 | 24 | 0.011 | 0.086 |
| C8 | 9 | 0 | 0.490 | 0 | 1.000 | 1.000 |

Few people are named, so treat these tests as descriptive.

## Figures

- `fig_named_reach` (main text): one 100% bar per person showing where their
  email goes, coloured by community, own community first (outlined); P (main
  partition) on the right. Rows: the people named in Congress, the 3 strongest
  bridges who were never named, and a grey reference bar for the median of
  everyone else (share kept inside their own community, and median P).
- `fig_si_brokers_zp` (supplement): P (x) against within-community degree z (y)
  for everyone, averaged over runs with SD lines; colour = community, ring =
  named in Congress; the named people are labelled.
