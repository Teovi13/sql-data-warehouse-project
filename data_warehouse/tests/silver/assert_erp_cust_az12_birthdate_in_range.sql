{#
    Purpose:
        Birthdates must fall between 1924-01-01 and today. Depends on the run
        date, like the Silver model it checks.
#}

select
    cid,
    bdate
from {{ ref('erp_cust_az12') }}
where bdate < '1924-01-01'
   or bdate > getdate()
