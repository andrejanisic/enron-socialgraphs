--remove
WITH RECURSIVE lines(email_id, line, rest) AS (
    SELECT
        email_id,
        '',
        COALESCE(body_clean, '') || CHAR(10)
    FROM emails

    UNION ALL

    SELECT
        email_id,
        substr(rest, 1, instr(rest, CHAR(10)) - 1),
        substr(rest, instr(rest, CHAR(10)) + 1)
    FROM lines
    WHERE rest != ''
),
cleaned AS (
    SELECT
        email_id,
        group_concat(line, CHAR(10)) AS new_body
    FROM lines
    WHERE line NOT LIKE '%HOU/ECT%'
    GROUP BY email_id
)
UPDATE emails
SET body_clean = (
    SELECT new_body
    FROM cleaned
    WHERE cleaned.email_id = emails.email_id
)
WHERE email_id IN (
    SELECT email_id
    FROM lines
    WHERE line LIKE '%HOU/ECT%'
);

-- Inspect affected emails
SELECT email_id, body_clean
FROM emails
WHERE email_id IN (
    SELECT email_id
    FROM lines
    WHERE line LIKE '%HOU/ECT%'
);

-- COMMIT;   -- if satisfied
-- ROLLBACK; -- if not