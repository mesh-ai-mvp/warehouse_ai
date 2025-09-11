"""
Analytics Service Layer
Business logic for complex analytics calculations, caching, and data processing
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta, date
import json
import sqlite3
import hashlib
from loguru import logger
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader


class AnalyticsService:
    """Service for handling analytics calculations and caching"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.logger = logger.bind(name="analytics_service")
        self.cache_ttl_minutes = 15  # Cache for 15 minutes

    def _get_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key for operation and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{operation}:{param_str}".encode()).hexdigest()

    def _get_cached_result(
        self, cache_key: str, conn: sqlite3.Connection
    ) -> Optional[Dict[str, Any]]:
        """Get cached result if still valid"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT metric_value, expires_at 
                FROM analytics_cache 
                WHERE metric_key = ?
            """,
                (cache_key,),
            )

            result = cursor.fetchone()
            if result and datetime.now() < datetime.fromisoformat(result[1]):
                return json.loads(result[0])
            elif result:
                # Expired cache, delete it
                cursor.execute(
                    "DELETE FROM analytics_cache WHERE metric_key = ?", (cache_key,)
                )
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Cache retrieval error: {str(e)}")

        return None

    def _cache_result(
        self,
        cache_key: str,
        data: Dict[str, Any],
        time_range: str,
        conn: sqlite3.Connection,
    ):
        """Cache the result with appropriate TTL"""
        try:
            expires_at = datetime.now() + timedelta(minutes=self.cache_ttl_minutes)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO analytics_cache 
                (metric_key, metric_value, time_range, expires_at)
                VALUES (?, ?, ?, ?)
            """,
                (cache_key, json.dumps(data), time_range, expires_at.isoformat()),
            )

            conn.commit()
        except Exception as e:
            self.logger.warning(f"Cache storage error: {str(e)}")

    def calculate_advanced_kpis(
        self, time_range: str = "30d", filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate advanced KPIs with caching and complex business logic"""

        filters = filters or {}
        cache_key = self._get_cache_key(
            "advanced_kpis", {"time_range": time_range, "filters": filters}
        )

        conn = self.data_loader.get_connection()

        # Try to get cached result
        cached = self._get_cached_result(cache_key, conn)
        if cached:
            self.logger.info("Returning cached KPI results")
            conn.close()
            return cached

        self.logger.info(f"Calculating advanced KPIs for time_range: {time_range}")

        try:
            cursor = conn.cursor()

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
                start_date = end_date - timedelta(days=30)

            # Advanced KPIs calculation
            kpis = {}

            # 1. Financial KPIs
            financial_data = self._calculate_financial_kpis(
                cursor, start_date, end_date
            )
            kpis.update(financial_data)

            # 2. Operational KPIs
            operational_data = self._calculate_operational_kpis(
                cursor, start_date, end_date
            )
            kpis.update(operational_data)

            # 3. Quality KPIs
            quality_data = self._calculate_quality_kpis(cursor, start_date, end_date)
            kpis.update(quality_data)

            # 4. Trend analysis
            trends = self._calculate_trend_analysis(cursor, start_date, end_date)

            result = {
                "kpis": kpis,
                "trends": trends,
                "metadata": {
                    "time_range": time_range,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "calculated_at": datetime.now().isoformat(),
                },
            }

            # Cache the result
            self._cache_result(cache_key, result, time_range, conn)

            conn.close()
            return result

        except Exception as e:
            conn.close()
            self.logger.error(f"Error calculating advanced KPIs: {str(e)}")
            raise

    def _calculate_financial_kpis(
        self, cursor: sqlite3.Cursor, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Calculate financial KPIs"""

        # Total revenue and order metrics
        cursor.execute(
            """
            SELECT 
                COALESCE(SUM(total_amount), 0) as total_revenue,
                COUNT(*) as total_orders,
                AVG(total_amount) as avg_order_value,
                MIN(total_amount) as min_order_value,
                MAX(total_amount) as max_order_value,
                COUNT(DISTINCT supplier_id) as active_suppliers
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        financial_row = cursor.fetchone()

        # Revenue by supplier
        cursor.execute(
            """
            SELECT 
                supplier_name,
                SUM(total_amount) as supplier_revenue,
                COUNT(*) as supplier_orders
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY supplier_id, supplier_name
            ORDER BY supplier_revenue DESC
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        supplier_revenues = cursor.fetchall()

        # Calculate revenue concentration (top 3 suppliers)
        total_revenue = financial_row[0] if financial_row else 0
        top_3_revenue = (
            sum(row[1] for row in supplier_revenues[:3]) if supplier_revenues else 0
        )
        revenue_concentration = (top_3_revenue / max(total_revenue, 1)) * 100

        return {
            "totalRevenue": round(financial_row[0] if financial_row else 0, 2),
            "totalOrders": financial_row[1] if financial_row else 0,
            "avgOrderValue": round(
                financial_row[2] if financial_row and financial_row[2] else 0, 2
            ),
            "minOrderValue": round(
                financial_row[3] if financial_row and financial_row[3] else 0, 2
            ),
            "maxOrderValue": round(
                financial_row[4] if financial_row and financial_row[4] else 0, 2
            ),
            "activeSuppliers": financial_row[5] if financial_row else 0,
            "revenueConcentration": round(revenue_concentration, 1),
            "topSuppliers": [
                {"name": row[0], "revenue": round(row[1], 2), "orders": row[2]}
                for row in supplier_revenues[:5]
            ],
        }

    def _calculate_operational_kpis(
        self, cursor: sqlite3.Cursor, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Calculate operational KPIs"""

        # Inventory turnover and stock metrics
        cursor.execute(
            """
            WITH latest_stock AS (
                SELECT 
                    med_id,
                    on_hand as current_stock,
                    ROW_NUMBER() OVER (PARTITION BY med_id ORDER BY date DESC) as rn
                FROM consumption_history
                WHERE date >= ?
            ),
            consumption_stats AS (
                SELECT 
                    med_id,
                    AVG(qty_dispensed) as avg_daily_consumption,
                    SUM(qty_dispensed) as total_consumption
                FROM consumption_history
                WHERE date >= ? AND date <= ?
                GROUP BY med_id
            )
            SELECT 
                COUNT(DISTINCT ls.med_id) as total_medications,
                AVG(ls.current_stock) as avg_stock_level,
                AVG(cs.avg_daily_consumption) as avg_daily_consumption,
                COUNT(CASE WHEN ls.current_stock <= 20 THEN 1 END) as critical_stock_items,
                COUNT(CASE WHEN ls.current_stock <= 50 THEN 1 END) as low_stock_items,
                SUM(cs.total_consumption) as total_consumption
            FROM latest_stock ls
            LEFT JOIN consumption_stats cs ON ls.med_id = cs.med_id
            WHERE ls.rn = 1
        """,
            (start_date.isoformat(), start_date.isoformat(), end_date.isoformat()),
        )

        operational_row = cursor.fetchone()

        # Calculate inventory turnover
        avg_stock = operational_row[1] if operational_row and operational_row[1] else 0
        total_consumption = (
            operational_row[5] if operational_row and operational_row[5] else 0
        )
        inventory_turnover = (
            (total_consumption / max(avg_stock, 1)) if avg_stock > 0 else 0
        )

        # Order fulfillment metrics
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders,
                AVG(CASE 
                    WHEN actual_delivery_date IS NOT NULL AND requested_delivery_date IS NOT NULL 
                    THEN julianday(actual_delivery_date) - julianday(requested_delivery_date)
                    ELSE NULL 
                END) as avg_delivery_delay
            FROM purchase_orders
            WHERE created_at >= ? AND created_at <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        fulfillment_row = cursor.fetchone()

        # Calculate fulfillment rate
        total_orders = fulfillment_row[0] if fulfillment_row else 0
        completed_orders = fulfillment_row[1] if fulfillment_row else 0
        fulfillment_rate = (
            (completed_orders / max(total_orders, 1)) * 100 if total_orders > 0 else 0
        )

        return {
            "totalMedications": operational_row[0] if operational_row else 0,
            "avgStockLevel": round(
                operational_row[1] if operational_row and operational_row[1] else 0, 1
            ),
            "avgDailyConsumption": round(
                operational_row[2] if operational_row and operational_row[2] else 0, 1
            ),
            "criticalStockItems": operational_row[3] if operational_row else 0,
            "lowStockItems": operational_row[4] if operational_row else 0,
            "inventoryTurnover": round(inventory_turnover, 2),
            "fulfillmentRate": round(fulfillment_rate, 1),
            "avgDeliveryDelay": round(
                fulfillment_row[3] if fulfillment_row and fulfillment_row[3] else 0, 1
            ),
            "orderCancellationRate": round(
                (fulfillment_row[2] / max(total_orders, 1)) * 100
                if fulfillment_row and total_orders > 0
                else 0,
                1,
            ),
        }

    def _calculate_quality_kpis(
        self, cursor: sqlite3.Cursor, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Calculate quality and compliance KPIs"""

        # Supplier quality metrics
        cursor.execute(
            """
            SELECT 
                COUNT(DISTINCT supplier_id) as total_suppliers,
                AVG(CASE 
                    WHEN actual_delivery_date <= requested_delivery_date THEN 1.0 
                    ELSE 0.0 
                END) * 100 as on_time_delivery_rate,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_deliveries,
                COUNT(*) as total_deliveries
            FROM purchase_orders
            WHERE created_at >= ? AND created_at <= ?
            AND actual_delivery_date IS NOT NULL
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        quality_row = cursor.fetchone()

        # Stock accuracy and compliance
        cursor.execute(
            """
            SELECT 
                AVG(CASE WHEN censored = 0 THEN 1.0 ELSE 0.0 END) * 100 as stock_accuracy,
                COUNT(CASE WHEN censored = 1 THEN 1 END) as stockout_incidents,
                COUNT(*) as total_demand_events
            FROM consumption_history
            WHERE date >= ? AND date <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        accuracy_row = cursor.fetchone()

        # Calculate service level
        total_demand = accuracy_row[2] if accuracy_row else 0
        stockout_incidents = accuracy_row[1] if accuracy_row else 0
        service_level = (
            ((total_demand - stockout_incidents) / max(total_demand, 1)) * 100
            if total_demand > 0
            else 0
        )

        return {
            "totalSuppliers": quality_row[0] if quality_row else 0,
            "onTimeDeliveryRate": round(
                quality_row[1] if quality_row and quality_row[1] else 0, 1
            ),
            "deliverySuccessRate": round(
                (quality_row[2] / max(quality_row[3], 1)) * 100
                if quality_row and quality_row[3] > 0
                else 0,
                1,
            ),
            "stockAccuracy": round(
                accuracy_row[0] if accuracy_row and accuracy_row[0] else 0, 1
            ),
            "serviceLevel": round(service_level, 1),
            "stockoutIncidents": stockout_incidents,
        }

    def _calculate_trend_analysis(
        self, cursor: sqlite3.Cursor, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Calculate trend analysis comparing with previous period"""

        # Calculate previous period dates
        period_length = (end_date - start_date).days
        prev_start_date = start_date - timedelta(days=period_length)
        prev_end_date = start_date

        # Current period metrics
        cursor.execute(
            """
            SELECT 
                COALESCE(SUM(total_amount), 0) as revenue,
                COUNT(*) as orders,
                AVG(total_amount) as avg_order_value
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at <= ?
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        current_metrics = cursor.fetchone()

        # Previous period metrics
        cursor.execute(
            """
            SELECT 
                COALESCE(SUM(total_amount), 0) as revenue,
                COUNT(*) as orders,
                AVG(total_amount) as avg_order_value
            FROM purchase_orders 
            WHERE created_at >= ? AND created_at < ?
        """,
            (prev_start_date.isoformat(), prev_end_date.isoformat()),
        )

        prev_metrics = cursor.fetchone()

        # Calculate trends
        def calculate_trend(current, previous):
            if previous and previous > 0:
                return round(((current - previous) / previous) * 100, 1)
            return 0.0

        current_revenue = current_metrics[0] if current_metrics else 0
        current_orders = current_metrics[1] if current_metrics else 0
        current_avg_order = (
            current_metrics[2] if current_metrics and current_metrics[2] else 0
        )

        prev_revenue = prev_metrics[0] if prev_metrics else 0
        prev_orders = prev_metrics[1] if prev_metrics else 0
        prev_avg_order = prev_metrics[2] if prev_metrics and prev_metrics[2] else 0

        return {
            "revenueChange": calculate_trend(current_revenue, prev_revenue),
            "ordersChange": calculate_trend(current_orders, prev_orders),
            "avgOrderValueChange": calculate_trend(current_avg_order, prev_avg_order),
            "period": {
                "current": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "previous": {
                    "start": prev_start_date.isoformat(),
                    "end": prev_end_date.isoformat(),
                },
            },
        }

    def calculate_predictive_analytics(
        self, medication_id: Optional[str] = None, forecast_days: int = 30
    ) -> Dict[str, Any]:
        """Calculate predictive analytics and forecasts"""

        self.logger.info(f"Calculating predictive analytics for {forecast_days} days")

        conn = self.data_loader.get_connection()
        cursor = conn.cursor()

        try:
            # Get historical consumption data
            if medication_id:
                cursor.execute(
                    """
                    SELECT date, qty_dispensed
                    FROM consumption_history
                    WHERE med_id = ? AND date >= date('now', '-90 days')
                    ORDER BY date
                """,
                    (medication_id,),
                )
            else:
                cursor.execute("""
                    SELECT date, SUM(qty_dispensed) as total_dispensed
                    FROM consumption_history
                    WHERE date >= date('now', '-90 days')
                    GROUP BY date
                    ORDER BY date
                """)

            historical_data = cursor.fetchall()

            if not historical_data:
                conn.close()
                return {"forecast": [], "confidence": 0, "trend": "unknown"}

            # Simple trend analysis and forecasting
            consumption_values = [row[1] for row in historical_data]
            dates = [row[0] for row in historical_data]

            # Calculate trend
            if len(consumption_values) >= 7:
                recent_avg = sum(consumption_values[-7:]) / 7
                older_avg = (
                    sum(consumption_values[-14:-7]) / 7
                    if len(consumption_values) >= 14
                    else recent_avg
                )

                if older_avg > 0:
                    trend_percentage = ((recent_avg - older_avg) / older_avg) * 100
                else:
                    trend_percentage = 0

                if trend_percentage > 5:
                    trend = "increasing"
                elif trend_percentage < -5:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
                recent_avg = sum(consumption_values) / len(consumption_values)
                trend_percentage = 0

            # Simple forecast (moving average with trend)
            forecast = []
            base_forecast = recent_avg
            daily_trend = trend_percentage / 100 / 30  # Daily trend factor

            for i in range(forecast_days):
                forecast_value = base_forecast * (1 + daily_trend * i)
                forecast_date = datetime.strptime(dates[-1], "%Y-%m-%d") + timedelta(
                    days=i + 1
                )

                forecast.append(
                    {
                        "date": forecast_date.strftime("%Y-%m-%d"),
                        "forecast": max(0, round(forecast_value, 1)),
                        "confidence": max(
                            0.3, 0.9 - (i / forecast_days) * 0.6
                        ),  # Decreasing confidence
                    }
                )

            # Calculate overall confidence
            data_quality = min(
                1.0, len(consumption_values) / 30
            )  # More data = higher confidence
            variance = (
                sum([(x - recent_avg) ** 2 for x in consumption_values[-7:]]) / 7
                if len(consumption_values) >= 7
                else 0
            )
            stability = max(0.1, 1 - (variance / max(recent_avg, 1)))

            overall_confidence = (data_quality * stability) * 0.9  # Max 90% confidence

            conn.close()

            return {
                "forecast": forecast,
                "confidence": round(overall_confidence, 2),
                "trend": trend,
                "trend_percentage": round(trend_percentage, 1),
                "recent_avg": round(recent_avg, 1),
                "data_points": len(consumption_values),
            }

        except Exception as e:
            conn.close()
            self.logger.error(f"Error calculating predictive analytics: {str(e)}")
            raise

    def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            conn = self.data_loader.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM analytics_cache WHERE expires_at < ?",
                (datetime.now().isoformat(),),
            )
            deleted_count = cursor.rowcount

            conn.commit()
            conn.close()

            self.logger.info(f"Cleaned up {deleted_count} expired cache entries")

        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {str(e)}")
