# **Naming Conventions**

This document outlines the naming conventions used for schemas, tables, views, columns, and other objects in the data warehouse.

## **Table of Contents**

1. [General Principles](#general-principles)
2. [Table Naming Conventions](#table-naming-conventions)
   - [Bronze Rules](#bronze-rules)
   - [Silver Rules](#silver-rules)
   - [Gold Rules](#gold-rules)
3. [Column Naming Conventions](#column-naming-conventions)
   - [Surrogate Keys](#surrogate-keys)
   - [Technical Columns](#technical-columns)
4. [Constraint Naming Conventions](#constraint-naming-conventions)
5. [Stored Procedure](#stored-procedure)
6. [Python Ingestion Layer](#python-ingestion-layer)
---

## **General Principles**

- **Naming Conventions**: Use snake_case, with lowercase letters and underscores (`_`) to separate words.
- **Language**: Use English for all names.
- **Avoid Reserved Words**: Do not use SQL reserved words as object names.

## **Table Naming Conventions**

### **Bronze Rules**
- All names must start with the source system name, and table names must match their original names without renaming.
- **`<sourcesystem>_<entity>`**  
  - `<sourcesystem>`: Name of the source system (e.g., `crm`, `erp`).  
  - `<entity>`: Exact table name from the source system.  
  - Example: `crm_cust_info` → Customer information from the CRM system.
- **Exception: operational tables.** A table that does not come from a source system but records what the warehouse itself does has no source system prefix and is named after its purpose. Today there is one: `bronze.load_log`, the history of the loads made by the Python ingestion layer. It is created by its own script (`scripts/bronze/ddl_load_log.sql`), is never dropped or truncated, and is not touched by `bronze.load_bronze`.

### **Silver Rules**
- All names must start with the source system name, and table names must match their original names without renaming.
- **`<sourcesystem>_<entity>`**  
  - `<sourcesystem>`: Name of the source system (e.g., `crm`, `erp`).  
  - `<entity>`: Exact table name from the source system.  
  - Example: `crm_cust_info` → Customer information from the CRM system.

### **Gold Rules**
- All names must use meaningful, business-aligned names for tables, starting with the category prefix.
- **`<category>_<entity>`**  
  - `<category>`: Describes the role of the table, such as `dim` (dimension) or `fact` (fact table).  
  - `<entity>`: Descriptive name of the table, aligned with the business domain (e.g., `customers`, `products`, `sales`).  
  - Examples:
    - `dim_customers` → Dimension table for customer data.  
    - `fact_sales` → Fact table containing sales transactions.  

#### **Glossary of Category Patterns**

| Pattern     | Meaning                           | Example(s)                              |
|-------------|-----------------------------------|-----------------------------------------|
| `dim_`      | Dimension table                  | `dim_customers`, `dim_products`         |
| `fact_`     | Fact table                       | `fact_sales`                            |

The Gold objects are views, not tables, but they follow the same rule.

## **Column Naming Conventions**

### **Surrogate Keys**  
- All primary keys in dimension tables must use the suffix `_key`.
- **`<table_name>_key`**  
  - `<table_name>`: Refers to the name of the table or entity the key belongs to.  
  - `_key`: A suffix indicating that this column is a surrogate key.  
  - Example: `customer_key` → Surrogate key in the `dim_customers` table.
  
### **Technical Columns**
- All technical columns must start with the prefix `dwh_`, followed by a descriptive name indicating the column's purpose.
- **`dwh_<column_name>`**  
  - `dwh`: Prefix exclusively for system-generated metadata.  
  - `<column_name>`: Descriptive name indicating the column's purpose.  
  - Example: `dwh_create_date` → System-generated column that stores when the row was loaded into the table (`DATETIME2`, default `GETDATE()`). It exists in every Silver table. Bronze keeps the source columns as they arrive, and the Gold views do not expose it.
 
## **Constraint Naming Conventions**

- Constraints created with an explicit name use a prefix that says their type, followed by the table (without schema) and, when it applies, the column.
- **`PK_<table>`**: primary key. Example: `PK_load_log`.
- **`DF_<table>_<column>`**: default value. Example: `DF_load_log_logged_at`.
- **`CK_<table>_<column>`**: check constraint. Example: `CK_load_log_status`.

## **Stored Procedure**

- All stored procedures used for loading data must follow the naming pattern:
- **`load_<layer>`**, created in the schema of the layer it loads.

  - `<layer>`: Represents the layer being loaded, `bronze` or `silver`. The Gold layer has no loading procedure because its objects are views over Silver.
  - Example:
    - `bronze.load_bronze` → Stored procedure for loading data into the Bronze layer.
    - `silver.load_silver` → Stored procedure for loading data into the Silver layer.

## **Python Ingestion Layer**

- **Modules and files**: snake_case, named after what they do (`readers.py`, `converters.py`, `validators.py`, `loaders.py`).
- **Validators**: every function in `ingestion/validators.py` is named **`find_<problem>`** (for example `find_nulls`, `find_duplicates`) and returns the rows it flags, so an empty result means nothing was flagged.
- **Tests**: files are named **`tests/test_<topic>.py`**, usually after the module they test (`test_validators.py` for `validators.py`). Each test function checks one behavior and is named after it (`test_find_duplicates_ignores_nulls`).
