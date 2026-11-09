-- HQ receive writer grants. Run on KSS (HQ PARTS9) as admin.
-- Matches POS_MSSQL_WRITER_USERNAME=python_writer in .env.
-- Needed before HQ_RECEIVE_PIMAS_WRITE_ENABLED=true.
-- Confirmed grants (idempotent):

GRANT SELECT, INSERT, UPDATE ON dbo.PIMAS TO [python_writer];
GRANT SELECT, INSERT, UPDATE ON dbo.PIDET TO [python_writer];
-- INSERT needed to create new product codes from the receive screen.
GRANT SELECT, INSERT, UPDATE ON dbo.ICMAS TO [python_writer];
GRANT SELECT, UPDATE ON dbo.ICLOW TO [python_writer];
GRANT SELECT ON dbo.APMAS TO [python_writer];
