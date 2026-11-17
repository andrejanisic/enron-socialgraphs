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