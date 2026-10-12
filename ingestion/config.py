"""Source configuration: which CSV file feeds each Bronze table."""

from pathlib import Path

# Repository root: the folder that contains ``ingestion/``. It is computed
# from this file's location, so the code works from any working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
CRM_DIR = DATASETS_DIR / "source_crm"
ERP_DIR = DATASETS_DIR / "source_erp"
COMPACT_DATE = "%Y%m%d"
CRM_CUSTOMERS = "bronze.crm_cust_info"
CRM_PRODUCTS = "bronze.crm_prd_info"
CRM_SALES = "bronze.crm_sales_details"
DASHED_DATE = "%Y-%m-%d"
ERP_CUSTOMERS = "bronze.erp_cust_az12"
ERP_LOCATIONS = "bronze.erp_loc_a101"
ERP_CATEGORIES = "bronze.erp_px_cat_g1v2"

# Bronze table name -> source CSV file.
SOURCES = {
    CRM_CUSTOMERS: CRM_DIR / "cust_info.csv",
    CRM_PRODUCTS: CRM_DIR / "prd_info.csv",
    CRM_SALES: CRM_DIR / "sales_details.csv",
    ERP_CUSTOMERS: ERP_DIR / "CUST_AZ12.csv",
    ERP_LOCATIONS: ERP_DIR / "LOC_A101.csv",
    ERP_CATEGORIES: ERP_DIR / "PX_CAT_G1V2.csv",
}
