# Analysis 2: communities vs the org chart

Graph: 147 people with at least one link, 1444 undirected
links (weight = emails in both directions, emails to oneself left out).
Left out for having no links to anyone else: Mary Fischer.
Louvain was run with 50 seeds; the run with the highest Q is used.
Communities are numbered by size (C1 = largest).

## Louvain and its checks

| measure | value |
|---|---|
| Communities (best run) | 8 |
| Modularity Q (best run) | 0.659 |
| Q across seeds, min to max | 0.656 to 0.659 |
| NMI between seed runs, mean (min) | 0.933 (0.798) |
| Q in shuffled graphs, mean ± sd | 0.540 ± 0.014 |
| Q vs shuffled graphs, z (p) | 8.7 (< 0.01) |
| NMI with full-corpus communities | 0.688 |
| Backbone: links kept | 204 of 1444 |
| Backbone: kept by filter / strongest link / reconnect | 188 / 14 / 2 |
| Backbone: people kept | 147 of 147 |

## Do communities follow the org chart?

NMI = 0 means no relation, 1 = communities and labels are the same grouping.
AMI corrects NMI for chance. The null is 1000 shuffles of the labels.
Role leaves out people labelled Unknown; department leaves out people with none.

| compared with | people | groups | nmi | ami | null_mean | z | p |
|---|---|---|---|---|---|---|---|
| department | 146 | 15 | 0.608 | 0.531 | 0.163 | 25.116 | < 0.001 |
| role | 125 | 6 | 0.324 | 0.258 | 0.089 | 12.970 | < 0.001 |

## Communities

| community | people | emails_inside_share | top_departments | top_roles | best_connected |
|---|---|---|---|---|---|
| C1 | 48 | 0.709 | ENA East Power (16); EWS (8); ENA Gas Financial (5) | Trading (13); Executive (10); VP / Director (10) | Louise Kitchen; John Lavorato; John Arnold; Errol McLaughlin; Sally Beck |
| C2 | 23 | 0.792 | ENA Gas West (13); ENA Gas Texas (3); Energy Operations (3) | Trading (8); Manager / staff (6); Unknown (6) | Michael Grigsby; Matthew Lenhart; Eric Bass; Kam Keiser; Phillip Love |
| C3 | 18 | 0.937 | ENA West Power Real Time (11); ENA West Power (7) | Manager / staff (8); Trading (6); Unknown (4) | William Whalley Williams; Kate Symes; Cara Semperger; Ryan Slinger; Mark Guzman |
| C4 | 17 | 0.934 | ETS (16); EWS (1) | VP / Director (6); Executive (4); Manager / staff (3) | Kimberly Watson; Michelle Lokay; Steven Harris; Shelley Corman; Rod Hayslett |
| C5 | 11 | 0.869 | ENA Legal (10); ENA Gas East (1) | Legal (10); Trading (1) | Tana Jones; Sara Shackleton; Mark Taylor; Stephanie Panus; Susan Bailey |
| C6 | 11 | 0.642 | ENA Gas West (5); ENA Legal (3); ENA Gas Central (3) | Trading (7); Legal (3); Manager / staff (1) | Barry Tycholiz; Gerald Nemec; Kim Ward; Debra Perlingiere; Mark Whitt |
| C7 | 10 | 0.787 | Regulatory and Government Affairs (4); ENA Legal (3); Enron (2) | Legal (5); Gov. & regulatory (3); Executive (1) | Jeff Dasovich; Richard Shapiro; James Steffes; Mary C. Hain; Steven Kean |
| C8 | 9 | 0.664 | ENA Gas East (7); ENA Gas Central (1); EES (1) | Unknown (5); Trading (3); Manager / staff (1) | Chris Germany; Scott Neal; Judy Townsend; Scott Hendrickson; Andrea Ring |

`emails_inside_share` = share of the community's email weight that stays inside it.

## Second methods

| method | communities | Q | NMI with Louvain |
|---|---|---|---|
| Louvain (best of seeds) | 8 | 0.659 | 1.000 |
| Leiden (best of 10) | 9 | 0.659 | 0.927 |
| Greedy modularity | 9 | 0.658 | 0.870 |

## Resolution sweep

| resolution | communities | Q (at resolution 1) | NMI with department |
|---|---|---|---|
| 0.500 | 5 | 0.640 | 0.540 |
| 0.750 | 7 | 0.657 | 0.568 |
| 1.000 | 8 | 0.659 | 0.608 |
| 1.500 | 9 | 0.658 | 0.614 |
| 2.000 | 10 | 0.655 | 0.645 |

## The org-chart match (Analysis 2c)

- Email weight inside communities: 81.5% (chance given each
  community's total email: 15.6%).
- Pairs of people who are together in some Louvain runs but not others
  (0.1 < share < 0.9): 5.1% of all pairs.

How often members of each community end up together across the 50 runs
(1 = always):

| community | people | together_share |
|---|---|---|
| C1 | 48 | 0.674 |
| C2 | 23 | 0.995 |
| C3 | 18 | 0.978 |
| C4 | 17 | 1.000 |
| C5 | 11 | 1.000 |
| C6 | 11 | 0.847 |
| C7 | 10 | 0.488 |
| C8 | 9 | 0.970 |

Observed / expected email between communities (1 = chance; diagonal = within):

| community | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 1 | 3.96 | 0.62 | 0.07 | 0.08 | 0.29 | 0.45 | 0.60 | 0.80 |
| 2 | 0.62 | 6.84 | 0.06 | 0.00 | 0.03 | 0.60 | 0.14 | 0.81 |
| 3 | 0.07 | 0.06 | 10.12 | 0.00 | 0.07 | 0.07 | 0.18 | 0.00 |
| 4 | 0.08 | 0.00 | 0.00 | 6.50 | 0.06 | 0.22 | 0.17 | 0.02 |
| 5 | 0.29 | 0.03 | 0.07 | 0.06 | 3.53 | 0.52 | 0.12 | 0.25 |
| 6 | 0.45 | 0.60 | 0.07 | 0.22 | 0.52 | 8.99 | 0.24 | 0.39 |
| 7 | 0.60 | 0.14 | 0.18 | 0.17 | 0.12 | 0.24 | 6.45 | 0.05 |
| 8 | 0.80 | 0.81 | 0.00 | 0.02 | 0.25 | 0.39 | 0.05 | 22.76 |

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
