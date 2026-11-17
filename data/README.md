# Data

This folder contains the curated Enron email database and the corresponding communication network.

## `enron_main_characters.sqlite`

A SQLite database containing information about the 148 selected main characters in the Enron dataset. It includes only emails exchanged between these individuals.

The database consists of three tables:

- **`people`** – Information about the 148 individuals.
- **`emails`** – Information about each email, including its date, sender, subject, and body.
- **`email_recipients`** – Links emails to their recipients. This is a separate table because a single email can have multiple recipients.

## `main_characters_graph.pkl`

A NetworkX directed, weighted graph constructed directly from the SQLite database.

- **Nodes** represent the 148 individuals.
- **Directed edges** represent emails sent from one individual to another.
- **Edge weights** indicate the number of emails exchanged in that direction. Each email contributes 1 to the weight of the corresponding sender-to-recipient edge.
- **Edge attributes** store information (subject, date, body etc) about all the emails represented by that edge, allowing individual messages to be inspected.

The graph contains all possible information that we will need. The database is the there as the source of the data, just in case we want to construct the graph again.