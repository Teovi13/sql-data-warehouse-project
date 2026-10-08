"""Catalog of validation rules for the Bronze tables.

Each rule is a ``(table, check, params)`` tuple: the table name, a validator
from ``ingestion.validators`` and its keyword arguments. The rules are run by
``ingestion.report.run_validations``.
"""

from ingestion.validators import (
    find_containing,
    find_date_order_violations,
    find_duplicates,
    find_future_dates,
    find_invalid_dates,
    find_invalid_values,
    find_non_positive,
    find_not_uppercase,
    find_nulls,
    find_prefixed,
    find_total_mismatches,
    find_untrimmed,
)

CRM_CUSTOMERS = "bronze.crm_cust_info"
CRM_PRODUCTS = "bronze.crm_prd_info"
CRM_SALES = "bronze.crm_sales_details"
ERP_CUSTOMERS = "bronze.erp_cust_az12"
ERP_LOCATIONS = "bronze.erp_loc_a101"
ERP_CATEGORIES = "bronze.erp_px_cat_g1v2"

DASHED_DATE = "%Y-%m-%d"
COMPACT_DATE = "%Y%m%d"

RULES = [
    # crm_cust_info
    (CRM_CUSTOMERS, find_nulls, {"column": "cst_id"}),
    (CRM_CUSTOMERS, find_duplicates, {"column": "cst_id"}),
    (CRM_CUSTOMERS, find_untrimmed, {"column": "cst_firstname"}),
    (CRM_CUSTOMERS, find_untrimmed, {"column": "cst_lastname"}),
    (CRM_CUSTOMERS, find_invalid_values, {
        "column": "cst_marital_status",
        "allowed": ["S", "M"],
    }),
    (CRM_CUSTOMERS, find_invalid_values, {
        "column": "cst_gndr",
        "allowed": ["F", "M"],
    }),
    (CRM_CUSTOMERS, find_invalid_dates, {
        "column": "cst_create_date",
        "date_format": DASHED_DATE,
    }),
    # crm_prd_info
    (CRM_PRODUCTS, find_duplicates, {"column": "prd_key"}),
    (CRM_PRODUCTS, find_nulls, {"column": "prd_cost"}),
    (CRM_PRODUCTS, find_non_positive, {"column": "prd_cost"}),
    (CRM_PRODUCTS, find_nulls, {"column": "prd_line"}),
    (CRM_PRODUCTS, find_not_uppercase, {"column": "prd_line"}),
    (CRM_PRODUCTS, find_invalid_dates, {
        "column": "prd_start_dt",
        "date_format": DASHED_DATE,
    }),
    (CRM_PRODUCTS, find_invalid_dates, {
        "column": "prd_end_dt",
        "date_format": DASHED_DATE,
    }),
    # crm_sales_details
    (CRM_SALES, find_nulls, {"column": "sls_sales"}),
    (CRM_SALES, find_nulls, {"column": "sls_price"}),
    (CRM_SALES, find_non_positive, {"column": "sls_sales"}),
    (CRM_SALES, find_non_positive, {"column": "sls_price"}),
    (CRM_SALES, find_invalid_dates, {
        "column": "sls_order_dt",
        "date_format": COMPACT_DATE,
    }),
    (CRM_SALES, find_invalid_dates, {
        "column": "sls_ship_dt",
        "date_format": COMPACT_DATE,
    }),
    (CRM_SALES, find_invalid_dates, {
        "column": "sls_due_dt",
        "date_format": COMPACT_DATE,
    }),
    (CRM_SALES, find_date_order_violations, {
        "earlier": "sls_order_dt",
        "later": "sls_ship_dt",
        "date_format": COMPACT_DATE,
    }),
    (CRM_SALES, find_date_order_violations, {
        "earlier": "sls_ship_dt",
        "later": "sls_due_dt",
        "date_format": COMPACT_DATE,
    }),
    (CRM_SALES, find_date_order_violations, {
        "earlier": "sls_order_dt",
        "later": "sls_due_dt",
        "date_format": COMPACT_DATE,
    }),
    (CRM_SALES, find_total_mismatches, {
        "total": "sls_sales",
        "quantity": "sls_quantity",
        "unit_price": "sls_price",
    }),
    # erp_cust_az12
    (ERP_CUSTOMERS, find_prefixed, {
        "column": "cid",
        "prefix": "NAS",
    }),
    (ERP_CUSTOMERS, find_future_dates, {
        "column": "bdate",
        "date_format": DASHED_DATE,
    }),
    (ERP_CUSTOMERS, find_invalid_values, {
        "column": "gen",
        "allowed": ["M", "F", "Male", "Female"],
    }),
    (ERP_CUSTOMERS, find_invalid_dates, {
        "column": "bdate",
        "date_format": DASHED_DATE,
    }),
    # erp_loc_a101
    (ERP_LOCATIONS, find_containing, {
        "column": "cid",
        "text": "-",
    }),
    (ERP_LOCATIONS, find_nulls, {"column": "cntry"}),
    # erp_px_cat_g1v2
    (ERP_CATEGORIES, find_untrimmed, {"column": "maintenance"}),
]
