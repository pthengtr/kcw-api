-- HQ PO writer grants. Run on KSS (HQ PARTS9) as admin.
-- Do not run this until you are ready to set HQ_PO_ICLOW_STAMP_ENABLED=true.
-- The app updates ORDERED, DOCNO, and DOCDATE only. It does not set RECEIVED.

GRANT SELECT ON dbo.ICLOW TO [python_writer];
GRANT UPDATE ON dbo.ICLOW TO [python_writer];
GRANT SELECT ON dbo.APMAS TO [python_writer];
GRANT SELECT ON dbo.ICMAS TO [python_writer];
