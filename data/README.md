# Data

This folder contains the curated Enron email database and the corresponding communication network.

## `enron_main_characters.sqlite`

A SQLite database containing information about the 148 selected main characters in the Enron dataset. It includes only emails exchanged between these individuals.

The database consists of three tables:

- **`people`** – Information about the 148 individuals.
- **`emails`** – Information about each email, including its date, sender, subject, and body:
  - `body_clean` – the text with signatures (BlackBerry footer, long signatures) and the
    headers of forwarded messages removed; forwarded text itself is kept.
  - `body_raw` – the text before that clean-up, with the "Forwarded by" lines. Text analyses
    use it to tell a sender's own words from what they forwarded.
  - `message_type` – `human`, `automated`, `uncertain`, or `generated` (Outlook
    synchronisation logs and similar).
- **`email_recipients`** – Links emails to their recipients. This is a separate table because a single email can have multiple recipients.

## `main_characters_graph.pkl`

A NetworkX directed, weighted graph constructed directly from the SQLite database.

- **Nodes** represent the 148 individuals.
- **Directed edges** represent emails sent from one individual to another.
- **Edge weights** indicate the number of emails exchanged in that direction. Each email contributes 1 to the weight of the corresponding sender-to-recipient edge.
- **Edge attributes** store information (subject, date, body etc) about all the emails represented by that edge, allowing individual messages to be inspected.

The graph contains all possible information that we will need. The database is the there as the source of the data, just in case we want to construct the graph again.

## Cleaning the email texts

The clean-up of `body_clean` can be repeated on the original database, in this order:

1. `uv run python -m enron.remove_forwarded_by` – copies the original text to `body_raw`,
   then removes each "Forwarded by" line and the header that follows it (sender, date,
   To, cc, Subject), up to the first line of real text.
2. `src/enron/database_updates.sql` – removes the BlackBerry footer and long signatures.
3. `uv run python -m enron.import_new_people` – adds people without a mailbox (Fastow,
   Causey, Glisan, Kopper, McMahon, Watkins, Mintz) and their emails with the 148, from
   `temp_names.csv` and `temp_mails.csv`.
4. Steps 1 and 2 again, so the imported emails get `body_raw` and are cleaned the same way.
