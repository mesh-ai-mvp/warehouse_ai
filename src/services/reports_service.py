"""
Reports Service Layer
Business logic for report generation, template management, and export functionality
"""

import csv
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader


class ReportsService:
    """Service for handling report generation and management"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.logger = logger.bind(name="reports_service")
        self.report_output_dir = (
            "reports_output"  # Directory for generated report files
        )

        # Ensure output directory exists
        os.makedirs(self.report_output_dir, exist_ok=True)

    def validate_report_template(
        self, template_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate report template structure and required fields"""

        required_fields = ["name", "type", "template_data", "fields_config"]

        # Check required fields
        for field in required_fields:
            if field not in template_data or not template_data[field]:
                return False, f"Missing required field: {field}"

        # Validate type
        valid_types = ["inventory", "financial", "supplier", "consumption", "custom"]
        if template_data["type"] not in valid_types:
            return (
                False,
                f"Invalid report type. Must be one of: {', '.join(valid_types)}",
            )

        # Validate template_data structure
        template_config = template_data["template_data"]
        if not isinstance(template_config, dict) or "title" not in template_config:
            return (
                False,
                "template_data must be a dictionary with at least a 'title' field",
            )

        # Validate fields_config structure
        fields_config = template_data["fields_config"]
        if not isinstance(fields_config, dict) or "fields" not in fields_config:
            return False, "fields_config must be a dictionary with a 'fields' array"

        fields = fields_config["fields"]
        if not isinstance(fields, list) or len(fields) == 0:
            return False, "fields_config must contain at least one field definition"

        # Validate each field definition
        for i, field in enumerate(fields):
            if not isinstance(field, dict):
                return False, f"Field {i} must be a dictionary"

            if "name" not in field or "type" not in field:
                return False, f"Field {i} must have 'name' and 'type' properties"

            valid_field_types = [
                "text",
                "number",
                "date",
                "currency",
                "percentage",
                "boolean",
                "rating",
            ]
            if field["type"] not in valid_field_types:
                return (
                    False,
                    f"Field {i} has invalid type. Must be one of: {', '.join(valid_field_types)}",
                )

        return True, None

    def generate_report_data(
        self, template_id: int, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate report data based on template and parameters"""

        parameters = parameters or {}
        conn = self.data_loader.get_connection()

        try:
            cursor = conn.cursor()

            # Get template
            cursor.execute(
                "SELECT * FROM report_templates WHERE id = ? AND is_active = 1",
                (template_id,),
            )
            template_row = cursor.fetchone()

            if not template_row:
                raise ValueError(f"Template {template_id} not found or inactive")

            template_name = template_row[1]
            template_type = template_row[3]
            template_data = json.loads(template_row[4]) if template_row[4] else {}
            fields_config = json.loads(template_row[5]) if template_row[5] else {}
            default_params = json.loads(template_row[10]) if template_row[10] else {}

            # Merge parameters
            effective_params = {**default_params, **parameters}

            self.logger.info(
                f"Generating report data for template '{template_name}' (type: {template_type})"
            )

            # Generate data based on report type
            if template_type == "inventory":
                data = self._generate_inventory_data(
                    cursor, effective_params, fields_config
                )
            elif template_type == "financial":
                data = self._generate_financial_data(
                    cursor, effective_params, fields_config
                )
            elif template_type == "supplier":
                data = self._generate_supplier_data(
                    cursor, effective_params, fields_config
                )
            elif template_type == "consumption":
                data = self._generate_consumption_data(
                    cursor, effective_params, fields_config
                )
            elif template_type == "custom":
                data = self._generate_custom_data(
                    cursor, effective_params, fields_config, template_data
                )
            else:
                raise ValueError(f"Unsupported report type: {template_type}")

            # Add metadata
            result = {
                "template_id": template_id,
                "template_name": template_name,
                "template_type": template_type,
                "generated_at": datetime.now().isoformat(),
                "parameters": effective_params,
                "data": data,
                "total_records": len(data),
                "fields": fields_config.get("fields", []),
            }

            conn.close()
            return result

        except Exception as e:
            conn.close()
            self.logger.error(f"Error generating report data: {str(e)}")
            raise

    def _generate_inventory_data(
        self,
        cursor: sqlite3.Cursor,
        params: Dict[str, Any],
        fields_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate inventory report data"""

        low_stock_only = params.get("lowStockOnly", False)
        params.get("includeExpired", True)
        category_filter = params.get("category")
        supplier_filter = params.get("supplier")

        # Build dynamic query based on requested fields
        field_mapping = {
            "name": "m.name",
            "category": "m.category",
            "current_stock": "COALESCE(ch.on_hand, 0)",
            "reorder_point": "COALESCE(ac.avg_daily * 30, 100)",
            "supplier": "s.name",
            "pack_size": "m.pack_size",
            "shelf_life_days": "m.shelf_life_days",
            "days_supply": "CASE WHEN ac.avg_daily > 0 THEN ch.on_hand / ac.avg_daily ELSE 30 END",
            "total_value": "COALESCE(ch.on_hand, 0) * COALESCE(dp.price_per_unit, 0)",
            "last_updated": "ch.date",
            "stock_status": """
                CASE 
                    WHEN COALESCE(ch.on_hand, 0) <= COALESCE(ac.avg_daily * 10, 30) THEN 'Critical'
                    WHEN COALESCE(ch.on_hand, 0) <= COALESCE(ac.avg_daily * 20, 60) THEN 'Low'
                    WHEN COALESCE(ch.on_hand, 0) <= COALESCE(ac.avg_daily * 50, 150) THEN 'Medium'
                    ELSE 'High'
                END
            """,
        }

        # Get requested fields
        requested_fields = [field["name"] for field in fields_config.get("fields", [])]

        # Build SELECT clause
        select_fields = []
        for field in requested_fields:
            if field in field_mapping:
                select_fields.append(f"{field_mapping[field]} as {field}")
            else:
                # Default fallback
                select_fields.append(f"NULL as {field}")

        if not select_fields:
            select_fields = [
                "m.name",
                "m.category",
                "COALESCE(ch.on_hand, 0) as current_stock",
            ]

        query = f"""
            SELECT {", ".join(select_fields)}
            FROM medications m
            LEFT JOIN (
                SELECT med_id, on_hand, date,
                       ROW_NUMBER() OVER (PARTITION BY med_id ORDER BY date DESC) as rn
                FROM consumption_history
            ) ch ON m.med_id = ch.med_id AND ch.rn = 1
            LEFT JOIN (
                SELECT med_id, AVG(qty_dispensed) as avg_daily
                FROM consumption_history
                WHERE date >= date('now', '-30 days')
                GROUP BY med_id
            ) ac ON m.med_id = ac.med_id
            LEFT JOIN suppliers s ON m.supplier_id = s.supplier_id
            LEFT JOIN (
                SELECT med_id, price_per_unit,
                       ROW_NUMBER() OVER (PARTITION BY med_id ORDER BY valid_from DESC) as rn
                FROM drug_prices
            ) dp ON m.med_id = dp.med_id AND dp.rn = 1
        """

        where_conditions = []
        query_params = []

        if low_stock_only:
            where_conditions.append(
                "COALESCE(ch.on_hand, 0) <= COALESCE(ac.avg_daily * 30, 100)"
            )

        if category_filter:
            where_conditions.append("m.category = ?")
            query_params.append(category_filter)

        if supplier_filter:
            where_conditions.append("s.name = ?")
            query_params.append(supplier_filter)

        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)

        query += " ORDER BY m.category, m.name"

        cursor.execute(query, query_params)
        results = cursor.fetchall()

        # Convert to list of dictionaries
        data = []
        for row in results:
            record = {}
            for i, field in enumerate(requested_fields):
                value = row[i] if i < len(row) else None

                # Format values based on field type
                field_def = next(
                    (f for f in fields_config.get("fields", []) if f["name"] == field),
                    {},
                )
                field_type = field_def.get("type", "text")

                if field_type == "number" and value is not None:
                    record[field] = int(value)
                elif field_type == "currency" and value is not None:
                    record[field] = round(float(value), 2)
                elif field_type == "percentage" and value is not None:
                    record[field] = round(float(value), 1)
                else:
                    record[field] = value

            data.append(record)

        return data

    def _generate_financial_data(
        self,
        cursor: sqlite3.Cursor,
        params: Dict[str, Any],
        fields_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate financial report data"""

        include_forecasts = params.get("includeForecasts", True)
        time_range = params.get("timeRange", "6m")

        # Calculate date range
        end_date = date.today()
        if time_range == "3m":
            start_date = end_date - timedelta(days=90)
        elif time_range == "6m":
            start_date = end_date - timedelta(days=180)
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=180)

        # Get monthly financial data
        cursor.execute(
            """
            SELECT 
                strftime('%Y-%m', created_at) as period,
                SUM(total_amount) as revenue,
                COUNT(*) as orders,
                AVG(total_amount) as avg_order_value,
                COUNT(DISTINCT supplier_id) as unique_suppliers,
                MIN(total_amount) as min_order,
                MAX(total_amount) as max_order
            FROM purchase_orders
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY period
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        results = cursor.fetchall()

        data = []
        for row in results:
            (
                period,
                revenue,
                orders,
                avg_order_value,
                unique_suppliers,
                min_order,
                max_order,
            ) = row

            # Convert period to readable format
            try:
                period_date = datetime.strptime(period, "%Y-%m")
                period_label = period_date.strftime("%b %Y")
            except ValueError:
                period_label = period

            # Calculate forecasts if requested
            forecast = revenue * 1.05 if include_forecasts and revenue else 0

            record = {
                "period": period_label,
                "revenue": round(revenue or 0, 2),
                "orders": orders or 0,
                "avg_order_value": round(avg_order_value or 0, 2),
                "unique_suppliers": unique_suppliers or 0,
                "min_order": round(min_order or 0, 2),
                "max_order": round(max_order or 0, 2),
                "forecast": round(forecast, 2) if include_forecasts else None,
            }

            data.append(record)

        return data

    def _generate_supplier_data(
        self,
        cursor: sqlite3.Cursor,
        params: Dict[str, Any],
        fields_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate supplier performance report data"""

        min_order_threshold = params.get("minOrderThreshold", 1)
        time_range = params.get("timeRange", "3m")

        # Calculate date range
        end_date = date.today()
        if time_range == "1m":
            start_date = end_date - timedelta(days=30)
        elif time_range == "3m":
            start_date = end_date - timedelta(days=90)
        elif time_range == "6m":
            start_date = end_date - timedelta(days=180)
        else:
            start_date = end_date - timedelta(days=90)

        cursor.execute(
            """
            SELECT 
                s.name,
                s.status,
                s.avg_lead_time,
                s.email,
                s.contact_name,
                s.phone,
                COUNT(po.po_id) as total_orders,
                SUM(po.total_amount) as total_value,
                AVG(po.total_amount) as avg_order_value,
                COUNT(CASE 
                    WHEN po.actual_delivery_date <= po.requested_delivery_date 
                    THEN 1 
                END) as on_time_orders,
                AVG(CASE 
                    WHEN po.actual_delivery_date > po.requested_delivery_date 
                    THEN julianday(po.actual_delivery_date) - julianday(po.requested_delivery_date)
                    ELSE 0 
                END) as avg_delay,
                COUNT(CASE WHEN po.status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN po.status = 'cancelled' THEN 1 END) as cancelled_orders
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
                AND po.created_at >= ? AND po.created_at <= ?
            GROUP BY s.supplier_id, s.name, s.status, s.avg_lead_time, s.email, s.contact_name, s.phone
            HAVING COUNT(po.po_id) >= ?
            ORDER BY total_orders DESC, total_value DESC
        """,
            (start_date.isoformat(), end_date.isoformat(), min_order_threshold),
        )

        results = cursor.fetchall()

        data = []
        for row in results:
            (
                name,
                status,
                avg_lead_time,
                email,
                contact_name,
                phone,
                total_orders,
                total_value,
                avg_order_value,
                on_time_orders,
                avg_delay,
                completed_orders,
                cancelled_orders,
            ) = row

            # Calculate performance metrics
            on_time_percentage = (
                (on_time_orders / max(total_orders, 1)) * 100 if total_orders > 0 else 0
            )
            completion_rate = (
                (completed_orders / max(total_orders, 1)) * 100
                if total_orders > 0
                else 0
            )
            cancellation_rate = (
                (cancelled_orders / max(total_orders, 1)) * 100
                if total_orders > 0
                else 0
            )

            # Calculate rating based on performance
            if on_time_percentage >= 95:
                rating = 4.8
            elif on_time_percentage >= 90:
                rating = 4.5
            elif on_time_percentage >= 85:
                rating = 4.2
            elif on_time_percentage >= 80:
                rating = 4.0
            else:
                rating = 3.5

            # Adjust rating based on other factors
            if completion_rate >= 95:
                rating += 0.1
            if cancellation_rate <= 2:
                rating += 0.1
            if avg_delay and avg_delay <= 1:
                rating += 0.1

            rating = min(5.0, rating)  # Cap at 5.0

            record = {
                "name": name,
                "status": status or "Unknown",
                "avg_lead_time": round(avg_lead_time or 0, 1),
                "email": email or "",
                "contact_name": contact_name or "",
                "phone": phone or "",
                "orders": total_orders,
                "total_value": round(total_value or 0, 2),
                "avg_order_value": round(avg_order_value or 0, 2),
                "on_time": round(on_time_percentage, 1),
                "avg_delay": round(avg_delay or 0, 1),
                "completion_rate": round(completion_rate, 1),
                "cancellation_rate": round(cancellation_rate, 1),
                "rating": round(rating, 1),
            }

            data.append(record)

        return data

    def _generate_consumption_data(
        self,
        cursor: sqlite3.Cursor,
        params: Dict[str, Any],
        fields_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate consumption trends report data"""

        time_range = params.get("timeRange", "6m")
        include_forecasts = params.get("includeForecasts", True)
        medication_id = params.get("medicationId")

        # Calculate date range
        end_date = date.today()
        if time_range == "3m":
            start_date = end_date - timedelta(days=90)
        elif time_range == "6m":
            start_date = end_date - timedelta(days=180)
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=180)

        # Base query for consumption data
        base_query = """
            SELECT 
                strftime('%Y-%m', ch.date) as period,
                SUM(ch.qty_dispensed) as consumption,
                AVG(ch.qty_dispensed) as avg_daily_consumption,
                COUNT(DISTINCT ch.med_id) as unique_medications,
                COUNT(DISTINCT po.po_id) as orders_placed,
                SUM(CASE WHEN ch.censored = 1 THEN 1 ELSE 0 END) as stockout_days,
                COUNT(*) as total_days
            FROM consumption_history ch
            LEFT JOIN medications m ON ch.med_id = m.med_id
            LEFT JOIN purchase_orders po ON m.supplier_id = po.supplier_id 
                AND date(po.created_at) = ch.date
            WHERE ch.date >= ? AND ch.date <= ?
        """

        query_params = [start_date.isoformat(), end_date.isoformat()]

        if medication_id:
            base_query += " AND ch.med_id = ?"
            query_params.append(medication_id)

        base_query += " GROUP BY strftime('%Y-%m', ch.date) ORDER BY period"

        cursor.execute(base_query, query_params)
        results = cursor.fetchall()

        data = []
        for row in results:
            (
                period,
                consumption,
                avg_daily_consumption,
                unique_medications,
                orders_placed,
                stockout_days,
                total_days,
            ) = row

            # Convert period to readable format
            try:
                period_date = datetime.strptime(period, "%Y-%m")
                period_label = period_date.strftime("%b %Y")
            except ValueError:
                period_label = period

            # Calculate forecast if requested (simple trend-based)
            forecast = consumption * 1.05 if include_forecasts and consumption else 0

            # Calculate service level
            service_level = (
                ((total_days - stockout_days) / max(total_days, 1)) * 100
                if total_days > 0
                else 0
            )

            record = {
                "period": period_label,
                "month": period_date.strftime("%b")
                if "period_date" in locals()
                else period,
                "consumption": int(consumption or 0),
                "avg_daily_consumption": round(avg_daily_consumption or 0, 1),
                "unique_medications": unique_medications or 0,
                "orders": orders_placed or 0,
                "forecast": int(forecast) if include_forecasts else None,
                "service_level": round(service_level, 1),
                "stockout_incidents": stockout_days or 0,
            }

            data.append(record)

        return data

    def _generate_custom_data(
        self,
        cursor: sqlite3.Cursor,
        params: Dict[str, Any],
        fields_config: Dict[str, Any],
        template_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate custom report data based on template configuration"""

        # Custom reports allow for flexible SQL queries defined in template_data
        custom_query = template_data.get("custom_query")

        if not custom_query:
            # Fallback to basic inventory query
            return self._generate_inventory_data(cursor, params, fields_config)

        # Execute custom query with parameters
        try:
            # Simple parameter substitution (basic security - in production, use proper parameterization)
            formatted_query = custom_query
            for key, value in params.items():
                if isinstance(value, str):
                    formatted_query = formatted_query.replace(
                        f"{{{{ {key} }}}}", f"'{value}'"
                    )
                else:
                    formatted_query = formatted_query.replace(
                        f"{{{{ {key} }}}}", str(value)
                    )

            cursor.execute(formatted_query)
            results = cursor.fetchall()

            # Convert to dictionaries using field config
            field_names = [field["name"] for field in fields_config.get("fields", [])]

            data = []
            for row in results:
                record = {}
                for i, field_name in enumerate(field_names):
                    if i < len(row):
                        record[field_name] = row[i]
                    else:
                        record[field_name] = None
                data.append(record)

            return data

        except Exception as e:
            self.logger.error(f"Error executing custom query: {str(e)}")
            raise ValueError(f"Custom query execution failed: {str(e)}")

    def export_report_to_csv(
        self, report_data: Dict[str, Any], filename: Optional[str] = None
    ) -> str:
        """Export report data to CSV file"""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.csv"

        filepath = os.path.join(self.report_output_dir, filename)

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                if not report_data["data"]:
                    writer = csv.writer(csvfile)
                    writer.writerow(["No data available"])
                else:
                    fieldnames = list(report_data["data"][0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    # Write header with readable labels
                    header_row = {}
                    for field in fieldnames:
                        field_def = next(
                            (
                                f
                                for f in report_data.get("fields", [])
                                if f["name"] == field
                            ),
                            {},
                        )
                        header_row[field] = field_def.get(
                            "label", field.replace("_", " ").title()
                        )
                    writer.writerow(header_row)

                    # Write data
                    writer.writerows(report_data["data"])

            self.logger.info(f"Report exported to CSV: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error exporting report to CSV: {str(e)}")
            raise

    def export_report_to_json(
        self, report_data: Dict[str, Any], filename: Optional[str] = None
    ) -> str:
        """Export report data to JSON file"""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.json"

        filepath = os.path.join(self.report_output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as jsonfile:
                json.dump(report_data, jsonfile, indent=2, ensure_ascii=False)

            self.logger.info(f"Report exported to JSON: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error exporting report to JSON: {str(e)}")
            raise

    def schedule_report(
        self,
        template_id: int,
        cron_expression: str,
        next_run: Optional[datetime] = None,
    ) -> int:
        """Schedule a report for automatic generation"""

        conn = self.data_loader.get_connection()

        try:
            cursor = conn.cursor()

            # Verify template exists
            cursor.execute(
                "SELECT id FROM report_templates WHERE id = ? AND is_active = 1",
                (template_id,),
            )
            if not cursor.fetchone():
                raise ValueError(f"Template {template_id} not found or inactive")

            # Calculate next run time if not provided
            if not next_run:
                next_run = datetime.now() + timedelta(
                    hours=1
                )  # Default to 1 hour from now

            cursor.execute(
                """
                INSERT INTO report_schedules 
                (template_id, cron_expression, next_run)
                VALUES (?, ?, ?)
            """,
                (template_id, cron_expression, next_run.isoformat()),
            )

            schedule_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info(f"Report scheduled with ID: {schedule_id}")
            return schedule_id

        except Exception as e:
            conn.close()
            self.logger.error(f"Error scheduling report: {str(e)}")
            raise

    def get_scheduled_reports(self) -> List[Dict[str, Any]]:
        """Get all scheduled reports"""

        conn = self.data_loader.get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    rs.*,
                    rt.name as template_name,
                    rt.type as template_type,
                    rt.format as template_format
                FROM report_schedules rs
                JOIN report_templates rt ON rs.template_id = rt.id
                WHERE rs.is_active = 1
                ORDER BY rs.next_run
            """)

            results = cursor.fetchall()

            schedules = []
            for row in results:
                schedules.append(
                    {
                        "id": row[0],
                        "template_id": row[1],
                        "template_name": row[5],
                        "template_type": row[6],
                        "template_format": row[7],
                        "cron_expression": row[2],
                        "next_run": row[3],
                        "last_run": row[4],
                        "is_active": bool(row[5]),
                        "created_at": row[6],
                    }
                )

            conn.close()
            return schedules

        except Exception as e:
            conn.close()
            self.logger.error(f"Error getting scheduled reports: {str(e)}")
            raise

    def cleanup_old_reports(self, days_to_keep: int = 30):
        """Clean up old report files and history"""

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        try:
            # Clean up database history
            conn = self.data_loader.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM report_history 
                WHERE executed_at < ? AND status = 'completed'
            """,
                (cutoff_date.isoformat(),),
            )

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            # Clean up files
            files_deleted = 0
            for filename in os.listdir(self.report_output_dir):
                filepath = os.path.join(self.report_output_dir, filename)
                if os.path.isfile(filepath):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        files_deleted += 1

            self.logger.info(
                f"Cleaned up {deleted_count} old report records and {files_deleted} files"
            )

        except Exception as e:
            self.logger.error(f"Error cleaning up old reports: {str(e)}")
