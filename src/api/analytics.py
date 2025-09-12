"""
Analytics API endpoints for KPIs, trends, and performance metrics
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader

# Initialize router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Global data loader instance
data_loader = DataLoader()

# Logger
analytics_logger = logger.bind(name="analytics")


def aggregate_data_by_period(
    data: List[Dict[str, Any]], days_per_period: int, value_key: str
) -> List[Dict[str, Any]]:
    """Aggregate daily data into periods (weekly/monthly) by summing values"""
    if not data or days_per_period <= 1:
        return data

    aggregated = []
    current_period = []

    for i, item in enumerate(data):
        current_period.append(item)

        # When we reach the period size or it's the last item
        if len(current_period) == days_per_period or i == len(data) - 1:
            if current_period:
                # Sum the values for this period
                total_value = sum(d.get(value_key, 0) for d in current_period)

                # Use the last date of the period as the period date
                period_date = current_period[-1]["date"]

                # Create aggregated item
                aggregated_item = {
                    "date": period_date,
                    value_key: round(total_value, 2),
                }

                # For forecast data, also aggregate bounds
                if (
                    "upper_bound" in current_period[0]
                    and "lower_bound" in current_period[0]
                ):
                    aggregated_item["upper_bound"] = round(
                        sum(d.get("upper_bound", 0) for d in current_period), 2
                    )
                    aggregated_item["lower_bound"] = round(
                        sum(d.get("lower_bound", 0) for d in current_period), 2
                    )

                aggregated.append(aggregated_item)
                current_period = []

    return aggregated


@router.get("/kpis")
async def get_analytics_kpis(
    time_range: str = Query("30d", description="Time range: 7d, 30d, 90d, 1y"),
    filters: Optional[str] = Query(None, description="JSON encoded filters"),
) -> Dict[str, Any]:
    """Get real-time KPI calculations"""
    try:
        analytics_logger.info(f"Calculating KPIs for time_range: {time_range}")

        # Parse filters
        # TODO: Implement filtering logic using filter_dict
        if filters:
            try:
                json.loads(filters)
            except json.JSONDecodeError:
                pass

        # Calculate date range
        end_date = date.today()
        if time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Calculate KPIs

        # Total Revenue (from purchase orders)
        cursor.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) as total_revenue
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        total_revenue = cursor.fetchone()[0] or 0

        # Total Orders
        cursor.execute(
            """
            SELECT COUNT(*) as total_orders
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        total_orders = cursor.fetchone()[0] or 0

        # Average Order Value
        avg_order_value = total_revenue / max(total_orders, 1)

        # Low Stock Items
        cursor.execute(
            """
            SELECT COUNT(DISTINCT m.med_id) as low_stock_count
            FROM medications m
            JOIN consumption_history ch ON m.med_id = ch.med_id
            WHERE ch.date >= ? AND ch.on_hand <= 50
        """,
            (start_date.isoformat(),),
        )
        low_stock_items = cursor.fetchone()[0] or 0

        # Critical Stock Items (less than 20 units)
        cursor.execute(
            """
            SELECT COUNT(DISTINCT m.med_id) as critical_stock_count
            FROM medications m
            JOIN consumption_history ch ON m.med_id = ch.med_id
            WHERE ch.date >= ? AND ch.on_hand <= 20
        """,
            (start_date.isoformat(),),
        )
        critical_stock_items = cursor.fetchone()[0] or 0

        # Total Suppliers
        cursor.execute("SELECT COUNT(*) FROM suppliers WHERE status = 'OK'")
        total_suppliers = cursor.fetchone()[0] or 0

        # On-time Deliveries (calculated from purchase orders)
        cursor.execute(
            """
            SELECT 
                COUNT(CASE WHEN actual_delivery_date <= requested_delivery_date THEN 1 END) as on_time,
                COUNT(*) as total
            FROM purchase_orders 
            WHERE actual_delivery_date IS NOT NULL 
            AND requested_delivery_date IS NOT NULL
            AND created_at >= ? AND created_at <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        delivery_stats = cursor.fetchone()
        on_time_deliveries = 0
        if delivery_stats and delivery_stats[1] > 0:
            on_time_deliveries = (delivery_stats[0] / delivery_stats[1]) * 100

        # Inventory Turnover (consumption vs average stock)
        cursor.execute(
            """
            SELECT 
                AVG(qty_dispensed) as avg_consumption,
                AVG(on_hand) as avg_stock
            FROM consumption_history
            WHERE date >= ? AND date <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        turnover_data = cursor.fetchone()
        inventory_turnover = 0
        if turnover_data and turnover_data[1] and turnover_data[1] > 0:
            inventory_turnover = (turnover_data[0] or 0) / turnover_data[1]

        # Calculate trends (compare with previous period)
        prev_start_date = start_date - (end_date - start_date)

        # Revenue trend
        cursor.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) as prev_revenue
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at < ?
        """,
            (prev_start_date.isoformat(), start_date.isoformat()),
        )
        prev_revenue = cursor.fetchone()[0] or 0
        revenue_change = ((total_revenue - prev_revenue) / max(prev_revenue, 1)) * 100

        # Orders trend
        cursor.execute(
            """
            SELECT COUNT(*) as prev_orders
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at < ?
        """,
            (prev_start_date.isoformat(), start_date.isoformat()),
        )
        prev_orders = cursor.fetchone()[0] or 0
        orders_change = ((total_orders - prev_orders) / max(prev_orders, 1)) * 100

        # Average order value trend
        prev_avg_order_value = prev_revenue / max(prev_orders, 1)
        avg_order_change = (
            (avg_order_value - prev_avg_order_value) / max(prev_avg_order_value, 1)
        ) * 100

        # Stock alerts trend
        cursor.execute(
            """
            SELECT COUNT(DISTINCT m.med_id) as prev_low_stock
            FROM medications m
            JOIN consumption_history ch ON m.med_id = ch.med_id
            WHERE ch.date >= ? AND ch.date < ? AND ch.on_hand <= 50
        """,
            (prev_start_date.isoformat(), start_date.isoformat()),
        )
        prev_low_stock = cursor.fetchone()[0] or 0
        stock_alerts_change = (
            (low_stock_items - prev_low_stock) / max(prev_low_stock, 1)
        ) * 100

        conn.close()

        return {
            "kpis": {
                "totalRevenue": round(total_revenue, 2),
                "totalOrders": total_orders,
                "avgOrderValue": round(avg_order_value, 2),
                "lowStockItems": low_stock_items,
                "criticalStockItems": critical_stock_items,
                "totalSuppliers": total_suppliers,
                "onTimeDeliveries": round(on_time_deliveries, 1),
                "inventoryTurnover": round(inventory_turnover, 1),
            },
            "trends": {
                "revenueChange": round(revenue_change, 1),
                "ordersChange": round(orders_change, 1),
                "avgOrderChange": round(avg_order_change, 1),
                "stockAlertsChange": round(stock_alerts_change, 1),
            },
        }

    except Exception as e:
        analytics_logger.error(f"Error calculating KPIs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating KPIs: {str(e)}")


@router.get("/consumption-trends")
async def get_consumption_trends(
    time_range: str = Query("6m", description="Time range: 3m, 6m, 1y"),
    medication_id: Optional[str] = Query(None, description="Specific medication ID"),
) -> List[Dict[str, Any]]:
    """Get consumption trends with forecasting"""
    try:
        analytics_logger.info(f"Getting consumption trends for range: {time_range}")

        # Calculate date range
        end_date = date.today()
        if time_range == "3m":
            start_date = end_date - timedelta(days=90)
            group_by = "strftime('%Y-%m', date)"
            date_format = "month"
        elif time_range == "6m":
            start_date = end_date - timedelta(days=180)
            group_by = "strftime('%Y-%m', date)"
            date_format = "month"
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
            group_by = "strftime('%Y-%m', date)"
            date_format = "month"
        else:
            start_date = end_date - timedelta(days=180)
            group_by = "strftime('%Y-%m', date)"
            date_format = "month"

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Base query
        base_query = """
            SELECT 
                {group_by} as period,
                SUM(qty_dispensed) as consumption,
                COUNT(DISTINCT po.po_id) as orders,
                0 as forecast
            FROM consumption_history ch
            LEFT JOIN medications m ON ch.med_id = m.med_id
            LEFT JOIN purchase_orders po ON m.supplier_id = po.supplier_id 
                AND date(po.created_at) = ch.date
            WHERE ch.date >= ? AND ch.date <= ?
        """.format(group_by=group_by)

        params = [start_date.isoformat(), end_date.isoformat()]

        if medication_id:
            base_query += " AND ch.med_id = ?"
            params.append(medication_id)

        base_query += " GROUP BY " + group_by + " ORDER BY period"

        cursor.execute(base_query, params)
        results = cursor.fetchall()

        # Process results
        trends = []
        for row in results:
            period, consumption, orders, forecast = row

            # Convert period to readable format
            if date_format == "month":
                try:
                    period_date = datetime.strptime(period, "%Y-%m")
                    period_label = period_date.strftime("%b")
                except ValueError:
                    period_label = period
            else:
                period_label = period

            trends.append(
                {
                    "month": period_label,
                    "consumption": int(consumption or 0),
                    "orders": int(orders or 0),
                    "forecast": int(consumption * 1.05)
                    if consumption
                    else 0,  # Simple 5% growth forecast
                }
            )

        conn.close()

        return trends

    except Exception as e:
        analytics_logger.error(f"Error getting consumption trends: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting consumption trends: {str(e)}"
        )


@router.get("/supplier-performance")
async def get_supplier_performance(
    time_range: str = Query("3m", description="Time range: 1m, 3m, 6m, 1y"),
) -> List[Dict[str, Any]]:
    """Get supplier performance analytics"""
    try:
        analytics_logger.info(f"Getting supplier performance for range: {time_range}")

        # Calculate date range
        end_date = date.today()
        if time_range == "1m":
            start_date = end_date - timedelta(days=30)
        elif time_range == "3m":
            start_date = end_date - timedelta(days=90)
        elif time_range == "6m":
            start_date = end_date - timedelta(days=180)
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=90)  # Default

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                s.name,
                COUNT(po.po_id) as orders,
                COUNT(CASE 
                    WHEN po.actual_delivery_date <= po.requested_delivery_date 
                    THEN 1 
                END) as on_time_orders,
                AVG(CASE 
                    WHEN po.actual_delivery_date > po.requested_delivery_date 
                    THEN julianday(po.actual_delivery_date) - julianday(po.requested_delivery_date)
                    ELSE 0 
                END) as avg_delay,
                s.avg_lead_time,
                CASE
                    WHEN COUNT(po.po_id) = 0 THEN 4.0
                    WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 95 THEN 4.8
                    WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 90 THEN 4.5
                    WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 85 THEN 4.2
                    ELSE 4.0
                END as rating
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
                AND po.created_at >= ? AND po.created_at <= ?
            GROUP BY s.supplier_id, s.name, s.avg_lead_time
            HAVING COUNT(po.po_id) > 0
            ORDER BY orders DESC
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        results = cursor.fetchall()

        performance = []
        for row in results:
            name, orders, on_time_orders, avg_delay, avg_lead_time, rating = row
            on_time_percentage = (
                (on_time_orders / max(orders, 1)) * 100 if orders > 0 else 0
            )

            performance.append(
                {
                    "name": name,
                    "orders": orders,
                    "onTime": round(on_time_percentage, 1),
                    "avgDelay": round(avg_delay or 0, 1),
                    "leadTime": round(avg_lead_time or 7.0, 1),
                    "rating": round(rating, 1),
                }
            )

        conn.close()

        return performance

    except Exception as e:
        analytics_logger.error(f"Error getting supplier performance: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting supplier performance: {str(e)}"
        )


@router.get("/category-breakdown")
async def get_category_breakdown() -> List[Dict[str, Any]]:
    """Get inventory category breakdown"""
    try:
        analytics_logger.info("Getting category breakdown")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                m.category,
                COUNT(m.med_id) as count,
                COALESCE(SUM(ch.qty_dispensed), 0) as total_dispensed
            FROM medications m
            LEFT JOIN consumption_history ch ON m.med_id = ch.med_id
                AND ch.date >= date('now', '-30 days')
            GROUP BY m.category
            ORDER BY count DESC
        """)

        results = cursor.fetchall()

        # Calculate total for percentages
        total_count = sum(row[1] for row in results)

        # Color palette
        colors = [
            "#0088FE",
            "#00C49F",
            "#FFBB28",
            "#FF8042",
            "#8884D8",
            "#82CA9D",
            "#FFC658",
        ]

        breakdown = []
        for i, (category, count, dispensed) in enumerate(results):
            percentage = (count / max(total_count, 1)) * 100
            breakdown.append(
                {
                    "name": category or "Unknown",
                    "value": int(percentage),
                    "count": count,
                    "dispensed": int(dispensed or 0),
                    "color": colors[i % len(colors)],
                }
            )

        conn.close()

        return breakdown

    except Exception as e:
        analytics_logger.error(f"Error getting category breakdown: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting category breakdown: {str(e)}"
        )


@router.get("/stock-alerts")
async def get_stock_alerts() -> List[Dict[str, Any]]:
    """Get critical stock monitoring alerts"""
    try:
        analytics_logger.info("Getting stock alerts")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Get latest stock levels for each medication
        cursor.execute("""
            WITH latest_stock AS (
                SELECT 
                    ch.med_id,
                    ch.on_hand as current,
                    ch.qty_dispensed,
                    ROW_NUMBER() OVER (PARTITION BY ch.med_id ORDER BY ch.date DESC) as rn
                FROM consumption_history ch
            ),
            avg_consumption AS (
                SELECT 
                    med_id,
                    AVG(qty_dispensed) as avg_daily
                FROM consumption_history
                WHERE date >= date('now', '-30 days')
                GROUP BY med_id
            )
            SELECT 
                m.name as medication,
                ls.current,
                COALESCE(ac.avg_daily * 30, 100) as reorder_point,  -- 30 days supply
                CASE 
                    WHEN ac.avg_daily > 0 THEN ls.current / ac.avg_daily
                    ELSE 30  -- Default to 30 days if no consumption data
                END as days_left,
                CASE
                    WHEN ls.current <= COALESCE(ac.avg_daily * 10, 30) THEN 'critical'
                    WHEN ls.current <= COALESCE(ac.avg_daily * 20, 60) THEN 'low'
                    ELSE 'medium'
                END as priority
            FROM medications m
            JOIN latest_stock ls ON m.med_id = ls.med_id AND ls.rn = 1
            LEFT JOIN avg_consumption ac ON m.med_id = ac.med_id
            WHERE ls.current <= COALESCE(ac.avg_daily * 30, 100)  -- Only show low stock items
            ORDER BY 
                CASE 
                    WHEN ac.avg_daily > 0 THEN ls.current / ac.avg_daily
                    ELSE 30
                END ASC
        """)

        results = cursor.fetchall()

        alerts = []
        for row in results:
            medication, current, reorder_point, days_left, priority = row

            alerts.append(
                {
                    "medication": medication,
                    "current": int(current),
                    "reorder": int(reorder_point),
                    "daysLeft": int(days_left),
                    "priority": priority,
                }
            )

        conn.close()

        return alerts

    except Exception as e:
        analytics_logger.error(f"Error getting stock alerts: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting stock alerts: {str(e)}"
        )


@router.get("/revenue-trends")
async def get_revenue_trends(
    time_range: str = Query("6m", description="Time range: 3m, 6m, 1y"),
) -> List[Dict[str, Any]]:
    """Get revenue trends over time"""
    try:
        analytics_logger.info(f"Getting revenue trends for range: {time_range}")

        # Calculate date range
        end_date = date.today()
        if time_range == "3m":
            start_date = end_date - timedelta(days=90)
        elif time_range == "6m":
            start_date = end_date - timedelta(days=180)
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=180)  # Default

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                strftime('%Y-%m', created_at) as period,
                SUM(total_amount) as revenue,
                COUNT(*) as orders,
                AVG(total_amount) as avg_order_value
            FROM purchase_orders
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY period
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        results = cursor.fetchall()

        trends = []
        for row in results:
            period, revenue, orders, avg_order_value = row

            # Convert period to readable format
            try:
                period_date = datetime.strptime(period, "%Y-%m")
                period_label = period_date.strftime("%b %Y")
            except ValueError:
                period_label = period

            trends.append(
                {
                    "period": period_label,
                    "revenue": round(revenue or 0, 2),
                    "orders": orders or 0,
                    "avgOrderValue": round(avg_order_value or 0, 2),
                }
            )

        conn.close()

        return trends

    except Exception as e:
        analytics_logger.error(f"Error getting revenue trends: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting revenue trends: {str(e)}"
        )


@router.get("/stock-level-trends")
async def get_stock_level_trends(
    medication_id: Optional[int] = Query(None, description="Specific medication ID"),
    time_range: str = Query("7d", description="Time range: 7d, 30d, 90d"),
) -> Dict[str, Any]:
    """Get stock level trends with predictions"""
    try:
        analytics_logger.info(
            f"Getting stock level trends for time_range: {time_range}"
        )

        # Calculate date range
        end_date = date.today()
        if time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        if medication_id:
            # Get stock levels for specific medication
            cursor.execute(
                """
                SELECT 
                    ch.date,
                    ch.on_hand as stock_level
                FROM consumption_history ch
                JOIN medications m ON ch.med_id = m.med_id
                WHERE ch.med_id = ? AND ch.date >= ? AND ch.date <= ?
                ORDER BY ch.date
            """,
                (medication_id, start_date.isoformat(), end_date.isoformat()),
            )

            results = cursor.fetchall()

            # Get medication details
            cursor.execute(
                "SELECT name FROM medications WHERE med_id = ?", (medication_id,)
            )
            med_info = cursor.fetchone()

            medication_name = med_info[0] if med_info else f"Medication {medication_id}"
            reorder_point = 100  # Default reorder point

        else:
            # Get average stock levels across all medications
            cursor.execute(
                """
                SELECT 
                    ch.date,
                    AVG(ch.on_hand) as avg_stock_level
                FROM consumption_history ch
                JOIN medications m ON ch.med_id = m.med_id
                WHERE ch.date >= ? AND ch.date <= ?
                GROUP BY ch.date
                ORDER BY ch.date
            """,
                (start_date.isoformat(), end_date.isoformat()),
            )

            results = cursor.fetchall()
            medication_name = "Average Stock Levels"
            reorder_point = 100  # Default reorder point

        # Format data for charts
        stock_data = []
        for row in results:
            stock_data.append(
                {
                    "date": row[0],
                    "stock_level": round(row[1], 2),
                    "reorder_point": reorder_point,
                }
            )

        return {
            "medication_name": medication_name,
            "reorder_point": reorder_point,
            "data": stock_data,
            "time_range": time_range,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    except Exception as e:
        analytics_logger.error(f"Error getting stock level trends: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting stock level trends: {str(e)}"
        )


@router.get("/consumption-forecast")
async def get_consumption_forecast(
    medication_id: Optional[int] = Query(None, description="Specific medication ID"),
    forecast_days: int = Query(7, description="Number of days to forecast"),
    time_scale: str = Query(
        "weekly",
        regex="^(weekly|monthly|quarterly)$",
        description="Time scale for forecast aggregation",
    ),
) -> Dict[str, Any]:
    """Get consumption forecast with AI predictions sourced from poc_supplychain.db.

    The model uses recent daily consumption and weekday seasonality to produce
    realistic, non-flat daily forecasts.
    """
    try:
        analytics_logger.info(
            f"Getting consumption forecast for medication: {medication_id}, time_scale: {time_scale}"
        )

        # Adjust parameters based on time scale
        if time_scale == "weekly":
            # For weekly: 14 days forecast, 30 days history (reasonable for chart display)
            forecast_days = max(forecast_days, 14)
            historical_days = 30
        elif time_scale == "monthly":
            # For monthly: 60 days forecast, 90 days history
            forecast_days = max(forecast_days, 60)
            historical_days = 90
        elif time_scale == "quarterly":
            # For quarterly: 90 days forecast, 180 days history
            forecast_days = max(forecast_days, 90)
            historical_days = 180
        else:
            # Default to weekly
            historical_days = 30

        conn = data_loader.get_connection()
        cursor = conn.cursor()
        analytics_logger.info(f"Using database: {data_loader.db_path}")

        # Get the latest date available in the data instead of using today
        if medication_id:
            cursor.execute(
                "SELECT MAX(date) FROM consumption_history WHERE med_id = ?",
                (medication_id,),
            )
        else:
            cursor.execute("SELECT MAX(date) FROM consumption_history")

        latest_date_result = cursor.fetchone()
        if latest_date_result and latest_date_result[0]:
            latest_date = datetime.strptime(latest_date_result[0], "%Y-%m-%d").date()
        else:
            latest_date = date.today()

        # Use adjusted history period for seasonality from the latest available data
        historical_start = latest_date - timedelta(days=historical_days)
        analytics_logger.info(
            f"Latest data date: {latest_date}, Historical start date: {historical_start}, historical_days: {historical_days}"
        )

        if medication_id:
            query = """
                SELECT ch.date, SUM(ch.qty_dispensed) as consumption
                FROM consumption_history ch
                WHERE ch.med_id = ? AND ch.date >= ?
                GROUP BY ch.date
                ORDER BY ch.date
                """
            params = (medication_id, historical_start.isoformat())

            cursor.execute(query, params)
            rows = cursor.fetchall()  # Fetch consumption history results immediately

            cursor.execute(
                "SELECT name FROM medications WHERE med_id = ?", (medication_id,)
            )
            med_info = cursor.fetchone()
            medication_name = med_info[0] if med_info else f"Medication {medication_id}"
        else:
            cursor.execute(
                """
                SELECT ch.date, SUM(ch.qty_dispensed) as consumption
                FROM consumption_history ch
                WHERE ch.date >= ?
                GROUP BY ch.date
                ORDER BY ch.date
                """,
                (historical_start.isoformat(),),
            )
            rows = (
                cursor.fetchall()
            )  # Fetch dashboard consumption history results immediately
            medication_name = "Total Consumption"

        analytics_logger.info(f"Processing {len(rows)} rows from consumption_history")
        if len(rows) > 0:
            analytics_logger.info(
                f"Sample rows: {rows[:3]} ... {rows[-3:] if len(rows) > 3 else ''}"
            )

        # Build dense daily series (fill missing with 0 to keep structure)
        history_map: Dict[str, float] = {}
        for r in rows:
            history_map[str(r[0])] = float(r[1] or 0)

        # Generate continuous dates from historical_start to today
        today_d = date.today()
        dates: List[date] = []
        d = historical_start
        while d <= today_d:
            dates.append(d)
            d += timedelta(days=1)

        historical_data: List[Dict[str, Any]] = []
        for d in dates:
            ds = d.isoformat()
            historical_data.append(
                {"date": ds, "consumption": history_map.get(ds, 0.0)}
            )

        # Baseline metrics from history so they are always available (even if using DB forecasts)
        last_n_base = (
            historical_data[-84:] if len(historical_data) > 84 else historical_data
        )
        values_base = [float(item["consumption"] or 0) for item in last_n_base]
        recent_vals_base = values_base[-28:] if len(values_base) >= 28 else values_base
        earlier_vals_base = (
            values_base[-56:-28]
            if len(values_base) >= 56
            else values_base[: max(len(values_base) - 28, 0)]
        )
        recent_avg = sum(recent_vals_base) / max(len(recent_vals_base), 1)
        earlier_avg = (
            sum(earlier_vals_base) / max(len(earlier_vals_base), 1)
            if earlier_vals_base
            else recent_avg
        )
        if earlier_avg <= 0:
            earlier_avg = recent_avg or 1.0
        trend_change = (recent_avg - earlier_avg) / earlier_avg
        # Remove artificial trend caps to allow natural growth patterns
        if trend_change > 1.0:
            trend_change = 1.0  # Allow up to 100% growth
        if trend_change < -0.5:
            trend_change = -0.5  # Limit decline to 50%

        # Compute weekday factors from history (used to shape DB forecasts too)
        weekday_totals_base = {i: 0.0 for i in range(7)}
        weekday_counts_base = {i: 0 for i in range(7)}
        for item in last_n_base:
            dt_b = datetime.fromisoformat(item["date"]).date()
            wd_b = dt_b.weekday()
            val_b = float(item["consumption"] or 0)
            weekday_totals_base[wd_b] += val_b
            weekday_counts_base[wd_b] += 1
        overall_avg_base = sum(values_base) / max(len(values_base), 1) or 1.0
        weekday_factors_base = {
            wd: (weekday_totals_base[wd] / max(weekday_counts_base[wd], 1))
            / overall_avg_base
            for wd in range(7)
        }

        # Residual volatility from history (used to scale noise for DB forecasts)
        resids_base = []
        for item in last_n_base:
            dt_b = datetime.fromisoformat(item["date"]).date()
            wd_b = dt_b.weekday()
            expected_b = recent_avg * weekday_factors_base.get(wd_b, 1.0)
            resids_base.append((item["consumption"] or 0) - expected_b)
        if resids_base:
            mean_resid_b = sum(resids_base) / len(resids_base)
            var_b = sum((r - mean_resid_b) ** 2 for r in resids_base) / max(
                len(resids_base) - 1, 1
            )
            std_resid_base = var_b**0.5
        else:
            std_resid_base = max(1.0, recent_avg * 0.2)

        last_hist_date = datetime.fromisoformat(historical_data[-1]["date"]).date()
        # Use recent_avg instead of last value for continuity (avoid starting from 0)
        last_hist_value = recent_avg

        # Try to read forecasts from DB first (6-month horizon in forecasts_med)
        db_forecast: Optional[List[Dict[str, Any]]] = None
        if medication_id:
            cursor.execute(
                "SELECT horizon_days, forecast_mean FROM forecasts_med WHERE med_id = ? ORDER BY timestamp DESC LIMIT 1",
                (medication_id,),
            )
            fr = cursor.fetchone()
            if fr:
                horizon_days, forecast_mean_json = fr
                mean_list = json.loads(forecast_mean_json or "[]")
                if isinstance(mean_list, list) and len(mean_list) >= max(
                    1, forecast_days - 1
                ):
                    import random as _rnd
                    # Add fixed seed based on medication_id and date for consistent forecasts
                    seed_value = (medication_id or 0) * 10000 + last_hist_date.toordinal()
                    _rnd.seed(seed_value)

                    shaped = []
                    for i in range(forecast_days):
                        f_date = last_hist_date + timedelta(days=i)
                        wd = f_date.weekday()
                        if i == 0:
                            # Start forecast from recent average for smooth transition
                            pred = recent_avg
                        else:
                            idx = min(len(mean_list) - 1, i - 1)
                            base_level = float(mean_list[idx])
                            weekday_variation = 1.0 + _rnd.uniform(-0.2, 0.2)
                            pred = max(
                                0.0,
                                base_level
                                * weekday_factors_base.get(wd, 1.0)
                                * weekday_variation,
                            )
                            # Noise scaled by residual volatility and level
                            noise = _rnd.gauss(
                                0, max(std_resid_base * 0.6, pred * 0.15, 1.0)
                            )
                            pred = max(0.0, pred + noise)
                            # Occasional spikes
                            if _rnd.random() < 0.02:
                                pred *= _rnd.uniform(1.5, 3.0)
                        margin = max(std_resid_base * 1.0, pred * 0.25, 1.0)
                        shaped.append(
                            {
                                "date": f_date.isoformat(),
                                "predicted": round(pred, 2),
                                "upper_bound": round(pred + margin, 2),
                                "lower_bound": round(max(0.0, pred - margin), 2),
                            }
                        )
                    db_forecast = shaped
        else:
            # Average forecasts across all meds if available (use first N meds to limit load)
            cursor.execute(
                "SELECT horizon_days, forecast_mean FROM forecasts_med ORDER BY timestamp DESC"
            )
            rows_fc = cursor.fetchall()
            means = []
            for h, fm in rows_fc:
                try:
                    arr = json.loads(fm or "[]")
                    if isinstance(arr, list) and len(arr) >= max(1, forecast_days - 1):
                        means.append(
                            arr[: forecast_days - 1 if forecast_days > 1 else 1]
                        )
                except Exception:
                    continue
            if means:
                import numpy as _np
                import random as _rnd
                # Fixed seed for consistent dashboard forecasts
                seed_value = last_hist_date.toordinal()
                _rnd.seed(seed_value)

                # Fix: Sum forecasts across medications for dashboard totals, don't average them
                avg = _np.sum(_np.array(means, dtype=float), axis=0).tolist()
                shaped = []
                for i in range(forecast_days):
                    f_date = last_hist_date + timedelta(days=i)
                    wd = f_date.weekday()
                    if i == 0:
                        # Start dashboard forecast from recent average for continuity
                        pred = recent_avg
                    else:
                        idx = min(len(avg) - 1, i - 1)
                        base_level = float(avg[idx])
                        weekday_variation = 1.0 + _rnd.uniform(-0.2, 0.2)
                        pred = max(
                            0.0,
                            base_level
                            * weekday_factors_base.get(wd, 1.0)
                            * weekday_variation,
                        )
                        noise = _rnd.gauss(
                            0, max(std_resid_base * 0.6, pred * 0.15, 1.0)
                        )
                        pred = max(0.0, pred + noise)
                        if _rnd.random() < 0.02:
                            pred *= _rnd.uniform(1.5, 3.0)
                    margin = max(std_resid_base * 1.0, pred * 0.25, 1.0)
                    shaped.append(
                        {
                            "date": f_date.isoformat(),
                            "predicted": round(pred, 2),
                            "upper_bound": round(pred + margin, 2),
                            "lower_bound": round(max(0.0, pred - margin), 2),
                        }
                    )
                db_forecast = shaped

        if not historical_data:
            # Fallback
            base = 10.0
            forecast_data = [
                {
                    "date": (today_d + timedelta(days=i)).isoformat(),
                    "predicted": base,
                    "upper_bound": round(base * 1.2, 2),
                    "lower_bound": round(base * 0.8, 2),
                }
                for i in range(1, forecast_days + 1)
            ]
            return {
                "medication_name": medication_name,
                "historical_data": [],
                "forecast_data": forecast_data,
                "forecast_days": forecast_days,
                "avg_consumption": base,
                "trend": 0.0,
            }

        # If DB forecast is available, use it; otherwise compute on the fly
        if db_forecast is not None:
            forecast_data = db_forecast
        else:
            # Compute weekday seasonality factors from the last 12 weeks
            last_n = (
                historical_data[-84:] if len(historical_data) > 84 else historical_data
            )
            weekday_totals = {i: 0.0 for i in range(7)}
            weekday_counts = {i: 0 for i in range(7)}
            values = []
            for item in last_n:
                dt = datetime.fromisoformat(item["date"]).date()
                wd = dt.weekday()  # 0=Mon
                val = float(item["consumption"] or 0)
                weekday_totals[wd] += val
                weekday_counts[wd] += 1
                values.append(val)

            overall_avg = sum(values) / max(len(values), 1)
            # Avoid divide-by-zero
            if overall_avg <= 0:
                overall_avg = 1.0

            weekday_factors = {
                wd: (weekday_totals[wd] / max(weekday_counts[wd], 1)) / overall_avg
                for wd in range(7)
            }

            # Compute recent vs earlier averages to capture trend (last 4 weeks vs previous 4 weeks)
            recent_vals = values[-28:] if len(values) >= 28 else values
            earlier_vals = (
                values[-56:-28]
                if len(values) >= 56
                else values[: max(len(values) - 28, 0)]
            )
            recent_avg = sum(recent_vals) / max(len(recent_vals), 1)
            earlier_avg = (
                sum(earlier_vals) / max(len(earlier_vals), 1)
                if earlier_vals
                else recent_avg
            )
            if earlier_avg <= 0:
                earlier_avg = recent_avg or 1.0
            trend_change = (recent_avg - earlier_avg) / earlier_avg
            # Clamp to keep forecasts sane
            # Remove artificial trend caps for more realistic forecasts
            if trend_change > 1.0:
                trend_change = 1.0  # Allow up to 100% growth
            if trend_change < -0.5:
                trend_change = -0.5  # Limit decline to 50%

            # Residual std for CI
            expected_by_day = []
            resids = []
            for item in last_n:
                dt = datetime.fromisoformat(item["date"]).date()
                wd = dt.weekday()
                expected = recent_avg * weekday_factors.get(wd, 1.0)
                expected_by_day.append(expected)
                resids.append((item["consumption"] or 0) - expected)
            if resids:
                mean_resid = sum(resids) / len(resids)
                variance = sum((r - mean_resid) ** 2 for r in resids) / max(
                    len(resids) - 1, 1
                )
                std_resid = variance**0.5
            else:
                std_resid = recent_avg * 0.2

            # Build forecast repeating weekday pattern scaled by recent level and trend
            forecast_data = []
            for i in range(0, forecast_days):
                # Start forecasts from the last historical date for continuity
                future_date = last_hist_date + timedelta(days=i)
                wd = future_date.weekday()
                if i == 0:
                    # Use recent_avg for smooth visual transition from historical to forecast
                    pred = recent_avg
                else:
                    # Apply full trend impact for more realistic forecasts
                    base_level = recent_avg * (1 + trend_change)
                    import random
                    # Fixed seed for consistent fallback forecasts
                    seed_value = (medication_id or 0) * 10000 + last_hist_date.toordinal()
                    random.seed(seed_value)

                    daily_noise = random.gauss(0, std_resid * 0.25)
                    spike_mult = (
                        random.uniform(1.5, 3.0) if random.random() < 0.02 else 1.0
                    )
                    weekday_variation = 1.0 + random.uniform(-0.2, 0.2)
                    pred = max(
                        0.0,
                        (base_level + daily_noise)
                        * weekday_factors.get(wd, 1.0)
                        * weekday_variation
                        * spike_mult,
                    )

                margin = max(std_resid * 1.2, pred * 0.25)
                forecast_data.append(
                    {
                        "date": future_date.isoformat(),
                        "predicted": round(pred, 2),
                        "upper_bound": round(pred + margin, 2),
                        "lower_bound": round(max(0.0, pred - margin), 2),
                    }
                )

        # Apply scaling factors before aggregation to compensate for forecast underestimation
        if time_scale == "monthly":
            # Apply scaling factor for monthly aggregation (7-day periods)
            scaling_factor = 1.2  # 20% increase for weekly aggregation uncertainty
            for item in forecast_data:
                item["predicted"] = item["predicted"] * scaling_factor
                item["upper_bound"] = item["upper_bound"] * scaling_factor
                item["lower_bound"] = item["lower_bound"] * scaling_factor

            # Aggregate historical data by week (7-day periods)
            historical_data = aggregate_data_by_period(
                historical_data, 7, "consumption"
            )
            forecast_data = aggregate_data_by_period(forecast_data, 7, "predicted")
        elif time_scale == "quarterly":
            # Apply scaling factor for quarterly aggregation (30-day periods)
            scaling_factor = 1.5  # 50% increase for monthly aggregation uncertainty
            for item in forecast_data:
                item["predicted"] = item["predicted"] * scaling_factor
                item["upper_bound"] = item["upper_bound"] * scaling_factor
                item["lower_bound"] = item["lower_bound"] * scaling_factor

            # Aggregate historical data by month (~30-day periods)
            historical_data = aggregate_data_by_period(
                historical_data, 30, "consumption"
            )
            forecast_data = aggregate_data_by_period(forecast_data, 30, "predicted")
        # Weekly scale uses daily data (no aggregation needed)

        # Improve alignment for aggregated views to create smooth transitions
        if time_scale in ("monthly", "quarterly") and historical_data and forecast_data:
            # Align dates and values for smooth visual continuity
            forecast_data[0]["date"] = historical_data[-1]["date"]
            # Use the average of last few historical points for smooth transition
            last_historical_values = [
                item["consumption"]
                for item in historical_data[-3:]
                if item["consumption"] > 0
            ]
            if last_historical_values:
                smooth_transition_value = sum(last_historical_values) / len(
                    last_historical_values
                )
                forecast_data[0]["predicted"] = smooth_transition_value
                forecast_data[0]["upper_bound"] = smooth_transition_value * 1.25
                forecast_data[0]["lower_bound"] = max(
                    0.0, smooth_transition_value * 0.75
                )

        return {
            "medication_name": medication_name,
            "historical_data": historical_data,
            "forecast_data": forecast_data,
            "forecast_days": forecast_days,
            "avg_consumption": round(recent_avg, 2),
            "trend": round(trend_change, 3),
            "time_scale": time_scale,
        }

    except Exception as e:
        analytics_logger.error(f"Error getting consumption forecast: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting consumption forecast: {str(e)}"
        )


@router.get("/delivery-timeline")
async def get_delivery_timeline() -> List[Dict[str, Any]]:
    """Get delivery and manufacturing timeline data"""
    try:
        analytics_logger.info("Getting delivery timeline")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Get active purchase orders
        cursor.execute("""
            SELECT 
                po.po_id,
                po.supplier_name,
                po.status,
                po.created_at,
                po.total_amount,
                COUNT(poi.item_id) as item_count
            FROM purchase_orders po
            LEFT JOIN purchase_order_items poi ON po.po_id = poi.po_id
            WHERE po.status IN ('pending', 'approved', 'in-progress')
            GROUP BY po.po_id
            ORDER BY po.created_at DESC
            LIMIT 10
        """)

        po_results = cursor.fetchall()

        timeline_tasks = []

        # Convert purchase orders to timeline tasks
        for row in po_results:
            po_id, supplier_name, status, created_at, total_amount, item_count = row

            # Simulate start and end dates based on creation time and status
            created_date = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            ).date()

            if status == "pending":
                start_date = created_date + timedelta(days=1)
                end_date = start_date + timedelta(days=7)  # 7 days for delivery
                task_status = "pending"
                progress = 0
            elif status == "approved":
                start_date = created_date
                end_date = start_date + timedelta(days=5)
                task_status = "in-progress"
                progress = 30
            else:  # in-progress
                start_date = created_date
                end_date = start_date + timedelta(days=3)
                task_status = "in-progress"
                progress = 70

            timeline_tasks.append(
                {
                    "id": f"po-{po_id}",
                    "title": f"PO #{po_id}",
                    "description": f"{item_count} items from {supplier_name}",
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "status": task_status,
                    "type": "delivery",
                    "progress": progress,
                    "priority": "medium",
                    "metadata": {
                        "supplier": supplier_name,
                        "amount": total_amount,
                        "items": item_count,
                    },
                }
            )

        # Add some additional delivery/logistics tasks if needed (simulated)
        if len(timeline_tasks) < 3:  # Only add if we have few purchase orders
            today = date.today()
            additional_tasks = [
                {
                    "id": "del-001",
                    "title": "Emergency Stock Replenishment",
                    "description": "Urgent delivery for critical medications",
                    "startDate": (today + timedelta(days=1)).isoformat(),
                    "endDate": (today + timedelta(days=2)).isoformat(),
                    "status": "pending",
                    "type": "delivery",
                    "progress": 0,
                    "priority": "critical",
                    "metadata": {
                        "supplier": "Express Medical Supply",
                        "amount": 5200,
                        "items": 15,
                    },
                }
            ]

            timeline_tasks.extend(additional_tasks)

        return timeline_tasks

    except Exception as e:
        analytics_logger.error(f"Error getting delivery timeline: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting delivery timeline: {str(e)}"
        )
