/*
===============================================================================
Quality Checks: Gold Layer
===============================================================================
Purpose:
    This script validates the integrity, consistency, and accuracy of the
    Gold layer views. It checks for:
    - Uniqueness of surrogate keys and of business keys in the dimension
      views.
    - Referential integrity between the fact view and its dimension views.
    - That the dimension attributes promised as never NULL in the data
      dictionary (country, gender, category) really are never NULL.
    - Grain of the fact view: one row per product within an order.
    - That the fact view has as many rows as its Silver source, so the
      joins did not duplicate or drop any sale.

Usage Notes:
    Run this script AFTER creating (or refreshing) the Gold layer views.
    Each check should return NO ROWS if the data is clean.
    Any row returned points to a data quality issue that needs to be
    investigated further back in the pipeline (Silver or Bronze layer).
===============================================================================
*/

USE DataWarehouse;
GO


-- ============================================================================
-- Checking 'gold.dim_customers'
-- ============================================================================
-- Uniqueness of the surrogate key (customer_key)
-- Expectation: No results.
-- customer_key is generated with ROW_NUMBER(), so it is unique by
-- construction. This check only fails if someone replaces ROW_NUMBER() with
-- another way of generating the key. It cannot detect duplicated customers.

SELECT
    customer_key,
    COUNT(*) AS duplicate_count
FROM gold.dim_customers
GROUP BY customer_key
HAVING COUNT(*) > 1;

-- Uniqueness of the business keys (customer_id and customer_number)
-- Expectation: No results.
-- This is the check that detects duplicated customers. If a join to the ERP
-- tables matched more than one row, the same customer would appear twice
-- (a "fan-out"), each copy with a different customer_key, and the surrogate
-- key check above would not notice.

SELECT
    customer_id,
    COUNT(*) AS duplicate_count
FROM gold.dim_customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

SELECT
    customer_number,
    COUNT(*) AS duplicate_count
FROM gold.dim_customers
GROUP BY customer_number
HAVING COUNT(*) > 1;

-- Unknown values are 'n/a', never NULL (country and gender)
-- Expectation: No results.
-- A customer with no row in the ERP tables would get NULL from the LEFT JOIN
-- instead of 'n/a', and a NULL becomes its own group in every GROUP BY.
-- The view fills these gaps with COALESCE; a row here means that was lost.
SELECT
    customer_key,
    country,
    gender
FROM gold.dim_customers
WHERE country IS NULL
   OR gender IS NULL;


-- ============================================================================
-- Checking 'gold.dim_products'
-- ============================================================================
-- Uniqueness of the surrogate key (product_key)
-- Expectation: No results.
-- Same reasoning as above: product_key comes from ROW_NUMBER(), so it is
-- unique by construction.
SELECT
    product_key,
    COUNT(*) AS duplicate_count
FROM gold.dim_products
GROUP BY product_key
HAVING COUNT(*) > 1;

-- Uniqueness of the business key (product_number)
-- Expectation: No results.
-- fact_sales joins to dim_products by product_number, so it must be unique:
-- a product with two current versions (prd_end_dt IS NULL) would multiply
-- its sales in the fact view.
SELECT
    product_number,
    COUNT(*) AS duplicate_count
FROM gold.dim_products
GROUP BY product_number
HAVING COUNT(*) > 1;

-- Every product has a category
-- Expectation: No results.
-- category and maintenance come from a LEFT JOIN to the ERP category table
-- by category_id. A row here is a product whose category_id has no match
-- there, so its category, subcategory and maintenance are NULL.
SELECT
    product_key,
    product_number,
    category_id
FROM gold.dim_products
WHERE category IS NULL;


-- ============================================================================
-- Checking 'gold.fact_sales'
-- ============================================================================
-- Foreign Key Integrity (Dimensions)
-- Expectation: No results.
-- Checks that every row in fact_sales successfully matches a row in both
-- dim_customers and dim_products. A row returned here means a sale
-- references a customer_key or product_key that doesn't exist in its
-- dimension - an orphaned fact record.
SELECT
    *
FROM gold.fact_sales f
LEFT JOIN gold.dim_customers c
    ON c.customer_key = f.customer_key
LEFT JOIN gold.dim_products p
    ON p.product_key = f.product_key
WHERE c.customer_key IS NULL
   OR p.product_key IS NULL;


-- Grain
-- Expectation: No results.
-- The grain of fact_sales is one row per product within one order, so the
-- pair (order_number, product_key) must not repeat. A row here means the
-- same product appears twice in the same order, or a join duplicated a sale.
SELECT
    order_number,
    product_key,
    COUNT(*) AS duplicate_count
FROM gold.fact_sales
GROUP BY order_number, product_key
HAVING COUNT(*) > 1;


-- Row count against the Silver source
-- Expectation: No results.
-- Every sale in silver.crm_sales_details must appear exactly once in
-- fact_sales: the joins to the dimensions are LEFT JOINs on unique keys, so
-- they can neither drop nor multiply rows. Different counts here mean a
-- dimension has duplicate keys or the view was changed to filter sales.
SELECT
    s.silver_rows,
    f.gold_rows
FROM (SELECT COUNT(*) AS silver_rows FROM silver.crm_sales_details) AS s
CROSS JOIN (SELECT COUNT(*) AS gold_rows FROM gold.fact_sales) AS f
WHERE s.silver_rows <> f.gold_rows;
