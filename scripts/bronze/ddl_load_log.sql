/*
===============================================================================
DDL Script: Create Bronze Load Log Table
===============================================================================
Purpose:
    This script creates the 'bronze.load_log' table, which keeps one row per
    load attempt made by the Python ingestion layer, so that the last load of
    each table, its outcome and its errors can be queried later.

    Unlike the bronze data tables, this table is history, so the script only
    creates it when it does not exist and never drops it. Running it again is
    safe, but it does not change an existing table: use ALTER TABLE for that.
===============================================================================
*/

IF OBJECT_ID ('bronze.load_log', 'U') IS NULL
	CREATE TABLE bronze.load_log (
		load_id INT IDENTITY(1, 1),
		table_name NVARCHAR(257) NOT NULL, -- schema.table: 128 + 1 + 128
		status NVARCHAR(10) NOT NULL,
		rows_loaded INT, -- NULL when the load failed
		error_message NVARCHAR(2000), -- NULL when the load succeeded
		logged_at DATETIME2(3) NOT NULL
			CONSTRAINT DF_load_log_logged_at DEFAULT SYSDATETIME(),
		CONSTRAINT PK_load_log PRIMARY KEY (load_id),
		CONSTRAINT CK_load_log_status CHECK (status IN ('SUCCESS', 'FAILED'))
	);
GO