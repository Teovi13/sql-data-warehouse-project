/*
Create Database and Schemas
=====================
Script Purpose:
The code creates a new database called "DataWarehouse" after checking if it already exists.

If it already exists, it is deleted and recreated.
Finally, the three database schemas "bronze," "silver," and "gold" are created.
*/

USE master;
GO

--Delete and recreate the "DataWarehouse" database, hypothetically ensuring that no one was using it.
IF EXISTS (SELECT 1 FROM sys.databases WHERE name = 'DataWarehouse')
BEGIN 
	ALTER DATABASE DataWarehouse SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
	DROP DATABASE DataWarehouse;
END;
GO

--Create the database
CREATE DATABASE DataWarehouse;
GO

USE DataWarehouse;
GO

--Create the bronze-silver-gold schemas
CREATE SCHEMA bronze;
GO

CREATE SCHEMA silver;
GO

CREATE SCHEMA gold;
