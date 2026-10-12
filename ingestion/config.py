"""Configuration: table names, date formats, CSV sources and column types."""

from pathlib import Path

# Repository root: the folder that contains ``ingestion/``. It is computed
# from this file's location, so the code works from any working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
CRM_DIR = DATASETS_DIR / "source_crm"
ERP_DIR = DATASETS_DIR / "source_erp"

# Bronze table names and CSV date formats shared by several modules.
COMPACT_DATE = "%Y%m%d"
CRM_CUSTOMERS = "bronze.crm_cust_info"
CRM_PRODUCTS = "bronze.crm_prd_info"
CRM_SALES = "bronze.crm_sales_details"
DASHED_DATE = "%Y-%m-%d"
ERP_CATEGORIES = "bronze.erp_px_cat_g1v2"
ERP_CUSTOMERS = "bronze.erp_cust_az12"
ERP_LOCATIONS = "bronze.erp_loc_a101"

# Bronze table name -> source CSV file.
SOURCES = {
    CRM_CUSTOMERS: CRM_DIR / "cust_info.csv",
    CRM_PRODUCTS: CRM_DIR / "prd_info.csv",
    CRM_SALES: CRM_DIR / "sales_details.csv",
    ERP_CUSTOMERS: ERP_DIR / "CUST_AZ12.csv",
    ERP_LOCATIONS: ERP_DIR / "LOC_A101.csv",
    ERP_CATEGORIES: ERP_DIR / "PX_CAT_G1V2.csv",
}

# Bronze table name -> column types, following the destination DDL. "integer"
# and "text" list column names; "date" maps each date column to the format
# used in its CSV. Every CSV column belongs to exactly one of the three.
COLUMN_TYPES = {
    CRM_CUSTOMERS: {
        "integer": ["cst_id"],
        "date": {"cst_create_date": DASHED_DATE},
        "text": ["cst_key",
                 "cst_firstname",
                 "cst_lastname",
                 "cst_marital_status",
                 "cst_gndr",
                 ],
    },
    CRM_PRODUCTS: {
        "integer": ["prd_id", "prd_cost"],
        "date": {"prd_start_dt": DASHED_DATE, "prd_end_dt": DASHED_DATE},
        "text": ["prd_key", "prd_nm", "prd_line"],
    },
    CRM_SALES: {
        "integer": ["sls_cust_id",
                    "sls_order_dt",
                    "sls_ship_dt",
                    "sls_sales",
                    "sls_quantity",
                    "sls_price",
                    ],
        "date": {"sls_due_dt": COMPACT_DATE},
        "text": ["sls_ord_num", "sls_prd_key"],
    },
    ERP_CUSTOMERS: {
        "integer": [],
        "date": {"bdate": DASHED_DATE},
        "text": ["cid", "gen"],
    },
    ERP_LOCATIONS: {
        "integer": [],
        "date": {},
        "text": ["cid", "cntry"],
    },
    ERP_CATEGORIES: {
        "integer": [],
        "date": {},
        "text": ["id", "cat", "subcat", "maintenance"],
    },
}
