-- SQLite
-- Every query updating the database will be here, so we are able to recreate it

-- Remove blackberry
UPDATE emails
SET body_clean = REPLACE(
    body_clean,
    'Sent from my BlackBerry Wireless Handheld (www.BlackBerry.net)',
    ''
)
WHERE body_clean LIKE '%Sent from my BlackBerry Wireless Handheld (www.BlackBerry.net)%';

-- Remove debra's long signatures
UPDATE emails
SET body_clean = REPLACE(
    body_clean,
    'Debra Perlingiere
Enron North America Corp.
Legal Department
1400 Smith Street, EB 3885
Houston, Texas 77002
dperlin@enron.com
Phone 713-853-7658
Fax  713-646-3490',
    ''
)
WHERE body_clean LIKE '%Debra Perlingiere
Enron North America Corp.
Legal Department
1400 Smith Street, EB 3885
Houston, Texas 77002
dperlin@enron.com
Phone 713-853-7658
Fax  713-646-3490%';

-- Remove Carol's signatures
UPDATE emails 
SET body_clean = REPLACE(
body_clean,
'Carol St. Clair
EB 3889
713-853-3989 (Phone)
713-646-3393 (Fax)
carol.st.clair@enron.com',
''
)
WHERE body_clean LIKE '%Carol St. Clair
EB 3889
713-853-3989 (Phone)
713-646-3393 (Fax)
carol.st.clair@enron.com%';

-- Remove Sara's signatures
UPDATE emails 
SET body_clean = REPLACE(
body_clean,
'Sara Shackleton
Enron North America Corp.
1400 Smith Street, EB 3801a
Houston, Texas  77002
713-853-5620 (phone)
713-646-3490 (fax)
sara.shackleton@enron.com',
''
)
WHERE body_clean LIKE '%Sara Shackleton
Enron North America Corp.
1400 Smith Street, EB 3801a
Houston, Texas  77002
713-853-5620 (phone)
713-646-3490 (fax)
sara.shackleton@enron.com%';

-- Remove Sara's other signatures
UPDATE emails 
SET body_clean = REPLACE(
body_clean,
'Sara Shackleton
Enron Wholesale Services
1400 Smith Street, EB3801a
Houston, TX  77002
Ph:  (713) 853-5620
Fax: (713) 646-3490',
''
)
WHERE body_clean LIKE '%Sara Shackleton
Enron Wholesale Services
1400 Smith Street, EB3801a
Houston, TX  77002
Ph:  (713) 853-5620
Fax: (713) 646-3490%';

-- Some mails end with just a first name. Remove it
WITH names(name) AS (
    VALUES
        ('Kim'),
        ('Sara'),
        ('Lynn'),
        ('Debra'),
        ('Karen'),
        ('Lisa'),
        ('Susan'),
        ('Mark'),
        ('Marie'),
        ('Clair')
),
normalized AS (
    SELECT
        e.email_id,
        LOWER(
            TRIM(RTRIM(e.body_clean, '.,!?;:"''()[]{}<>- '))
        ) AS cleaned_body
    FROM emails e
    WHERE e.body_clean IS NOT NULL
),
matches AS (
    SELECT DISTINCT
        normalized.email_id,
        names.name
    FROM normalized
    JOIN names
        ON normalized.cleaned_body LIKE '%' || LOWER(names.name)
)
UPDATE emails
SET body_clean = RTRIM(
    SUBSTR(
        body_clean,
        1,
        LENGTH(body_clean) - (
            SELECT LENGTH(name)
            FROM matches
            WHERE matches.email_id = emails.email_id
            LIMIT 1
        )
    ),
    '.,!?;:"''()[]{}<>- '
)
WHERE email_id IN (SELECT email_id FROM matches);

-- Inspect the affected rows before committing:
SELECT email_id, body_clean
FROM emails
WHERE email_id IN (SELECT email_id FROM matches);

-- Remove Debra's long signatures (she has two for some reason)
UPDATE emails
SET body_clean = TRIM(
    REPLACE(
        body_clean,
        'Debra Perlingiere
Enron North America Legal
1400 Smith Street, EB 3885
Houston, Texas 77002
dperlin@enron
713-853-7658
713-646-3490 Fax',
        ''
    ),
    CHAR(10) || CHAR(13) || ' '
)
WHERE body_clean LIKE '%Debra Perlingiere
Enron North America Legal
1400 Smith Street, EB 3885
Houston, Texas 77002
dperlin@enron
713-853-7658
713-646-3490 Fax%';

UPDATE emails
SET body_clean = TRIM(
    REPLACE(
        body_clean,
        'Debra Perlingiere
Enron North America Corp.
1400 Smith Street, EB 3885
Houston, Texas 77002
dperlin@enron.com
Phone 713-853-7658
Fax  713-646-3490',
        ''
    ),
    CHAR(10) || CHAR(13) || ' '
)
WHERE body_clean LIKE '%Debra Perlingiere
Enron North America Corp.
1400 Smith Street, EB 3885
Houston, Texas 77002
dperlin@enron.com
Phone 713-853-7658
Fax  713-646-3490%';

-- Set automated lotus calendar meetings as generated
UPDATE emails
SET message_type = 'generated'
WHERE body_clean LIKE '%*~*~*~*~*%';

-- Remove Susan's signatures
UPDATE emails 
SET body_clean = REPLACE(
body_clean,
'Susan S. Bailey
Enron North America Corp.
1400 Smith Street, Suite 3803A
Houston, Texas 77002
Phone: (713) 853-4737
Fax: (713) 646-3490
Email: Susan.Bailey@enron.com',
''
)
WHERE body_clean LIKE '%Susan S. Bailey
Enron North America Corp.
1400 Smith Street, Suite 3803A
Houston, Texas 77002
Phone: (713) 853-4737
Fax: (713) 646-3490
Email: Susan.Bailey@enron.com%';