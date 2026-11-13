# External data: `enron_external.sqlite`

This database holds everything we added *around* the email data: who each person is
(full name, job title, role), where they are named in public in the US Congress
hearings and reports on Enron, and the per-person results of our network analysis
(RQ1/RQ2).

It is a separate file from the main database, `enron_main_characters.sqlite`, which holds the
emails. The two are linked by **`person_id`**. That is the same number as
`people.person_id` in the main database.

| File | What it is |
|---|---|
| `data/enron_main_characters.sqlite` | Main database: `people`, `emails`, `recipients` (see `data/README.md`) |
| `data/enron_external.sqlite` | This database: 5 tables, described below |
| `data/schema_external.sql` | The `CREATE TABLE` statements of this database, with a comment on each column |
| `src/enron/add_external_data.py` | The script that built this database (kept to show how it was made) |

The source CSV files are **not** in the repository. To use the data you only need
`enron_external.sqlite`. Rebuilding it (below) needs the CSV files in `data/external/`;
ask the person who built the database for them.

---

## Building or updating the database

From the project root:

```powershell
uv add pandas          # once
uv run python src/enron/add_external_data.py --tables data/external
```

The script:

- only **reads** the main database and never changes it;
- deletes `enron_external.sqlite` and rebuilds it from scratch, so running it again is safe;
- writes `schema_external.sql` again;
- prints how many people it linked. The first line should say `Matched 148 of 148 people`.

Run it again whenever the CSV files in `data/external/` or the main database change.

### Source files it needs (in `data/external/`, any subfolder)

| File | Used for |
|---|---|
| `edo_enron-custodians-data.tsv` | `person_info`: folder, main address, full name, title of the 148 custodians |
| `jse_employees.csv` | `person_info`: department and title |
| `roles.csv` | `person_info`: hand-checked roles |
| `rq2_people.csv` | `full_network_metrics`, and roles for people not in `roles.csv` |
| `aliases.csv` | `email_addresses` |
| `congress_docs.csv` | `congress_documents` |
| `congress_mentions_all.csv` | `congress_mentions` |
| `hand_check_mentions.csv`, `hand_check_people.csv` | `congress_mentions.hand_correct` |

---

## How to use it

### From Python

`enron.loaders.connect()` opens the main database with this one attached as `ext`,
and `enron.loaders.load_people()` returns one row per person with name, role and
department:

```python
import pandas as pd
from enron.loaders import connect, load_people

people = load_people()          # index = person_id

conn = connect()
mentions = pd.read_sql("""
    SELECT i.full_name, i.role, COUNT(m.mention_id) AS congress_mentions
    FROM people p
    JOIN ext.person_info i USING (person_id)
    LEFT JOIN ext.congress_mentions m USING (person_id)
    GROUP BY p.person_id
    ORDER BY congress_mentions DESC
""", conn)
conn.close()
```

Tables in the main database are used as they are (`people`, `emails`). Tables in this
database get the `ext.` prefix (`ext.person_info`).

### From DB Browser for SQLite

1. File → Open Database → `data/enron_main_characters.sqlite`
2. File → Attach Database → `data/enron_external.sqlite`, and name it `ext`
3. Write queries in the "Execute SQL" tab, as above.

To browse only this database, open `enron_external.sqlite` directly.

### Example queries

Who sends the most emails, with their real name and role:

```sql
SELECT i.full_name, i.role, COUNT(*) AS sent
FROM emails e
JOIN ext.person_info i ON i.person_id = e.sender_id
GROUP BY i.person_id
ORDER BY sent DESC
LIMIT 10;
```

Where Kenneth Lay is named in Congress, with the text around each mention:

```sql
SELECT d.title, m.matched_text, m.context_snippet
FROM ext.congress_mentions m
JOIN ext.congress_documents d USING (doc_id)
WHERE m.person_name = 'Kenneth Lay';
```

The "hidden core" among the 148, central in email but never named in public:

```sql
SELECT i.full_name, i.role, f.degree, f.pagerank
FROM ext.full_network_metrics f
JOIN ext.person_info i USING (person_id)
WHERE f.group_label = 'Hidden core'
ORDER BY f.pagerank DESC;
```

---

## Tables

`person_id` is empty (NULL) for people who are not among the 148 in `people`. They are
kept, not dropped.

### `person_info`: who each person is

One row per person in `people` (148 rows). This turns folder names like `dasovich-j`
into real people.

| Field | Meaning |
|---|---|
| `person_id` | Same as `people.person_id` (primary key) |
| `full_name` | Full name, e.g. `Jeff Dasovich` |
| `email` | Main email address, e.g. `jeff.dasovich@enron.com` |
| `folder` | Mail folder name, the same as `people.name` |
| `edo_title` | Job title from the EDO custodian list (empty for about half) |
| `jse_department` | Department from the JSE employee list, e.g. `ENA Legal` |
| `jse_title` | Job title from the JSE employee list, e.g. `VP & Gen Cnsl` |
| `role` | Hand-checked role group: `Executive`, `VP / Director`, `Trading`, `Legal`, `Gov. & regulatory`, `Manager / staff` or `Unknown`. Empty for the 6 people missing from the network analysis. |

### `email_addresses`: which address belongs to whom

One row per email address (253 rows). Some people used several addresses.
These are **addresses**, not messages. Messages are in the main database's `emails`.

| Field | Meaning |
|---|---|
| `address` | One email address (primary key) |
| `person_id` | Whose address it is |
| `main_address` | That person's main address |
| `match_method` | How it was linked: `custodian` (their official address, 148), `sent-folder` (found in their sent mail, 64) or `same-name` (same name, 41) |

### `congress_documents`: the public sources

The 10 US Congress documents on Enron from 2001–2002, downloaded from govinfo.gov
(10 rows).

| Field | Meaning |
|---|---|
| `doc_id` | govinfo package id, e.g. `CHRG-107hhrg77985` (primary key) |
| `doc_type` | `hearing` (8) or `committee print` (a committee report, 2) |
| `title` | Document title |
| `n_chars` | Length of the text in characters |
| `enron_count` | How often the word "Enron" appears |
| `kept` | 1 if used in the analysis (at least 10 mentions of Enron); all 10 are kept |
| `source` | Where it came from |

### `congress_mentions`: who is named in public, and where

One row per place a person is named in one of those documents (1,237 rows, about 19
people). Counting rows per person gives their public visibility.

| Field | Meaning |
|---|---|
| `mention_id` | Row number (primary key) |
| `doc_id` | Which document (links to `congress_documents`) |
| `person_id` | Who is named. Empty for people outside the 148, e.g. Jeffrey McMahon, Richard Causey, Jordan Mintz. |
| `email` | That person's main address, set even when `person_id` is empty |
| `person_name` | Their name, e.g. `Kenneth Lay` |
| `matched_text` | How the name was written in the document, e.g. `Mr. Skilling`, `Jeff McMahon` |
| `context_snippet` | The text around the mention, for checking |
| `hand_correct` | 1 = a hand check confirmed it is the right person; empty = not checked. Wrong matches were already removed. |
| `hand_note` | The note from the hand check |

### `full_network_metrics`: results of the network analysis (RQ1/RQ2)

One row per person in our **full-corpus** email network (1,892 rows). That network
includes everyone who exchanged at least 10 emails, not only the 148. 142 of the 148
are in it.

> These numbers come from a different network than the 148-person email graph
> (`main_characters_graph.pkl`). Don't compare them directly with what
> `inspect_network.py` prints, and say which network a number comes from in the paper.

| Field | Meaning |
|---|---|
| `email` | Main email address (identifies the person in this network) |
| `person_id` | Link to `people`, or empty if not among the 148 |
| `k_threshold` | Minimum number of emails for a link in this network (10) |
| `name` | Full name |
| `group_label` | `Hidden core` (central in email, never named in public, 181), `Public faces` (central and named, 9), `Public only` (named but barely in the email network, 10), `Others` (1,692) |
| `role` | Role group, same categories as `person_info.role` |
| `title_auto` | Job title found automatically in emails |
| `is_custodian` | 1 if the person is one of the 148 custodians |
| `community` | Which email cluster the person belongs to (community detection) |
| `degree` | Number of different people they exchange email with |
| `pagerank` | PageRank: important if in contact with other important people |
| `private_pct` | Centrality in the email network as a percentile rank (0–100) |
| `betweenness` | How often they sit on the shortest path between two others |
| `broker_z` | How much more of a go-between they are than in randomised networks (z-score) |
| `broker_p` | p-value for `broker_z` |
| `broker` | 1 if a go-between: `broker_z` ≥ 2, top 10% betweenness and degree ≥ 5 (95 people) |
| `invisible_broker` | 1 if a go-between who is never named in public (91 people) |
| `public_mentions` | Times named in the Congress documents |
| `comention_degree` | Number of other people they are named alongside in those documents |
| `matched_forms` | The name forms that were matched, separated by `;` |

---

## Good to know

- **SQLite can't enforce links between two files.** Nothing stops a `person_id` in this
  database from pointing at someone missing from `people`. The build script does the
  matching itself, so check that it prints `Matched 148 of 148 people`.
- **Some text fields contain line breaks** (`matched_text`, `matched_forms`), as written
  in the original documents.
- **Shared folders in the JSE list:** eight mail folders belong to two different people
  (e.g. two Susan Scotts). The script picks the one whose name matches the custodian
  list.
