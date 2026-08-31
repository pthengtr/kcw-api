-- Transfer writer grants (HQ↔SYP inventory)
-- Run on KSS (HQ) and kss-pc (SYP) as admin; replace python_writer with POS_MSSQL_WRITER_USERNAME.

-- Ship (stock out): SIMAS + SIDET at source branch
GRANT SELECT ON dbo.SIMAS TO [python_writer];
GRANT INSERT ON dbo.SIMAS TO [python_writer];
GRANT SELECT ON dbo.SIDET TO [python_writer];
GRANT INSERT ON dbo.SIDET TO [python_writer];
-- Remediation / line corrections (optional; ship writer normally INSERT-only)
GRANT UPDATE ON dbo.SIDET TO [python_writer];

-- Receive (stock in): PIMAS + PIDET at destination branch
GRANT SELECT ON dbo.PIMAS TO [python_writer];
GRANT INSERT ON dbo.PIMAS TO [python_writer];
GRANT SELECT ON dbo.PIDET TO [python_writer];
GRANT INSERT ON dbo.PIDET TO [python_writer];

-- On-hand at both sites (SELECT for product lookup during write)
GRANT SELECT ON dbo.ICMAS TO [python_writer];
GRANT UPDATE ON dbo.ICMAS TO [python_writer];

-- ICLOW stamp (SYP kss-pc only): submit/cancel/receive updates ORDERED/DOCNO/RECEIVED
-- Required when TRANSFER_ICLOW_STAMP_ENABLED=true on syp-ubuntu-server.
GRANT UPDATE ON dbo.ICLOW TO [python_writer];

-- HQ (KSS): TF SIMAS ship + 3TF PIMAS receive (SYP→HQ)
-- SYP (kss-pc): 3TF SIMAS ship + TF PIMAS receive (HQ→SYP)
