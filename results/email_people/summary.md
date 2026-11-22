# Did the central people write about what Congress investigated?

Congress-theme emails = own-word emails tagged with any of themes 1-7 by the term lists (45 emails). Chance = the theme flags shuffled over all own-word emails 10,000 times; every email keeps its sender and recipients, so people who write a lot are expected to write more theme emails. `ratio` = observed / expected; `p_high` = share of shuffles at least as high as observed, `p_low` = at least as low.

## Groups

One group per person, in this order: named by Congress (named at least once in the hand-checked Congress mentions); central core (top 20% by PageRank); brokers (betweenness z >= 2 against degree-preserving shuffles, with both email-weighted and links-only betweenness, and at least 5 links); others.

| group | people | emails_written | congress_written | energy_written | members |
|---|---|---|---|---|---|
| Named by Congress | 8 | 474 | 7 | 34 | John Lavorato; Louise Kitchen; Steven Kean; Rick Buy; Kenneth Lay; Richard Sanders; James Derrick; Jeffery Skilling |
| Central core | 28 | 5357 | 8 | 731 | Mark Taylor; Sara Shackleton; Michael Grigsby; Tana Jones; Kim Ward; John Arnold; Barry Tycholiz; Gerald Nemec; Matthew Lenhart; Susan Bailey; Kimberly Watson; William Whalley Williams |
| Brokers | 7 | 376 | 2 | 135 | Diana Scholtes; Don Baughman; John M. Forney; Robert Badeer; Kay Mann; Larry Campbell; Mary C. Hain |
| Others | 105 | 3218 | 28 | 332 | Lindy Donoho; Dan Hyvl; Keith Holst; Elizabeth Sager; Dutch Quigley; Stacy Dickson; Hunter Shively; Scott Neal; Kam Keiser; Kevin Presto; Tracy Geaccone; Douglas Gilberth-Smith |

## Who wrote the Congress-theme emails

| group | observed | expected | chance_low | chance_high | ratio | p_high | p_low |
|---|---|---|---|---|---|---|---|
| Named by Congress | 7.000 | 2.300 | 0.000 | 6.000 | 3.090 | 0.007 | 0.998 |
| Central core | 8.000 | 25.600 | 19.000 | 32.000 | 0.310 | 1.000 | 0.000 |
| Brokers | 2.000 | 1.800 | 0.000 | 5.000 | 1.120 | 0.539 | 0.739 |
| Others | 28.000 | 15.300 | 9.000 | 22.000 | 1.820 | 0.000 | 1.000 |

## Who received them

Recipients without the sender; each email weighted 1 / number of recipients.

| group | observed | expected | chance_low | chance_high | ratio | p_high | p_low |
|---|---|---|---|---|---|---|---|
| Named by Congress | 8.667 | 3.500 | 0.600 | 7.167 | 2.450 | 0.004 | 0.996 |
| Central core | 12.500 | 23.000 | 16.833 | 29.129 | 0.540 | 1.000 | 0.000 |
| Brokers | 0.333 | 1.200 | 0.000 | 3.500 | 0.280 | 0.781 | 0.243 |
| Others | 18.500 | 15.100 | 9.378 | 20.967 | 1.230 | 0.126 | 0.876 |

## For contrast: energy emails

Written:

| group | observed | expected | chance_low | chance_high | ratio | p_high | p_low |
|---|---|---|---|---|---|---|---|
| Named by Congress | 34.000 | 61.900 | 48.000 | 76.000 | 0.550 | 1.000 | 0.000 |
| Central core | 731.000 | 700.200 | 668.000 | 732.000 | 1.040 | 0.031 | 0.974 |
| Brokers | 135.000 | 49.200 | 37.000 | 62.000 | 2.740 | 0.000 | 1.000 |
| Others | 332.000 | 420.700 | 391.000 | 451.000 | 0.790 | 1.000 | 0.000 |

Received:

| group | observed | expected | chance_low | chance_high | ratio | p_high | p_low |
|---|---|---|---|---|---|---|---|
| Named by Congress | 126.155 | 97.300 | 80.959 | 113.898 | 1.300 | 0.000 | 1.000 |
| Central core | 595.056 | 629.100 | 598.543 | 659.471 | 0.950 | 0.985 | 0.015 |
| Brokers | 65.291 | 32.300 | 23.497 | 41.504 | 2.020 | 0.000 | 1.000 |
| Others | 408.499 | 413.200 | 384.698 | 442.120 | 0.990 | 0.623 | 0.377 |

## When

8 of the 45 Congress-theme emails were written before October 2001 (`early_emails.csv`); all of them, with sender, group and first words, are in `congress_emails.csv`. Per month: `timeline.csv`.

| date | emails | theme_emails | energy_emails |
|---|---|---|---|
| 2000-07 | 139 | 1 | 16 |
| 2000-09 | 203 | 1 | 20 |
| 2000-10 | 258 | 1 | 35 |
| 2000-11 | 315 | 1 | 57 |
| 2001-01 | 232 | 3 | 33 |
| 2001-08 | 500 | 1 | 87 |
| 2001-10 | 1156 | 6 | 145 |
| 2001-11 | 928 | 25 | 88 |
| 2001-12 | 365 | 2 | 31 |
| 2002-01 | 590 | 3 | 75 |
| 2002-03 | 160 | 1 | 16 |

## Robustness (central core and named people)

| variant | side | central core: observed | expected | ratio | p_low | p_high | named: observed | named: expected | named: p_high |
|---|---|---|---|---|---|---|---|---|---|
| main (PageRank top 20%, weighted receiving) | written | 8.000 | 25.656 | 0.312 | 0.000 | 1.000 | 7.000 | 2.249 | 0.006 |
| main (PageRank top 20%, weighted receiving) | received | 12.500 | 22.984 | 0.544 | 0.000 | 1.000 | 8.667 | 3.560 | 0.005 |
| central = top 20% by links | written | 10.000 | 17.362 | 0.576 | 0.013 | 0.993 | 7.000 | 2.249 | 0.006 |
| central = top 20% by links | received | 15.833 | 12.984 | 1.219 | 0.852 | 0.150 | 8.667 | 3.560 | 0.005 |
| receiving unweighted | written | 8.000 | 25.656 | 0.312 | 0.000 | 1.000 | 7.000 | 2.249 | 0.006 |
| receiving unweighted | received | 17.000 | 37.136 | 0.458 | 0.001 | 1.000 | 12.000 | 5.311 | 0.025 |
| forwarded text included | written | 16.000 | 33.643 | 0.476 | 0.000 | 1.000 | 7.000 | 2.927 | 0.023 |
| forwarded text included | received | 19.900 | 30.189 | 0.659 | 0.003 | 0.998 | 10.667 | 4.643 | 0.003 |
| named = named 10+ times | written | 11.000 | 27.193 | 0.405 | 0.000 | 1.000 | 3.000 | 0.370 | 0.006 |
| named = named 10+ times | received | 18.000 | 25.680 | 0.701 | 0.006 | 0.995 | 2.500 | 0.437 | 0.010 |

## People outside the email network

Added from other people's mailboxes (they have no mailbox of their own), so only their emails with the 148 are seen and they are left out of the group tests above. Own-word emails they wrote and received:

| full_name | written | written_congress | written_energy | received | received_congress | congress_mentions |
|---|---|---|---|---|---|---|
| Andrew Fastow | 7 | 4 | 0 | 1 | 0 | 538 |
| Richard Causey | 14 | 2 | 0 | 44 | 2 | 113 |
| Ben Glisan | 6 | 2 | 1 | 10 | 4 | 62 |
| Michael Kopper | 0 | 0 | 0 | 0 | 0 | 117 |
| Jeffrey Mcmahon | 18 | 0 | 0 | 31 | 1 | 184 |
| Sherron Watkins | 5 | 1 | 0 | 6 | 0 | 241 |
| Jordan Mintz | 26 | 0 | 0 | 16 | 1 | 76 |

Figures: `fig_email_people` (main): Congress-theme emails written and received by each group against the range expected by chance; `fig_si_email_people_ratio` (supplement): observed / expected for the Congress themes and energy.

Files: `people.csv` (every person: group, network position, emails written and received), `groups.csv`, `tests.csv`, `timeline.csv`, `congress_emails.csv`, `early_emails.csv`, `robustness.csv`.
