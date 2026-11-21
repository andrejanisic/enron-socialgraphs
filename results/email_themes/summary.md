# The emails against the Congress themes

## A. Preparing the emails

| step | emails |
|---|---|
| all emails | 14982 |
| human-written (threshold 0.8) | 13475 |
| not an Outlook synchronisation log | 13475 |
| with own text of at least 5 words | 9922 |
| one copy per sender and text | 9620 |
| own words (pasted news articles set aside) | 9501 |

Thirty cleaned emails next to their originals: `cleaning_check.md`.

## C. Theme coverage

Share of texts with the theme (one name term or two general terms), and theme terms per 10,000 words (independent of text length). Congress texts = passages of about 180 words; emails = the sender's own words, without pasted news articles. 'incl. forwarded text' also counts forwarded and quoted text (what people passed on or replied to); 'pasted articles' counts the news articles set aside (`press_emails.csv`).

| theme | Congress texts with theme (%) | emails with theme (%) | Congress terms per 10k words | email terms per 10k words | emails with theme | emails with theme incl. forwarded text | pasted articles with theme |
|---|---|---|---|---|---|---|---|
| The partnerships: who knew | 21.53 | 0.08 | 48.44 | 1.17 | 8 | 13 | 2 |
| The special purpose entities and their accounting | 22.68 | 0.12 | 31.18 | 0.43 | 11 | 14 | 1 |
| Andersen and the auditing | 33.26 | 0.00 | 90.93 | 0.98 | 0 | 4 | 2 |
| The board's duties and executive pay | 7.75 | 0.07 | 21.60 | 1.53 | 7 | 8 | 1 |
| Employees' stock and retirement losses | 5.41 | 0.05 | 13.09 | 0.48 | 5 | 5 | 0 |
| Analysts and rating agencies | 5.62 | 0.02 | 25.62 | 1.31 | 2 | 6 | 3 |
| The collapse and what it meant for people | 12.76 | 0.25 | 31.68 | 4.95 | 24 | 24 | 3 |
| Energy markets and trading | 9.52 | 12.98 | 35.57 | 126.07 | 1233 | 1547 | 115 |

`theme_table.csv` holds the same numbers rounded for the paper; `Congress / emails` is how many times more often Congress uses the theme's terms.

Words most typical of each side (rates per 10,000 words):

Congress: andersen, accountant, collapse, powers, fasb, auditor, chewco, spe, profession, ljm2, pension, spes, puhca, ljm, raptors, insider, fiduciary, auditing, winokur, pitt

Emails: mmbtu, tw, mw, puc, el paso, socal, dwr, eol, da, assembly, curve, ercot, transwestern, storage, px, df, st, sj, pkg, stan

## D. Two methods for tagging emails

Method 1, term list: the theme's terms (one name term, or two general terms). Method 2, similarity: the emails whose words are most similar (TF-IDF) to the theme's Congress passages (emails of at least 30 words); it tags as many emails as the term list, and at least 10, so the question is whether the two pick the same emails. With fewer than about 10 tagged emails, overlap and kappa rest on a handful of emails and say little.

| theme | emails tagged by term list | emails tagged by similarity | emails tagged by both | term-list emails also found by similarity (%) | overlap, both / either (Jaccard) | agreement beyond chance (Cohen's kappa) |
|---|---|---|---|---|---|---|
| The partnerships: who knew | 8 | 10 | 2 | 25.00 | 0.12 | 0.22 |
| The special purpose entities and their accounting | 11 | 11 | 0 | 0.00 | 0.00 | -0.00 |
| Andersen and the auditing | 0 | 10 | 0 | 0.00 | 0.00 | 0.00 |
| The board's duties and executive pay | 7 | 10 | 1 | 14.29 | 0.06 | 0.12 |
| Employees' stock and retirement losses | 5 | 10 | 3 | 60.00 | 0.25 | 0.40 |
| Analysts and rating agencies | 2 | 10 | 1 | 50.00 | 0.09 | 0.17 |
| The collapse and what it meant for people | 24 | 24 | 5 | 20.83 | 0.12 | 0.21 |
| Energy markets and trading | 1233 | 1233 | 605 | 49.07 | 0.33 | 0.41 |

## Hand check

`hand_check_template.csv` holds 95 emails. Copy it to `data/hand_check_emails.csv`, fill in `about_theme` (yes/no; for rows asking about any theme, the theme number or 0), then run `uv run python -m enron.check_email_themes`.

## Figures

- `fig_theme_coverage`: how many times more often Congress uses each theme's terms than the emails (main)
- `fig_si_word_comparison`: the words most typical of each text (supplement)
