-- Transfer writer grants (HQ↔SYP inventory)
-- Run on KSS (HQ) and kss-pc (SYP) as admin; replace python_writer with POS_MSSQL_WRITER_USERNAME.

-- Ship (stock out): SIMAS + SIDET at source branch
GRANT INSERT ON dbo.SIMAS TO [python_writer];
GRANT INSERT ON dbo.SIDET TO [python_writer];

-- Receive (stock in): PIMAS + PIDET at destination branch
GRANT INSERT ON dbo.PIMAS TO [python_writer];
GRANT INSERT ON dbo.PIDET TO [python_writer];

-- On-hand at both sites
GRANT UPDATE ON dbo.ICMAS TO [python_writer];

-- HQ (KSS): TF SIMAS ship + 3TF PIMAS receive (SYP→HQ)
-- SYP (kss-pc): 3TF SIMAS ship + TF PIMAS receive (HQ→SYP)
