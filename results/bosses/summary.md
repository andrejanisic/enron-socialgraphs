# The bosses: what they wrote and whom they wrote to

Finance core = seven finance and legal managers without a mailbox, whose emails with the 148 were added; executives = role Executive among the 148. The database holds only emails that involve at least one of the 148, so email among the finance core alone is missing.

## Who emails whom

Deliveries (one per sender-recipient pair; rows = senders):

| sender | Finance core | Executives | Others |
|---|---|---|---|
| Finance core | 11 | 61 | 25 |
| Executives | 85 | 872 | 1621 |
| Others | 20 | 1624 | 19691 |

Observed / expected given each group's volume (1 = as much as chance):

| sender | Finance core | Executives | Others |
|---|---|---|---|
| Finance core | 23.47 | 5.90 | 0.29 |
| Executives | 6.82 | 3.18 | 0.71 |
| Others | 0.19 | 0.71 | 1.04 |

Deliveries inside the finance core: 11 (only those copied to one of the 148).

Pairs in contact (at least one email either way): 104 of the 210 possible pairs of bosses with any email (50%), against 1,511 of 11,628 among everyone (13%).

Pairs of bosses who exchanged email (most first):

| person_a | group_a | person_b | group_b | a_to_b | b_to_a | total |
|---|---|---|---|---|---|---|
| John Lavorato | Executives | Louise Kitchen | Executives | 9 | 112 | 121 |
| Louise Kitchen | Executives | Sally Beck | Executives | 41 | 70 | 111 |
| Rod Hayslett | Executives | Stanley Horton | Executives | 35 | 19 | 54 |
| Danny McCarty | Executives | Rod Hayslett | Executives | 21 | 30 | 51 |
| Lawrence Greg Whalley | Executives | Louise Kitchen | Executives | 7 | 38 | 45 |
| John Lavorato | Executives | Sally Beck | Executives | 1 | 38 | 39 |
| Sally Beck | Executives | Richard Causey | Finance core | 33 | 6 | 39 |
| Lawrence Greg Whalley | Executives | John Lavorato | Executives | 16 | 22 | 38 |
| Steven Kean | Executives | Kenneth Lay | Executives | 22 | 8 | 30 |
| Danny McCarty | Executives | Stanley Horton | Executives | 12 | 9 | 21 |
| Lawrence Greg Whalley | Executives | Steven Kean | Executives | 1 | 20 | 21 |
| Jeffrey Shankman | Executives | Louise Kitchen | Executives | 9 | 11 | 20 |
| Louise Kitchen | Executives | Rick Buy | Executives | 16 | 3 | 19 |
| Jeffrey Shankman | Executives | Rick Buy | Executives | 17 | 2 | 19 |
| Jeffrey Shankman | Executives | Lawrence Greg Whalley | Executives | 13 | 4 | 17 |
| Steven Kean | Executives | Louise Kitchen | Executives | 10 | 5 | 15 |
| Rick Buy | Executives | Sally Beck | Executives | 4 | 10 | 14 |
| Lawrence Greg Whalley | Executives | Sally Beck | Executives | 1 | 11 | 12 |
| Kenneth Lay | Executives | Stanley Horton | Executives | 6 | 5 | 11 |
| Steven Kean | Executives | Stanley Horton | Executives | 9 | 1 | 10 |
| Steven Kean | Executives | John Lavorato | Executives | 10 | 0 | 10 |
| John Lavorato | Executives | Rick Buy | Executives | 2 | 8 | 10 |
| Kenneth Lay | Executives | Sally Beck | Executives | 7 | 3 | 10 |
| Jeffrey Shankman | Executives | John Lavorato | Executives | 7 | 2 | 9 |
| John Lavorato | Executives | Stanley Horton | Executives | 1 | 8 | 9 |

## What they wrote: topics

The team's NMF topic model (15 topics, fitted once on 12,865 emails from everyone; labels from `reports/nmf/topic_labels.csv`). Each email's topic weights are rescaled to sum to 1, and a set's topic share is the mean over its emails, as for the communities' topic mix. 'Bosses to bosses' = emails a boss sent with at least one other boss among the recipients; 'bosses to others only' = the rest of the bosses' emails.

Mean topic share (%):

| topic | Finance core (n=80) | Executives (n=1299) | Others (n=11486) | Bosses to bosses (n=720) | Bosses to others only (n=659) |
|---|---|---|---|---|---|
| Energy Market | 9.1 | 9.3 | 10.3 | 9.9 | 8.7 |
| EOL Credits | 5.2 | 1.2 | 2.4 | 1.8 | 1.0 |
| Master Agreements | 2.7 | 2.2 | 5.3 | 2.0 | 2.5 |
| MMBTU Delivery | 0.8 | 1.1 | 2.6 | 0.7 | 1.6 |
| Global Contracts and Facilities | 1.2 | 1.3 | 2.4 | 1.5 | 1.1 |
| Let Me Know If You Have Questions | 11.6 | 7.1 | 7.9 | 7.6 | 7.1 |
| Review Comments on Drafts or Attachments | 12.8 | 9.0 | 14.0 | 8.7 | 9.8 |
| Meetings and Discussions | 13.8 | 21.1 | 12.6 | 20.6 | 20.8 |
| Plans for Tonight | 1.7 | 1.8 | 1.3 | 1.7 | 1.9 |
| Approving Messages | 8.9 | 6.0 | 5.8 | 6.1 | 6.3 |
| Apologies and Hopes for Tomorrow | 0.9 | 2.5 | 1.4 | 2.0 | 2.9 |
| Jim Steffe Discussions | 2.9 | 3.0 | 3.2 | 3.6 | 2.5 |
| Positivity and Thoughtfulness | 10.6 | 10.7 | 7.6 | 10.9 | 10.6 |
| It Works | 10.2 | 7.2 | 5.5 | 7.8 | 6.9 |
| Deals and Changes | 7.6 | 15.8 | 17.2 | 14.6 | 16.0 |

Topics most over-represented against the others (share, ratio to the others; topics with at least 2% share):

- Finance core: EOL Credits (5.2%, 2.2x); It Works (10.2%, 1.9x); Approving Messages (8.9%, 1.5x)
- Executives: Apologies and Hopes for Tomorrow (2.5%, 1.8x); Meetings and Discussions (21.1%, 1.7x); Positivity and Thoughtfulness (10.7%, 1.4x)
- Bosses to bosses: Meetings and Discussions (20.6%, 1.6x); Positivity and Thoughtfulness (10.9%, 1.4x); Apologies and Hopes for Tomorrow (2.0%, 1.4x)

How different the topic mixes are (total variation distance: half the summed absolute differences of the topic shares; 0 = same mix), against shuffling the emails between the two sets:

| comparison | distance (percentage points) | p (10,000 shuffles) |
|---|---|---|
| Finance core vs Others | 18.6 | 0.0002 |
| Executives vs Others | 15.2 | < 0.0001 |
| Bosses to bosses vs Bosses to others only | 5.2 | 0.098 |

Each boss's topic mix (%):

| name | group | emails | Energy Market | EOL Credits | Master Agreements | MMBTU Delivery | Global Contracts and Facilities | Let Me Know If You Have Questions | Review Comments on Drafts or Attachments | Meetings and Discussions | Plans for Tonight | Approving Messages | Apologies and Hopes for Tomorrow | Jim Steffe Discussions | Positivity and Thoughtfulness | It Works | Deals and Changes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Jordan Mintz | Finance core | 27 | 6.8 | 0.7 | 2.5 | 0.5 | 0.7 | 19.1 | 22.3 | 11.9 | 0.3 | 3.9 | 0.6 | 5.4 | 8.1 | 11.4 | 5.7 |
| Jeffrey Mcmahon | Finance core | 21 | 10.0 | 15.5 | 4.4 | 0.1 | 1.5 | 3.6 | 11.2 | 9.4 | 5.5 | 10.3 | 2.1 | 1.6 | 12.3 | 6.7 | 6.0 |
| Richard Causey | Finance core | 14 | 13.7 | 0.6 | 1.7 | 0.9 | 2.2 | 14.6 | 4.6 | 24.8 | 0.6 | 11.0 | 0.0 | 2.3 | 9.9 | 7.8 | 5.3 |
| Andrew Fastow | Finance core | 7 | 6.8 | 0.0 | 0.0 | 0.5 | 2.4 | 14.2 | 3.0 | 19.3 | 0.3 | 10.4 | 0.8 | 1.8 | 18.6 | 5.4 | 16.5 |
| Ben Glisan | Finance core | 6 | 12.6 | 10.2 | 1.9 | 5.2 | 0.0 | 4.1 | 12.6 | 6.0 | 0.1 | 8.2 | 0.3 | 0.2 | 4.8 | 17.5 | 16.5 |
| Sherron Watkins | Finance core | 5 | 4.3 | 0.0 | 4.1 | 0.0 | 0.0 | 1.5 | 5.7 | 14.4 | 0.1 | 23.2 | 0.3 | 0.6 | 14.1 | 23.7 | 8.2 |
| Michael Kopper | Finance core | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Louise Kitchen | Executives | 341 | 10.0 | 1.3 | 3.2 | 0.6 | 1.5 | 5.2 | 10.6 | 16.4 | 2.5 | 6.2 | 3.1 | 2.6 | 12.7 | 7.8 | 15.4 |
| Rod Hayslett | Executives | 234 | 9.3 | 1.0 | 2.4 | 1.7 | 0.7 | 5.4 | 9.0 | 21.4 | 1.6 | 4.7 | 4.5 | 3.5 | 11.0 | 6.6 | 16.3 |
| Sally Beck | Executives | 195 | 8.8 | 0.7 | 2.7 | 0.6 | 2.5 | 7.1 | 7.3 | 33.2 | 0.6 | 4.4 | 0.4 | 2.3 | 5.0 | 12.1 | 12.3 |
| John Lavorato | Executives | 74 | 5.9 | 1.2 | 1.2 | 1.3 | 0.3 | 8.3 | 2.2 | 16.5 | 4.5 | 5.6 | 2.3 | 2.6 | 14.0 | 6.8 | 26.0 |
| Stanley Horton | Executives | 71 | 6.9 | 2.3 | 1.5 | 0.8 | 0.6 | 8.5 | 8.9 | 25.7 | 1.9 | 8.5 | 6.7 | 2.3 | 9.2 | 5.6 | 10.5 |
| Steven Kean | Executives | 67 | 10.5 | 0.9 | 0.7 | 0.3 | 1.9 | 5.7 | 28.7 | 13.3 | 0.8 | 9.1 | 0.5 | 3.4 | 10.7 | 4.6 | 7.4 |
| Jeffrey Shankman | Executives | 52 | 7.8 | 3.2 | 2.3 | 0.7 | 1.5 | 12.3 | 3.9 | 9.8 | 1.5 | 6.7 | 1.8 | 2.8 | 15.4 | 6.2 | 24.0 |
| Danny McCarty | Executives | 50 | 13.8 | 1.2 | 1.5 | 3.4 | 1.6 | 8.2 | 5.5 | 16.4 | 0.5 | 6.5 | 1.9 | 1.4 | 19.9 | 4.3 | 13.8 |
| Mike McConnell | Executives | 50 | 6.4 | 0.1 | 1.3 | 6.3 | 0.1 | 11.7 | 8.5 | 48.9 | 0.5 | 3.6 | 1.2 | 0.4 | 2.8 | 2.6 | 5.6 |
| John Giffith | Executives | 49 | 4.7 | 0.2 | 0.3 | 0.4 | 0.2 | 13.9 | 6.9 | 20.5 | 1.1 | 5.9 | 2.0 | 3.6 | 7.9 | 1.5 | 30.8 |
| Rick Buy | Executives | 47 | 8.9 | 1.8 | 1.0 | 0.4 | 0.4 | 6.2 | 5.4 | 14.9 | 5.6 | 5.4 | 0.4 | 12.8 | 10.6 | 7.5 | 18.9 |
| Lawrence Greg Whalley | Executives | 43 | 13.8 | 0.6 | 1.4 | 0.4 | 2.2 | 11.1 | 4.0 | 9.2 | 0.3 | 9.0 | 0.4 | 1.9 | 14.5 | 6.8 | 24.6 |
| Kenneth Lay | Executives | 12 | 25.9 | 0.6 | 0.4 | 0.5 | 0.4 | 5.6 | 7.1 | 22.8 | 4.9 | 18.0 | 0.1 | 1.8 | 4.0 | 5.5 | 2.3 |
| Jeffery Skilling | Executives | 7 | 16.1 | 1.2 | 8.8 | 0.0 | 3.5 | 5.1 | 7.4 | 35.1 | 0.4 | 5.5 | 0.6 | 0.2 | 5.4 | 3.1 | 7.5 |
| David Delainey | Executives | 7 | 10.6 | 12.0 | 2.5 | 0.3 | 1.2 | 1.1 | 3.0 | 3.8 | 0.4 | 1.1 | 0.0 | 12.9 | 16.6 | 7.5 | 12.5 |

Topic labels:

| topic | short title | long title |
|---|---|---|
| 0 | Energy Market | California Electricity Markets and Regulatory Pricing |
| 1 | EOL Credits | EOL Credit Responses and Documentation |
| 2 | Master Agreements | ISDA Master Agreement Execution and Counterparty Entities |
| 3 | MMBTU Delivery | Natural Gas Delivery Capacity and San Juan Supply |
| 4 | Global Contracts and Facilities | European Global Contracts and EOL Approvals |
| 5 | Let Me Know If You Have Questions | Informal Discussions, Questions and Requests for Assistance |
| 6 | Review Comments on Drafts or Attachments | Drafting and Reviewing Legal Agreements |
| 7 | Meetings and Discussions | Meetings, Office Coordination and Scheduling |
| 8 | Plans for Tonight | Informal Personal and Social Coordination |
| 9 | Approving Messages | Document Feedback and General Approval |
| 10 | Apologies and Hopes for Tomorrow | Informal Updates, Apologies and Follow-ups |
| 11 | Jim Steffe Discussions | Jim Steffe and FERC-Related Discussions |
| 12 | Positivity and Thoughtfulness | General Workplace Conversations and Problem-Solving Help |
| 13 | It Works | Work Coordination and Group Communication |
| 14 | Deals and Changes | Energy Trading and Gas Deals and Market Operations |

## What they wrote: Congress themes and typical words

Congress themes (term lists) in each group's own-word emails:

| group | own-word emails | any finance theme (%) | 95% CI | energy (%) | LJM and the related-party partnerships | Special purpose entities, Raptor hedges and hidden debt | Arthur Andersen and the audits | The board, its committees and executive pay | Employees' retirement savings and Enron stock | Wall Street analysts and credit rating agencies | The bankruptcy and its impact on employees | Energy trading and power markets |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Finance core | 76 | 11.8 | 6.4-21.0 | 1.3 | 3 | 5 | 0 | 0 | 0 | 0 | 1 | 1 |
| Executives | 1019 | 1.1 | 0.6-1.9 | 8.6 | 0 | 1 | 0 | 2 | 0 | 1 | 7 | 88 |
| Others | 8403 | 0.4 | 0.3-0.6 | 13.6 | 5 | 5 | 0 | 5 | 5 | 1 | 16 | 1141 |

Words most typical of each group of bosses against everyone else (weighted log-odds z):

| group | word | count | count_others | z |
|---|---|---|---|---|
| Finance core | school | 14 | 18 | 10.2 |
| Finance core | gift | 10 | 22 | 8.2 |
| Finance core | eim | 9 | 5 | 8.0 |
| Finance core | contribution | 8 | 15 | 7.5 |
| Finance core | business | 25 | 357 | 6.9 |
| Finance core | accounting | 8 | 26 | 6.8 |
| Finance core | pledge | 6 | 7 | 6.7 |
| Finance core | organize | 7 | 20 | 6.5 |
| Finance core | matching | 5 | 4 | 6.1 |
| Finance core | ut | 5 | 6 | 6.1 |
| Finance core | raptor | 5 | 8 | 6.0 |
| Finance core | dealbench | 7 | 1 | 5.5 |
| Finance core | officer | 7 | 38 | 5.5 |
| Finance core | bob | 9 | 71 | 5.5 |
| Finance core | reporting | 5 | 19 | 5.2 |
| Executives | operation | 106 | 58 | 15.2 |
| Executives | team | 161 | 233 | 14.9 |
| Executives | operations | 108 | 10 | 13.2 |
| Executives | business | 170 | 357 | 12.4 |
| Executives | meeting | 261 | 767 | 11.6 |
| Executives | office | 160 | 368 | 11.3 |
| Executives | bob | 70 | 71 | 11.1 |
| Executives | process | 108 | 198 | 10.8 |
| Executives | mm | 56 | 62 | 9.7 |
| Executives | budget | 52 | 53 | 9.6 |
| Executives | hall | 44 | 9 | 9.5 |
| Executives | risk | 107 | 240 | 9.4 |
| Executives | stan | 56 | 69 | 9.3 |
| Executives | operational | 50 | 53 | 9.3 |
| Executives | netco | 42 | 31 | 9.2 |

## Each boss

| name | group | title or department | deliveries sent | deliveries received | emails with a topic | main topic | main topic (% of emails) | own-word emails | finance-theme emails | energy emails | other bosses in contact | main contacts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Richard Causey | Finance core | Chief accounting officer | 30 | 47 | 14 | Meetings and Discussions | 28.6 | 14 | 2 | 0 | 13 | Sally Beck (executives, 39); Rod Hayslett (executives, 9); Ben Glisan (finance core, 4); Lawrence Greg Whalley (executives, 3); Steven Kean (executives, 3) |
| Jeffrey Mcmahon | Finance core | Treasurer until 2000, chief financial officer from October 2001 | 23 | 33 | 21 | Review Comments on Drafts or Attachments | 23.8 | 18 | 0 | 0 | 14 | Lawrence Greg Whalley (executives, 9); Rick Buy (executives, 8); Sally Beck (executives, 8); Steven Kean (executives, 5); Rod Hayslett (executives, 4) |
| Jordan Mintz | Finance core | General counsel, Enron Global Finance | 23 | 17 | 27 | Review Comments on Drafts or Attachments | 33.3 | 26 | 0 | 0 | 5 | Mark Haedicke (others, 9); Sally Beck (executives, 6); Sara Shackleton (others, 5); Rod Hayslett (executives, 4); Elizabeth Sager (others, 2) |
| Ben Glisan | Finance core | Treasurer | 9 | 11 | 6 | Approving Messages | 33.3 | 6 | 2 | 1 | 9 | Richard Causey (finance core, 4); Rick Buy (executives, 4); Louise Kitchen (executives, 2); Lawrence Greg Whalley (executives, 2); Sally Beck (executives, 2) |
| Andrew Fastow | Finance core | Chief financial officer | 7 | 2 | 7 | Approving Messages | 28.6 | 7 | 4 | 0 | 5 | Jeffery Skilling (executives, 3); Louise Kitchen (executives, 3); Lawrence Greg Whalley (executives, 1); Ben Glisan (finance core, 1); Rick Buy (executives, 1) |
| Sherron Watkins | Finance core | Vice president, corporate development | 5 | 6 | 5 | It Works | 40.0 | 5 | 1 | 0 | 3 | Rick Buy (executives, 4); Sally Beck (executives, 3); Richard Causey (finance core, 2); Mark Haedicke (others, 1); Michelle Cash (others, 1) |
| Michael Kopper | Finance core | Managing director, Global Finance (Fastow's aide) | 0 | 0 | 0 |  |  | 0 | 0 | 0 | 0 |  |
| Louise Kitchen | Executives | EWS | 661 | 425 | 338 | Deals and Changes | 19.2 | 260 | 3 | 17 | 14 | John Lavorato (executives, 121); Sally Beck (executives, 111); Mark Taylor (others, 95); Tana Jones (others, 68); Kevin Presto (others, 57) |
| Sally Beck | Executives | Energy Operations | 358 | 92 | 195 | Meetings and Discussions | 50.3 | 201 | 2 | 40 | 17 | Louise Kitchen (executives, 111); John Lavorato (executives, 39); Richard Causey (finance core, 39); Stacey White (others, 28); Rick Buy (executives, 14) |
| Rod Hayslett | Executives | ETS | 336 | 241 | 232 | Meetings and Discussions | 22.8 | 124 | 0 | 1 | 11 | Tracy Geaccone (others, 265); Drew Fossum (others, 59); Stanley Horton (executives, 54); Danny McCarty (executives, 51); Shelley Corman (others, 47) |
| Kenneth Lay | Executives | Enron | 249 | 51 | 12 | Energy Market | 33.3 | 6 | 0 | 1 | 12 | Steven Kean (executives, 30); Stanley Horton (executives, 11); James Derrick (others, 10); Sally Beck (executives, 10); Mark Taylor (others, 8) |
| John Lavorato | Executives | EWS | 193 | 582 | 73 | Deals and Changes | 34.2 | 62 | 0 | 4 | 11 | Louise Kitchen (executives, 121); John Arnold (others, 83); Jeff Dasovich (others, 58); Kevin Presto (others, 39); Sally Beck (executives, 39) |
| Steven Kean | Executives | Enron | 148 | 188 | 66 | Review Comments on Drafts or Attachments | 33.3 | 56 | 0 | 7 | 13 | Jeff Dasovich (others, 101); Richard Shapiro (others, 62); Kenneth Lay (executives, 30); James Steffes (others, 22); Lawrence Greg Whalley (executives, 21) |
| John Giffith | Executives | ENA Gas Financial | 132 | 118 | 49 | Deals and Changes | 36.7 | 33 | 0 | 1 | 1 | Errol McLaughlin (others, 72); John Arnold (others, 45); Dutch Quigley (others, 30); Lawrence May (others, 27); Michael Maggi (others, 24) |
| Stanley Horton | Executives | ETS | 109 | 123 | 71 | Meetings and Discussions | 29.6 | 58 | 1 | 3 | 12 | Rod Hayslett (executives, 54); Shelley Corman (others, 50); Danny McCarty (executives, 21); Drew Fossum (others, 14); Kenneth Lay (executives, 11) |
| Mike McConnell | Executives | EWS | 107 | 190 | 50 | Meetings and Discussions | 62.0 | 45 | 0 | 4 | 2 | Kimberly Watson (others, 133); Michelle Lokay (others, 57); Bill Rapp (others, 24); Paul Y'Barbo (others, 17); Lindy Donoho (others, 15) |
| Danny McCarty | Executives | ETS | 68 | 114 | 50 | Positivity and Thoughtfulness | 30.0 | 39 | 0 | 5 | 5 | Rod Hayslett (executives, 51); Shelley Corman (others, 26); Drew Fossum (others, 21); Stanley Horton (executives, 21); Steven Harris (others, 18) |
| Jeffrey Shankman | Executives | EWS | 61 | 51 | 52 | Deals and Changes | 32.7 | 48 | 1 | 1 | 10 | Louise Kitchen (executives, 20); Rick Buy (executives, 19); Lawrence Greg Whalley (executives, 17); John Arnold (others, 12); John Lavorato (executives, 9) |
| Lawrence Greg Whalley | Executives | EWS | 50 | 241 | 43 | Deals and Changes | 30.2 | 31 | 0 | 2 | 14 | Louise Kitchen (executives, 45); John Lavorato (executives, 38); Jeff Dasovich (others, 32); Steven Kean (executives, 21); Jeffrey Shankman (executives, 17) |
| Jeffery Skilling | Executives | Enron | 48 | 28 | 7 | Meetings and Discussions | 42.9 | 6 | 0 | 0 | 13 | Jeffrey Shankman (executives, 7); Sally Beck (executives, 7); James Derrick (others, 5); Lawrence Greg Whalley (executives, 4); Louise Kitchen (executives, 4) |
| Rick Buy | Executives | Enron | 46 | 97 | 47 | Deals and Changes | 25.5 | 43 | 3 | 2 | 16 | Louise Kitchen (executives, 19); Jeffrey Shankman (executives, 19); Mary C. Hain (others, 19); Sally Beck (executives, 14); John Lavorato (executives, 10) |
| David Delainey | Executives | EWS | 12 | 16 | 6 | Deals and Changes | 33.3 | 7 | 1 | 0 | 8 | Sally Beck (executives, 5); Richard Shapiro (others, 4); Louise Kitchen (executives, 3); Rick Buy (executives, 3); Steven Kean (executives, 3) |

