{#
    Purpose:
        Birthdates must fall between 1924-01-01 and the reference date (var
        reference_date, the same one the Silver model uses).
#}

select
    cid,
    bdate
from {{ ref('erp_cust_az12') }}
where bdate < '1924-01-01'
   or bdate > cast('{{ var("reference_date") }}' as date)
