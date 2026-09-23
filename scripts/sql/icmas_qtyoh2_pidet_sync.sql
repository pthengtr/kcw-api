-- HQ (KSS) PARTS9 — sync ICMAS.QTYOH2 after PIDET changes
--
-- STATUS (2026-09-24): line-only formula. Trigger left DISABLED — superseded by
--   app on-read sync (src/db/qtyoh2_ledger.py on stock-check Take / explorer open).
--   Prefer QTYOH2_SYNC_ON_READ over enabling this PIDET trigger.
--
--   DISABLE TRIGGER dbo.trg_PIDET_sync_icmas_qtyoh2 ON dbo.PIDET;
--   ENABLE TRIGGER dbo.trg_PIDET_sync_icmas_qtyoh2 ON dbo.PIDET;
--
-- Problem: KAcc often writes purchase lines (PIDET) without updating QTYOH2 until
-- the product view is opened (rebuild). Stock-check can then SA the same gap →
-- double-apply when KAcc later rebuilds.
--
-- Fix: AFTER INSERT/UPDATE/DELETE on PIDET, recompute QTYOH2 for touched BCODEs
-- using the KAcc product-open identity (confirmed 2026-09-24 open test):
--
--   QTYOH2 = QTYBEG2
--          + Σ PIDET QTY×MTP   (line CANCELED <> 'Y' only)
--          − Σ SIDET QTY×MTP   (JOURMODE <> '0'; line CANCELED <> 'Y' only)
--
-- Line-only: do NOT filter on PIMAS/SIMAS. Header cancel with line still active
-- (e.g. DN6907-017) stays in the sum — same as KAcc. Do NOT JOIN headers
-- (duplicate keys inflate Σ). Orphan detail (no header) is included automatically.
--
-- Does NOT modify QTYBEG2.
-- SIDET is not triggered here (sale path usually updates OH live).
--
-- Requires: IDX_PIDET_BCODE / IDX_SIDET_BCODE (present on KSS).
-- Audit: ICMAS UPDATE still hits trg_ICMAS_qtyoh2_audit.
--
-- Disable for bulk loads:
--   DISABLE TRIGGER dbo.trg_PIDET_sync_icmas_qtyoh2 ON dbo.PIDET;
--   ... bulk ...
--   ENABLE TRIGGER dbo.trg_PIDET_sync_icmas_qtyoh2 ON dbo.PIDET;

USE PARTS9;
GO

CREATE OR ALTER TRIGGER dbo.trg_PIDET_sync_icmas_qtyoh2
ON dbo.PIDET
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- Skip nested re-entry (should not happen; PIDET is not written from ICMAS).
    IF TRIGGER_NESTLEVEL() > 1
        RETURN;

    IF NOT EXISTS (SELECT 1 FROM inserted)
       AND NOT EXISTS (SELECT 1 FROM deleted)
        RETURN;

    ;WITH touched AS (
        SELECT DISTINCT
            LTRIM(RTRIM(CONVERT(NVARCHAR(50), BCODE))) AS bcode
        FROM inserted
        WHERE BCODE IS NOT NULL
          AND LTRIM(RTRIM(CONVERT(NVARCHAR(50), BCODE))) <> N''
        UNION
        SELECT DISTINCT
            LTRIM(RTRIM(CONVERT(NVARCHAR(50), BCODE))) AS bcode
        FROM deleted
        WHERE BCODE IS NOT NULL
          AND LTRIM(RTRIM(CONVERT(NVARCHAR(50), BCODE))) <> N''
    ),
    pi AS (
        SELECT
            LTRIM(RTRIM(CONVERT(NVARCHAR(50), p.BCODE))) AS bcode,
            SUM(
                CONVERT(FLOAT, p.QTY)
                * COALESCE(NULLIF(CONVERT(FLOAT, p.MTP), 0), 1.0)
            ) AS units
        FROM dbo.PIDET AS p
        INNER JOIN touched AS t
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
        INNER JOIN touched AS t
            ON LTRIM(RTRIM(CONVERT(NVARCHAR(50), d.BCODE))) = t.bcode
        WHERE LTRIM(RTRIM(COALESCE(d.JOURMODE, N''))) <> N'0'
          AND UPPER(LTRIM(RTRIM(COALESCE(d.CANCELED, N'')))) <> N'Y'
        GROUP BY LTRIM(RTRIM(CONVERT(NVARCHAR(50), d.BCODE)))
    ),
    ledger AS (
        SELECT
            t.bcode,
            CONVERT(FLOAT, COALESCE(i.QTYBEG2, 0))
                + COALESCE(pi.units, 0)
                - COALESCE(si.units, 0) AS new_qtyoh2,
            CONVERT(FLOAT, i.QTYOH2) AS old_qtyoh2,
            i.ID AS icmas_id
        FROM touched AS t
        INNER JOIN dbo.ICMAS AS i
            ON LTRIM(RTRIM(CONVERT(NVARCHAR(50), i.BCODE))) = t.bcode
        LEFT JOIN pi ON pi.bcode = t.bcode
        LEFT JOIN si ON si.bcode = t.bcode
    )
    UPDATE i
    SET QTYOH2 = l.new_qtyoh2
    FROM dbo.ICMAS AS i
    INNER JOIN ledger AS l
        ON i.ID = l.icmas_id
    WHERE EXISTS (
        SELECT CONVERT(FLOAT, l.new_qtyoh2)
        EXCEPT
        SELECT CONVERT(FLOAT, l.old_qtyoh2)
    );
END
GO

-- Keep disabled after re-apply until smoke ENABLE.
DISABLE TRIGGER dbo.trg_PIDET_sync_icmas_qtyoh2 ON dbo.PIDET;
GO

SELECT name, is_disabled, create_date, modify_date
FROM sys.triggers
WHERE name = N'trg_PIDET_sync_icmas_qtyoh2';
GO
