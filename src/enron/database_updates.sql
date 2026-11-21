-- SQLite
-- Every query updating the database will be here, so we are able to recreate it
-- Order: run `uv run python -m enron.remove_forwarded_by` first (it keeps the original
-- text in emails.body_raw), then these queries; after import_new_people, run both again.
-- Note: message_type 'generated' (Outlook synchronisation logs) was set separately;
-- add that query here so the database can be recreated.

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