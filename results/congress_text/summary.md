# What the Congress documents say

11,421 paragraphs kept of 14,573; 2,438 passages of about 180 words.

## Vocabulary

195,512 content words (lemmas, stopwords removed), 8,762 distinct, 2,974 used once. Zipf slope over all words: -1.03.

| rank | word | count | per_10k |
|---|---|---|---|
| 1 | enron | 5804 | 296.9 |
| 2 | company | 2616 | 133.8 |
| 3 | accounting | 1787 | 91.4 |
| 4 | board | 1598 | 81.7 |
| 5 | transaction | 1485 | 76.0 |
| 6 | financial | 1392 | 71.2 |
| 7 | report | 1260 | 64.4 |
| 8 | stock | 1187 | 60.7 |
| 9 | statement | 989 | 50.6 |
| 10 | audit | 921 | 47.1 |
| 11 | investor | 899 | 46.0 |
| 12 | work | 856 | 43.8 |
| 13 | year | 849 | 43.4 |
| 14 | people | 838 | 42.9 |
| 15 | business | 832 | 42.6 |
| 16 | sec | 822 | 42.0 |
| 17 | issue | 817 | 41.8 |
| 18 | market | 812 | 41.5 |
| 19 | employee | 740 | 37.8 |
| 20 | public | 737 | 37.7 |
| 21 | investment | 732 | 37.4 |
| 22 | andersen | 729 | 37.3 |
| 23 | information | 726 | 37.1 |
| 24 | auditor | 720 | 36.8 |
| 25 | management | 708 | 36.2 |
| 26 | analyst | 697 | 35.6 |
| 27 | firm | 690 | 35.3 |
| 28 | rule | 669 | 34.2 |
| 29 | need | 669 | 34.2 |
| 30 | interest | 660 | 33.8 |

## Phrases (collocations)

Bigrams:

| phrase | count | likelihood_ratio | pmi |
|---|---|---|---|
| arthur andersen | 330 | 3620.2 | 7.9 |
| balance sheet | 229 | 2729.7 | 8.7 |
| conflict interest | 280 | 2713.9 | 7.5 |
| wall street | 183 | 2627.4 | 9.7 |
| financial statement | 322 | 2024.2 | 5.5 |
| vinson elkins | 122 | 1917.4 | 10.4 |
| special purpose | 177 | 1857.8 | 8.1 |
| purpose entity | 154 | 1448.1 | 7.6 |
| related party | 115 | 1390.6 | 9.0 |
| board directors | 153 | 1362.3 | 6.8 |
| rating agency | 129 | 1342.2 | 8.2 |
| new york | 106 | 1297.2 | 8.7 |
| credit rating | 123 | 1224.4 | 7.9 |
| investment banking | 110 | 1089.4 | 7.7 |
| united states | 62 | 1068.5 | 11.5 |
| securities exchange | 81 | 1022.5 | 9.5 |
| ken lay | 84 | 988.7 | 8.5 |
| capital market | 119 | 972.0 | 6.8 |
| mark market | 101 | 966.0 | 7.5 |
| accounting standard | 164 | 906.5 | 5.1 |
| enron stock | 312 | 893.8 | 3.1 |
| financial reporting | 114 | 818.3 | 6.1 |
| stock price | 117 | 797.4 | 6.0 |
| natural gas | 54 | 782.3 | 10.5 |
| exchange commission | 71 | 746.4 | 8.4 |

Trigrams:

| phrase | count | likelihood_ratio | pmi |
|---|---|---|---|
| special purpose entity | 152 | 3603.2 | 16.6 |
| chief financial officer | 85 | 3310.7 | 14.3 |
| credit rating agency | 71 | 2604.5 | 16.8 |
| securities exchange commission | 70 | 1908.9 | 18.9 |
| enron financial statement | 62 | 2167.7 | 8.2 |
| mark market accounting | 60 | 1448.6 | 13.5 |
| related party transaction | 54 | 2017.5 | 14.9 |
| enron board directors | 45 | 1594.1 | 10.1 |
| chief operating officer | 44 | 3326.4 | 17.7 |
| wall street journal | 43 | 3219.7 | 19.5 |
| relate party transaction | 42 | 1065.2 | 13.6 |
| chief executive officer | 41 | 3130.4 | 15.5 |
| accept accounting principle | 40 | 1095.4 | 15.8 |
| follow prepare statement | 40 | 1002.8 | 15.0 |
| generally accept accounting | 39 | 893.4 | 15.8 |

Concordance lines for the top phrases: `concordance.md`.

## Fingerprints

Top TF-IDF words per document: `fingerprints_documents.csv`; per main speaker: `fingerprints_speakers.csv`.

## Topics (10)

Stability = mean NMI between passages' main topic over 3 seeds.

| LDA stability | NMF stability | LDA vs NMF |
|---|---|---|
| 0.39 | 0.65 | 0.36 |

LDA topics:

| topic | share | passages_main | top_words |
|---|---|---|---|
| 1 | 0.099 | 204 | andersen, report, arthur, audit, transaction, accounting, counsel, investigation, statement, record, document, elkins |
| 2 | 0.137 | 366 | skilling, fastow, ljm, transaction, lay, meeting, board, officer, partnership, correct, concern, control |
| 3 | 0.172 | 503 | people, happen, statement, employee, problem, understand, investor, work, congress, find, business, financial |
| 4 | 0.053 | 76 | market, energy, accounting, year, gas, need, collapse, utility, industry, electricity, congress, consumer |
| 5 | 0.071 | 125 | interest, accounting, entity, conflict, spe, special, purpose, investor, partnership, financial, percent, rule |
| 6 | 0.037 | 36 | board, director, compensation, management, duty, corporate, corporation, shareholder, directors, fail, officer, fiduciary |
| 7 | 0.088 | 208 | stock, employee, year, money, plan, sell, people, work, lose, share, business, pay |
| 8 | 0.110 | 293 | transaction, asset, stock, risk, value, accounting, financial, statement, hedge, investment, raptor, earning |
| 9 | 0.058 | 139 | analyst, rating, investment, research, credit, street, firm, stock, wall, investor, agency, banking |
| 10 | 0.176 | 488 | accounting, sec, audit, auditor, financial, standard, public, rule, need, system, firm, issue |

NMF topics:

| topic | share | passages_main | top_words |
|---|---|---|---|
| 1 | 0.097 | 261 | audit, auditor, andersen, firm, service, client, fee, arthur, auditing, consulting, work, internal |
| 2 | 0.071 | 159 | analyst, research, investment, banking, firm, investor, street, wall, conflict, interest, recommendation, sell |
| 3 | 0.094 | 190 | sec, review, staff, filing, commission, puhca, public, act, market, exemption, fraud, utility |
| 4 | 0.123 | 305 | skilling, lay, fastow, meeting, mcmahon, concern, talk, watkins, correct, memo, august, conflict |
| 5 | 0.176 | 487 | people, happen, employee, statement, collapse, congress, investor, work, forward, bankruptcy, corporate, corporation |
| 6 | 0.116 | 289 | board, ljm, transaction, control, fastow, report, approve, approval, review, director, interest, finance |
| 7 | 0.038 | 76 | rating, credit, agency, analyst, moody, grade, information, bond, staff, downgrade, fitch, rater |
| 8 | 0.105 | 255 | stock, sell, share, year, plan, money, price, option, employee, pge, buy, value |
| 9 | 0.082 | 187 | accounting, standard, fasb, financial, rule, reporting, issue, market, need, principle, investor, guidance |
| 10 | 0.099 | 229 | transaction, hedge, raptor, asset, risk, entity, value, spe, purpose, loss, investment, party |

Matching LDA topic to the NMF topic its passages most often have:

| LDA topic | NMF topic |
|---|---|
| 1 | 1 |
| 2 | 4 |
| 3 | 5 |
| 4 | 5 |
| 5 | 10 |
| 6 | 6 |
| 7 | 8 |
| 8 | 10 |
| 9 | 2 |
| 10 | 1 |

## Next

`hand_labels_template.csv` holds 50 random passages. Label each with the topic it is about (from the topic tables, without looking at the model's choice), then compare with `passages.csv`.

## Figures

- `fig_si_zipf`: rank-frequency plot of all words (supplement)
- `fig_si_congress_topics`: topic shares per document, LDA (supplement)
