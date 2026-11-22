# The emails against the Congress themes

## A. Preparing the emails

| step | emails |
|---|---|
| all emails | 14982 |
| human-written (threshold 0.8) | 13475 |
| not an Outlook synchronisation log | 13475 |
| with own text of at least 5 words | 9922 |
| one copy per sender and text | 9620 |
| own words (pasted news articles set aside) | 9498 |

Thirty cleaned emails next to their originals: `cleaning_check.md`.

## C. Theme coverage

Share of texts with the theme (one name term or two general terms), and theme terms per 10,000 words (independent of text length). Congress texts = passages of about 180 words; emails = the sender's own words, without pasted news articles. 'incl. forwarded text' also counts forwarded and quoted text (what people passed on or replied to); 'pasted articles' counts the news articles set aside (`press_emails.csv`).

| theme | Congress texts with theme (%) | emails with theme (%) | Congress terms per 10k words | email terms per 10k words | emails with theme | emails with theme incl. forwarded text | pasted articles with theme |
|---|---|---|---|---|---|---|---|
| LJM and the related-party partnerships | 21.53 | 0.08 | 48.44 | 1.18 | 8 | 13 | 2 |
| Special purpose entities, Raptor hedges and hidden debt | 22.68 | 0.12 | 31.18 | 0.43 | 11 | 14 | 1 |
| Arthur Andersen and the audits | 33.26 | 0.00 | 90.93 | 0.98 | 0 | 4 | 2 |
| The board, its committees and executive pay | 7.75 | 0.07 | 21.60 | 1.53 | 7 | 8 | 1 |
| Employees' retirement savings and Enron stock | 5.41 | 0.05 | 13.09 | 0.46 | 5 | 5 | 0 |
| Wall Street analysts and credit rating agencies | 5.62 | 0.02 | 25.62 | 1.30 | 2 | 6 | 3 |
| The bankruptcy and its impact on employees | 12.76 | 0.25 | 31.68 | 4.75 | 24 | 24 | 3 |
| Energy trading and power markets | 9.52 | 12.95 | 35.57 | 124.89 | 1230 | 1544 | 118 |

`theme_table.csv` holds the same numbers rounded for the paper; `Congress / emails` is how many times more often Congress uses the theme's terms.

Words most typical of each side (rates per 10,000 words):

Congress: andersen, accountant, collapse, powers, fasb, auditor, spe, chewco, profession, ljm2, pension, spes, puhca, ljm, raptors, insider, fiduciary, auditing, winokur, pitt

Emails: mmbtu, tw, mw, puc, el paso, socal, dwr, eol, da, assembly, curve, ercot, transwestern, storage, px, df, st, sj, pkg, stan

## D. Two methods for tagging emails

Method 1, term list: the theme's terms (one name term, or two general terms, and no exclude term). Method 2, retrieval: each text is split into chunks of about 180 words of equal size and embedded with `sentence-transformers/all-mpnet-base-v2`; an email's similarity to a theme is the average cosine similarity of its chunks to the theme's profile (the mean embedding of the Congress passages whose main LDA topic belongs to the theme). An email is tagged when it is among the 1% of emails most similar to the theme, the theme is the one it is most similar to, it has at least 30 words and it holds none of the theme's exclude terms. The threshold is set among the emails because emails and hearings are written so differently that even off-topic Congress passages are more similar to a theme than almost any email. A theme can get no emails. Thresholds and counts (other percentiles as a sensitivity check):

| theme | Congress passages of the theme | threshold (similarity) | emails at or above it | of these, theme is the best match | emails tagged | also tagged by the term list | emails tagged at 98th percentile | emails tagged at 99.5th percentile |
|---|---|---|---|---|---|---|---|---|
| LJM and the related-party partnerships | 366 | 0.622 | 49 | 11 | 7 | 0 | 11 | 2 |
| Special purpose entities, Raptor hedges and hidden debt | 418 | 0.637 | 49 | 14 | 14 | 0 | 28 | 8 |
| Arthur Andersen and the audits | 692 | 0.582 | 49 | 0 | 0 | 0 | 0 | 0 |
| The board, its committees and executive pay | 36 | 0.591 | 49 | 1 | 1 | 0 | 2 | 1 |
| Employees' retirement savings and Enron stock | 208 | 0.651 | 49 | 24 | 23 | 3 | 45 | 13 |
| Wall Street analysts and credit rating agencies | 139 | 0.548 | 49 | 2 | 2 | 0 | 3 | 2 |
| The bankruptcy and its impact on employees | 503 | 0.633 | 49 | 13 | 12 | 0 | 17 | 5 |
| Energy trading and power markets | 76 | 0.639 | 49 | 23 | 23 | 13 | 41 | 12 |

How far the two methods pick the same emails. With fewer than about 10 tagged emails, overlap and kappa rest on a handful of emails and say little.

| theme | emails tagged by term list | emails tagged by similarity | emails tagged by both | term-list emails also found by similarity (%) | overlap, both / either (Jaccard) | agreement beyond chance (Cohen's kappa) |
|---|---|---|---|---|---|---|
| LJM and the related-party partnerships | 8 | 7 | 0 | 0.00 | 0.00 | -0.00 |
| Special purpose entities, Raptor hedges and hidden debt | 11 | 14 | 0 | 0.00 | 0.00 | -0.00 |
| Arthur Andersen and the audits | 0 | 0 | 0 | 0.00 | 0.00 |  |
| The board, its committees and executive pay | 7 | 1 | 0 | 0.00 | 0.00 | -0.00 |
| Employees' retirement savings and Enron stock | 5 | 23 | 3 | 60.00 | 0.12 | 0.21 |
| Wall Street analysts and credit rating agencies | 2 | 2 | 0 | 0.00 | 0.00 | -0.00 |
| The bankruptcy and its impact on employees | 24 | 12 | 0 | 0.00 | 0.00 | -0.00 |
| Energy trading and power markets | 1230 | 23 | 13 | 1.06 | 0.01 | 0.02 |

## Hand checks

`hand_check_template.csv` holds 89 emails (term list, retrieval only, no theme). Copy it to `data/hand_check_emails.csv`, fill in `about_theme` (yes/no; for rows asking about any theme, the theme number or 0), then run `uv run python -m enron.check_email_themes`.

`hand_check_retrieval_template.csv` holds the emails only the embedding retrieval tags (up to 4 per theme). Copy it to `data/hand_check_retrieval.csv`, fill in `about_theme` (yes/no), then run `uv run python -m enron.check_email_themes --labels data/hand_check_retrieval.csv --key results/email_themes/hand_check_retrieval_key.csv`.

## Figures

- `fig_theme_coverage`: how many times more often Congress uses each theme's terms than the emails (main)
- `fig_si_word_comparison`: the words most typical of each text (supplement)
