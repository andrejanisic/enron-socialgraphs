# Analysis 2: communities vs the org chart

Graph: 153 people with at least one link, 1511 undirected
links (weight = emails in both directions, emails to oneself left out).
Left out for having no links to anyone else: Mary Fischer, kopper-m.
Louvain was run with 50 seeds; the run with the highest Q is used.
Communities are numbered by size (C1 = largest).

## Louvain and its checks

| measure | value |
|---|---|
| Communities (best run) | 9 |
| Modularity Q (best run) | 0.659 |
| Q across seeds, min to max | 0.656 to 0.659 |
| NMI between seed runs, mean (min) | 0.936 (0.802) |
| Q in shuffled graphs, mean ± sd | 0.544 ± 0.011 |
| Q vs shuffled graphs, z (p) | 10.1 (< 0.01) |
| NMI with full-corpus communities | 0.696 |
| Backbone: links kept | 212 of 1511 |
| Backbone: kept by filter / strongest link / reconnect | 194 / 16 / 2 |
| Backbone: people kept | 153 of 153 |

## Do communities follow the org chart?

NMI = 0 means no relation, 1 = communities and labels are the same grouping.
AMI corrects NMI for chance. The null is 1000 shuffles of the labels.
Role leaves out people labelled Unknown; department leaves out people with none.

| compared with | people | groups | nmi | ami | null_mean | z | p |
|---|---|---|---|---|---|---|---|
| department | 146 | 15 | 0.621 | 0.539 | 0.178 | 24.962 | < 0.001 |
| role | 125 | 6 | 0.282 | 0.203 | 0.099 | 9.854 | < 0.001 |

## Communities

| community | people | emails_inside_share | top_departments | top_roles | best_connected |
|---|---|---|---|---|---|
| C1 | 50 | 0.656 | ENA East Power (16); EWS (7); Enron (4) | Unknown (13); Trading (11); Executive (9) | Louise Kitchen; John Lavorato; Sally Beck; Kevin Presto; Kenneth Lay |
| C2 | 23 | 0.792 | ENA Gas West (13); ENA Gas Texas (3); Energy Operations (3) | Trading (8); Manager / staff (6); Unknown (6) | Michael Grigsby; Matthew Lenhart; Eric Bass; Kam Keiser; Phillip Love |
| C3 | 18 | 0.937 | ENA West Power Real Time (11); ENA West Power (7) | Manager / staff (8); Trading (6); Unknown (4) | William Whalley Williams; Kate Symes; Cara Semperger; Ryan Slinger; Mark Guzman |
| C4 | 17 | 0.931 | ETS (16); EWS (1) | VP / Director (6); Executive (4); Manager / staff (3) | Kimberly Watson; Michelle Lokay; Steven Harris; Shelley Corman; Rod Hayslett |
| C5 | 11 | 0.869 | ENA Legal (10); ENA Gas East (1) | Legal (10); Trading (1) | Tana Jones; Sara Shackleton; Mark Taylor; Stephanie Panus; Susan Bailey |
| C6 | 11 | 0.641 | ENA Gas West (5); ENA Legal (3); ENA Gas Central (3) | Trading (7); Legal (3); Manager / staff (1) | Barry Tycholiz; Gerald Nemec; Kim Ward; Debra Perlingiere; Mark Whitt |
| C7 | 9 | 0.663 | ENA Gas East (7); ENA Gas Central (1); EES (1) | Unknown (5); Trading (3); Manager / staff (1) | Chris Germany; Scott Neal; Judy Townsend; Scott Hendrickson; Andrea Ring |
| C8 | 8 | 0.622 | ENA Gas Financial (5); Energy Operations (1); EWS (1) | Manager / staff (3); Trading (2); VP / Director (2) | John Arnold; Errol McLaughlin; Dutch Quigley; Andy Zipper; John Giffith |
| C9 | 6 | 0.801 | Regulatory and Government Affairs (4); Enron (1); ENA West Power (1) | Gov. & regulatory (3); Legal (1); Executive (1) | Jeff Dasovich; Richard Shapiro; James Steffes; Mary C. Hain; Steven Kean |

`emails_inside_share` = share of the community's email weight that stays inside it.

## Second methods

| method | communities | Q | NMI with Louvain |
|---|---|---|---|
| Louvain (best of seeds) | 9 | 0.659 | 1.000 |
| Leiden (best of 10) | 9 | 0.658 | 0.989 |
| Greedy modularity | 9 | 0.657 | 0.919 |

## Resolution sweep

| resolution | communities | Q (at resolution 1) | NMI with department |
|---|---|---|---|
| 0.500 | 5 | 0.638 | 0.562 |
| 0.750 | 7 | 0.657 | 0.585 |
| 1.000 | 9 | 0.659 | 0.621 |
| 1.500 | 10 | 0.657 | 0.659 |
| 2.000 | 10 | 0.655 | 0.645 |

## The org-chart match (Analysis 2c)

- Email weight inside communities: 80.2% (chance given each
  community's total email: 14.3%).
- Pairs of people who are together in some Louvain runs but not others
  (0.1 < share < 0.9): 4.6% of all pairs.

How often members of each community end up together across the 50 runs
(1 = always):

| community | people | together_share |
|---|---|---|
| C1 | 50 | 0.923 |
| C2 | 23 | 0.997 |
| C3 | 18 | 0.983 |
| C4 | 17 | 1.000 |
| C5 | 11 | 1.000 |
| C6 | 11 | 0.858 |
| C7 | 9 | 0.976 |
| C8 | 8 | 0.935 |
| C9 | 6 | 1.000 |

Observed / expected email between communities (1 = chance; diagonal = within):

| community | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 4.53 | 0.55 | 0.08 | 0.15 | 0.30 | 0.30 | 0.78 | 0.92 | 0.79 |
| 2 | 0.55 | 6.90 | 0.06 | 0.00 | 0.03 | 0.61 | 0.81 | 0.61 | 0.16 |
| 3 | 0.08 | 0.06 | 10.21 | 0.00 | 0.07 | 0.07 | 0.00 | 0.00 | 0.20 |
| 4 | 0.15 | 0.00 | 0.00 | 6.52 | 0.06 | 0.22 | 0.02 | 0.00 | 0.15 |
| 5 | 0.30 | 0.03 | 0.07 | 0.06 | 3.55 | 0.53 | 0.26 | 0.41 | 0.04 |
| 6 | 0.30 | 0.61 | 0.07 | 0.22 | 0.53 | 9.04 | 0.40 | 0.80 | 0.24 |
| 7 | 0.78 | 0.81 | 0.00 | 0.02 | 0.26 | 0.40 | 22.92 | 0.61 | 0.06 |
| 8 | 0.92 | 0.61 | 0.00 | 0.00 | 0.41 | 0.80 | 0.61 | 12.20 | 0.00 |
| 9 | 0.79 | 0.16 | 0.20 | 0.15 | 0.04 | 0.24 | 0.06 | 0.00 | 7.26 |

Figures:
- `fig_email_matrix` (main): emails between communities as numbers (diagonal,
  bold = inside a community; right = each community's total); each row shaded
  in its community's colour, darker = larger share of its email.
- `fig_community_heatmap` (main): people per community and department / role;
  numbers = people, each row in its community's colour, darker = larger share.
- `fig_si_community_mixing` (supplement): the observed / expected table above.

## Figure

`figures/fig_communities.png`, drawn by the course's five rules (week 4):
1. backbone = disparity filter (α = 0.05), plus each person's strongest link, plus
   the strongest link joining any group the filter cut off from the main network;
2. ForceAtlas2 layout of the backbone; 3. colour = Louvain community found on the
full graph, each named in the legend by its most common department;
4. size = emails sent and received; 5. the 10 people with most emails named.
