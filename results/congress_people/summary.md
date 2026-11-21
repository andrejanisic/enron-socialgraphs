# People named in the Congress documents

6,548 person mentions (spaCy, label PERSON) in 10 documents, merged into 298 people named at least 3 times (mentions + speaking turns).

- Among the 148: 6 people, 1,200 mentions
- Not among the 148: 292 people, 4,394 mentions
- Unclear (surname only, shared with one of the 148): 3 names

The list also holds members of Congress, witnesses from outside Enron and authors of documents; `title_used` (Senator, Chairman, Mr., Ms.) and `example` help tell them apart. Names are found automatically, so check rare names in `example` before using them.

## By group

Groups come from `data/congress_people_groups.csv` (labelled by hand; a draft to check). Names without a label are mostly rarely named.

| group | people | mentions | among_148 |
|---|---|---|---|
| Enron | 21 | 2654 | 6 |
| Member of Congress | 77 | 1109 | 0 |
| not labelled | 155 | 839 | 0 |
| Enron board | 15 | 371 | 0 |
| SEC, FASB and accounting bodies | 11 | 257 | 0 |
| Outside witness or expert | 12 | 205 | 0 |
| Arthur Andersen | 5 | 121 | 0 |
| Enron employee (retiree witness) | 2 | 38 | 0 |

## Enron people Congress named who are not among the 148

| name | mentions | documents | speaking_turns | title_used | group |
|---|---|---|---|---|---|
| Andrew Fastow | 538 | 9 | 7 | Mr | Enron |
| Sherron Watkins | 241 | 8 | 531 | Ms | Enron |
| Jeff McMahon | 184 | 5 | 358 | Mr | Enron |
| William Powers | 132 | 7 | 716 | Mr | Enron board |
| Michael Kopper | 117 | 6 | 10 | Mr | Enron |
| Richard Causey | 113 | 6 | 9 | Mr | Enron |
| Herbert Winokur | 86 | 6 | 194 | Mr | Enron board |
| Jordan Mintz | 76 | 5 | 161 | Mr | Enron |
| Ben Glisan | 62 | 4 | 0 | Mr | Enron |
| Robert Jaedicke | 54 | 4 | 169 | Dr | Enron board |
| Cliff Baxter | 48 | 5 | 0 | Mr | Enron |
| Charles LeMaistre | 32 | 2 | 0 | Dr | Enron board |
| Joe Sutton | 20 | 4 | 0 | Mr | Enron |
| Charles Prestwood | 19 | 1 | 47 | Mr | Enron employee (retiree witness) |
| Janice Farmer | 19 | 2 | 38 | Ms | Enron employee (retiree witness) |
| Mordaunt | 15 | 2 | 0 | Ms | Enron |
| Norman Blake | 14 | 1 | 0 | Mr | Enron board |
| Rebecca Mark | 13 | 6 | 0 |  | Enron |
| Stephen Cooper | 10 | 2 | 0 | Mr | Enron |
| John Duncan | 8 | 1 | 0 |  | Enron board |
| John Wakeham | 7 | 1 | 0 |  | Enron board |
| Raymond Troubh | 7 | 3 | 0 | Mr | Enron board |
| Cindy Olson | 6 | 2 | 0 |  | Enron |
| Frank Savage | 6 | 2 | 0 | Mr | Enron board |
| Rex Rogers | 6 | 3 | 0 |  | Enron |
| Robert Belfer | 6 | 1 | 0 | Mr | Enron board |
| John Mendelsohn | 5 | 1 | 0 | Dr | Enron board |
| Mary Joyce | 5 | 1 | 0 | Ms | Enron |
| Charls Walker | 4 | 1 | 0 | Mr | Enron board |
| Ronnie Chan | 4 | 2 | 0 | Mr | Enron board |
| Paulo Pereira | 3 | 1 | 0 | Mr | Enron board |
| Wendy Gramm | 3 | 2 | 0 | Dr | Enron board |

## Among the 148

| name | mentions | documents | speaking_turns | title_used | group | name_in_148 | role_in_148 |
|---|---|---|---|---|---|---|---|
| Jeff Skilling | 592 | 9 | 778 | Mr | Enron | Jeffery Skilling | Executive |
| Ken Lay | 480 | 9 | 0 | Mr | Enron | Kenneth Lay | Executive |
| Rick Buy | 101 | 6 | 7 | Mr | Enron | Rick Buy | Executive |
| Jim Derrick | 19 | 4 | 0 | Mr | Enron | James Derrick | Legal |
| Richard Sanders | 4 | 2 | 22 | Mr | Enron | Richard Sanders | Legal |
| Steve Kean | 4 | 3 | 0 |  | Enron | Steven Kean | Executive |

## Not among the 148 (30 most mentioned)

| name | mentions | documents | speaking_turns | title_used | group |
|---|---|---|---|---|---|
| Andrew Fastow | 538 | 9 | 7 | Mr | Enron |
| Sherron Watkins | 241 | 8 | 531 | Ms | Enron |
| Jeff McMahon | 184 | 5 | 358 | Mr | Enron |
| William Powers | 132 | 7 | 716 | Mr | Enron board |
| Michael Kopper | 117 | 6 | 10 | Mr | Enron |
| Richard Causey | 113 | 6 | 9 | Mr | Enron |
| Herbert Winokur | 86 | 6 | 194 | Mr | Enron board |
| Harvey Pitt | 79 | 5 | 155 | Mr | SEC, FASB and accounting bodies |
| Jordan Mintz | 76 | 5 | 161 | Mr | Enron |
| Joseph Berardino | 64 | 4 | 338 | Mr | Arthur Andersen |
| Ben Glisan | 62 | 4 | 0 | Mr | Enron |
| John Dingell | 61 | 7 | 179 | Mr | Member of Congress |
| Robert Jaedicke | 54 | 4 | 169 | Dr | Enron board |
| Cliff Baxter | 48 | 5 | 0 | Mr | Enron |
| James Greenwood | 47 | 5 | 539 | Chairman | Member of Congress |
| Arthur Levitt | 47 | 6 | 0 | Chairman | SEC, FASB and accounting bodies |
| James Chanos | 40 | 4 | 79 | Mr | Outside witness or expert |
| Paul Kanjorski | 38 | 1 | 93 | Mr | Member of Congress |
| Olson | 37 | 3 | 41 | Mr |  |
| Tauzin | 33 | 5 | 670 | Chairman | Member of Congress |
| Christopher John | 32 | 6 | 98 | Mr | Member of Congress |
| Michael Oxley | 32 | 1 | 45 | Chairman | Member of Congress |
| Charles LeMaistre | 32 | 2 | 0 | Dr | Enron board |
| Thomas Bauer | 31 | 2 | 54 | Mr | Arthur Andersen |
| James Castellano | 29 | 1 | 137 | Mr | SEC, FASB and accounting bodies |
| Deutsch | 29 | 4 | 127 | Mr | Member of Congress |
| Cliff Stearns | 28 | 5 | 316 | Mr | Member of Congress |
| Scott Cleland | 26 | 2 | 219 | Mr | Outside witness or expert |
| Edward Markey | 26 | 5 | 162 | Mr | Member of Congress |
| Barbara Boxer | 25 | 2 | 156 | Senator | Member of Congress |

