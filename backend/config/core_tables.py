"""
Core table definitions for RAG system
Based on analysis in DATABASE_ANALYSIS_AND_STRATEGY.md
"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class TableMetadata:
    """Metadata for a single table"""
    schema: str
    table: str
    description: str
    business_terms: List[str]
    common_questions: List[str]
    key_columns: Dict[str, str]
    sample_values: Dict[str, List[str]]
    row_count: int
    tier: int  # 1=Essential, 2=Important, 3=Nice-to-have

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.table}"


# ============================================================================
# TIER 1: ESSENTIAL TABLES (12 tables - 70% of queries)
# ============================================================================

CORE_TABLES = [
    # SALES DEPARTMENT (5 tables)
    TableMetadata(
        schema="sales",
        table="salesorderheader",
        description="Main sales transaction table containing every customer order with dates, amounts, salesperson, territory, and customer info. This is the CENTRAL FACT TABLE for all sales analytics.",
        business_terms=[
            "sales", "orders", "revenue", "transactions", "purchases",
            "sales amount", "order date", "customer orders", "sales performance"
        ],
        common_questions=[
            "total sales by period",
            "sales trends over time",
            "revenue by territory",
            "quarterly sales comparison",
            "sales by salesperson",
            "customer purchase history"
        ],
        key_columns={
            "salesorderid": "Primary key - unique order identifier",
            "revisionnumber": "Order revision number",
            "orderdate": "Date when order was placed - use for time-based analysis",
            "duedate": "Expected delivery date",
            "shipdate": "Actual ship date (NULL if not shipped yet)",
            "status": "Order status (1=In process, 2=Approved, 3=Backordered, 4=Rejected, 5=Shipped, 6=Cancelled)",
            "onlineorderflag": "True if online order, False if sales rep order",
            "purchaseordernumber": "Customer PO number",
            "accountnumber": "Customer account number",
            "customerid": "Foreign key to sales.customer - join for customer analysis",
            "salespersonid": "Foreign key to sales.salesperson - join for salesperson analysis (NULL for online)",
            "territoryid": "Foreign key to sales.salesterritory - join for geographic analysis",
            "billtoaddressid": "Billing address FK",
            "shiptoaddressid": "Shipping address FK",
            "shipmethodid": "Shipping method FK",
            "creditcardid": "Credit card FK (NULL if not CC payment)",
            "currencyrateid": "Currency rate FK (NULL if USD)",
            "subtotal": "Order subtotal before tax",
            "taxamt": "Tax amount",
            "freight": "Shipping/freight cost",
            "totaldue": "Total amount due (subtotal + tax + freight)",
            "comment": "Order comments",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "orderdate": ["2024-07-15", "2024-08-22", "2024-09-10"],
            "totaldue": ["1234.56", "5678.90", "999.99"]
        },
        row_count=31465,
        tier=1
    ),

    TableMetadata(
        schema="sales",
        table="salesorderdetail",
        description="Line items for each sales order. Contains product details, quantities, and prices for every item in an order. Join with salesorderheader for order context. IMPORTANT: This table does NOT have a 'linetotal' column - calculate revenue as: orderqty * unitprice * (1 - unitpricediscount)",
        business_terms=[
            "line items", "order details", "products sold", "order quantity",
            "product revenue", "item-level sales", "product performance"
        ],
        common_questions=[
            "what products were sold",
            "top selling products",
            "product revenue breakdown",
            "items per order",
            "product sales volume"
        ],
        key_columns={
            "salesorderid": "Foreign key to salesorderheader - links to order",
            "salesorderdetailid": "Primary key - unique line item identifier",
            "productid": "Foreign key to production.product - which product was sold",
            "orderqty": "Quantity ordered - use for volume analysis",
            "unitprice": "Price per unit",
            "unitpricediscount": "Discount AMOUNT per unit (not percentage) - subtract from unitprice",
            "specialofferid": "Foreign key to special offer",
            "carriertrackingnumber": "Shipping tracking number",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "orderqty": ["1", "5", "10"],
            "unitprice": ["49.99", "199.99", "1499.99"],
            "unitpricediscount": ["0.0", "0.05", "0.15"]
        },
        row_count=121317,
        tier=1
    ),

    TableMetadata(
        schema="sales",
        table="customer",
        description="Customer master records. Links to person table for individual customers or store table for business customers.",
        business_terms=[
            "customers", "buyers", "clients", "customer accounts",
            "customer segmentation", "customer base"
        ],
        common_questions=[
            "customer count",
            "customer segmentation",
            "customer purchase patterns",
            "top customers by revenue",
            "customer retention"
        ],
        key_columns={
            "customerid": "Primary key - unique customer identifier",
            "personid": "Foreign key to person.person - for individual customers",
            "storeid": "Foreign key to sales.store - for business customers",
            "territoryid": "Foreign key to sales.salesterritory - customer's territory"
        },
        sample_values={},
        row_count=19820,
        tier=1
    ),

    TableMetadata(
        schema="sales",
        table="salesperson",
        description="Sales representatives who process orders. Links to humanresources.employee for employee details.",
        business_terms=[
            "salespeople", "sales reps", "sales representatives", "account managers",
            "sales team", "sales force", "sales staff"
        ],
        common_questions=[
            "salesperson performance",
            "top performing salespeople",
            "sales by salesperson",
            "salesperson quotas",
            "sales team analysis"
        ],
        key_columns={
            "businessentityid": "Primary key and foreign key to humanresources.employee",
            "territoryid": "Foreign key to sales.salesterritory - salesperson's territory",
            "salesquota": "DEPRECATED - Static quota snapshot (may be outdated). DO NOT USE for quota analysis - use sales.salespersonquotahistory instead",
            "bonus": "Bonus earned",
            "commissionpct": "Commission percentage"
        },
        sample_values={},
        row_count=17,
        tier=1
    ),

    TableMetadata(
        schema="sales",
        table="salesterritory",
        description="Geographic sales territories (regions). Contains territory names and country information.",
        business_terms=[
            "territories", "regions", "geographic areas", "sales regions",
            "market segments", "geographic segmentation"
        ],
        common_questions=[
            "sales by territory",
            "territory performance",
            "regional analysis",
            "top performing territories",
            "geographic trends"
        ],
        key_columns={
            "territoryid": "Primary key - unique territory identifier",
            "name": "Territory name (e.g., 'Northeast', 'Southwest')",
            "countryregioncode": "ISO country code",
            "group": "Geographic grouping (North America, Europe, Pacific)",
            "salesytd": "Year-to-date sales",
            "saleslastyear": "Last year total sales",
            "costytd": "Year-to-date costs",
            "costlastyear": "Last year total costs",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "name": ["Northeast", "Southwest", "Canada", "France"],
            "group": ["North America", "Europe", "Pacific"]
        },
        row_count=10,
        tier=1
    ),

    # PRODUCTION DEPARTMENT (4 tables)
    TableMetadata(
        schema="production",
        table="product",
        description="Product catalog with all sellable products. Contains product names, categories, prices, and specifications.",
        business_terms=[
            "products", "items", "catalog", "SKU", "product line",
            "merchandise", "inventory items", "product catalog"
        ],
        common_questions=[
            "product list",
            "product categories",
            "product prices",
            "product details",
            "available products"
        ],
        key_columns={
            "productid": "Primary key - unique product identifier",
            "name": "Product name",
            "productnumber": "Product SKU/number",
            "makeflag": "True if manufactured in-house, False if purchased",
            "finishedgoodsflag": "True if sellable product",
            "color": "Product color",
            "safetystocklevel": "Minimum inventory quantity",
            "reorderpoint": "Inventory level that triggers reorder",
            "standardcost": "Standard cost",
            "listprice": "Selling price",
            "size": "Product size",
            "sizeunitmeasurecode": "Unit of measure for size",
            "weight": "Product weight",
            "weightunitmeasurecode": "Unit of measure for weight",
            "daystomanufacture": "Days to manufacture",
            "productline": "Product line (R=Road, M=Mountain, T=Touring, S=Standard)",
            "class": "Product class (H=High, M=Medium, L=Low)",
            "style": "Product style (W=Womens, M=Mens, U=Universal)",
            "productsubcategoryid": "FK to subcategory",
            "productmodelid": "FK to product model",
            "sellstartdate": "Date product available for sale",
            "sellenddate": "Date product no longer for sale",
            "discontinueddate": "Date product was discontinued",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "name": ["Mountain-200 Black, 42", "Road-650 Red, 58", "Touring-1000 Blue, 60"],
            "listprice": ["2294.99", "782.99", "2384.07"]
        },
        row_count=504,
        tier=1
    ),

    TableMetadata(
        schema="production",
        table="productsubcategory",
        description="Product subcategories (e.g., 'Mountain Bikes', 'Road Bikes'). Groups products into subcategories.",
        business_terms=[
            "subcategories", "product types", "product groups",
            "product classification", "product segments"
        ],
        common_questions=[
            "product subcategories",
            "sales by subcategory",
            "subcategory performance",
            "product grouping"
        ],
        key_columns={
            "productsubcategoryid": "Primary key",
            "name": "Subcategory name",
            "productcategoryid": "Foreign key to productcategory"
        },
        sample_values={
            "name": ["Mountain Bikes", "Road Bikes", "Touring Bikes", "Helmets", "Jerseys"]
        },
        row_count=37,
        tier=1
    ),

    TableMetadata(
        schema="production",
        table="productcategory",
        description="Top-level product categories (Bikes, Components, Clothing, Accessories). Highest level of product grouping.",
        business_terms=[
            "categories", "product categories", "top-level categories",
            "product divisions", "main categories"
        ],
        common_questions=[
            "sales by category",
            "category performance",
            "revenue by category",
            "category trends"
        ],
        key_columns={
            "productcategoryid": "Primary key",
            "name": "Category name"
        },
        sample_values={
            "name": ["Bikes", "Components", "Clothing", "Accessories"]
        },
        row_count=4,
        tier=1
    ),

    TableMetadata(
        schema="production",
        table="productinventory",
        description="Current inventory levels for products at different locations. Shows available stock.",
        business_terms=[
            "inventory", "stock", "available quantity", "warehouse inventory",
            "stock levels", "inventory on hand"
        ],
        common_questions=[
            "inventory levels",
            "stock availability",
            "out of stock products",
            "inventory by location"
        ],
        key_columns={
            "productid": "Foreign key to product",
            "locationid": "Foreign key to location - warehouse location",
            "quantity": "Quantity in stock",
            "shelf": "Shelf location",
            "bin": "Bin location"
        },
        sample_values={
            "quantity": ["10", "50", "100", "0"]
        },
        row_count=1069,
        tier=1
    ),

    # HR DEPARTMENT (2 tables)
    TableMetadata(
        schema="humanresources",
        table="employee",
        description="Employee master records with job titles, hire dates, and organizational hierarchy. Links to person table for personal details.",
        business_terms=[
            "employees", "staff", "workforce", "personnel", "team members",
            "human resources", "organizational chart"
        ],
        common_questions=[
            "employee count",
            "employees by department",
            "employee hire dates",
            "organizational structure",
            "employee details"
        ],
        key_columns={
            "businessentityid": "Primary key and foreign key to person.person",
            "nationalidnumber": "National ID number (SSN)",
            "loginid": "Network login ID",
            "jobtitle": "Employee job title",
            "birthdate": "Employee birth date",
            "maritalstatus": "Marital status (S=Single, M=Married)",
            "gender": "Employee gender (M/F)",
            "hiredate": "Date employee was hired",
            "salariedflag": "True if salaried, False if hourly",
            "vacationhours": "Available vacation hours",
            "sickleavehours": "Available sick leave hours",
            "currentflag": "True if currently employed",
            "organizationnode": "Hierarchical position in org tree (NOTE: there is NO organizationlevel column)",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "jobtitle": ["Sales Representative", "Production Technician", "Marketing Manager"],
            "hiredate": ["2023-01-15", "2022-06-01", "2021-03-10"]
        },
        row_count=290,
        tier=1
    ),

    TableMetadata(
        schema="humanresources",
        table="department",
        description="Company departments (Sales, Production, Marketing, etc.). Organizational structure.",
        business_terms=[
            "departments", "divisions", "business units", "organizational units",
            "company departments", "org structure"
        ],
        common_questions=[
            "department list",
            "employees by department",
            "department structure",
            "organizational analysis"
        ],
        key_columns={
            "departmentid": "Primary key",
            "name": "Department name",
            "groupname": "Department group"
        },
        sample_values={
            "name": ["Sales", "Production", "Marketing", "Human Resources", "Finance"],
            "groupname": ["Sales and Marketing", "Manufacturing", "Executive General and Administration"]
        },
        row_count=16,
        tier=1
    ),

    # PERSON DEPARTMENT (1 table)
    TableMetadata(
        schema="person",
        table="person",
        description="Individual person records with names and demographics. Master table for all people (customers, employees, contacts).",
        business_terms=[
            "people", "individuals", "persons", "names", "contacts",
            "personal information", "demographics"
        ],
        common_questions=[
            "person details",
            "customer names",
            "employee names",
            "contact information"
        ],
        key_columns={
            "businessentityid": "Primary key",
            "persontype": "Person type (SC=Store Contact, IN=Individual, SP=Sales Person, EM=Employee, VC=Vendor Contact, GC=General Contact)",
            "namestyle": "Name format (0=Western, 1=Eastern)",
            "title": "Title (Mr., Ms., etc.)",
            "firstname": "First name",
            "middlename": "Middle name",
            "lastname": "Last name",
            "suffix": "Suffix (Jr., Sr., etc.)",
            "emailpromotion": "Email promo preference (0=No email, 1=From AW, 2=From AW and partners)",
            "additionalcontactinfo": "Additional contact XML",
            "demographics": "Demographics XML",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "firstname": ["John", "Sarah", "Michael"],
            "lastname": ["Smith", "Johnson", "Williams"]
        },
        row_count=19972,
        tier=1
    ),

    TableMetadata(
        schema="person",
        table="address",
        description="Street addresses for people and businesses. Geographic location data.",
        business_terms=[
            "addresses", "locations", "street addresses", "geographic data",
            "billing address", "shipping address"
        ],
        common_questions=[
            "customer locations",
            "addresses by state",
            "geographic distribution",
            "address details"
        ],
        key_columns={
            "addressid": "Primary key",
            "addressline1": "Street address line 1",
            "addressline2": "Street address line 2",
            "city": "City name",
            "stateprovinceid": "Foreign key to stateprovince",
            "postalcode": "ZIP/postal code"
        },
        sample_values={
            "city": ["Seattle", "New York", "Los Angeles", "Chicago"],
            "postalcode": ["98052", "10001", "90001"]
        },
        row_count=19614,
        tier=1
    ),
]


# ============================================================================
# TIER 2: IMPORTANT TABLES (8 tables - for deeper analysis)
# ============================================================================

IMPORTANT_TABLES = [
    TableMetadata(
        schema="purchasing",
        table="purchaseorderheader",
        description="Purchase orders from vendors/suppliers for products. Total order value = subtotal + taxamt + freight (no totaldue column exists). IMPORTANT: This table has shipdate (actual ship date) but NO duedate or expected_delivery_date columns. For on-time delivery analysis, use status column (4=Complete) or compare shipdate to orderdate.",
        business_terms=["purchase orders", "vendor orders", "procurement", "supplier orders"],
        common_questions=["purchase order status", "orders from vendors", "procurement history", "vendor performance"],
        key_columns={
            "purchaseorderid": "Primary key",
            "revisionnumber": "Version number of the order",
            "status": "Order status code (1=Pending, 2=Approved, 3=Rejected, 4=Complete)",
            "employeeid": "Foreign key to employee who created order",
            "vendorid": "Foreign key to vendor/supplier",
            "shipmethodid": "Foreign key to shipping method",
            "orderdate": "Date order was placed",
            "shipdate": "Actual ship date (when order was shipped) - NOTE: there is NO duedate column",
            "subtotal": "Pre-tax purchase subtotal",
            "taxamt": "Tax amount",
            "freight": "Shipping/freight cost",
            "modifieddate": "Last modification date"
        },
        sample_values={},
        row_count=4012,
        tier=2
    ),

    TableMetadata(
        schema="purchasing",
        table="vendor",
        description="Vendor/supplier master records. Companies that supply products to AdventureWorks. Join with purchasing.purchaseorderheader on vendorid = businessentityid for purchase order analysis. Join with purchasing.productvendor for vendor-product relationships. creditrating indicates vendor reliability (1=best, 5=worst).",
        business_terms=["vendors", "suppliers", "manufacturers", "partners"],
        common_questions=["vendor list", "vendor performance", "supplier details"],
        key_columns={
            "businessentityid": "Primary key (vendor ID)",
            "accountnumber": "Vendor account number",
            "name": "Vendor/supplier name",
            "creditrating": "Credit rating (1=Superior, 2=Excellent, 3=Above average, 4=Average, 5=Below average)",
            "preferredvendorstatus": "True if preferred vendor",
            "activeflag": "True if vendor is active",
            "purchasingwebserviceurl": "Vendor web service URL",
            "modifieddate": "Last modification date"
        },
        sample_values={},
        row_count=104,
        tier=2
    ),

    TableMetadata(
        schema="purchasing",
        table="productvendor",
        description="Product-vendor relationship. Which vendors supply which products. Join with purchasing.vendor on businessentityid for vendor info. Join with production.product on productid for product info. Use for vendor analysis: lead times, costs, order quantities.",
        business_terms=["product sources", "supplier products", "vendor products"],
        common_questions=["who supplies this product", "vendor product catalog", "vendor lead times"],
        key_columns={
            "productid": "FK to product",
            "businessentityid": "FK to vendor (vendor ID)",
            "averageleadtime": "Average lead time in days",
            "standardprice": "Standard purchase price",
            "lastreceiptcost": "Cost of last receipt",
            "lastreceiptdate": "Date of last receipt",
            "minorderqty": "Minimum order quantity",
            "maxorderqty": "Maximum order quantity",
            "onorderqty": "Quantity currently on order",
            "unitmeasurecode": "Unit of measure",
            "modifieddate": "Last modification date"
        },
        sample_values={},
        row_count=460,
        tier=2
    ),

    TableMetadata(
        schema="production",
        table="workorder",
        description="Manufacturing work orders. Production tracking.",
        business_terms=["work orders", "production orders", "manufacturing", "production tracking"],
        common_questions=["production volume", "manufacturing status", "work order details"],
        key_columns={
            "workorderid": "Primary key",
            "productid": "Foreign key to product being manufactured",
            "orderqty": "Quantity to produce",
            "startdate": "Production start date",
            "enddate": "Production end date"
        },
        sample_values={},
        row_count=72591,
        tier=2
    ),

    TableMetadata(
        schema="production",
        table="transactionhistory",
        description="Product transaction history. Tracks all product movements.",
        business_terms=["transactions", "product movements", "inventory transactions"],
        common_questions=["product transaction history", "inventory movements"],
        key_columns={
            "transactionid": "Primary key",
            "productid": "Foreign key to product",
            "transactiondate": "Date of transaction",
            "transactiontype": "Type (W=WorkOrder, S=Sales, P=Purchase)",
            "quantity": "Quantity moved"
        },
        sample_values={},
        row_count=113443,
        tier=2
    ),

    TableMetadata(
        schema="humanresources",
        table="employeepayhistory",
        description="Employee salary and pay rate history. Compensation tracking. IMPORTANT: This table does NOT have an 'enddate' column. It tracks pay changes over time using 'ratechangedate'. To get current compensation, use: WHERE ratechangedate = (SELECT MAX(ratechangedate) FROM employeepayhistory WHERE businessentityid = e.businessentityid)",
        business_terms=["salary", "pay", "compensation", "wages", "pay rate"],
        common_questions=["employee salaries", "pay history", "compensation analysis"],
        key_columns={
            "businessentityid": "Foreign key to employee - identifies which employee",
            "ratechangedate": "Date when this rate became effective - use MAX() to get current rate",
            "rate": "Hourly or salary rate - current compensation value",
            "payfrequency": "Pay frequency (1=Monthly, 2=Biweekly)",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "rate": ["15.00", "25.50", "42.00"],
            "payfrequency": ["1", "2"]
        },
        row_count=316,
        tier=2
    ),

    TableMetadata(
        schema="sales",
        table="creditcard",
        description="Credit card information for orders. Join with sales.salesorderheader on creditcardid. cardtype: Vista, SuperiorCard, ColonialVoice, Distinguish. Note: Card numbers are masked for security.",
        business_terms=["credit cards", "payment methods", "payment info"],
        common_questions=["payment methods used", "credit card types"],
        key_columns={
            "creditcardid": "Primary key",
            "cardtype": "Card type (Vista, SuperiorCard, ColonialVoice, Distinguish)",
            "cardnumber": "Credit card number (last 4 digits visible)",
            "expmonth": "Expiration month",
            "expyear": "Expiration year",
            "modifieddate": "Last modification date"
        },
        sample_values={},
        row_count=19118,
        tier=2
    ),

    TableMetadata(
        schema="sales",
        table="currencyrate",
        description="Currency exchange rates by date. Multi-currency support.",
        business_terms=["exchange rates", "currency conversion", "foreign exchange"],
        common_questions=["currency rates", "exchange rate history"],
        key_columns={
            "currencyrateid": "Primary key",
            "currencyratedate": "Date of rate",
            "fromcurrencycode": "Source currency",
            "tocurrencycode": "Target currency",
            "averagerate": "Exchange rate"
        },
        sample_values={},
        row_count=13532,
        tier=2
    ),

    TableMetadata(
        schema="sales",
        table="salespersonquotahistory",
        description="Historical sales quota tracking for salespeople. Records quota changes over time. CRITICAL: Use this table (NOT salesperson.salesquota) for quota analysis. To get current quota, use: WHERE quotadate = (SELECT MAX(quotadate) FROM salespersonquotahistory WHERE businessentityid = sp.businessentityid)",
        business_terms=[
            "sales quotas", "quota tracking", "quota history", "sales targets",
            "quota attainment", "quota performance", "sales goals", "quota changes",
            "underperforming", "quota vs actual", "meeting quota", "exceeding quota"
        ],
        common_questions=[
            "current sales quotas",
            "quota attainment by salesperson",
            "quota vs actual sales",
            "territory quota performance",
            "salespeople meeting quotas",
            "underperforming territories",
            "quota trends over time",
            "who is below quota",
            "quota achievement rate"
        ],
        key_columns={
            "businessentityid": "Foreign key to sales.salesperson - identifies which salesperson",
            "quotadate": "Effective date of this quota - use MAX() to get most recent quota",
            "salesquota": "Quota amount for this period - the actual quota value to compare against sales",
            "modifieddate": "Last modification date"
        },
        sample_values={
            "quotadate": ["2025-03-01", "2024-11-30", "2024-08-30", "2024-05-30"],
            "salesquota": ["187000", "84000", "116000", "263000"]
        },
        row_count=163,
        tier=2
    ),

    # ========================================================================
    # DATABASE VIEWS (Pre-computed JOINs for simplified queries)
    # ========================================================================

    # HUMAN RESOURCES VIEWS
    TableMetadata(
        schema="humanresources",
        table="vemployee",
        description="Complete employee view with 8 JOINs. Combines employee, person, contact, address, and department information into a single unified view. Use this view instead of manually joining employee + person + contact tables for employee queries.",
        business_terms=[
            "employee information", "employee details", "employee contact",
            "employee address", "employee phone", "employee email",
            "employee demographics", "employee full info", "staff directory"
        ],
        common_questions=[
            "employee names and contact info",
            "employee addresses and phone numbers",
            "employee email addresses",
            "complete employee directory",
            "employee demographics with location",
            "staff contact information"
        ],
        key_columns={
            "businessentityid": "Employee identifier",
            "firstname": "Employee first name",
            "lastname": "Employee last name",
            "jobtitle": "Current job title",
            "phonenumber": "Primary phone number",
            "emailaddress": "Email address",
            "addressline1": "Street address",
            "city": "City name",
            "stateprovincename": "State or province"
        },
        sample_values={
            "jobtitle": ["Chief Executive Officer", "Vice President of Engineering", "Engineering Manager"],
            "city": ["Bothell", "Seattle", "Redmond"]
        },
        row_count=290,
        tier=1
    ),

    TableMetadata(
        schema="humanresources",
        table="vemployeedepartment",
        description="Current employee department assignments with 3 JOINs. Shows employee name, department name, and group for all current assignments. Use this view for current department-related queries instead of joining employee + department + departmenthistory.",
        business_terms=[
            "employee department", "current department", "department assignment",
            "department roster", "who works in department", "department members",
            "org chart", "organizational structure", "team composition"
        ],
        common_questions=[
            "which employees are in which departments",
            "current department assignments",
            "who works in the sales department",
            "employees by department",
            "department headcount",
            "organizational breakdown"
        ],
        key_columns={
            "businessentityid": "Employee identifier",
            "firstname": "Employee first name",
            "lastname": "Employee last name",
            "jobtitle": "Current job title",
            "department": "Department name",
            "groupname": "Department group (e.g., Sales and Marketing, Executive General)"
        },
        sample_values={
            "department": ["Executive", "Engineering", "Tool Design", "Sales"],
            "groupname": ["Executive General and Administration", "Research and Development", "Sales and Marketing"]
        },
        row_count=290,
        tier=1
    ),

    TableMetadata(
        schema="humanresources",
        table="vemployeedepartmenthistory",
        description="Complete employee department history with 4 JOINs. Tracks all department assignments over time including start/end dates and shift information. Use for historical department analysis and employee movement tracking.",
        business_terms=[
            "department history", "department changes", "employee transfers",
            "department movements", "org changes", "employee transitions",
            "shift assignments", "historical assignments", "career progression"
        ],
        common_questions=[
            "employee department change history",
            "when did employee change departments",
            "previous department assignments",
            "department transfer timeline",
            "employee career moves",
            "shift assignment history"
        ],
        key_columns={
            "businessentityid": "Employee identifier",
            "firstname": "Employee first name",
            "lastname": "Employee last name",
            "department": "Department name",
            "groupname": "Department group",
            "startdate": "Assignment start date",
            "enddate": "Assignment end date (NULL = current)"
        },
        sample_values={
            "department": ["Executive", "Engineering", "Tool Design"],
            "shift": ["Day", "Evening", "Night"]
        },
        row_count=296,
        tier=2
    ),

    # SALES VIEWS
    TableMetadata(
        schema="sales",
        table="vsalesperson",
        description="Complete salesperson information with 10 JOINs. Combines salesperson, employee, person, contact, address, and territory data. Use this view for salesperson queries instead of manually joining multiple tables.",
        business_terms=[
            "salesperson info", "sales rep details", "salesperson contact",
            "salesperson territory", "sales team", "sales rep directory",
            "salesperson quota", "sales rep performance", "territory assignment"
        ],
        common_questions=[
            "salesperson names and territories",
            "sales rep contact information",
            "who covers which territory",
            "salesperson phone and email",
            "sales team directory",
            "territory assignments by rep"
        ],
        key_columns={
            "businessentityid": "Salesperson identifier",
            "firstname": "First name",
            "lastname": "Last name",
            "jobtitle": "Job title",
            "phonenumber": "Phone number",
            "emailaddress": "Email address",
            "territoryname": "Sales territory name",
            "countryregionname": "Territory country name",
            "territorygroup": "Territory group (e.g., North America, Europe, Pacific)",
            "salesquota": "Current sales quota",
            "salesytd": "Sales year-to-date",
            "saleslastyear": "Sales last year"
        },
        sample_values={
            "territoryname": ["Northwest", "Northeast", "Central", "Southwest", "Australia", "France"],
            "territorygroup": ["North America", "Europe", "Pacific"]
        },
        row_count=17,
        tier=1
    ),

    TableMetadata(
        schema="sales",
        table="vindividualcustomer",
        description="Individual customer details with 9 JOINs. Combines customer, person, contact, and address information for non-store customers. Use for individual customer demographic queries.",
        business_terms=[
            "individual customer", "customer demographics", "customer contact",
            "customer address", "personal customer", "retail customer",
            "customer phone", "customer email", "customer location"
        ],
        common_questions=[
            "individual customer contact info",
            "customer addresses and phone numbers",
            "customer demographics by location",
            "personal customer directory",
            "customer email addresses",
            "retail customer information"
        ],
        key_columns={
            "businessentityid": "Customer identifier",
            "firstname": "Customer first name",
            "lastname": "Customer last name",
            "phonenumber": "Primary phone number",
            "emailaddress": "Email address",
            "addressline1": "Street address",
            "city": "City name",
            "stateprovincename": "State or province",
            "countryregionname": "Country name"
        },
        sample_values={
            "city": ["Seattle", "Los Angeles", "New York", "Chicago"],
            "countryregionname": ["United States", "Canada", "United Kingdom"]
        },
        row_count=18484,
        tier=2
    ),

    # PURCHASING VIEWS
    TableMetadata(
        schema="purchasing",
        table="vvendorwithcontacts",
        description="Vendor contact information with 6 JOINs. Combines vendor, person, and contact data. Use for vendor contact and communication queries.",
        business_terms=[
            "vendor contacts", "supplier contacts", "vendor phone",
            "vendor email", "vendor contact person", "supplier communication",
            "vendor directory", "supplier information"
        ],
        common_questions=[
            "vendor contact information",
            "how to contact vendors",
            "vendor phone numbers and emails",
            "supplier contact details",
            "vendor contact persons",
            "vendor communication info"
        ],
        key_columns={
            "businessentityid": "Vendor identifier",
            "name": "Vendor company name",
            "contacttype": "Type of contact (e.g., Purchasing Agent, Owner)",
            "firstname": "Contact person first name",
            "lastname": "Contact person last name",
            "phonenumber": "Contact phone number",
            "emailaddress": "Contact email address"
        },
        sample_values={
            "contacttype": ["Purchasing Agent", "Owner/Marketing Assistant", "Purchasing Manager"],
            "name": ["Australia Bike Retailer", "Allenson Cycles", "Advanced Bicycles"]
        },
        row_count=104,
        tier=2
    ),

    TableMetadata(
        schema="purchasing",
        table="vvendorwithaddresses",
        description="Vendor address information with 5 JOINs. Combines vendor with full address details. Use for vendor location and shipping address queries.",
        business_terms=[
            "vendor addresses", "supplier locations", "vendor shipping",
            "vendor city", "vendor state", "supplier address",
            "vendor location", "where vendors are located"
        ],
        common_questions=[
            "vendor addresses",
            "where are vendors located",
            "vendor shipping addresses",
            "vendor locations by city/state",
            "supplier geographic distribution",
            "vendor address details"
        ],
        key_columns={
            "businessentityid": "Vendor identifier",
            "name": "Vendor company name",
            "addresstype": "Type of address (e.g., Main Office, Shipping)",
            "addressline1": "Street address",
            "city": "City name",
            "stateprovincename": "State or province",
            "postalcode": "Postal/ZIP code",
            "countryregionname": "Country name"
        },
        sample_values={
            "addresstype": ["Main Office", "Shipping", "Primary"],
            "countryregionname": ["United States", "Canada", "Australia"]
        },
        row_count=104,
        tier=2
    ),
]


# ============================================================================
# ANCHOR TABLES (Always included in RAG context)
# ============================================================================

ANCHOR_TABLES = {
    "sales": [
        "sales.salesorderheader",
        "sales.customer",
        "production.product"
    ],
    "hr": [
        "humanresources.employee",
        "person.person",
        "humanresources.department",
        "humanresources.employeepayhistory"
    ],
    "production": [
        "production.product",
        "production.productcategory",
        "production.workorder"
    ],
    "purchasing": [
        "purchasing.purchaseorderheader",
        "purchasing.vendor",
        "production.product"
    ],
    "general": [
        "sales.salesorderheader",
        "production.product",
        "humanresources.employee",
        "person.person"
    ]
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_core_tables() -> List[TableMetadata]:
    """Get all core tables (Tier 1)"""
    return CORE_TABLES


def get_all_important_tables() -> List[TableMetadata]:
    """Get important tables (Tier 2)"""
    return IMPORTANT_TABLES


def get_all_tables() -> List[TableMetadata]:
    """Get all tables (Tier 1 + Tier 2)"""
    return CORE_TABLES + IMPORTANT_TABLES


def get_table_by_name(schema: str, table: str) -> TableMetadata:
    """Get table metadata by schema and table name"""
    for t in get_all_tables():
        if t.schema == schema and t.table == table:
            return t
    raise ValueError(f"Table {schema}.{table} not found in metadata")


def get_anchor_tables_for_domain(domain: str) -> List[str]:
    """Get anchor tables for a specific domain"""
    return ANCHOR_TABLES.get(domain, ANCHOR_TABLES["general"])
