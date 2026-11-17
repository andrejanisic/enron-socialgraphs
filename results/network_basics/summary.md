# Analysis 1: network basics and null models

Shuffled graphs: 1000 (degree-preserving edge swaps); random graphs: 1000 with the same number of people and links; label shuffles: 5000.

## The network

| statistic | value |
|---|---|
| People | 148.000 |
| People with no links (emailed only themselves) | 1.000 |
| Emails between people | 23808.000 |
| Emails to oneself (left out) | 1314.000 |
| Directed links (who emails whom) | 2083.000 |
| Undirected links | 1444.000 |
| Density (directed) | 0.096 |
| Reciprocity (share of links answered) | 0.614 |
| Mean contacts emailed (out-degree) | 14.074 |
| Max out-degree | 68.000 |
| Max in-degree | 67.000 |
| Largest connected part (undirected) | 147.000 |
| Largest strongly connected part | 145.000 |
| Average clustering | 0.524 |
| Average path length (steps) | 2.120 |
| Diameter (steps) | 4.000 |

## Against null models (Table 1)

z and p are against the shuffled graphs, which keep every person's number of contacts; p is two-sided.

| Statistic | Email network | Random graphs | Shuffled graphs | z | p |
|---|---|---|---|---|---|
| Reciprocity | 0.614 | 0.097 | 0.150 ± 0.010 | 48.1 | < 0.001 |
| Average clustering | 0.528 | 0.135 | 0.248 ± 0.006 | 50.5 | < 0.001 |
| Transitivity | 0.390 | 0.134 | 0.216 ± 0.004 | 45.4 | < 0.001 |
| Average path length | 2.120 | 1.926 | 1.952 ± 0.006 | 28.3 | < 0.001 |
| Degree assortativity | -0.063 | -0.014 | -0.113 ± 0.013 | 3.9 | < 0.001 |

## Mixing by role and department

Assortativity r: 0 = links ignore the attribute, 1 = links only within groups. 'emails' weights each link by its number of emails.

| attribute | counted | r | shuffled mean | shuffled 95% | p | groups |
|---|---|---|---|---|---|---|
| Role | links | 0.121 | -0.010 | 0.007 | < 0.0002 | 7 |
| Role | emails | 0.374 | -0.019 | 0.040 | < 0.0002 | 7 |
| Department | links | 0.304 | -0.009 | 0.002 | < 0.0002 | 15 |
| Department | emails | 0.621 | -0.018 | 0.023 | < 0.0002 | 15 |

## Rich club

Highest rich-club ratio: rho = 1.32 for the 18 people with more than 30 contacts (shuffled graphs: 95% between 0.89 and 1.11).

Executives emailing each other:

| executives | possible links | links | shuffled graphs | p (shuffled) | random sets of 15 | p (random sets) |
|---|---|---|---|---|---|---|
| 15 | 105 | 61 | 34.3 | < 0.001 | 14.2 | < 0.0002 |

## Who mostly sends, who mostly receives

People with at least 100 emails, by share of their email that they sent.

| full_name | role | sent | received | sent_share |
|---|---|---|---|---|
| Craig Dean | Trading | 7 | 216 | 0.031 |
| Eric Linder | Manager / staff | 8 | 183 | 0.042 |
| Scott Hendrickson | Unknown | 8 | 124 | 0.061 |
| Robert Badeer | VP / Director | 16 | 242 | 0.062 |
| Keith Holst | VP / Director | 15 | 185 | 0.075 |
| Jeff Dasovich | Gov. & regulatory | 1771 | 356 | 0.833 |
| Kenneth Lay | Executive | 249 | 49 | 0.836 |
| Don Baughman | Trading | 197 | 38 | 0.838 |
| Chris Germany | Trading | 389 | 72 | 0.844 |
| William Whalley Williams | Manager / staff | 1360 | 155 | 0.898 |

## Figures

- `fig_role_mixing`: emails between roles, observed / expected (main text)
- `fig_si_null_models`: each statistic against both null models (supplement)
- `fig_si_rich_club`: rich-club ratio by number of contacts (supplement)
- `fig_si_send_receive`: emails sent against received per person (supplement)
