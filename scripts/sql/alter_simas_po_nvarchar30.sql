-- Expand SIMAS.PO so marketplace order ids fit (TikTok 18 / Lazada 16).
-- Was nvarchar(15); app truncating caused incomplete order numbers.
-- Run on KSS (HQ) PARTS9 as admin (sqlcmd -E).

SET NOCOUNT ON;
SET XACT_ABORT ON;

ALTER TABLE dbo.SIMAS ALTER COLUMN PO nvarchar(30) NULL;

SELECT
  t.name AS typ,
  c.max_length AS max_length_bytes,
  c.max_length / 2 AS max_chars
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE c.object_id = OBJECT_ID(N'dbo.SIMAS') AND c.name = N'PO';
