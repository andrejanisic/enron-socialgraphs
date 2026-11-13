-- Schema of data/enron_external.sqlite (written by src/enron/add_external_data.py)
-- person_id = people.person_id in data/enron_main_characters.sqlite

CREATE TABLE congress_documents (
    doc_id TEXT PRIMARY KEY,            -- govinfo package id, e.g. CHRG-107hhrg77985
    doc_type TEXT,                      -- hearing / committee print
    title TEXT,
    n_chars INTEGER,                    -- length of the document text
    enron_count INTEGER,                -- times the word 'Enron' appears
    kept INTEGER,                       -- 1 = used in the analysis (>= 10 'Enron')
    source TEXT
);

CREATE TABLE congress_mentions (
    mention_id INTEGER PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES congress_documents(doc_id),
    person_id INTEGER,                  -- NULL if the person is not in `people`
    email TEXT NOT NULL,                -- the person's main address
    person_name TEXT,
    matched_text TEXT,                  -- how the name was written, e.g. 'Mr. Skilling'
    context_snippet TEXT,               -- text around the mention
    hand_correct INTEGER,               -- 1 right person, 0 wrong, NULL not checked
    hand_note TEXT
);

CREATE TABLE email_addresses (
    address TEXT PRIMARY KEY,           -- one email address (not a message)
    person_id INTEGER,                  -- people.person_id in the main database
    main_address TEXT,                  -- the person's main address
    match_method TEXT                   -- custodian / sent-folder / same-name
);

CREATE TABLE "full_network_metrics" (
"email" TEXT,
  "person_id" REAL,
  "k_threshold" INTEGER,
  "name" TEXT,
  "group_label" TEXT,
  "role" TEXT,
  "title_auto" TEXT,
  "is_custodian" INTEGER,
  "community" INTEGER,
  "degree" INTEGER,
  "pagerank" REAL,
  "private_pct" REAL,
  "betweenness" REAL,
  "broker_z" REAL,
  "broker_p" REAL,
  "broker" INTEGER,
  "invisible_broker" INTEGER,
  "public_mentions" INTEGER,
  "comention_degree" INTEGER,
  "matched_forms" TEXT
);

CREATE TABLE person_info (
    person_id INTEGER PRIMARY KEY,      -- people.person_id in the main database
    full_name TEXT,
    email TEXT,                         -- main address, e.g. jeff.dasovich@enron.com
    folder TEXT,                        -- maildir folder, same as people.name
    edo_title TEXT,                     -- job title from the EDO custodian list
    jse_department TEXT,                -- department from the JSE employee sheet
    jse_title TEXT,                     -- job title from the JSE employee sheet
    role TEXT                           -- hand-checked role group used in RQ2
);

CREATE INDEX idx_addresses_person ON email_addresses(person_id);

CREATE INDEX idx_fullnet_person ON full_network_metrics(person_id);

CREATE INDEX idx_mentions_doc ON congress_mentions(doc_id);

CREATE INDEX idx_mentions_person ON congress_mentions(person_id);
