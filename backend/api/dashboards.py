"""
Dashboard API Endpoints
Provides data for Sales, Production, and Workforce dashboards
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import psycopg2
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from api.auth import get_current_user
from database.models import User
from config import settings
from utils.logger import logger


# Create router
router = APIRouter(prefix="/api/v1/dashboards", tags=["dashboards"])


# ============================================================================
# Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        dbname=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD
    )


# ============================================================================
# Pydantic Models
# ============================================================================

class SalesKPIsResponse(BaseModel):
    """Sales Dashboard KPIs"""
    total_revenue: float
    total_orders: int
    avg_order_value: float
    yoy_growth: float
    top_territory: str
    top_territory_revenue: float


class RevenueByTerritoryItem(BaseModel):
    """Revenue by territory item"""
    territory: str
    revenue: float
    orders: int
    avg_order_value: float


class RevenueTrendItem(BaseModel):
    """Revenue trend data point"""
    date: str  # ISO format date
    revenue: float
    orders: int


class CategoryBreakdownItem(BaseModel):
    """Product category breakdown"""
    category: str
    revenue: float
    orders: int
    units_sold: int
    percentage: float


class SalesRepItem(BaseModel):
    """Sales representative performance"""
    name: str
    territory: str
    orders: int
    revenue: float
    avg_order_value: float


# ============================================================================
# Sales Dashboard Endpoints
# ============================================================================

@router.get("/sales/kpis", response_model=SalesKPIsResponse)
def get_sales_kpis(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get Sales Dashboard KPIs"""
    logger.info(f"Fetching sales KPIs for user {current_user.email}")

    # Use default date range if not provided
    if not start_date or not end_date:
        start_date = "2024-01-01"
        end_date = "2024-12-31"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Current period metrics
        cur.execute("""
            SELECT
                COUNT(DISTINCT salesorderid) as total_orders,
                SUM(totaldue) as total_revenue,
                AVG(totaldue) as avg_order_value
            FROM sales.salesorderheader
            WHERE orderdate BETWEEN %s AND %s
        """, (start_date, end_date))

        current = cur.fetchone()
        total_orders = current[0] or 0
        total_revenue = float(current[1]) if current[1] else 0.0
        avg_order_value = float(current[2]) if current[2] else 0.0

        # Previous year for YoY (subtract 1 year from start and end dates)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        prev_start = start_dt.replace(year=start_dt.year - 1).strftime("%Y-%m-%d")
        prev_end = end_dt.replace(year=end_dt.year - 1).strftime("%Y-%m-%d")

        cur.execute("""
            SELECT SUM(totaldue) as prev_revenue
            FROM sales.salesorderheader
            WHERE orderdate BETWEEN %s AND %s
        """, (prev_start, prev_end))

        prev = cur.fetchone()
        prev_revenue = float(prev[0]) if prev and prev[0] else 0.0

        yoy_growth = 0.0
        if prev_revenue > 0:
            yoy_growth = ((total_revenue - prev_revenue) / prev_revenue) * 100

        # Top territory
        cur.execute("""
            SELECT
                st.name as territory,
                SUM(soh.totaldue) as revenue
            FROM sales.salesorderheader soh
            JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
            WHERE soh.orderdate BETWEEN %s AND %s
            GROUP BY st.name
            ORDER BY revenue DESC
            LIMIT 1
        """, (start_date, end_date))

        top_terr = cur.fetchone()
        top_territory = top_terr[0] if top_terr else "N/A"
        top_territory_revenue = float(top_terr[1]) if top_terr and top_terr[1] else 0.0

        return SalesKPIsResponse(
            total_revenue=total_revenue,
            total_orders=total_orders,
            avg_order_value=avg_order_value,
            yoy_growth=yoy_growth,
            top_territory=top_territory,
            top_territory_revenue=top_territory_revenue
        )

    except Exception as e:
        logger.error(f"Error fetching sales KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/sales/territories")
def get_territories(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """Get list of all sales territories for filter dropdown"""
    logger.info(f"Fetching territories list for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT name
            FROM sales.salesterritory
            ORDER BY name
        """)

        return [row[0] for row in cur.fetchall()]

    except Exception as e:
        logger.error(f"Error fetching territories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/sales/revenue-by-territory")
def get_revenue_by_territory(
    start_date: Optional[str] = Query("2024-01-01"),
    end_date: Optional[str] = Query("2024-12-31"),
    territories: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[RevenueByTerritoryItem]:
    """Get revenue breakdown by territory"""
    logger.info(f"Fetching revenue by territory for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                st.name as territory,
                COUNT(DISTINCT soh.salesorderid) as orders,
                SUM(soh.totaldue) as revenue,
                AVG(soh.totaldue) as avg_order_value
            FROM sales.salesorderheader soh
            JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
            WHERE soh.orderdate BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if territories:
            territory_list = [t.strip() for t in territories.split(",")]
            placeholders = ",".join(["%s"] * len(territory_list))
            query += f" AND st.name IN ({placeholders})"
            params.extend(territory_list)

        query += " GROUP BY st.name ORDER BY st.name ASC"  # Sort alphabetically, not by revenue

        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            results.append(RevenueByTerritoryItem(
                territory=row[0],
                orders=row[1],
                revenue=float(row[2]) if row[2] else 0.0,
                avg_order_value=float(row[3]) if row[3] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching revenue by territory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/sales/revenue-trend")
def get_revenue_trend(
    start_date: Optional[str] = Query("2024-01-01"),
    end_date: Optional[str] = Query("2024-12-31"),
    granularity: str = Query("month"),
    current_user: User = Depends(get_current_user)
) -> List[RevenueTrendItem]:
    """Get revenue trend over time"""
    logger.info(f"Fetching revenue trend for user {current_user.email}")

    granularity_map = {
        "day": "day",
        "week": "week",
        "month": "month",
        "quarter": "quarter"
    }

    trunc_format = granularity_map.get(granularity, "month")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(f"""
            SELECT
                DATE_TRUNC(%s, orderdate)::date as period,
                SUM(totaldue) as revenue,
                COUNT(DISTINCT salesorderid) as orders
            FROM sales.salesorderheader
            WHERE orderdate BETWEEN %s AND %s
            GROUP BY DATE_TRUNC(%s, orderdate)
            ORDER BY period
        """, (trunc_format, start_date, end_date, trunc_format))

        results = []
        for row in cur.fetchall():
            results.append(RevenueTrendItem(
                date=row[0].isoformat() if row[0] else "",
                revenue=float(row[1]) if row[1] else 0.0,
                orders=row[2] or 0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching revenue trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/sales/category-breakdown")
def get_category_breakdown(
    start_date: Optional[str] = Query("2024-01-01"),
    end_date: Optional[str] = Query("2024-12-31"),
    categories: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[CategoryBreakdownItem]:
    """Get revenue breakdown by product category"""
    logger.info(f"Fetching category breakdown for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get total revenue
        cur.execute("""
            SELECT SUM(sod.orderqty * sod.unitprice) as total_revenue
            FROM sales.salesorderdetail sod
            JOIN sales.salesorderheader soh ON sod.salesorderid = soh.salesorderid
            WHERE soh.orderdate BETWEEN %s AND %s
        """, (start_date, end_date))

        total_revenue = float(cur.fetchone()[0] or 0)

        # Get breakdown
        query = """
            SELECT
                pc.name AS category,
                COUNT(DISTINCT sod.salesorderid) AS orders,
                SUM(sod.orderqty) AS units_sold,
                SUM(sod.orderqty * sod.unitprice) AS revenue
            FROM sales.salesorderdetail sod
            JOIN production.product p ON sod.productid = p.productid
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            JOIN sales.salesorderheader soh ON sod.salesorderid = soh.salesorderid
            WHERE soh.orderdate BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if categories:
            category_list = [c.strip() for c in categories.split(",")]
            placeholders = ",".join(["%s"] * len(category_list))
            query += f" AND pc.name IN ({placeholders})"
            params.extend(category_list)

        query += " GROUP BY pc.name ORDER BY revenue DESC"

        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            revenue = float(row[3]) if row[3] else 0.0
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0.0

            results.append(CategoryBreakdownItem(
                category=row[0],
                orders=row[1] or 0,
                units_sold=row[2] or 0,
                revenue=revenue,
                percentage=percentage
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching category breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/sales/sales-reps")
def get_sales_reps(
    start_date: Optional[str] = Query("2024-01-01"),
    end_date: Optional[str] = Query("2024-12-31"),
    territory: Optional[str] = Query(None, description="Filter by territory name"),
    limit: int = Query(10),
    current_user: User = Depends(get_current_user)
) -> List[SalesRepItem]:
    """Get top sales representatives by revenue, optionally filtered by territory"""
    logger.info(f"Fetching sales reps for user {current_user.email}, territory={territory}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Note: Join territory on soh.territoryid (where sale happened)
        # not sp.territoryid (salesperson's assigned territory)
        query = """
            SELECT
                p.firstname || ' ' || p.lastname AS sales_rep,
                st.name AS territory,
                COUNT(DISTINCT soh.salesorderid) AS orders,
                SUM(soh.totaldue) AS revenue,
                AVG(soh.totaldue) AS avg_order_value
            FROM sales.salesorderheader soh
            JOIN sales.salesperson sp ON soh.salespersonid = sp.businessentityid
            JOIN humanresources.employee e ON sp.businessentityid = e.businessentityid
            JOIN person.person p ON e.businessentityid = p.businessentityid
            JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
            WHERE soh.orderdate BETWEEN %s AND %s
        """
        params = [start_date, end_date]

        # Add territory filter if specified
        if territory:
            query += " AND st.name = %s"
            params.append(territory)

        query += """
            GROUP BY p.firstname, p.lastname, st.name
            ORDER BY revenue DESC
            LIMIT %s
        """
        params.append(limit)

        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            results.append(SalesRepItem(
                name=row[0],
                territory=row[1],
                orders=row[2] or 0,
                revenue=float(row[3]) if row[3] else 0.0,
                avg_order_value=float(row[4]) if row[4] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching sales reps: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Production & Inventory Dashboard Endpoints
# ============================================================================

class ProductionKPIsResponse(BaseModel):
    """Production Dashboard KPIs"""
    total_inventory_value: float
    total_products: int
    low_stock_count: int
    avg_profit_margin: float
    avg_production_cost: float
    high_margin_products: int  # Products with margin > 60%


class InventoryByCategoryItem(BaseModel):
    """Inventory by category"""
    category: str
    total_quantity: int
    inventory_value: float
    product_count: int


class ProductInventoryItem(BaseModel):
    """Product inventory details"""
    product_id: int
    product_name: str
    category: str
    subcategory: str
    quantity: int
    list_price: float
    standard_cost: float
    profit_margin: float
    inventory_value: float


class LowStockItem(BaseModel):
    """Low stock product"""
    product_id: int
    product_name: str
    category: str
    subcategory: str
    quantity: int
    list_price: float
    profit_margin: float
    status: str  # "critical", "low", "warning"


class ProfitMarginItem(BaseModel):
    """Profit margin by category"""
    category: str
    avg_margin: float
    min_margin: float
    max_margin: float
    product_count: int


@router.get("/production/kpis", response_model=ProductionKPIsResponse)
def get_production_kpis(
    current_user: User = Depends(get_current_user)
):
    """Get Production & Inventory Dashboard KPIs"""
    logger.info(f"Fetching production KPIs for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Total inventory value and product count
        cur.execute("""
            SELECT
                COUNT(DISTINCT p.productid) as total_products,
                SUM(COALESCE(pi.quantity, 0) * p.listprice) as inventory_value
            FROM production.product p
            LEFT JOIN production.productinventory pi ON p.productid = pi.productid
            WHERE p.finishedgoodsflag = true
        """)
        result = cur.fetchone()
        total_products = result[0] or 0
        total_inventory_value = float(result[1]) if result[1] else 0.0

        # Low stock count (products with TOTAL inventory < 50 units across all locations)
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT p.productid
                FROM production.product p
                JOIN production.productinventory pi ON p.productid = pi.productid
                WHERE p.finishedgoodsflag = true
                GROUP BY p.productid
                HAVING SUM(pi.quantity) < 50 AND SUM(pi.quantity) > 0
            ) low_stock_products
        """)
        low_stock_count = cur.fetchone()[0] or 0

        # Average profit margin
        cur.execute("""
            SELECT
                AVG(CASE WHEN listprice > 0 THEN ((listprice - standardcost) / listprice) * 100 ELSE 0 END) as avg_margin
            FROM production.product
            WHERE finishedgoodsflag = true
            AND listprice > 0
            AND standardcost > 0
        """)
        avg_profit_margin = float(cur.fetchone()[0] or 0)

        # Average production cost
        cur.execute("""
            SELECT AVG(standardcost)
            FROM production.product
            WHERE finishedgoodsflag = true
            AND standardcost > 0
        """)
        avg_production_cost = float(cur.fetchone()[0] or 0)

        # High margin products (margin > 60%)
        cur.execute("""
            SELECT COUNT(*)
            FROM production.product
            WHERE finishedgoodsflag = true
            AND listprice > 0
            AND standardcost > 0
            AND ((listprice - standardcost) / listprice) * 100 > 60
        """)
        high_margin_products = cur.fetchone()[0] or 0

        return ProductionKPIsResponse(
            total_inventory_value=total_inventory_value,
            total_products=total_products,
            low_stock_count=low_stock_count,
            avg_profit_margin=avg_profit_margin,
            avg_production_cost=avg_production_cost,
            high_margin_products=high_margin_products
        )

    except Exception as e:
        logger.error(f"Error fetching production KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/production/inventory-by-category")
def get_inventory_by_category(
    current_user: User = Depends(get_current_user)
) -> List[InventoryByCategoryItem]:
    """Get inventory breakdown by product category"""
    logger.info(f"Fetching inventory by category for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                pc.name as category,
                SUM(COALESCE(pi.quantity, 0)) as total_quantity,
                SUM(COALESCE(pi.quantity, 0) * p.listprice) as inventory_value,
                COUNT(DISTINCT p.productid) as product_count
            FROM production.product p
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            LEFT JOIN production.productinventory pi ON p.productid = pi.productid
            WHERE p.finishedgoodsflag = true
            GROUP BY pc.name
            ORDER BY inventory_value DESC
        """)

        results = []
        for row in cur.fetchall():
            results.append(InventoryByCategoryItem(
                category=row[0],
                total_quantity=row[1] or 0,
                inventory_value=float(row[2]) if row[2] else 0.0,
                product_count=row[3] or 0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching inventory by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/production/profit-margins")
def get_profit_margins(
    current_user: User = Depends(get_current_user)
) -> List[ProfitMarginItem]:
    """Get profit margin analysis by category"""
    logger.info(f"Fetching profit margins for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                pc.name as category,
                AVG(CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END) as avg_margin,
                MIN(CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END) as min_margin,
                MAX(CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END) as max_margin,
                COUNT(DISTINCT p.productid) as product_count
            FROM production.product p
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            WHERE p.finishedgoodsflag = true
            AND p.listprice > 0
            AND p.standardcost > 0
            GROUP BY pc.name
            ORDER BY avg_margin DESC
        """)

        results = []
        for row in cur.fetchall():
            results.append(ProfitMarginItem(
                category=row[0],
                avg_margin=float(row[1]) if row[1] else 0.0,
                min_margin=float(row[2]) if row[2] else 0.0,
                max_margin=float(row[3]) if row[3] else 0.0,
                product_count=row[4] or 0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching profit margins: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


class LowStockCategoryCount(BaseModel):
    """Low stock count by category"""
    category: str
    count: int


@router.get("/production/low-stock-categories")
def get_low_stock_categories(
    threshold: int = Query(50, description="Stock level threshold"),
    current_user: User = Depends(get_current_user)
) -> List[LowStockCategoryCount]:
    """Get count of low stock products by category"""
    logger.info(f"Fetching low stock categories for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                pc.name as category,
                COUNT(DISTINCT p.productid) as count
            FROM production.product p
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            JOIN production.productinventory pi ON p.productid = pi.productid
            WHERE p.finishedgoodsflag = true
            GROUP BY pc.name, p.productid, p.name
            HAVING SUM(pi.quantity) < %s AND SUM(pi.quantity) > 0
        """, (threshold,))

        # Aggregate by category
        category_counts = {}
        for row in cur.fetchall():
            cat = row[0]
            if cat in category_counts:
                category_counts[cat] += 1
            else:
                category_counts[cat] = 1

        results = [LowStockCategoryCount(category=cat, count=count)
                   for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])]
        return results

    except Exception as e:
        logger.error(f"Error fetching low stock categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/production/low-stock")
def get_low_stock_products(
    threshold: int = Query(50, description="Stock level threshold"),
    limit: int = Query(50, description="Maximum number of results"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    current_user: User = Depends(get_current_user)
) -> List[LowStockItem]:
    """Get products with low inventory levels"""
    logger.info(f"Fetching low stock products for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                p.productid,
                p.name as product_name,
                pc.name as category,
                ps.name as subcategory,
                SUM(pi.quantity) as quantity,
                p.listprice,
                CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END as profit_margin
            FROM production.product p
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            JOIN production.productinventory pi ON p.productid = pi.productid
            WHERE p.finishedgoodsflag = true
        """
        params = []

        if category:
            query += " AND pc.name = %s"
            params.append(category)

        query += """
            GROUP BY p.productid, p.name, pc.name, ps.name, p.listprice, p.standardcost
            HAVING SUM(pi.quantity) < %s AND SUM(pi.quantity) > 0
            ORDER BY SUM(pi.quantity) ASC
            LIMIT %s
        """
        params.extend([threshold, limit])

        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            quantity = row[4] or 0
            # Determine status based on quantity
            if quantity < 10:
                status = "critical"
            elif quantity < 25:
                status = "low"
            else:
                status = "warning"

            results.append(LowStockItem(
                product_id=row[0],
                product_name=row[1],
                category=row[2],
                subcategory=row[3],
                quantity=quantity,
                list_price=float(row[5]) if row[5] else 0.0,
                profit_margin=float(row[6]) if row[6] else 0.0,
                status=status
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching low stock products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/production/products")
def get_product_inventory(
    category: Optional[str] = Query(None),
    min_margin: Optional[float] = Query(None),
    max_stock: Optional[int] = Query(None),
    limit: int = Query(50),
    current_user: User = Depends(get_current_user)
) -> List[ProductInventoryItem]:
    """Get product inventory with optional filters"""
    logger.info(f"Fetching product inventory for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                p.productid,
                p.name as product_name,
                pc.name as category,
                ps.name as subcategory,
                COALESCE(SUM(pi.quantity), 0) as quantity,
                p.listprice,
                p.standardcost,
                CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END as profit_margin,
                COALESCE(SUM(pi.quantity), 0) * p.listprice as inventory_value
            FROM production.product p
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            LEFT JOIN production.productinventory pi ON p.productid = pi.productid
            WHERE p.finishedgoodsflag = true
        """

        params = []

        if category:
            query += " AND pc.name = %s"
            params.append(category)

        query += """
            GROUP BY p.productid, p.name, pc.name, ps.name, p.listprice, p.standardcost
        """

        if min_margin is not None:
            query += " HAVING CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END >= %s"
            params.append(min_margin)

        if max_stock is not None:
            if min_margin is not None:
                query += " AND COALESCE(SUM(pi.quantity), 0) <= %s"
            else:
                query += " HAVING COALESCE(SUM(pi.quantity), 0) <= %s"
            params.append(max_stock)

        query += " ORDER BY inventory_value DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            results.append(ProductInventoryItem(
                product_id=row[0],
                product_name=row[1],
                category=row[2],
                subcategory=row[3],
                quantity=row[4] or 0,
                list_price=float(row[5]) if row[5] else 0.0,
                standard_cost=float(row[6]) if row[6] else 0.0,
                profit_margin=float(row[7]) if row[7] else 0.0,
                inventory_value=float(row[8]) if row[8] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching product inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/production/high-margin-low-stock")
def get_high_margin_low_stock(
    min_margin: float = Query(60, description="Minimum profit margin %"),
    max_stock: int = Query(50, description="Maximum stock level"),
    current_user: User = Depends(get_current_user)
) -> List[ProductInventoryItem]:
    """Get products with high profit margin but low stock (risk assessment)"""
    logger.info(f"Fetching high-margin low-stock products for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                p.productid,
                p.name as product_name,
                pc.name as category,
                ps.name as subcategory,
                COALESCE(SUM(pi.quantity), 0) as quantity,
                p.listprice,
                p.standardcost,
                CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END as profit_margin,
                COALESCE(SUM(pi.quantity), 0) * p.listprice as inventory_value
            FROM production.product p
            JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
            JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
            LEFT JOIN production.productinventory pi ON p.productid = pi.productid
            WHERE p.finishedgoodsflag = true
            AND p.listprice > 0
            AND p.standardcost > 0
            GROUP BY p.productid, p.name, pc.name, ps.name, p.listprice, p.standardcost
            HAVING
                CASE WHEN p.listprice > 0 THEN ((p.listprice - p.standardcost) / p.listprice) * 100 ELSE 0 END >= %s
                AND COALESCE(SUM(pi.quantity), 0) < %s
                AND COALESCE(SUM(pi.quantity), 0) > 0
            ORDER BY profit_margin DESC, quantity ASC
        """, (min_margin, max_stock))

        results = []
        for row in cur.fetchall():
            results.append(ProductInventoryItem(
                product_id=row[0],
                product_name=row[1],
                category=row[2],
                subcategory=row[3],
                quantity=row[4] or 0,
                list_price=float(row[5]) if row[5] else 0.0,
                standard_cost=float(row[6]) if row[6] else 0.0,
                profit_margin=float(row[7]) if row[7] else 0.0,
                inventory_value=float(row[8]) if row[8] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching high-margin low-stock products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ============================================================================
# Workforce & Operations Dashboard Endpoints
# ============================================================================

class WorkforceKPIsResponse(BaseModel):
    """Workforce Dashboard KPIs"""
    total_employees: int
    avg_annual_salary: float
    total_payroll: float
    avg_tenure_years: float
    departments_count: int
    sales_employees: int


class DepartmentStatsItem(BaseModel):
    """Department statistics"""
    department: str
    employee_count: int
    avg_salary: float
    total_payroll: float
    avg_tenure_years: float


class SalaryDistributionItem(BaseModel):
    """Salary distribution bucket"""
    salary_range: str
    min_salary: float
    max_salary: float
    employee_count: int
    percentage: float


class EmployeeItem(BaseModel):
    """Employee details"""
    employee_id: int
    name: str
    job_title: str
    department: str
    hire_date: str
    tenure_years: float
    hourly_rate: float
    annual_salary: float


class RevenuePerEmployeeItem(BaseModel):
    """Revenue per employee by department"""
    department: str
    employee_count: int
    avg_salary: float
    total_revenue: float
    revenue_per_employee: float


@router.get("/workforce/kpis", response_model=WorkforceKPIsResponse)
def get_workforce_kpis(
    current_user: User = Depends(get_current_user)
):
    """Get Workforce & Operations Dashboard KPIs"""
    logger.info(f"Fetching workforce KPIs for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Total employees (active - no end date in department history)
        cur.execute("""
            SELECT COUNT(DISTINCT e.businessentityid)
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            WHERE edh.enddate IS NULL
        """)
        total_employees = cur.fetchone()[0] or 0

        # Average salary and total payroll
        cur.execute("""
            SELECT
                AVG(eph.rate * 40 * 52) as avg_salary,
                SUM(eph.rate * 40 * 52) as total_payroll
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
            WHERE edh.enddate IS NULL
            AND eph.ratechangedate = (
                SELECT MAX(ratechangedate)
                FROM humanresources.employeepayhistory
                WHERE businessentityid = e.businessentityid
            )
        """)
        salary_result = cur.fetchone()
        avg_annual_salary = float(salary_result[0]) if salary_result[0] else 0.0
        total_payroll = float(salary_result[1]) if salary_result[1] else 0.0

        # Average tenure
        cur.execute("""
            SELECT AVG(EXTRACT(YEAR FROM age(CURRENT_DATE, e.hiredate)))
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            WHERE edh.enddate IS NULL
        """)
        avg_tenure_years = float(cur.fetchone()[0] or 0)

        # Number of departments
        cur.execute("""
            SELECT COUNT(DISTINCT d.departmentid)
            FROM humanresources.department d
            JOIN humanresources.employeedepartmenthistory edh ON d.departmentid = edh.departmentid
            WHERE edh.enddate IS NULL
        """)
        departments_count = cur.fetchone()[0] or 0

        # Sales employees count
        cur.execute("""
            SELECT COUNT(DISTINCT e.businessentityid)
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.department d ON edh.departmentid = d.departmentid
            WHERE edh.enddate IS NULL
            AND d.name = 'Sales'
        """)
        sales_employees = cur.fetchone()[0] or 0

        return WorkforceKPIsResponse(
            total_employees=total_employees,
            avg_annual_salary=avg_annual_salary,
            total_payroll=total_payroll,
            avg_tenure_years=avg_tenure_years,
            departments_count=departments_count,
            sales_employees=sales_employees
        )

    except Exception as e:
        logger.error(f"Error fetching workforce KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/workforce/departments")
def get_department_stats(
    current_user: User = Depends(get_current_user)
) -> List[DepartmentStatsItem]:
    """Get employee statistics by department"""
    logger.info(f"Fetching department stats for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                d.name AS department,
                COUNT(DISTINCT e.businessentityid) AS employee_count,
                AVG(eph.rate * 40 * 52) AS avg_salary,
                SUM(eph.rate * 40 * 52) AS total_payroll,
                AVG(EXTRACT(YEAR FROM age(CURRENT_DATE, e.hiredate))) AS avg_tenure
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.department d ON edh.departmentid = d.departmentid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
            WHERE edh.enddate IS NULL
            AND eph.ratechangedate = (
                SELECT MAX(ratechangedate)
                FROM humanresources.employeepayhistory
                WHERE businessentityid = e.businessentityid
            )
            GROUP BY d.name
            ORDER BY employee_count DESC
        """)

        results = []
        for row in cur.fetchall():
            results.append(DepartmentStatsItem(
                department=row[0],
                employee_count=row[1] or 0,
                avg_salary=float(row[2]) if row[2] else 0.0,
                total_payroll=float(row[3]) if row[3] else 0.0,
                avg_tenure_years=float(row[4]) if row[4] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching department stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/workforce/salary-distribution")
def get_salary_distribution(
    current_user: User = Depends(get_current_user)
) -> List[SalaryDistributionItem]:
    """Get salary distribution histogram data"""
    logger.info(f"Fetching salary distribution for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get total count for percentage calculation
        cur.execute("""
            SELECT COUNT(DISTINCT e.businessentityid)
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
            WHERE edh.enddate IS NULL
            AND eph.ratechangedate = (
                SELECT MAX(ratechangedate)
                FROM humanresources.employeepayhistory
                WHERE businessentityid = e.businessentityid
            )
        """)
        total_employees = cur.fetchone()[0] or 1

        # Get salary distribution in buckets
        cur.execute("""
            WITH salaries AS (
                SELECT DISTINCT ON (e.businessentityid)
                    e.businessentityid,
                    eph.rate * 40 * 52 AS annual_salary
                FROM humanresources.employee e
                JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
                JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
                WHERE edh.enddate IS NULL
                ORDER BY e.businessentityid, eph.ratechangedate DESC
            ),
            buckets AS (
                SELECT
                    CASE
                        WHEN annual_salary < 30000 THEN 1
                        WHEN annual_salary < 40000 THEN 2
                        WHEN annual_salary < 50000 THEN 3
                        WHEN annual_salary < 60000 THEN 4
                        WHEN annual_salary < 75000 THEN 5
                        WHEN annual_salary < 100000 THEN 6
                        WHEN annual_salary < 150000 THEN 7
                        ELSE 8
                    END AS bucket,
                    annual_salary
                FROM salaries
            )
            SELECT
                bucket,
                COUNT(*) AS employee_count
            FROM buckets
            GROUP BY bucket
            ORDER BY bucket
        """)

        bucket_labels = [
            ("$0 - $30K", 0, 30000),
            ("$30K - $40K", 30000, 40000),
            ("$40K - $50K", 40000, 50000),
            ("$50K - $60K", 50000, 60000),
            ("$60K - $75K", 60000, 75000),
            ("$75K - $100K", 75000, 100000),
            ("$100K - $150K", 100000, 150000),
            ("$150K+", 150000, 500000),
        ]

        bucket_counts = {i: 0 for i in range(1, 9)}
        for row in cur.fetchall():
            bucket_counts[row[0]] = row[1]

        results = []
        for i, (label, min_sal, max_sal) in enumerate(bucket_labels, 1):
            count = bucket_counts.get(i, 0)
            results.append(SalaryDistributionItem(
                salary_range=label,
                min_salary=float(min_sal),
                max_salary=float(max_sal),
                employee_count=count,
                percentage=(count / total_employees) * 100 if total_employees > 0 else 0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching salary distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/workforce/employees")
def get_employees(
    department: Optional[str] = Query(None),
    limit: int = Query(50),
    current_user: User = Depends(get_current_user)
) -> List[EmployeeItem]:
    """Get employee directory"""
    logger.info(f"Fetching employees for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                e.businessentityid,
                p.firstname || ' ' || p.lastname AS name,
                e.jobtitle,
                d.name AS department,
                e.hiredate,
                EXTRACT(YEAR FROM age(CURRENT_DATE, e.hiredate)) AS tenure_years,
                eph.rate AS hourly_rate,
                eph.rate * 40 * 52 AS annual_salary
            FROM humanresources.employee e
            JOIN person.person p ON e.businessentityid = p.businessentityid
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.department d ON edh.departmentid = d.departmentid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
            WHERE edh.enddate IS NULL
            AND eph.ratechangedate = (
                SELECT MAX(ratechangedate)
                FROM humanresources.employeepayhistory
                WHERE businessentityid = e.businessentityid
            )
        """

        params = []

        if department:
            query += " AND d.name = %s"
            params.append(department)

        query += " ORDER BY annual_salary DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            results.append(EmployeeItem(
                employee_id=row[0],
                name=row[1],
                job_title=row[2],
                department=row[3],
                hire_date=row[4].isoformat() if row[4] else "",
                tenure_years=float(row[5]) if row[5] else 0.0,
                hourly_rate=float(row[6]) if row[6] else 0.0,
                annual_salary=float(row[7]) if row[7] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/workforce/revenue-per-employee")
def get_revenue_per_employee(
    year: int = Query(2024),
    current_user: User = Depends(get_current_user)
) -> List[RevenuePerEmployeeItem]:
    """Get revenue per employee analysis by department (for Q3 experiment question)"""
    logger.info(f"Fetching revenue per employee for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            WITH dept_employees AS (
                SELECT
                    d.name AS department,
                    COUNT(DISTINCT e.businessentityid) AS employee_count,
                    AVG(eph.rate * 40 * 52) AS avg_salary
                FROM humanresources.employee e
                JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
                JOIN humanresources.department d ON edh.departmentid = d.departmentid
                JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
                WHERE edh.enddate IS NULL
                AND eph.ratechangedate = (
                    SELECT MAX(ratechangedate)
                    FROM humanresources.employeepayhistory
                    WHERE businessentityid = e.businessentityid
                )
                GROUP BY d.name
            ),
            sales_revenue AS (
                SELECT
                    'Sales' AS department,
                    SUM(soh.totaldue) AS total_revenue
                FROM sales.salesorderheader soh
                WHERE EXTRACT(YEAR FROM soh.orderdate) = %s
            )
            SELECT
                de.department,
                de.employee_count,
                de.avg_salary,
                COALESCE(sr.total_revenue, 0) AS total_revenue,
                CASE
                    WHEN de.department = 'Sales' AND de.employee_count > 0
                    THEN COALESCE(sr.total_revenue, 0) / de.employee_count
                    ELSE 0
                END AS revenue_per_employee
            FROM dept_employees de
            LEFT JOIN sales_revenue sr ON de.department = sr.department
            ORDER BY de.employee_count DESC
        """, (year,))

        results = []
        for row in cur.fetchall():
            results.append(RevenuePerEmployeeItem(
                department=row[0],
                employee_count=row[1] or 0,
                avg_salary=float(row[2]) if row[2] else 0.0,
                total_revenue=float(row[3]) if row[3] else 0.0,
                revenue_per_employee=float(row[4]) if row[4] else 0.0
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching revenue per employee: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/workforce/sales-roi-years")
def get_sales_roi_years(
    current_user: User = Depends(get_current_user)
):
    """Get available years for Sales ROI analysis"""
    logger.info(f"Fetching available years for sales ROI for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT EXTRACT(YEAR FROM orderdate)::int AS year
            FROM sales.salesorderheader
            ORDER BY year DESC
        """)
        years = [row[0] for row in cur.fetchall()]
        return {"years": years}

    except Exception as e:
        logger.error(f"Error fetching sales ROI years: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@router.get("/workforce/sales-roi")
def get_sales_roi(
    year: int = Query(2024),
    current_user: User = Depends(get_current_user)
):
    """Get Sales department ROI metrics (for Q3 experiment question)"""
    logger.info(f"Fetching sales ROI for user {current_user.email}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get Sales department employee count and average salary
        cur.execute("""
            SELECT
                COUNT(DISTINCT e.businessentityid) AS sales_employees,
                AVG(eph.rate * 40 * 52) AS avg_salary
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.department d ON edh.departmentid = d.departmentid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
            WHERE edh.enddate IS NULL
            AND d.name = 'Sales'
            AND eph.ratechangedate = (
                SELECT MAX(ratechangedate)
                FROM humanresources.employeepayhistory
                WHERE businessentityid = e.businessentityid
            )
        """)
        sales_result = cur.fetchone()
        sales_employees = sales_result[0] or 0
        avg_sales_salary = float(sales_result[1]) if sales_result[1] else 0.0

        # Get total revenue for the year
        cur.execute("""
            SELECT SUM(totaldue)
            FROM sales.salesorderheader
            WHERE EXTRACT(YEAR FROM orderdate) = %s
        """, (year,))
        total_revenue = float(cur.fetchone()[0] or 0)

        # Get company-wide average salary
        cur.execute("""
            SELECT AVG(eph.rate * 40 * 52)
            FROM humanresources.employee e
            JOIN humanresources.employeedepartmenthistory edh ON e.businessentityid = edh.businessentityid
            JOIN humanresources.employeepayhistory eph ON e.businessentityid = eph.businessentityid
            WHERE edh.enddate IS NULL
            AND eph.ratechangedate = (
                SELECT MAX(ratechangedate)
                FROM humanresources.employeepayhistory
                WHERE businessentityid = e.businessentityid
            )
        """)
        company_avg_salary = float(cur.fetchone()[0] or 0)

        # Calculate metrics
        revenue_per_sales_employee = total_revenue / sales_employees if sales_employees > 0 else 0
        roi_multiple = revenue_per_sales_employee / avg_sales_salary if avg_sales_salary > 0 else 0

        return {
            "year": year,
            "sales_employees": sales_employees,
            "avg_sales_salary": avg_sales_salary,
            "company_avg_salary": company_avg_salary,
            "total_revenue": total_revenue,
            "revenue_per_sales_employee": revenue_per_sales_employee,
            "roi_multiple": roi_multiple,
            "summary": f"Each Sales employee generated ${revenue_per_sales_employee:,.2f} in revenue, which is {roi_multiple:.1f}x their average salary."
        }

    except Exception as e:
        logger.error(f"Error fetching sales ROI: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# Export router
__all__ = ["router"]
