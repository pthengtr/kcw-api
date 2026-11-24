-- Run on PARTS9 **HQ KSS only** (receive-notes / รับชำระลูกหนี้ is HQ-only).
-- As a sysadmin or db_owner (e.g. WinRM Administrator + sqlcmd -E).
-- python_writer already has stock-check rights on SIMAS.
-- Receive notes needs RVMAS + SIMAS + BRDET + ARMAS read.
--
-- See docs/receive-notes.md

USE PARTS9;
GO

GRANT SELECT ON dbo.RVMAS TO python_writer;
GRANT SELECT ON dbo.SIMAS TO python_writer;
GRANT SELECT ON dbo.BRDET TO python_writer;
GRANT SELECT ON dbo.ARMAS TO python_writer;

GRANT INSERT ON dbo.RVMAS TO python_writer;
GRANT UPDATE ON dbo.RVMAS TO python_writer;
GRANT UPDATE ON dbo.SIMAS TO python_writer;
GRANT INSERT ON dbo.BRDET TO python_writer;
GRANT UPDATE ON dbo.BRDET TO python_writer;
GO
