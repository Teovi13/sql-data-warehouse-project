"""Source configuration: which CSV file feeds each Bronze table."""

from pathlib import Path

# Repository root: the folder that contains ``ingestion/``. It is computed
# from this file's location, so the code works from any working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
CRM_DIR = DATASETS_DIR / "source_crm"
ERP_DIR = DATASETS_DIR / "source_erp"

# Bronze table name -> source CSV file.
SOURCES = {
    "bronze.crm_cust_info": CRM_DIR / "cust_info.csv",
    "bronze.crm_prd_info": CRM_DIR / "prd_info.csv",
    "bronze.crm_sales_details": CRM_DIR / "sales_details.csv",
    "bronze.erp_cust_az12": ERP_DIR / "CUST_AZ12.csv",
    "bronze.erp_loc_a101": ERP_DIR / "LOC_A101.csv",
    "bronze.erp_px_cat_g1v2": ERP_DIR / "PX_CAT_G1V2.csv",
}
