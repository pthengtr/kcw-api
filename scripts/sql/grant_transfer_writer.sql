-- Grant permissions for transfer writers to SIMAS, SIDET, and ICMAS tables
-- This script should be run on both HQ and SYP databases

-- For HQ database (writing to TF bills)
GRANT INSERT ON dbo.SIMAS TO [pos_mssql_writer_username]
GRANT INSERT ON dbo.SIDET TO [pos_mssql_writer_username] 
GRANT UPDATE ON dbo.ICMAS TO [pos_mssql_writer_username]

-- For SYP database (reading TF bill info for validation and writing to receive bills)
GRANT INSERT ON dbo.SIMAS TO [pos_mssql_writer_username]
GRANT INSERT ON dbo.SIDET TO [pos_mssql_writer_username]
GRANT UPDATE ON dbo.ICMAS TO [pos_mssql_writer_username]

-- These grants can also be used as templates:
-- GRANT INSERT ON dbo.SIMAS TO [POS_MSSQL_WRITER_USERNAME]
-- GRANT INSERT ON dbo.SIDET TO [POS_MSSQL_WRITER_USERNAME] 
-- GRANT UPDATE ON dbo.ICMAS TO [POS_MSSQL_WRITER_USERNAME]