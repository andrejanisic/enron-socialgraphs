# Analysis 3: hidden vs public people

147 people with links; 8 named in Congress (mentions
hand-checked as wrong left out).

## RQ1: does centrality predict who was named?

AUC = chance that a named person is more central than an unnamed one (0.5 = no
difference; p one-sided, 5000 label shuffles). rho = Spearman correlation
with the number of mentions (2500 shuffles, two-sided). Top 20 = named
people among the 20 most central, against chance (hypergeometric).

| measure | AUC | p_AUC | rho | p_rho | named_in_top20 | expected_top20 | p_top20 |
|---|---|---|---|---|---|---|---|
| PageRank | 0.409 | 0.805 | -0.077 | 0.345 | 2 | 1.088 | 0.298 |
| Emails received | 0.500 | 0.489 | -0.007 | 0.942 | 2 | 1.088 | 0.298 |
| Emails sent | 0.619 | 0.140 | 0.092 | 0.266 | 1 | 1.088 | 0.699 |
| Betweenness | 0.500 | 0.481 | -0.006 | 0.952 | 2 | 1.088 | 0.298 |
| Eigenvector | 0.647 | 0.084 | 0.113 | 0.171 | 1 | 1.088 | 0.699 |

Where the named people rank (percentile 100 = most central; broker_z = betweenness
against shuffled graphs):

| full_name | role | mentions | PageRank percentile | broker_z |
|---|---|---|---|---|
| John Lavorato | Executive | 1 | 99.32 | -1.00 |
| Louise Kitchen | Executive | 1 | 96.60 | 2.21 |
| Steven Kean | Executive | 4 | 40.14 | -0.29 |
| Rick Buy | Executive | 91 | 36.73 | -0.70 |
| Kenneth Lay | Executive | 122 | 25.17 | -1.70 |
| Richard Sanders | Legal | 1 | 23.81 | -0.63 |
| James Derrick | Legal | 19 | 6.80 | -0.43 |
| Jeffery Skilling | Executive | 589 | 5.44 | -0.82 |

## Roles

Share of each role named in Congress:

| role | people | named | named_share |
|---|---|---|---|
| Executive | 15 | 6 | 0.40 |
| Legal | 20 | 2 | 0.10 |
| VP / Director | 20 | 0 | 0.00 |
| Gov. & regulatory | 5 | 0 | 0.00 |
| Trading | 38 | 0 | 0.00 |
| Manager / staff | 27 | 0 | 0.00 |
| Unknown | 22 | 0 | 0.00 |

Executives: 6 of 8 named people vs
9 of 139 others (Fisher exact p
9.9e-06, odds ratio 43.3).

## RQ2: brokers

Broker = betweenness z-score >= 2.0 against 100 degree-preserving shuffled
graphs, and at least 5 links. 14 brokers; 13 never
named in Congress.

| full_name | role | community | broker_z | degree | named |
|---|---|---|---|---|---|
| Stacy Dickson | Legal | 5 | 6.98 | 9 | False |
| Jeff Dasovich | Gov. & regulatory | 7 | 4.44 | 34 | False |
| Errol McLaughlin | Manager / staff | 1 | 3.73 | 15 | False |
| Michael Grigsby | Trading | 2 | 3.66 | 42 | False |
| Kate Symes | Manager / staff | 3 | 3.59 | 18 | False |
| Larry Campbell | Manager / staff | 1 | 3.34 | 10 | False |
| Kay Mann | Legal | 5 | 3.22 | 19 | False |
| Steven Harris | VP / Director | 4 | 3.12 | 19 | False |
| William Whalley Williams | Manager / staff | 3 | 3.00 | 24 | False |
| Joe Stepenovitch | Trading | 1 | 2.91 | 6 | False |
| Barry Tycholiz | Trading | 6 | 2.89 | 32 | False |
| Tana Jones | Legal | 5 | 2.83 | 30 | False |
| Kevin Hyatt | VP / Director | 4 | 2.79 | 21 | False |
| Louise Kitchen | Executive | 1 | 2.21 | 54 | True |

## Groups (central = top 20% by PageRank)

| group | Executive | Legal | VP / Director | Gov. & regulatory | Trading | Manager / staff | Unknown |
|---|---|---|---|---|---|---|---|
| Public faces | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Hidden core | 1 | 9 | 3 | 3 | 7 | 4 | 1 |
| Public only | 4 | 2 | 0 | 0 | 0 | 0 | 0 |
| Others | 8 | 9 | 17 | 2 | 31 | 23 | 21 |

## Agreement with the full-corpus network

PageRank on this graph vs the full-corpus network, 142 people in
both: Spearman rho = 0.40.

## Figures

- `fig_visibility` (main): a, share of each role named in Congress (counts at the
  bar ends); b, each named person's PageRank percentile, against the median
  (line) and middle 50% (band) of everyone else.
- `fig_brokers` (main): the brokers by betweenness z-score; named people in black;
  dashed line = z = 2.0.
- `fig_si_named_ranks` (supplement): rank of each named person on all five
  measures (1 = most central; darker = more central), with AUC and p.
- `fig_si_agreement` (supplement): PageRank rank on this graph against the
  full-corpus network; named people in black.
