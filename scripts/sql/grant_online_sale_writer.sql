-- Online sale writer grants (HQ TAD / CNTAD)
-- Run on KSS (HQ) as admin; replace python_writer with POS_MSSQL_WRITER_USERNAME.

-- Sales abbreviated invoice + credit note
GRANT SELECT ON dbo.SIMAS TO [python_writer];
GRANT INSERT ON dbo.SIMAS TO [python_writer];
GRANT SELECT ON dbo.SIDET TO [python_writer];
GRANT INSERT ON dbo.SIDET TO [python_writer];

-- Stock cut / restore on sale and return
GRANT SELECT ON dbo.ICMAS TO [python_writer];
GRANT UPDATE ON dbo.ICMAS TO [python_writer];

-- Shop master (read)
GRANT SELECT ON dbo.ARMAS TO [python_writer];
