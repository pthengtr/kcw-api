-- One-time: rename transfer-created TF bill (Gregorian YY → Buddhist 69, 4-digit seq).
-- Run on HQ PARTS9 (KSS) as db_owner/sysadmin, e.g. sqlcmd -S KSS -d PARTS9 -E -i remediate_tf2608_to_tf6908_0098.sql

SET XACT_ABORT ON;
BEGIN TRAN;

DECLARE @old nvarchar(15) = N'TF2608-00001';
DECLARE @new nvarchar(15) = N'TF6908-0098';

IF NOT EXISTS (SELECT 1 FROM dbo.SIMAS WHERE BILLNO = @old)
BEGIN
    RAISERROR('Old bill %s not found on SIMAS', 16, 1, @old);
    ROLLBACK TRAN;
    RETURN;
END

IF EXISTS (SELECT 1 FROM dbo.SIMAS WHERE BILLNO = @new)
BEGIN
    RAISERROR('Target bill %s already exists on SIMAS', 16, 1, @new);
    ROLLBACK TRAN;
    RETURN;
END

UPDATE dbo.SIDET SET BILLNO = @new WHERE BILLNO = @old;
UPDATE dbo.SIMAS SET BILLNO = @new WHERE BILLNO = @old;

COMMIT TRAN;

SELECT BILLNO, BILLDATE, REMARKS FROM dbo.SIMAS WHERE BILLNO = @new;
SELECT BILLNO, BCODE, QTY, LINE FROM dbo.SIDET WHERE BILLNO = @new;
