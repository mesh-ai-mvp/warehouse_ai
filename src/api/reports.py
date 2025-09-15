"""
Reports API endpoints for template management, generation, and export
"""

import csv
import io
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader
from services.report_ai_handler import ReportAIHandler
from services.pdf_generator import PDFReportGenerator

# Initialize router
router = APIRouter(prefix="/reports", tags=["reports"])

# Global data loader instance
data_loader = DataLoader()

# Initialize AI handler and PDF generator
report_ai_handler = ReportAIHandler()
pdf_generator = PDFReportGenerator()

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
    {
        "name": "Warehouse Chaos Dashboard",
        "description": "AI-powered analysis of warehouse inefficiencies and optimization opportunities",
        "type": "custom",
        "template_data": {
            "title": "Warehouse Chaos Analysis Dashboard",
            "sections": ["chaos_metrics", "problem_areas", "quick_wins", "recommendations"],
            "analysis_type": "full",
        },
        "fields_config": {
            "fields": [
                {"name": "metric_name", "label": "Metric", "type": "text", "required": True},
                {"name": "current_score", "label": "Current Score", "type": "number", "required": True},
                {"name": "target_score", "label": "Target", "type": "number", "required": True},
                {"name": "improvement_potential", "label": "Improvement %", "type": "number", "required": True},
                {"name": "priority", "label": "Priority", "type": "text", "required": True},
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "gauge",
                    "title": "Overall Efficiency Score",
                    "value": "efficiency_score",
                    "min": 0,
                    "max": 100,
                    "target": 85,
                },
                {
                    "type": "heatmap",
                    "title": "Warehouse Problem Zones",
                    "data": "heat_map_data",
                },
                {
                    "type": "bar",
                    "title": "Optimization Opportunities",
                    "x": "category",
                    "y": "impact_score",
                },
            ]
        },
        "format": "pdf",
        "frequency": "daily",
        "recipients": ["warehouse@company.com", "operations@company.com"],
        "parameters": {"analysis_type": "full", "include_ai_insights": True},
    },
    {
        "name": "Placement Efficiency Report",
        "description": "Product placement optimization and consolidation opportunities",
        "type": "custom",
        "template_data": {
            "title": "Placement Efficiency Analysis",
            "sections": ["velocity_analysis", "fragmentation", "consolidation_plan", "relocation_strategy"],
            "focus": "placement",
        },
        "fields_config": {
            "fields": [
                {"name": "item_name", "label": "Item", "type": "text", "required": True},
                {"name": "current_location", "label": "Current Location", "type": "text", "required": True},
                {"name": "optimal_location", "label": "Optimal Location", "type": "text", "required": True},
                {"name": "velocity_category", "label": "Velocity", "type": "text", "required": True},
                {"name": "time_savings", "label": "Time Savings (min/day)", "type": "number", "required": False},
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "scatter",
                    "title": "Velocity vs Location Analysis",
                    "x": "velocity_score",
                    "y": "grid_position",
                },
                {
                    "type": "sankey",
                    "title": "Relocation Flow",
                    "source": "current_zones",
                    "target": "optimal_zones",
                },
            ]
        },
        "format": "excel",
        "frequency": "weekly",
        "recipients": ["warehouse@company.com"],
        "parameters": {"focus": "placement", "include_simulation": True},
    },
    {
        "name": "FIFO Compliance Report",
        "description": "Expiry management and FIFO compliance monitoring",
        "type": "custom",
        "template_data": {
            "title": "FIFO Compliance & Expiry Management",
            "sections": ["compliance_score", "violations", "expiry_alerts", "corrective_actions"],
            "focus": "compliance",
        },
        "fields_config": {
            "fields": [
                {"name": "batch_number", "label": "Batch", "type": "text", "required": True},
                {"name": "item_name", "label": "Item", "type": "text", "required": True},
                {"name": "expiry_date", "label": "Expiry Date", "type": "date", "required": True},
                {"name": "days_remaining", "label": "Days Until Expiry", "type": "number", "required": True},
                {"name": "violation_type", "label": "Violation", "type": "text", "required": False},
                {"name": "action_required", "label": "Action", "type": "text", "required": True},
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "timeline",
                    "title": "Expiry Timeline",
                    "data": "expiry_schedule",
                },
                {
                    "type": "pie",
                    "title": "Compliance Status Distribution",
                    "value": "count",
                    "label": "status",
                },
            ]
        },
        "format": "pdf",
        "frequency": "daily",
        "recipients": ["compliance@company.com", "quality@company.com"],
        "parameters": {"focus": "compliance", "alert_threshold_days": 30},
    },
    {
        "name": "Movement Optimization Report",
        "description": "Picking path and movement pattern optimization analysis",
        "type": "custom",
        "template_data": {
            "title": "Movement Pattern Optimization",
            "sections": ["movement_stats", "path_analysis", "congestion_points", "layout_recommendations"],
            "focus": "movement",
        },
        "fields_config": {
            "fields": [
                {"name": "route", "label": "Route", "type": "text", "required": True},
                {"name": "frequency", "label": "Frequency", "type": "number", "required": True},
                {"name": "avg_time", "label": "Avg Time (sec)", "type": "number", "required": True},
                {"name": "distance", "label": "Distance (m)", "type": "number", "required": True},
                {"name": "optimization", "label": "Optimization", "type": "text", "required": False},
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "flow",
                    "title": "Movement Heat Flow",
                    "data": "flow_map",
                },
                {
                    "type": "line",
                    "title": "Hourly Movement Patterns",
                    "x": "hour",
                    "y": "movements",
                },
            ]
        },
        "format": "pdf",
        "frequency": "weekly",
        "recipients": ["operations@company.com"],
        "parameters": {"focus": "movement", "include_layout_changes": True},
    },
    {
        "name": "Comprehensive Warehouse Optimization",
        "description": "Complete AI-driven warehouse optimization analysis with ROI",
        "type": "custom",
        "template_data": {
            "title": "Comprehensive Warehouse Optimization Report",
            "sections": [
                "executive_summary",
                "chaos_analysis",
                "placement_optimization",
                "compliance_audit",
                "movement_analysis",
                "recommendations",
                "roi_analysis",
                "implementation_roadmap"
            ],
            "analysis_type": "full",
        },
        "fields_config": {
            "fields": [
                {"name": "recommendation", "label": "Recommendation", "type": "text", "required": True},
                {"name": "priority", "label": "Priority", "type": "text", "required": True},
                {"name": "effort", "label": "Effort", "type": "text", "required": True},
                {"name": "impact", "label": "Impact", "type": "text", "required": True},
                {"name": "timeline", "label": "Timeline", "type": "text", "required": True},
                {"name": "roi", "label": "ROI", "type": "currency", "required": False},
            ]
        },
        "chart_config": {
            "charts": [
                {
                    "type": "dashboard",
                    "title": "Optimization Scorecard",
                    "metrics": ["efficiency", "compliance", "utilization", "accuracy"],
                },
                {
                    "type": "waterfall",
                    "title": "ROI Breakdown",
                    "categories": ["savings", "costs", "net_benefit"],
                },
                {
                    "type": "gantt",
                    "title": "Implementation Timeline",
                    "tasks": "roadmap_tasks",
                },
            ]
        },
        "format": "pdf",
        "frequency": "monthly",
        "recipients": ["management@company.com", "operations@company.com"],
        "parameters": {
            "analysis_type": "full",
            "include_simulation": True,
            "include_ai_insights": True,
            "generate_action_plan": True
        },
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
    """Export a report to file with AI insights for PDF format"""
    try:
        reports_logger.info(
            f"Exporting report for template: {template_id} as {request.format}"
        )

        # Get template details
        conn = data_loader.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM report_templates WHERE id = ?", (template_id,))
        template_row = cursor.fetchone()

        if not template_row:
            raise HTTPException(status_code=404, detail="Template not found")

        # Parse template data
        template = {
            "id": template_row[0],
            "name": template_row[1],
            "description": template_row[2],
            "type": template_row[3],
            "template_data": json.loads(template_row[4]) if template_row[4] else {},
            "fields_config": json.loads(template_row[5]) if template_row[5] else {},
            "format": template_row[7],
            "frequency": template_row[8],
        }

        # Generate report data
        report_type = template["type"]
        parameters = request.parameters or {}
        report_data = await _generate_report_data(report_type, parameters, cursor)

        conn.close()

        # Handle different export formats
        if request.format.lower() == "csv":
            # Simple CSV export without AI insights
            return _export_csv({"data": report_data})

        elif request.format.lower() == "excel":
            # Excel export (can be enhanced with openpyxl later)
            return _export_csv({"data": report_data})  # Using CSV for now

        elif request.format.lower() == "pdf":
            # PDF export with AI insights
            reports_logger.info("Generating AI insights for PDF export")

            # Generate AI insights
            ai_insights = await report_ai_handler.generate_insights_for_report(
                report_type=report_type, report_data=report_data, parameters=parameters
            )

            # Generate PDF with insights
            pdf_content = pdf_generator.generate_report_pdf(
                template=template, data=report_data, ai_insights=ai_insights
            )

            # Return PDF as streaming response
            filename = f"{template['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_content),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
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
    elif report_type == "warehouse_optimization":
        return await _generate_warehouse_optimization_report_data(parameters, cursor)
    elif report_type == "custom":
        # Check if this is a warehouse optimization custom report
        if parameters.get("analysis_type") or parameters.get("focus") or parameters.get("include_ai_insights"):
            return await _generate_warehouse_optimization_report_data(parameters, cursor)
        else:
            # Generic custom report - return empty data for now
            return [{"message": "Custom report data generation not implemented"}]
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

    # Modified query to include suppliers even without recent orders
    cursor.execute(
        """
        SELECT
            s.name,
            COALESCE(COUNT(po.po_id), 0) as orders,
            COALESCE(COUNT(CASE
                WHEN po.actual_delivery_date <= po.requested_delivery_date
                THEN 1
            END), 0) as on_time_orders,
            COALESCE(AVG(CASE
                WHEN po.actual_delivery_date > po.requested_delivery_date
                THEN julianday(po.actual_delivery_date) - julianday(po.requested_delivery_date)
                ELSE 0
            END), 0) as avg_delay,
            CASE
                WHEN COUNT(po.po_id) = 0 THEN 4.0
                WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 95 THEN 4.8
                WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 90 THEN 4.5
                WHEN COUNT(CASE WHEN po.actual_delivery_date <= po.requested_delivery_date THEN 1 END) * 100.0 / COUNT(po.po_id) >= 85 THEN 4.2
                ELSE 4.0
            END as rating,
            s.avg_lead_time
        FROM suppliers s
        LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            AND date(po.created_at) >= date('now', '-6 months')
        WHERE s.status = 'OK' OR s.status IS NULL
        GROUP BY s.supplier_id, s.name, s.avg_lead_time
        ORDER BY orders DESC, s.name ASC
    """
    )

    results = cursor.fetchall()

    data = []
    for row in results:
        name, orders, on_time_orders, avg_delay, rating, avg_lead_time = row
        on_time_percentage = (
            (on_time_orders / max(orders, 1)) * 100 if orders > 0 else 0
        )

        data.append(
            {
                "name": name,
                "orders": orders,
                "on_time": round(on_time_percentage, 1),
                "avg_delay": round(avg_delay or 0, 1),
                "avg_lead_time": round(avg_lead_time or 0, 1),
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


async def _generate_warehouse_optimization_report_data(
    parameters: Dict[str, Any], cursor
) -> List[Dict[str, Any]]:
    """Generate warehouse optimization report data"""

    analysis_type = parameters.get("analysis_type", "full")
    focus = parameters.get("focus", "general")

    # Get chaos metrics
    cursor.execute("""
        SELECT
            metric_name,
            current_chaos_score,
            optimal_score,
            improvement_potential
        FROM warehouse_chaos_metrics
        ORDER BY improvement_potential DESC
    """)

    metrics = cursor.fetchall()

    # Get fragmentation data
    cursor.execute("""
        SELECT
            COUNT(DISTINCT b.batch_id) as fragmented_batches,
            COUNT(DISTINCT mp.position_id) as total_positions,
            SUM(mp.quantity) as total_quantity
        FROM medication_placements mp
        JOIN batch_info b ON mp.batch_id = b.batch_id
        WHERE mp.is_active = 1
        GROUP BY b.batch_id
        HAVING COUNT(DISTINCT mp.position_id) > 1
    """)

    fragmentation = cursor.fetchone()

    # Get velocity mismatches
    cursor.execute("""
        SELECT COUNT(*) as mismatches
        FROM medication_placements mp
        JOIN medications m ON mp.med_id = m.med_id
        JOIN medication_attributes ma ON m.med_id = ma.med_id
        JOIN shelf_positions sp ON mp.position_id = sp.position_id
        WHERE mp.is_active = 1
        AND ((ma.movement_category = 'Fast' AND sp.grid_y = 3)
            OR (ma.movement_category = 'Slow' AND sp.grid_y = 1))
    """)

    velocity_mismatches = cursor.fetchone()

    # Build report data based on focus
    data = []

    if focus == "compliance":
        # Focus on compliance metrics
        cursor.execute("""
            SELECT
                m.name as item_name,
                b.lot_number as batch_number,
                b.expiry_date,
                julianday(b.expiry_date) - julianday('now') as days_remaining,
                CASE
                    WHEN julianday(b.expiry_date) - julianday('now') <= 0 THEN 'Expired'
                    WHEN julianday(b.expiry_date) - julianday('now') <= 7 THEN 'Critical'
                    WHEN julianday(b.expiry_date) - julianday('now') <= 30 THEN 'Warning'
                    ELSE 'OK'
                END as status,
                'Immediate rotation required' as action_required
            FROM medication_placements mp
            JOIN batch_info b ON mp.batch_id = b.batch_id
            JOIN medications m ON mp.med_id = m.med_id
            WHERE mp.is_active = 1
            AND julianday(b.expiry_date) - julianday('now') <= 30
            ORDER BY days_remaining
            LIMIT 50
        """)

        for row in cursor.fetchall():
            data.append({
                "item_name": row[0],
                "batch_number": row[1],
                "expiry_date": row[2],
                "days_remaining": int(row[3]) if row[3] else 0,
                "violation_type": row[4],
                "action_required": row[5]
            })

    elif focus == "placement":
        # Focus on placement optimization
        cursor.execute("""
            SELECT
                m.name as item_name,
                a.aisle_code || '-' || s.shelf_code || '-' || sp.grid_label as current_location,
                CASE ma.movement_category
                    WHEN 'Fast' THEN 'A1-S1-P1'
                    WHEN 'Medium' THEN 'B1-S1-P5'
                    ELSE 'C1-S2-P8'
                END as optimal_location,
                ma.movement_category as velocity_category,
                ma.velocity_score * 2.5 as time_savings
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN medication_attributes ma ON m.med_id = ma.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mp.is_active = 1
            AND ((ma.movement_category = 'Fast' AND sp.grid_y = 3)
                OR (ma.movement_category = 'Slow' AND sp.grid_y = 1))
            LIMIT 50
        """)

        for row in cursor.fetchall():
            data.append({
                "item_name": row[0],
                "current_location": row[1],
                "optimal_location": row[2],
                "velocity_category": row[3],
                "time_savings": round(row[4], 1) if row[4] else 0
            })

    elif focus == "movement":
        # Focus on movement patterns
        cursor.execute("""
            SELECT
                movement_type || ' - ' || COALESCE(a.aisle_code || '-' || s.shelf_code, 'Unknown') as route,
                COUNT(*) as frequency,
                ROUND(AVG(sp.grid_x * 3 + sp.grid_y * 2), 1) as distance,
                COUNT(*) * 15 as avg_time,
                'Optimize path' as optimization
            FROM movement_history mh
            LEFT JOIN shelf_positions sp ON mh.position_id = sp.position_id
            LEFT JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            LEFT JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mh.movement_date >= datetime('now', '-30 days')
            GROUP BY movement_type, a.aisle_code, s.shelf_code
            HAVING COUNT(*) > 5
            ORDER BY frequency DESC
            LIMIT 50
        """)

        for row in cursor.fetchall():
            data.append({
                "route": row[0],
                "frequency": row[1],
                "distance": round(row[2], 1) if row[2] else 0,
                "avg_time": round(row[3], 1) if row[3] else 0,
                "optimization": row[4]
            })

    else:
        # General optimization metrics
        for metric in metrics:
            data.append({
                "metric_name": metric[0],
                "current_score": round(metric[1], 2) if metric[1] else 0,
                "target_score": metric[2] if metric[2] else 0,
                "improvement_potential": round(metric[3], 2) if metric[3] else 0,
                "priority": "High" if metric[3] and metric[3] > 10 else "Medium"
            })

        # Add summary metrics
        if fragmentation:
            data.append({
                "metric_name": "Batch Fragmentation",
                "current_score": fragmentation[0] if fragmentation[0] else 0,
                "target_score": 0,
                "improvement_potential": fragmentation[0] * 5 if fragmentation[0] else 0,
                "priority": "High"
            })

        if velocity_mismatches:
            data.append({
                "metric_name": "Velocity Mismatches",
                "current_score": velocity_mismatches[0] if velocity_mismatches[0] else 0,
                "target_score": 0,
                "improvement_potential": velocity_mismatches[0] * 3 if velocity_mismatches[0] else 0,
                "priority": "High"
            })

    return data if data else [{"message": "No optimization data available"}]


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


# PDF generation is now handled by PDFReportGenerator class with AI insights
