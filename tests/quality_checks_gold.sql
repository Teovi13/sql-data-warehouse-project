/*
===============================================================================
Quality Checks: Gold Layer
===============================================================================
Purpose:
    This script validates the integrity, consistency, and accuracy of the
    Gold layer views. It checks for:
    - Uniqueness of surrogate keys in the dimension views.
    - Referential integrity between the fact view and its dimension views.

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
-- customer_key is generated with ROW_NUMBER(), so it should never repeat.
-- A row here would indicate that the view's underlying JOINs are producing
-- duplicate rows per customer (a "fan-out" caused by a bad join condition).

SELECT
    customer_key,
    COUNT(*) AS duplicate_count
FROM gold.dim_customers
GROUP BY customer_key
HAVING COUNT(*) > 1;


-- ============================================================================
-- Checking 'gold.dim_products'
-- ============================================================================
-- Uniqueness of the surrogate key (product_key)
-- Expectation: No results.
-- Same reasoning as above: product_key must be unique, or the fact table
-- join (fact_sales -> dim_products) could multiply rows unexpectedly.
SELECT
    product_key,
    COUNT(*) AS duplicate_count
FROM gold.dim_products
GROUP BY product_key
HAVING COUNT(*) > 1;


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
