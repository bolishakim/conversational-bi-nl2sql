"""
Common JOIN paths and query templates
Phase 3: Query Templates
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class JoinPath:
    """Represents a common JOIN path between tables"""
    name: str
    description: str
    sql_template: str
    tables_involved: List[str]
    use_cases: List[str]


# ============================================================================
# COMMON JOIN PATHS (10-15 patterns)
# ============================================================================

JOIN_PATHS = {
    # PATH 1: SALES → SALESPERSON → EMPLOYEE → PERSON
    "sales_to_salesperson": JoinPath(
        name="Sales to Salesperson (HR)",
        description="Connect sales orders to salesperson details including employee and person info",
        sql_template="""
            sales.salesorderheader soh
            JOIN sales.salesperson sp ON soh.salespersonid = sp.businessentityid
            JOIN humanresources.employee e ON sp.businessentityid = e.businessentityid
            JOIN person.person p ON e.businessentityid = p.businessentityid
        """,
        tables_involved=[
            "sales.salesorderheader",
            "sales.salesperson",
            "humanresources.employee",
            "person.person"
        ],
        use_cases=[
            "salesperson performance analysis",
            "employee sales metrics",
            "sales by employee demographics"
        ]
    ),

    # PATH 2: SALES → PRODUCT → CATEGORY
    "sales_to_product": JoinPath(
        name="Sales to Product Category",
        description="Connect sales line items to product details and categories",
        sql_template="""
            sales.salesorderheader soh
            JOIN sales.salesorderdetail sod ON soh.salesorderid = sod.salesorderid
            JOIN production.product pr ON sod.productid = pr.productid
            JOIN production.productsubcategory psc ON pr.productsubcategoryid = psc.productsubcategoryid
            JOIN production.productcategory pc ON psc.productcategoryid = pc.productcategoryid
        """,
        tables_involved=[
            "sales.salesorderheader",
            "sales.salesorderdetail",
            "production.product",
            "production.productsubcategory",
            "production.productcategory"
        ],
        use_cases=[
            "product sales analysis",
            "category performance",
            "product revenue breakdown"
        ]
    ),

    # PATH 3: SALES → CUSTOMER → PERSON
    "sales_to_customer": JoinPath(
        name="Sales to Customer",
        description="Connect sales orders to customer personal details",
        sql_template="""
            sales.salesorderheader soh
            JOIN sales.customer c ON soh.customerid = c.customerid
            JOIN person.person p ON c.personid = p.businessentityid
        """,
        tables_involved=[
            "sales.salesorderheader",
            "sales.customer",
            "person.person"
        ],
        use_cases=[
            "customer purchase patterns",
            "customer demographics analysis",
            "customer segmentation"
        ]
    ),

    # PATH 4: SALES → TERRITORY
    "sales_to_territory": JoinPath(
        name="Sales to Territory",
        description="Connect sales to geographic territories",
        sql_template="""
            sales.salesorderheader soh
            JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
        """,
        tables_involved=[
            "sales.salesorderheader",
            "sales.salesterritory"
        ],
        use_cases=[
            "territorial sales analysis",
            "geographic performance",
            "regional trends"
        ]
    ),

    # PATH 5: EMPLOYEE → DEPARTMENT
    "employee_to_department": JoinPath(
        name="Employee to Department",
        description="Connect employees to their current department",
        sql_template="""
            humanresources.employee e
            JOIN person.person p ON e.businessentityid = p.businessentityid
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.department d ON edh.departmentid = d.departmentid
            WHERE edh.enddate IS NULL  -- Current department only
        """,
        tables_involved=[
            "humanresources.employee",
            "person.person",
            "humanresources.employeedepartmenthistory",
            "humanresources.department"
        ],
        use_cases=[
            "organizational structure",
            "department headcount",
            "employee distribution"
        ]
    ),

    # PATH 6: PRODUCT → VENDOR (Purchasing)
    "product_to_vendor": JoinPath(
        name="Product to Vendor",
        description="Connect products to their suppliers",
        sql_template="""
            production.product pr
            JOIN purchasing.productvendor pv ON pr.productid = pv.productid
            JOIN purchasing.vendor v ON pv.businessentityid = v.businessentityid
        """,
        tables_involved=[
            "production.product",
            "purchasing.productvendor",
            "purchasing.vendor"
        ],
        use_cases=[
            "supplier product catalog",
            "vendor analysis",
            "product sourcing"
        ]
    ),

    # PATH 7: PRODUCT → INVENTORY
    "product_to_inventory": JoinPath(
        name="Product to Inventory",
        description="Connect products to current inventory levels",
        sql_template="""
            production.product pr
            LEFT JOIN production.productinventory pi ON pr.productid = pi.productid
        """,
        tables_involved=[
            "production.product",
            "production.productinventory"
        ],
        use_cases=[
            "inventory levels",
            "stock availability",
            "out-of-stock analysis"
        ]
    ),

    # PATH 8: PURCHASE ORDERS → VENDOR → EMPLOYEE
    "purchase_to_vendor": JoinPath(
        name="Purchase Orders to Vendor",
        description="Connect purchase orders to vendor and purchasing employee",
        sql_template="""
            purchasing.purchaseorderheader poh
            JOIN purchasing.vendor v ON poh.vendorid = v.businessentityid
            JOIN humanresources.employee e ON poh.employeeid = e.businessentityid
            JOIN person.person p ON e.businessentityid = p.businessentityid
        """,
        tables_involved=[
            "purchasing.purchaseorderheader",
            "purchasing.vendor",
            "humanresources.employee",
            "person.person"
        ],
        use_cases=[
            "procurement analysis",
            "vendor orders",
            "purchasing employee activity"
        ]
    ),

    # PATH 9: WORKORDER → PRODUCT
    "workorder_to_product": JoinPath(
        name="Work Orders to Product",
        description="Connect manufacturing work orders to products",
        sql_template="""
            production.workorder wo
            JOIN production.product pr ON wo.productid = pr.productid
            JOIN production.productsubcategory psc ON pr.productsubcategoryid = psc.productsubcategoryid
            JOIN production.productcategory pc ON psc.productcategoryid = pc.productcategoryid
        """,
        tables_involved=[
            "production.workorder",
            "production.product",
            "production.productsubcategory",
            "production.productcategory"
        ],
        use_cases=[
            "production volume",
            "manufacturing efficiency",
            "product production analysis"
        ]
    ),

    # PATH 10: EMPLOYEE → PAY HISTORY
    "employee_to_pay": JoinPath(
        name="Employee to Pay History",
        description="Connect employees to salary information",
        sql_template="""
            humanresources.employee e
            JOIN person.person p ON e.businessentityid = p.businessentityid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
        """,
        tables_involved=[
            "humanresources.employee",
            "person.person",
            "humanresources.employeepayhistory"
        ],
        use_cases=[
            "compensation analysis",
            "salary history",
            "pay rate trends"
        ]
    ),

    # PATH 11: SALES → ADDRESS (Geographic)
    "sales_to_address": JoinPath(
        name="Sales to Address",
        description="Connect sales to billing/shipping addresses",
        sql_template="""
            sales.salesorderheader soh
            JOIN person.address a ON soh.billtoaddressid = a.addressid
            JOIN person.stateprovince sp ON a.stateprovinceid = sp.stateprovinceid
        """,
        tables_involved=[
            "sales.salesorderheader",
            "person.address",
            "person.stateprovince"
        ],
        use_cases=[
            "geographic sales distribution",
            "sales by state/city",
            "regional analysis"
        ]
    ),

    # PATH 12: COMPREHENSIVE SALES ANALYSIS
    "comprehensive_sales": JoinPath(
        name="Comprehensive Sales Analysis",
        description="Full sales analysis with customer, product, salesperson, and territory",
        sql_template="""
            sales.salesorderheader soh
            -- Customer info
            JOIN sales.customer c ON soh.customerid = c.customerid
            LEFT JOIN person.person cust_person ON c.personid = cust_person.businessentityid
            -- Salesperson info
            LEFT JOIN sales.salesperson sp ON soh.salespersonid = sp.businessentityid
            LEFT JOIN humanresources.employee e ON sp.businessentityid = e.businessentityid
            LEFT JOIN person.person emp_person ON e.businessentityid = emp_person.businessentityid
            -- Territory info
            LEFT JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
            -- Product details
            JOIN sales.salesorderdetail sod ON soh.salesorderid = sod.salesorderid
            JOIN production.product pr ON sod.productid = pr.productid
            LEFT JOIN production.productsubcategory psc ON pr.productsubcategoryid = psc.productsubcategoryid
            LEFT JOIN production.productcategory pc ON psc.productcategoryid = pc.productcategoryid
        """,
        tables_involved=[
            "sales.salesorderheader", "sales.salesorderdetail",
            "sales.customer", "sales.salesperson", "sales.salesterritory",
            "production.product", "production.productsubcategory", "production.productcategory",
            "humanresources.employee", "person.person"
        ],
        use_cases=[
            "comprehensive sales analysis",
            "multi-dimensional analysis",
            "cross-department insights"
        ]
    ),

    # PATH 13: SALES TO QUOTA PERFORMANCE (NEW - Phase 3)
    "sales_to_quota": JoinPath(
        name="Sales to Quota Performance",
        description="Connect sales performance to current quotas using quota history",
        sql_template="""
            -- Current quotas (using MAX quotadate for most recent)
            WITH current_quotas AS (
                SELECT
                    businessentityid,
                    salesquota
                FROM sales.salespersonquotahistory sq
                WHERE quotadate = (
                    SELECT MAX(quotadate)
                    FROM sales.salespersonquotahistory
                    WHERE businessentityid = sq.businessentityid
                )
            )
            SELECT
                sp.businessentityid,
                p.firstname || ' ' || p.lastname AS salesperson_name,
                st.name AS territory_name,
                cq.salesquota AS current_quota,
                SUM(soh.totaldue) AS actual_sales,
                ROUND((SUM(soh.totaldue) / cq.salesquota * 100)::numeric, 2) AS quota_attainment_pct
            FROM sales.salesperson sp
            JOIN sales.salesterritory st ON sp.territoryid = st.territoryid
            JOIN humanresources.employee e ON sp.businessentityid = e.businessentityid
            JOIN person.person p ON e.businessentityid = p.businessentityid
            JOIN current_quotas cq ON sp.businessentityid = cq.businessentityid
            LEFT JOIN sales.salesorderheader soh ON sp.businessentityid = soh.salespersonid
                AND EXTRACT(YEAR FROM soh.orderdate) = 2024
            GROUP BY sp.businessentityid, p.firstname, p.lastname, st.name, cq.salesquota
            ORDER BY quota_attainment_pct ASC
        """,
        tables_involved=[
            "sales.salesperson",
            "sales.salespersonquotahistory",
            "sales.salesorderheader",
            "sales.salesterritory",
            "humanresources.employee",
            "person.person"
        ],
        use_cases=[
            "quota attainment analysis",
            "salesperson performance vs target",
            "underperforming territory identification",
            "quota vs actual sales comparison"
        ]
    ),

    # PATH 14: EMPLOYEE PAY EQUITY ANALYSIS (NEW - Phase 3)
    "employee_pay_equity": JoinPath(
        name="Employee Pay Equity Analysis",
        description="Statistical analysis for pay equity using outlier detection (not grouping)",
        sql_template="""
            -- Calculate mean and standard deviation for each tenure group
            WITH employee_tenure AS (
                SELECT
                    e.businessentityid,
                    p.firstname || ' ' || p.lastname AS employee_name,
                    EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.hiredate)) AS years_tenure,
                    eph.rate AS current_rate
                FROM humanresources.employee e
                JOIN person.person p ON e.businessentityid = p.businessentityid
                JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
                WHERE eph.ratechangedate = (
                    SELECT MAX(ratechangedate)
                    FROM humanresources.employeepayhistory
                    WHERE businessentityid = e.businessentityid
                )
            ),
            pay_stats AS (
                SELECT
                    AVG(current_rate) AS mean_rate,
                    STDDEV(current_rate) AS stddev_rate
                FROM employee_tenure
            )
            -- Identify outliers: >2 standard deviations from mean
            SELECT
                et.employee_name,
                et.years_tenure,
                et.current_rate,
                ps.mean_rate,
                ps.stddev_rate,
                ROUND(((et.current_rate - ps.mean_rate) / NULLIF(ps.stddev_rate, 0))::numeric, 2) AS z_score,
                CASE
                    WHEN ABS((et.current_rate - ps.mean_rate) / NULLIF(ps.stddev_rate, 0)) > 2
                    THEN 'Outlier'
                    ELSE 'Normal'
                END AS pay_status
            FROM employee_tenure et, pay_stats ps
            WHERE ABS((et.current_rate - ps.mean_rate) / NULLIF(ps.stddev_rate, 0)) > 2
            ORDER BY z_score DESC
        """,
        tables_involved=[
            "humanresources.employee",
            "humanresources.employeepayhistory",
            "person.person"
        ],
        use_cases=[
            "pay equity analysis",
            "compensation disparity detection",
            "outlier identification in salaries",
            "statistical pay fairness analysis",
            "controlling for tenure effects"
        ]
    ),
}


# ============================================================================
# QUERY TEMPLATES FOR COMMON PATTERNS
# ============================================================================

@dataclass
class QueryTemplate:
    """Represents a reusable query template"""
    name: str
    description: str
    sql_template: str
    variables: List[str]
    example_question: str


QUERY_TEMPLATES = {
    # TEMPLATE 1: Time-based aggregation
    "time_aggregation": QueryTemplate(
        name="Time-based Aggregation",
        description="Aggregate metrics by time period (day, month, quarter, year)",
        sql_template="""
            SELECT
                EXTRACT({time_unit} FROM {date_column}) as period,
                COUNT(DISTINCT {id_column}) as count,
                ROUND(SUM({amount_column})::numeric, 2) as total
            FROM {table_name}
            WHERE {date_column} >= '{start_date}'
              AND {date_column} <= '{end_date}'
            GROUP BY 1
            ORDER BY 1;
        """,
        variables=["time_unit", "date_column", "id_column", "amount_column", "table_name", "start_date", "end_date"],
        example_question="What are sales by quarter for 2024?"
    ),

    # TEMPLATE 2: Top N ranking
    "top_n_ranking": QueryTemplate(
        name="Top N Ranking",
        description="Find top N items by a metric",
        sql_template="""
            SELECT
                {dimension_column} as item,
                COUNT(DISTINCT {id_column}) as count,
                ROUND(SUM({metric_column})::numeric, 2) as total
            FROM {table_name}
            {join_clause}
            WHERE {filter_clause}
            GROUP BY 1
            ORDER BY total DESC
            LIMIT {n};
        """,
        variables=["dimension_column", "id_column", "metric_column", "table_name", "join_clause", "filter_clause", "n"],
        example_question="What are the top 10 products by revenue?"
    ),

    # TEMPLATE 3: Year-over-year comparison
    "yoy_comparison": QueryTemplate(
        name="Year-over-Year Comparison",
        description="Compare metrics between years",
        sql_template="""
            WITH yearly_data AS (
                SELECT
                    EXTRACT(YEAR FROM {date_column}) as year,
                    {dimension_column} as dimension,
                    ROUND(SUM({metric_column})::numeric, 2) as total
                FROM {table_name}
                {join_clause}
                WHERE {filter_clause}
                GROUP BY 1, 2
            )
            SELECT
                dimension,
                MAX(CASE WHEN year = {current_year} THEN total END) as current_year,
                MAX(CASE WHEN year = {previous_year} THEN total END) as previous_year,
                ROUND(
                    ((MAX(CASE WHEN year = {current_year} THEN total END) -
                      MAX(CASE WHEN year = {previous_year} THEN total END)) /
                     NULLIF(MAX(CASE WHEN year = {previous_year} THEN total END), 0) * 100)::numeric,
                    2
                ) as yoy_growth_pct
            FROM yearly_data
            GROUP BY dimension
            ORDER BY current_year DESC NULLS LAST;
        """,
        variables=["date_column", "dimension_column", "metric_column", "table_name", "join_clause", "filter_clause", "current_year", "previous_year"],
        example_question="Compare sales by territory for 2024 vs 2023"
    ),

    # TEMPLATE 4: Percentage breakdown
    "percentage_breakdown": QueryTemplate(
        name="Percentage Breakdown",
        description="Break down totals into percentages",
        sql_template="""
            WITH totals AS (
                SELECT
                    {dimension_column} as category,
                    ROUND(SUM({metric_column})::numeric, 2) as amount
                FROM {table_name}
                {join_clause}
                WHERE {filter_clause}
                GROUP BY 1
            ),
            grand_total AS (
                SELECT SUM(amount) as total FROM totals
            )
            SELECT
                t.category,
                t.amount,
                ROUND((t.amount / gt.total * 100)::numeric, 2) as percentage
            FROM totals t, grand_total gt
            ORDER BY t.amount DESC;
        """,
        variables=["dimension_column", "metric_column", "table_name", "join_clause", "filter_clause"],
        example_question="What percentage of sales comes from each product category?"
    ),

    # TEMPLATE 5: Moving average
    "moving_average": QueryTemplate(
        name="Moving Average",
        description="Calculate moving average over time",
        sql_template="""
            WITH daily_data AS (
                SELECT
                    {date_column}::date as date,
                    ROUND(SUM({metric_column})::numeric, 2) as daily_total
                FROM {table_name}
                WHERE {filter_clause}
                GROUP BY 1
            )
            SELECT
                date,
                daily_total,
                ROUND(AVG(daily_total) OVER (
                    ORDER BY date
                    ROWS BETWEEN {window_size} PRECEDING AND CURRENT ROW
                )::numeric, 2) as moving_avg
            FROM daily_data
            ORDER BY date;
        """,
        variables=["date_column", "metric_column", "table_name", "filter_clause", "window_size"],
        example_question="Show sales with 7-day moving average"
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_join_path(path_name: str) -> JoinPath:
    """Get a specific JOIN path by name"""
    if path_name not in JOIN_PATHS:
        raise ValueError(f"JOIN path '{path_name}' not found")
    return JOIN_PATHS[path_name]


def get_relevant_join_paths(tables: List[str]) -> List[JoinPath]:
    """Get JOIN paths that involve the given tables"""
    relevant_paths = []
    for path_name, path in JOIN_PATHS.items():
        if any(table in path.tables_involved for table in tables):
            relevant_paths.append(path)
    return relevant_paths


def get_query_template(template_name: str) -> QueryTemplate:
    """Get a specific query template by name"""
    if template_name not in QUERY_TEMPLATES:
        raise ValueError(f"Query template '{template_name}' not found")
    return QUERY_TEMPLATES[template_name]


def list_all_join_paths() -> Dict[str, str]:
    """List all available JOIN paths with descriptions"""
    return {name: path.description for name, path in JOIN_PATHS.items()}


def list_all_templates() -> Dict[str, str]:
    """List all available query templates with descriptions"""
    return {name: template.description for name, template in QUERY_TEMPLATES.items()}
