-- Optional one-shot: align ICMAS.QTYOH2 to ledger for SKUs that already have PIDET
-- but stale OH (same identity as trg_PIDET_sync_icmas_qtyoh2).
-- Run manually after enabling the trigger if you want to heal existing rows.
-- Does NOT change QTYBEG2.
--
-- Line-only (matches KAcc product-open): sum PIDET/SIDET on line filters only —
-- no PIMAS/SIMAS header check. Do not JOIN headers (duplicate keys inflate Σ).
--
-- Safer: only SKUs with PIDET in last N days — adjust the filter.

USE PARTS9;
GO

;WITH recent_pi AS (
    SELECT DISTINCT LTRIM(RTRIM(CONVERT(NVARCHAR(50), BCODE))) AS bcode
    FROM dbo.PIDET
    WHERE BILLDATE >= DATEADD(day, -90, CAST(GETDATE() AS date))
      AND UPPER(LTRIM(RTRIM(COALESCE(CANCELED, N'')))) <> N'Y'
),
pi AS (
    SELECT
        LTRIM(RTRIM(CONVERT(NVARCHAR(50), p.BCODE))) AS bcode,
        SUM(
            CONVERT(FLOAT, p.QTY)
            * COALESCE(NULLIF(CONVERT(FLOAT, p.MTP), 0), 1.0)
        ) AS units
    FROM dbo.PIDET AS p
    INNER JOIN recent_pi AS t
        ON LTRIM(RTRIM(CONVERT(NVARCHAR(50), p.BCODE))) = t.bcode
    WHERE UPPER(LTRIM(RTRIM(COALESCE(p.CANCELED, N'')))) <> N'Y'
    GROUP BY LTRIM(RTRIM(CONVERT(NVARCHAR(50), p.BCODE)))
),
si AS (
    SELECT
        LTRIM(RTRIM(CONVERT(NVARCHAR(50), d.BCODE))) AS bcode,
        SUM(
            CONVERT(FLOAT, d.QTY)
            * COALESCE(NULLIF(CONVERT(FLOAT, d.MTP), 0), 1.0)
        ) AS units
    FROM dbo.SIDET AS d
    INNER JOIN recent_pi AS t
        ON LTRIM(RTRIM(CONVERT(NVARCHAR(50), d.BCODE))) = t.bcode
    WHERE LTRIM(RTRIM(COALESCE(d.JOURMODE, N''))) <> N'0'
      AND UPPER(LTRIM(RTRIM(COALESCE(d.CANCELED, N'')))) <> N'Y'
    GROUP BY LTRIM(RTRIM(CONVERT(NVARCHAR(50), d.BCODE)))
),
ledger AS (
    SELECT
        t.bcode,
        i.ID AS icmas_id,
        CONVERT(FLOAT, i.QTYOH2) AS old_qtyoh2,
        CONVERT(FLOAT, COALESCE(i.QTYBEG2, 0))
            + COALESCE(pi.units, 0)
            - COALESCE(si.units, 0) AS new_qtyoh2
    FROM recent_pi AS t
    INNER JOIN dbo.ICMAS AS i
        ON LTRIM(RTRIM(CONVERT(NVARCHAR(50), i.BCODE))) = t.bcode
    LEFT JOIN pi ON pi.bcode = t.bcode
    LEFT JOIN si ON si.bcode = t.bcode
)
-- Preview first:
SELECT TOP 100 bcode, old_qtyoh2, new_qtyoh2, new_qtyoh2 - old_qtyoh2 AS delta
FROM ledger
WHERE EXISTS (
    SELECT CONVERT(FLOAT, new_qtyoh2)
    EXCEPT
    SELECT CONVERT(FLOAT, old_qtyoh2)
)
ORDER BY ABS(new_qtyoh2 - old_qtyoh2) DESC;

-- Uncomment to apply:
-- UPDATE i
-- SET QTYOH2 = l.new_qtyoh2
-- FROM dbo.ICMAS AS i
-- INNER JOIN ledger AS l ON i.ID = l.icmas_id
-- WHERE EXISTS (
--     SELECT CONVERT(FLOAT, l.new_qtyoh2)
--     EXCEPT
--     SELECT CONVERT(FLOAT, l.old_qtyoh2)
-- );
GO
