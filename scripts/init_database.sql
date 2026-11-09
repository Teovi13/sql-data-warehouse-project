/*
===============================================================================
Create the database and its schemas
===============================================================================
Script Purpose:
    Creates the "DataWarehouse" database and the schemas "bronze", "silver"
    and "gold", each one only if it does not exist yet. Running it again on
    an existing warehouse changes nothing.

    It never drops the database: the warehouse keeps state that cannot be
    rebuilt from the source files, the load history (bronze.load_log) and
    the dbt snapshots (schema "snapshots"). To start from scratch on purpose,
    drop the database by hand first, knowing that both are lost.

    The schema "snapshots" (and dbt_test__audit, for failing test rows) is
    created by dbt on its first production run.
===============================================================================
*/

USE master;
GO

IF DB_ID('DataWarehouse') IS NULL
    CREATE DATABASE DataWarehouse;
GO

USE DataWarehouse;
GO

-- CREATE SCHEMA must be the only statement of its batch, so it runs through EXEC
IF SCHEMA_ID('bronze') IS NULL EXEC('CREATE SCHEMA bronze');
IF SCHEMA_ID('silver') IS NULL EXEC('CREATE SCHEMA silver');
IF SCHEMA_ID('gold')   IS NULL EXEC('CREATE SCHEMA gold');
GO
