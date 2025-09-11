"""
Reports API endpoints for template management, generation, and export
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, date, timedelta
import json
import sys
import os
import uuid
import csv
import io
from loguru import logger

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader

# Initialize router
router = APIRouter(prefix="/reports", tags=["reports"])

# Global data loader instance
data_loader = DataLoader()

# Logger
reports_logger = logger.bind(name="reports")


# Pydantic models for request/response
class ReportTemplate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # inventory, financial, supplier, consumption, custom
    template_data: Dict[str, Any]
    fields_config: Dict[str, Any]
    chart_config: Optional[Dict[str, Any]] = None
    format: str = "pdf"  # pdf, excel, csv
    frequency: str = "manual"  # manual, daily, weekly, monthly
    recipients: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None


class UpdateReportTemplate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    fields_config: Optional[Dict[str, Any]] = None
    chart_config: Optional[Dict[str, Any]] = None
    format: Optional[str] = None
    frequency: Optional[str] = None
    recipients: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class RunReportRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = None
    format: Optional[str] = None


class ExportReportRequest(BaseModel):
    format: str  # pdf, excel, csv
    parameters: Optional[Dict[str, Any]] = None


# Default report templates
DEFAULT_TEMPLATES = [
    {
        "name": "Inventory Stock Report",
        "description": "Current stock levels and reorder points",
        "type": "inventory",
        "template_data": {
            "title": "Inventory Stock Report",
            "sections": ["summary", "stock_levels", "reorder_alerts"],
            "grouping": "category",
        },
        "fields_config": {
            "fields": [
                {
                    "name": "name",
                    "label": "Medication",
                    "type": "text",
                    "required": True,
                },
                {
                    "name": "category",
                    "label": "Category",
                    "type": "text",
                    "required": True,
                },
                {
                    "name": "current_stock",
                    "label": "Current Stock",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "reorder_point",
                    "label": "Reorder Point",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "supplier",
                    "label": "Supplier",
                    "type": "text",
                    "required": False,
                },
                {
                    "name": "days_supply",
                    "label": "Days Supply",
                    "type": "number",
                    "required": False,
                },
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "bar",
                    "title": "Stock Levels by Category",
                    "x": "category",
                    "y": "current_stock",
                },
                {
                    "type": "pie",
                    "title": "Stock Distribution",
                    "value": "current_stock",
                    "label": "category",
                },
            ]
        },
        "format": "pdf",
        "frequency": "daily",
        "recipients": ["warehouse@company.com", "manager@company.com"],
        "parameters": {"includeExpired": True, "lowStockOnly": False},
    },
    {
        "name": "Monthly Financial Summary",
        "description": "Revenue, expenses, and profitability analysis",
        "type": "financial",
        "template_data": {
            "title": "Monthly Financial Summary",
            "sections": ["revenue", "expenses", "profitability", "trends"],
            "period": "monthly",
        },
        "fields_config": {
            "fields": [
                {"name": "period", "label": "Period", "type": "text", "required": True},
                {
                    "name": "revenue",
                    "label": "Revenue",
                    "type": "currency",
                    "required": True,
                },
                {
                    "name": "orders",
                    "label": "Orders",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "avg_order_value",
                    "label": "Avg Order Value",
                    "type": "currency",
                    "required": True,
                },
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "line",
                    "title": "Revenue Trend",
                    "x": "period",
                    "y": "revenue",
                },
                {"type": "area", "title": "Order Volume", "x": "period", "y": "orders"},
            ]
        },
        "format": "excel",
        "frequency": "monthly",
        "recipients": ["finance@company.com"],
        "parameters": {"includeForecasts": True},
    },
    {
        "name": "Supplier Performance",
        "description": "On-time delivery and quality metrics",
        "type": "supplier",
        "template_data": {
            "title": "Supplier Performance Report",
            "sections": ["performance", "delivery", "quality"],
            "ranking": True,
        },
        "fields_config": {
            "fields": [
                {"name": "name", "label": "Supplier", "type": "text", "required": True},
                {
                    "name": "orders",
                    "label": "Total Orders",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "on_time",
                    "label": "On-time %",
                    "type": "percentage",
                    "required": True,
                },
                {
                    "name": "avg_delay",
                    "label": "Avg Delay (days)",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "rating",
                    "label": "Rating",
                    "type": "rating",
                    "required": True,
                },
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "bar",
                    "title": "On-time Delivery %",
                    "x": "name",
                    "y": "on_time",
                },
                {
                    "type": "scatter",
                    "title": "Orders vs Rating",
                    "x": "orders",
                    "y": "rating",
                },
            ]
        },
        "format": "pdf",
        "frequency": "weekly",
        "recipients": ["procurement@company.com"],
        "parameters": {"minOrderThreshold": 5},
    },
    {
        "name": "Consumption Trends",
        "description": "Historical consumption patterns and forecasts",
        "type": "consumption",
        "template_data": {
            "title": "Consumption Trends Analysis",
            "sections": ["trends", "forecasts", "patterns"],
            "time_range": "6m",
        },
        "fields_config": {
            "fields": [
                {"name": "month", "label": "Month", "type": "text", "required": True},
                {
                    "name": "consumption",
                    "label": "Consumption",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "forecast",
                    "label": "Forecast",
                    "type": "number",
                    "required": True,
                },
                {
                    "name": "orders",
                    "label": "Orders",
                    "type": "number",
                    "required": False,
                },
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "line",
                    "title": "Consumption vs Forecast",
                    "x": "month",
                    "y": ["consumption", "forecast"],
                },
                {
                    "type": "area",
                    "title": "Monthly Consumption",
                    "x": "month",
                    "y": "consumption",
                },
            ]
        },
        "format": "excel",
        "frequency": "weekly",
        "recipients": ["analytics@company.com"],
        "parameters": {"includeForecasts": True, "timeRange": "6m"},
    },
]


@router.get("/templates")
async def get_report_templates(
    type: Optional[str] = Query(None, description="Filter by report type"),
    active_only: bool = Query(True, description="Only active templates"),
) -> List[Dict[str, Any]]:
    """Get all report templates"""
    try:
        reports_logger.info("Getting report templates")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Check if templates table exists and has data
        cursor.execute("SELECT COUNT(*) FROM report_templates")
        template_count = cursor.fetchone()[0]

        # If no templates exist, create default templates
        if template_count == 0:
            reports_logger.info("No templates found, creating default templates")
            for template in DEFAULT_TEMPLATES:
                cursor.execute(
                    """
                    INSERT INTO report_templates 
                    (name, description, type, template_data, fields_config, chart_config, 
                     format, frequency, recipients, parameters, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'system')
                """,
                    (
                        template["name"],
                        template["description"],
                        template["type"],
                        json.dumps(template["template_data"]),
                        json.dumps(template["fields_config"]),
                        json.dumps(template.get("chart_config")),
                        template["format"],
                        template["frequency"],
                        json.dumps(template.get("recipients", [])),
                        json.dumps(template.get("parameters", {})),
                    ),
                )
            conn.commit()

        # Build query
        query = "SELECT * FROM report_templates"
        params = []

        where_clauses = []
        if active_only:
            where_clauses.append("is_active = 1")
        if type:
            where_clauses.append("type = ?")
            params.append(type)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()

        templates = []
        for row in results:
            template = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "template_data": json.loads(row[4]) if row[4] else {},
                "fields_config": json.loads(row[5]) if row[5] else {},
                "chart_config": json.loads(row[6]) if row[6] else None,
                "format": row[7],
                "frequency": row[8],
                "recipients": json.loads(row[9]) if row[9] else [],
                "parameters": json.loads(row[10]) if row[10] else {},
                "created_by": row[11],
                "created_at": row[12],
                "updated_at": row[13],
                "is_active": bool(row[14]),
            }

            # Add last run info if available
            cursor.execute(
                """
                SELECT executed_at, status FROM report_history 
                WHERE template_id = ? ORDER BY executed_at DESC LIMIT 1
            """,
                (template["id"],),
            )
            last_run = cursor.fetchone()
            if last_run:
                template["lastRun"] = last_run[0]
                template["lastStatus"] = last_run[1]

            templates.append(template)

        conn.close()

        return templates

    except Exception as e:
        reports_logger.error(f"Error getting report templates: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting report templates: {str(e)}"
        )


@router.post("/templates")
async def create_report_template(template: ReportTemplate) -> Dict[str, Any]:
    """Create a new report template"""
    try:
        reports_logger.info(f"Creating report template: {template.name}")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO report_templates 
            (name, description, type, template_data, fields_config, chart_config, 
             format, frequency, recipients, parameters, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'user')
        """,
            (
                template.name,
                template.description,
                template.type,
                json.dumps(template.template_data),
                json.dumps(template.fields_config),
                json.dumps(template.chart_config) if template.chart_config else None,
                template.format,
                template.frequency,
                json.dumps(template.recipients or []),
                json.dumps(template.parameters or {}),
            ),
        )

        template_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"id": template_id, "message": "Template created successfully"}

    except Exception as e:
        reports_logger.error(f"Error creating report template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating report template: {str(e)}"
        )


@router.put("/templates/{template_id}")
async def update_report_template(
    template_id: int, template: UpdateReportTemplate
) -> Dict[str, Any]:
    """Update an existing report template"""
    try:
        reports_logger.info(f"Updating report template: {template_id}")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Build update query dynamically
        update_fields = []
        params = []

        if template.name is not None:
            update_fields.append("name = ?")
            params.append(template.name)
        if template.description is not None:
            update_fields.append("description = ?")
            params.append(template.description)
        if template.template_data is not None:
            update_fields.append("template_data = ?")
            params.append(json.dumps(template.template_data))
        if template.fields_config is not None:
            update_fields.append("fields_config = ?")
            params.append(json.dumps(template.fields_config))
        if template.chart_config is not None:
            update_fields.append("chart_config = ?")
            params.append(json.dumps(template.chart_config))
        if template.format is not None:
            update_fields.append("format = ?")
            params.append(template.format)
        if template.frequency is not None:
            update_fields.append("frequency = ?")
            params.append(template.frequency)
        if template.recipients is not None:
            update_fields.append("recipients = ?")
            params.append(json.dumps(template.recipients))
        if template.parameters is not None:
            update_fields.append("parameters = ?")
            params.append(json.dumps(template.parameters))
        if template.is_active is not None:
            update_fields.append("is_active = ?")
            params.append(template.is_active)

        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        params.append(template_id)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        query = f"UPDATE report_templates SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")

        conn.commit()
        conn.close()

        return {"message": "Template updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        reports_logger.error(f"Error updating report template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating report template: {str(e)}"
        )


@router.delete("/templates/{template_id}")
async def delete_report_template(template_id: int) -> Dict[str, Any]:
    """Delete a report template"""
    try:
        reports_logger.info(f"Deleting report template: {template_id}")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM report_templates WHERE id = ?", (template_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")

        conn.commit()
        conn.close()

        return {"message": "Template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        reports_logger.error(f"Error deleting report template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting report template: {str(e)}"
        )


@router.post("/templates/{template_id}/run")
async def run_report(template_id: int, request: RunReportRequest) -> Dict[str, Any]:
    """Run a report and return the data"""
    try:
        reports_logger.info(f"Running report for template: {template_id}")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Get template
        cursor.execute("SELECT * FROM report_templates WHERE id = ?", (template_id,))
        template_row = cursor.fetchone()

        if not template_row:
            raise HTTPException(status_code=404, detail="Template not found")

        json.loads(template_row[4]) if template_row[4] else {}
        json.loads(template_row[5]) if template_row[5] else {}
        report_type = template_row[3]

        # Merge parameters
        parameters = json.loads(template_row[10]) if template_row[10] else {}
        if request.parameters:
            parameters.update(request.parameters)

        # Record execution start
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        cursor.execute(
            """
            INSERT INTO report_history 
            (template_id, parameters, status, executed_by)
            VALUES (?, ?, 'running', 'api')
        """,
            (template_id, json.dumps(parameters)),
        )

        history_id = cursor.lastrowid
        conn.commit()

        # Generate report data based on type
        report_data = await _generate_report_data(report_type, parameters, cursor)

        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds() * 1000

        # Update execution record
        cursor.execute(
            """
            UPDATE report_history 
            SET status = 'completed', execution_time_ms = ?
            WHERE id = ?
        """,
            (execution_time, history_id),
        )

        conn.commit()
        conn.close()

        return {
            "template_id": template_id,
            "execution_id": execution_id,
            "data": report_data,
            "parameters": parameters,
            "execution_time_ms": execution_time,
            "generated_at": start_time.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        reports_logger.error(f"Error running report: {str(e)}")
        # Update execution record with error
        try:
            conn = data_loader.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE report_history 
                SET status = 'failed', error_message = ?
                WHERE template_id = ? AND status = 'running'
            """,
                (str(e), template_id),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error running report: {str(e)}")


@router.post("/templates/{template_id}/export")
async def export_report(template_id: int, request: ExportReportRequest):
    """Export a report to file"""
    try:
        reports_logger.info(
            f"Exporting report for template: {template_id} as {request.format}"
        )

        # Run the report first
        run_request = RunReportRequest(parameters=request.parameters)
        report_result = await run_report(template_id, run_request)

        # Generate file based on format
        if request.format.lower() == "csv":
            return _export_csv(report_result)
        elif request.format.lower() == "excel":
            return _export_excel(report_result)
        elif request.format.lower() == "pdf":
            return _export_pdf(report_result)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

    except HTTPException:
        raise
    except Exception as e:
        reports_logger.error(f"Error exporting report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting report: {str(e)}")


@router.get("/history")
async def get_report_history(
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    limit: int = Query(50, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[Dict[str, Any]]:
    """Get report execution history"""
    try:
        reports_logger.info("Getting report history")

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT rh.*, rt.name as template_name, rt.type as template_type
            FROM report_history rh
            JOIN report_templates rt ON rh.template_id = rt.id
        """
        params = []

        if template_id:
            query += " WHERE rh.template_id = ?"
            params.append(template_id)

        query += " ORDER BY rh.executed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        results = cursor.fetchall()

        history = []
        for row in results:
            history.append(
                {
                    "id": row[0],
                    "template_id": row[1],
                    "template_name": row[10],
                    "template_type": row[11],
                    "executed_at": row[2],
                    "parameters": json.loads(row[3]) if row[3] else {},
                    "status": row[4],
                    "file_path": row[5],
                    "file_size": row[6],
                    "execution_time_ms": row[7],
                    "error_message": row[8],
                    "executed_by": row[9],
                }
            )

        conn.close()

        return history

    except Exception as e:
        reports_logger.error(f"Error getting report history: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting report history: {str(e)}"
        )


# Helper functions
async def _generate_report_data(
    report_type: str, parameters: Dict[str, Any], cursor
) -> List[Dict[str, Any]]:
    """Generate report data based on type and parameters"""

    if report_type == "inventory":
        return await _generate_inventory_report_data(parameters, cursor)
    elif report_type == "financial":
        return await _generate_financial_report_data(parameters, cursor)
    elif report_type == "supplier":
        return await _generate_supplier_report_data(parameters, cursor)
    elif report_type == "consumption":
        return await _generate_consumption_report_data(parameters, cursor)
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported report type: {report_type}"
        )


async def _generate_inventory_report_data(
    parameters: Dict[str, Any], cursor
) -> List[Dict[str, Any]]:
    """Generate inventory report data"""

    low_stock_only = parameters.get("lowStockOnly", False)
    # TODO: Implement expired medication filtering using include_expired
    parameters.get("includeExpired", True)

    # Base query for inventory data
    query = """
        SELECT 
            m.name,
            m.category,
            COALESCE(ch.on_hand, 0) as current_stock,
            COALESCE(ac.avg_daily * 30, 100) as reorder_point,
            s.name as supplier,
            CASE 
                WHEN ac.avg_daily > 0 THEN ch.on_hand / ac.avg_daily
                ELSE 30
            END as days_supply
        FROM medications m
        LEFT JOIN (
            SELECT med_id, on_hand, 
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
    """

    params = []

    if low_stock_only:
        query += " WHERE COALESCE(ch.on_hand, 0) <= COALESCE(ac.avg_daily * 30, 100)"

    query += " ORDER BY m.category, m.name"

    cursor.execute(query, params)
    results = cursor.fetchall()

    data = []
    for row in results:
        data.append(
            {
                "name": row[0],
                "category": row[1],
                "current_stock": int(row[2]),
                "reorder_point": int(row[3]),
                "supplier": row[4] or "Unknown",
                "days_supply": round(row[5], 1),
            }
        )

    return data


async def _generate_financial_report_data(
    parameters: Dict[str, Any], cursor
) -> List[Dict[str, Any]]:
    """Generate financial report data"""

    parameters.get("includeForecasts", True)

    # Get monthly revenue data
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', created_at) as period,
            SUM(total_amount) as revenue,
            COUNT(*) as orders,
            AVG(total_amount) as avg_order_value
        FROM purchase_orders
        WHERE created_at >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY period
    """)

    results = cursor.fetchall()

    data = []
    for row in results:
        period, revenue, orders, avg_order_value = row

        # Convert period to readable format
        try:
            period_date = datetime.strptime(period, "%Y-%m")
            period_label = period_date.strftime("%b %Y")
        except ValueError:
            period_label = period

        data.append(
            {
                "period": period_label,
                "revenue": round(revenue or 0, 2),
                "orders": orders or 0,
                "avg_order_value": round(avg_order_value or 0, 2),
            }
        )

    return data


async def _generate_supplier_report_data(
    parameters: Dict[str, Any], cursor
) -> List[Dict[str, Any]]:
    """Generate supplier report data"""

    min_order_threshold = parameters.get("minOrderThreshold", 1)

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
            CASE
                WHEN COUNT(po.po_id) = 0 THEN 4.0
                WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 95 THEN 4.8
                WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 90 THEN 4.5
                WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 85 THEN 4.2
                ELSE 4.0
            END as rating
        FROM suppliers s
        LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            AND po.created_at >= date('now', '-3 months')
        GROUP BY s.supplier_id, s.name
        HAVING COUNT(po.po_id) >= ?
        ORDER BY orders DESC
    """,
        (min_order_threshold,),
    )

    results = cursor.fetchall()

    data = []
    for row in results:
        name, orders, on_time_orders, avg_delay, rating = row
        on_time_percentage = (
            (on_time_orders / max(orders, 1)) * 100 if orders > 0 else 0
        )

        data.append(
            {
                "name": name,
                "orders": orders,
                "on_time": round(on_time_percentage, 1),
                "avg_delay": round(avg_delay or 0, 1),
                "rating": round(rating, 1),
            }
        )

    return data


async def _generate_consumption_report_data(
    parameters: Dict[str, Any], cursor
) -> List[Dict[str, Any]]:
    """Generate consumption report data"""

    time_range = parameters.get("timeRange", "6m")
    include_forecasts = parameters.get("includeForecasts", True)

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

    cursor.execute(
        """
        SELECT 
            strftime('%Y-%m', date) as period,
            SUM(qty_dispensed) as consumption,
            COUNT(DISTINCT po.po_id) as orders
        FROM consumption_history ch
        LEFT JOIN medications m ON ch.med_id = m.med_id
        LEFT JOIN purchase_orders po ON m.supplier_id = po.supplier_id 
            AND date(po.created_at) = ch.date
        WHERE ch.date >= ? AND ch.date <= ?
        GROUP BY strftime('%Y-%m', date)
        ORDER BY period
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    results = cursor.fetchall()

    data = []
    for row in results:
        period, consumption, orders = row

        # Convert period to readable format
        try:
            period_date = datetime.strptime(period, "%Y-%m")
            period_label = period_date.strftime("%b")
        except ValueError:
            period_label = period

        forecast = int(consumption * 1.05) if consumption and include_forecasts else 0

        data.append(
            {
                "month": period_label,
                "consumption": int(consumption or 0),
                "orders": int(orders or 0),
                "forecast": forecast,
            }
        )

    return data


def _export_csv(report_result: Dict[str, Any]) -> StreamingResponse:
    """Export report data as CSV"""

    output = io.StringIO()

    if not report_result["data"]:
        writer = csv.writer(output)
        writer.writerow(["No data available"])
    else:
        # Get field names from first row
        fieldnames = list(report_result["data"][0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_result["data"])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )


def _export_excel(report_result: Dict[str, Any]) -> StreamingResponse:
    """Export report data as Excel (simplified CSV for now)"""
    # For now, return CSV format - could be enhanced with openpyxl later
    return _export_csv(report_result)


def _export_pdf(report_result: Dict[str, Any]) -> StreamingResponse:
    """Export report data as PDF (simplified text for now)"""

    # Create simple text representation
    content = f"Report Generated: {report_result['generated_at']}\n"
    content += f"Execution Time: {report_result['execution_time_ms']}ms\n\n"
    content += "Data:\n"

    for item in report_result["data"][:50]:  # Limit to first 50 items
        content += str(item) + "\n"

    if len(report_result["data"]) > 50:
        content += f"\n... and {len(report_result['data']) - 50} more items\n"

    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=report.txt"},
    )
