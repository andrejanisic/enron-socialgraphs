-- Database schema

CREATE INDEX idx_emails_date ON emails(date);

CREATE INDEX idx_emails_sender ON emails(sender_id);

CREATE INDEX idx_recipients_person
            ON recipients(recipient_id);

CREATE TABLE emails (
            email_id INTEGER PRIMARY KEY,
            date TEXT,
            sender_id INTEGER NOT NULL,
            subject TEXT,
            body_clean TEXT,
            message_type TEXT,
            human_probability REAL,
            source_path TEXT UNIQUE,

            FOREIGN KEY (sender_id) REFERENCES people(person_id)
        );

CREATE TABLE people (
            person_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            mail TEXT NOT NULL UNIQUE
        );

CREATE TABLE recipients (
            email_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,

            PRIMARY KEY (email_id, recipient_id),

            FOREIGN KEY (email_id) REFERENCES emails(email_id),
            FOREIGN KEY (recipient_id) REFERENCES people(person_id)
        );

