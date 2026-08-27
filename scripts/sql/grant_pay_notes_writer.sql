-- Run on PARTS9 **HQ KSS only** (pay-notes / ชำระเจ้าหนี้ is HQ-only; not for SYP kss-pc).
-- As a sysadmin or db_owner (e.g. WinRM Administrator + sqlcmd -E).
-- python_writer also has stock-check rights (SIMAS/SIDET/ICMAS).
-- Pay notes needs PVMAS + PIMAS + BPDET.
--
-- After applying, create-note / voucher writes should succeed.
-- See docs/pay-notes.md

USE PARTS9;
GO

-- Existence / MAX(VOUCNO) / header reads inside the writer transaction
GRANT SELECT ON dbo.PVMAS TO python_writer;
GRANT SELECT ON dbo.PIMAS TO python_writer;
GRANT SELECT ON dbo.BPDET TO python_writer;

-- Create note
GRANT INSERT ON dbo.PVMAS TO python_writer;
GRANT UPDATE ON dbo.PIMAS TO python_writer;

-- Mark paid (voucher)
GRANT UPDATE ON dbo.PVMAS TO python_writer;
GRANT INSERT ON dbo.BPDET TO python_writer;
GO

-- Verify (run as python_writer or check HAS_PERMS_BY_NAME while impersonating):
-- EXECUTE AS USER = 'python_writer';
-- SELECT
--   HAS_PERMS_BY_NAME('dbo.PVMAS','OBJECT','SELECT') AS pv_sel,
--   HAS_PERMS_BY_NAME('dbo.PVMAS','OBJECT','INSERT') AS pv_ins,
--   HAS_PERMS_BY_NAME('dbo.PVMAS','OBJECT','UPDATE') AS pv_upd,
--   HAS_PERMS_BY_NAME('dbo.PIMAS','OBJECT','SELECT') AS pi_sel,
--   HAS_PERMS_BY_NAME('dbo.PIMAS','OBJECT','UPDATE') AS pi_upd,
--   HAS_PERMS_BY_NAME('dbo.BPDET','OBJECT','SELECT') AS bp_sel,
--   HAS_PERMS_BY_NAME('dbo.BPDET','OBJECT','INSERT') AS bp_ins;
-- REVERT;
