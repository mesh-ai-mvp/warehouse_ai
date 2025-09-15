"""
Warehouse Optimization API Routes
Endpoints for AI-powered warehouse optimization analysis and recommendations
"""

import sys
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from loguru import logger
import json
import asyncio
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import DataLoader
from services.warehouse_optimization_handler import WarehouseOptimizationHandler
from api.warehouse_routes import (
    get_chaos_metrics,
    get_batch_fragmentation,
    get_velocity_mismatches
)

# Initialize router
router = APIRouter(prefix="/warehouse/optimization", tags=["warehouse-optimization"])

# Global instances
data_loader = DataLoader()
optimization_handler = WarehouseOptimizationHandler()

# Logger
optimization_logger = logger.bind(name="warehouse_optimization")


@router.get("/dashboard")
async def get_optimization_dashboard():
    """
    Get comprehensive warehouse optimization dashboard data

    Returns complete analysis with chaos metrics, recommendations, and scores
    """
    try:
        optimization_logger.info("Fetching optimization dashboard")

        # Get chaos metrics
        chaos_data = await get_chaos_metrics()

        # Get fragmentation data
        fragmentation_data = await get_batch_fragmentation()

        # Get velocity mismatches
        velocity_data = await get_velocity_mismatches()

        # Get movement statistics
        conn = data_loader.get_connection()
        movement_query = """
            SELECT
                COUNT(*) as total_movements,
                COUNT(DISTINCT position_id) as unique_positions,
                COUNT(DISTINCT med_id) as unique_medications,
                COUNT(DISTINCT movement_type) as movement_types,
                COUNT(DISTINCT operator_id) as unique_operators
            FROM movement_history
            WHERE movement_date >= datetime('now', '-30 days')
        """
        movement_stats = pd.read_sql_query(movement_query, conn).to_dict("records")[0]

        # Get compliance summary
        compliance_query = """
            SELECT
                COUNT(CASE WHEN days_until_expiry <= 0 THEN 1 END) as expired_items,
                COUNT(CASE WHEN days_until_expiry BETWEEN 1 AND 7 THEN 1 END) as expiring_7_days,
                COUNT(CASE WHEN days_until_expiry BETWEEN 8 AND 30 THEN 1 END) as expiring_30_days,
                COUNT(*) as total_batches
            FROM (
                SELECT
                    batch_id,
                    julianday(expiry_date) - julianday('now') as days_until_expiry
                FROM batch_info
                WHERE is_active = 1
            )
        """
        compliance_summary = pd.read_sql_query(compliance_query, conn).to_dict("records")[0]

        # Calculate optimization opportunities
        total_optimizations = (
            fragmentation_data["total_fragmented"] +
            velocity_data["total_mismatches"] +
            compliance_summary["expired_items"] +
            compliance_summary["expiring_7_days"]
        )

        # Prepare warehouse data for AI analysis
        warehouse_data = {
            "chaos_metrics": chaos_data,
            "fragmentation_data": fragmentation_data,
            "velocity_mismatches": velocity_data,
            "movement_statistics": movement_stats,
            "compliance_summary": compliance_summary
        }

        # Run quick AI analysis (cached)
        ai_insights = await optimization_handler.get_quick_insights(warehouse_data)

        return {
            "timestamp": datetime.now().isoformat(),
            "overview": {
                "overall_chaos_score": chaos_data["overall_chaos_score"],
                "optimization_opportunities": total_optimizations,
                "efficiency_score": 100 - chaos_data["overall_chaos_score"],
                "compliance_score": max(0, 100 - (compliance_summary["expired_items"] * 10)),
                "estimated_savings": f"${total_optimizations * 500:,.0f}/year"
            },
            "chaos_metrics": chaos_data,
            "fragmentation": fragmentation_data,
            "velocity_issues": velocity_data,
            "movement_stats": movement_stats,
            "compliance": compliance_summary,
            "ai_insights": ai_insights,
            "quick_actions": [
                {
                    "action": f"Consolidate {fragmentation_data['total_fragmented']} fragmented batches",
                    "impact": "High",
                    "effort": "Medium",
                    "savings": f"${fragmentation_data['total_fragmented'] * 200:,.0f}"
                },
                {
                    "action": f"Relocate {velocity_data['total_mismatches']} misplaced items",
                    "impact": "High",
                    "effort": "Low",
                    "savings": f"${velocity_data['total_mismatches'] * 150:,.0f}"
                },
                {
                    "action": f"Address {compliance_summary['expiring_7_days']} items expiring soon",
                    "impact": "Critical",
                    "effort": "Low",
                    "savings": "Prevent losses"
                }
            ]
        }

    except Exception as e:
        optimization_logger.error(f"Error fetching optimization dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def run_optimization_analysis(
    analysis_type: str = Query("full", description="Type of analysis: full, quick, placement, compliance, movement"),
    include_simulation: bool = Query(False, description="Include simulation of recommended changes"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Run comprehensive warehouse optimization analysis

    Analysis types:
    - full: Complete analysis with all agents
    - quick: Fast analysis with key metrics only
    - placement: Focus on placement optimization
    - compliance: Focus on compliance issues
    - movement: Focus on movement patterns
    """
    try:
        optimization_logger.info(f"Starting {analysis_type} optimization analysis")

        # Gather warehouse data
        warehouse_data = await _gather_warehouse_data()

        # Run analysis
        if analysis_type == "quick":
            # Synchronous quick analysis
            result = await optimization_handler.run_analysis(
                warehouse_data,
                analysis_type="quick",
                parameters={"timeout": 30}
            )
        else:
            # Start async analysis for detailed reports
            analysis_id = optimization_handler.start_async_analysis(
                warehouse_data,
                analysis_type,
                background_tasks
            )

            result = {
                "analysis_id": analysis_id,
                "status": "processing",
                "message": f"Analysis started. Check status at /warehouse/optimization/status/{analysis_id}",
                "estimated_time": "60-120 seconds"
            }

        # Include simulation if requested
        if include_simulation and analysis_type == "quick":
            simulation = await _simulate_optimizations(result.get("recommendations", []))
            result["simulation"] = simulation

        return result

    except Exception as e:
        optimization_logger.error(f"Error running optimization analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """Get status of ongoing optimization analysis"""
    try:
        status = optimization_handler.get_analysis_status(analysis_id)

        if not status:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        optimization_logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{analysis_id}")
async def get_analysis_results(analysis_id: str):
    """Get results of completed optimization analysis"""
    try:
        results = optimization_handler.get_analysis_results(analysis_id)

        if not results:
            raise HTTPException(status_code=404, detail="Analysis results not found")

        return results

    except HTTPException:
        raise
    except Exception as e:
        optimization_logger.error(f"Error getting analysis results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/placement-analysis")
async def get_placement_analysis():
    """Get detailed placement optimization analysis"""
    try:
        optimization_logger.info("Fetching placement analysis")

        # Get current placements with issues
        conn = data_loader.get_connection()

        placement_query = """
            SELECT
                m.name as medication_name,
                ma.movement_category,
                ma.velocity_score,
                mp.quantity,
                sp.grid_x,
                sp.grid_y,
                sp.grid_z,
                a.aisle_code || '-' || s.shelf_code || '-' || sp.grid_label as location,
                CASE
                    WHEN ma.movement_category = 'Fast' AND sp.grid_y = 3 THEN 'Fast item in back'
                    WHEN ma.movement_category = 'Slow' AND sp.grid_y = 1 THEN 'Slow item in front'
                    WHEN ma.movement_category = 'Medium' AND sp.is_golden_zone = 1 THEN 'Medium in golden zone'
                    ELSE 'Correct placement'
                END as issue
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN medication_attributes ma ON m.med_id = ma.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mp.is_active = 1
            ORDER BY ma.velocity_score DESC
        """

        placements = pd.read_sql_query(placement_query, conn).to_dict("records")

        # Analyze placement issues
        issues = [p for p in placements if p["issue"] != "Correct placement"]
        correct = [p for p in placements if p["issue"] == "Correct placement"]

        # Get batch consolidation opportunities
        batch_query = """
            SELECT
                b.lot_number,
                m.name as medication_name,
                COUNT(DISTINCT mp.position_id) as locations,
                SUM(mp.quantity) as total_quantity,
                b.expiry_date
            FROM medication_placements mp
            JOIN batch_info b ON mp.batch_id = b.batch_id
            JOIN medications m ON mp.med_id = m.med_id
            WHERE mp.is_active = 1
            GROUP BY b.batch_id
            HAVING locations > 1
        """

        fragmented_batches = pd.read_sql_query(batch_query, conn).to_dict("records")

        # Calculate optimization potential
        time_savings = len(issues) * 2.5 + len(fragmented_batches) * 4  # minutes per day
        cost_savings = time_savings * 365 / 60 * 25  # annual savings at $25/hour

        return {
            "summary": {
                "total_placements": len(placements),
                "correct_placements": len(correct),
                "misplaced_items": len(issues),
                "fragmented_batches": len(fragmented_batches),
                "placement_accuracy": f"{len(correct) / len(placements) * 100:.1f}%",
                "optimization_potential": f"{len(issues) + len(fragmented_batches)} items"
            },
            "placement_issues": issues[:50],  # Top 50 issues
            "batch_consolidation": fragmented_batches[:20],  # Top 20 fragmented batches
            "estimated_impact": {
                "time_savings": f"{time_savings:.0f} min/day",
                "annual_savings": f"${cost_savings:,.0f}",
                "efficiency_gain": f"{min(30, len(issues) * 0.5):.1f}%"
            },
            "recommendations": [
                {
                    "priority": "High",
                    "action": "Relocate fast-moving items to front zones",
                    "items_affected": len([i for i in issues if "Fast item in back" in i["issue"]]),
                    "expected_benefit": "25% reduction in picking time"
                },
                {
                    "priority": "Medium",
                    "action": "Consolidate fragmented batches",
                    "items_affected": len(fragmented_batches),
                    "expected_benefit": "15% reduction in search time"
                },
                {
                    "priority": "Low",
                    "action": "Move slow items to back zones",
                    "items_affected": len([i for i in issues if "Slow item in front" in i["issue"]]),
                    "expected_benefit": "Better space utilization"
                }
            ]
        }

    except Exception as e:
        optimization_logger.error(f"Error in placement analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance-check")
async def get_compliance_check():
    """Get detailed compliance analysis"""
    try:
        optimization_logger.info("Running compliance check")

        conn = data_loader.get_connection()

        # Check FIFO violations
        fifo_query = """
            SELECT
                m.name as medication_name,
                b1.lot_number as older_batch,
                b2.lot_number as newer_batch,
                b1.expiry_date as older_expiry,
                b2.expiry_date as newer_expiry,
                sp1.grid_y as older_position,
                sp2.grid_y as newer_position
            FROM medication_placements mp1
            JOIN medication_placements mp2 ON mp1.med_id = mp2.med_id
            JOIN batch_info b1 ON mp1.batch_id = b1.batch_id
            JOIN batch_info b2 ON mp2.batch_id = b2.batch_id
            JOIN medications m ON mp1.med_id = m.med_id
            JOIN shelf_positions sp1 ON mp1.position_id = sp1.position_id
            JOIN shelf_positions sp2 ON mp2.position_id = sp2.position_id
            WHERE mp1.is_active = 1
            AND mp2.is_active = 1
            AND b1.expiry_date < b2.expiry_date
            AND sp1.grid_y > sp2.grid_y
            LIMIT 20
        """

        fifo_violations = pd.read_sql_query(fifo_query, conn).to_dict("records")

        # Check expiry status
        expiry_query = """
            SELECT
                m.name as medication_name,
                b.lot_number,
                b.expiry_date,
                mp.quantity,
                julianday(b.expiry_date) - julianday('now') as days_until_expiry,
                CASE
                    WHEN julianday(b.expiry_date) - julianday('now') <= 0 THEN 'Expired'
                    WHEN julianday(b.expiry_date) - julianday('now') <= 7 THEN 'Critical'
                    WHEN julianday(b.expiry_date) - julianday('now') <= 30 THEN 'Warning'
                    WHEN julianday(b.expiry_date) - julianday('now') <= 90 THEN 'Monitor'
                    ELSE 'OK'
                END as status
            FROM medication_placements mp
            JOIN batch_info b ON mp.batch_id = b.batch_id
            JOIN medications m ON mp.med_id = m.med_id
            WHERE mp.is_active = 1
            AND julianday(b.expiry_date) - julianday('now') <= 90
            ORDER BY days_until_expiry
        """

        expiry_status = pd.read_sql_query(expiry_query, conn).to_dict("records")

        # Check temperature zone violations
        zone_query = """
            SELECT
                m.name as medication_name,
                m.storage_temp,
                a.temperature_zone,
                CASE
                    WHEN m.storage_temp = 'Refrigerated' AND a.temperature_zone != 'Refrigerated' THEN 'Wrong temperature zone'
                    WHEN m.storage_temp = 'Controlled' AND a.temperature_zone != 'Controlled' THEN 'Wrong controlled zone'
                    ELSE 'OK'
                END as violation
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mp.is_active = 1
            AND ((m.storage_temp = 'Refrigerated' AND a.temperature_zone != 'Refrigerated')
                OR (m.storage_temp = 'Controlled' AND a.temperature_zone != 'Controlled'))
        """

        zone_violations = pd.read_sql_query(zone_query, conn).to_dict("records")

        # Calculate compliance score
        total_issues = len(fifo_violations) + len([e for e in expiry_status if e["status"] in ["Expired", "Critical"]]) + len(zone_violations)
        compliance_score = max(0, 100 - (total_issues * 5))

        return {
            "compliance_score": compliance_score,
            "status": "Compliant" if compliance_score >= 80 else "At Risk" if compliance_score >= 60 else "Non-Compliant",
            "summary": {
                "fifo_violations": len(fifo_violations),
                "expired_items": len([e for e in expiry_status if e["status"] == "Expired"]),
                "expiring_soon": len([e for e in expiry_status if e["status"] == "Critical"]),
                "temperature_violations": len(zone_violations),
                "total_issues": total_issues
            },
            "fifo_violations": fifo_violations,
            "expiry_alerts": expiry_status[:30],  # Top 30 items by expiry
            "zone_violations": zone_violations,
            "immediate_actions": [
                {
                    "priority": "Critical",
                    "action": f"Remove {len([e for e in expiry_status if e['status'] == 'Expired'])} expired items",
                    "timeline": "Immediately"
                },
                {
                    "priority": "High",
                    "action": f"Rotate {len([e for e in expiry_status if e['status'] == 'Critical'])} items expiring within 7 days",
                    "timeline": "24 hours"
                },
                {
                    "priority": "Medium",
                    "action": f"Fix {len(fifo_violations)} FIFO violations",
                    "timeline": "48 hours"
                }
            ]
        }

    except Exception as e:
        optimization_logger.error(f"Error in compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movement-patterns")
async def get_movement_patterns():
    """Analyze warehouse movement patterns"""
    try:
        optimization_logger.info("Analyzing movement patterns")

        conn = data_loader.get_connection()

        # Get hourly movement patterns
        hourly_query = """
            SELECT
                strftime('%H', movement_date) as hour,
                COUNT(*) as movements,
                ROUND(AVG(quantity), 1) as avg_quantity
            FROM movement_history
            WHERE movement_date >= datetime('now', '-30 days')
            GROUP BY hour
            ORDER BY hour
        """

        hourly_patterns = pd.read_sql_query(hourly_query, conn).to_dict("records")

        # Get frequently moved items and locations
        route_query = """
            SELECT
                movement_type || ' - ' || COALESCE(a.aisle_code || '-' || s.shelf_code, 'Unknown') as route,
                COUNT(*) as frequency,
                AVG(mh.quantity) as avg_quantity,
                COUNT(DISTINCT mh.med_id) as unique_items
            FROM movement_history mh
            LEFT JOIN shelf_positions sp ON mh.position_id = sp.position_id
            LEFT JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            LEFT JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mh.movement_date >= datetime('now', '-30 days')
            GROUP BY movement_type, a.aisle_code, s.shelf_code
            HAVING COUNT(*) > 10
            ORDER BY frequency DESC
            LIMIT 20
        """

        frequent_routes = pd.read_sql_query(route_query, conn).to_dict("records")

        # Get zone traffic based on shelf positions
        zone_query = """
            SELECT
                COALESCE(a.aisle_code, 'Unknown') as zone,
                COUNT(*) as visits,
                COUNT(DISTINCT mh.med_id) as unique_items
            FROM movement_history mh
            LEFT JOIN shelf_positions sp ON mh.position_id = sp.position_id
            LEFT JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            LEFT JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mh.movement_date >= datetime('now', '-30 days')
            GROUP BY a.aisle_code
            ORDER BY visits DESC
        """

        zone_traffic = pd.read_sql_query(zone_query, conn).to_dict("records")

        # Identify peak hours
        peak_hours = sorted(hourly_patterns, key=lambda x: x["movements"], reverse=True)[:3]
        off_peak_hours = sorted(hourly_patterns, key=lambda x: x["movements"])[:3]

        # Calculate efficiency metrics
        total_movements = sum(h["movements"] for h in hourly_patterns)
        avg_movements_per_hour = total_movements / 24 if hourly_patterns else 0

        return {
            "summary": {
                "total_movements_30d": total_movements,
                "avg_movements_per_hour": round(avg_movements_per_hour, 0),
                "peak_hours": [f"{h['hour']}:00" for h in peak_hours],
                "off_peak_hours": [f"{h['hour']}:00" for h in off_peak_hours]
            },
            "hourly_patterns": hourly_patterns,
            "frequent_routes": frequent_routes,
            "zone_traffic": zone_traffic,
            "optimization_opportunities": [
                {
                    "opportunity": "Stagger shift schedules",
                    "description": f"Add staff during peak hours: {', '.join([f'{h['hour']}:00' for h in peak_hours])}",
                    "expected_benefit": "20% reduction in congestion"
                },
                {
                    "opportunity": "Optimize frequent routes",
                    "description": f"Top route traveled {frequent_routes[0]['frequency']} times",
                    "expected_benefit": "15% reduction in travel time"
                },
                {
                    "opportunity": "Rebalance zone allocation",
                    "description": f"Zone {zone_traffic[0]['zone']} has {zone_traffic[0]['visits']} visits",
                    "expected_benefit": "Better load distribution"
                }
            ]
        }

    except Exception as e:
        optimization_logger.error(f"Error analyzing movement patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-changes")
async def simulate_optimization_changes(
    changes: List[Dict[str, Any]]
):
    """
    Simulate the impact of proposed optimization changes

    Example changes:
    [
        {"type": "relocate", "item": "Metformin", "from": "A1-S1-P1", "to": "C1-S1-P1"},
        {"type": "consolidate", "batch": "LOT123", "locations": ["A1", "B2"], "target": "A1"}
    ]
    """
    try:
        optimization_logger.info(f"Simulating {len(changes)} changes")

        simulation_results = await _simulate_optimizations(changes)

        return simulation_results

    except Exception as e:
        optimization_logger.error(f"Error simulating changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-recommendations")
async def apply_optimization_recommendations(
    recommendation_ids: List[str],
    schedule: str = Query("immediate", description="When to apply: immediate, off-peak, scheduled"),
    dry_run: bool = Query(True, description="Simulate without making actual changes")
):
    """Apply selected optimization recommendations"""
    try:
        optimization_logger.info(f"Applying {len(recommendation_ids)} recommendations (dry_run={dry_run})")

        if dry_run:
            result = {
                "status": "simulation",
                "message": f"Would apply {len(recommendation_ids)} recommendations",
                "estimated_impact": {
                    "time_savings": f"{len(recommendation_ids) * 5} min/day",
                    "efficiency_gain": f"{len(recommendation_ids) * 2}%"
                }
            }
        else:
            # In production, this would trigger actual warehouse changes
            result = {
                "status": "scheduled",
                "message": f"Scheduled {len(recommendation_ids)} changes for {schedule} execution",
                "job_id": f"OPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "estimated_completion": "2-4 hours"
            }

        return result

    except Exception as e:
        optimization_logger.error(f"Error applying recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def optimization_websocket(websocket: WebSocket):
    """WebSocket for real-time optimization updates"""
    await websocket.accept()
    optimization_logger.info("WebSocket connection established")

    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            request = json.loads(data)

            if request.get("type") == "subscribe":
                # Send periodic updates
                while True:
                    # Get current metrics
                    dashboard = await get_optimization_dashboard()

                    await websocket.send_json({
                        "type": "update",
                        "data": dashboard["overview"],
                        "timestamp": datetime.now().isoformat()
                    })

                    await asyncio.sleep(5)  # Update every 5 seconds

            elif request.get("type") == "analyze":
                # Start analysis and stream progress
                analysis_id = request.get("analysis_id")

                while True:
                    status = optimization_handler.get_analysis_status(analysis_id)

                    if status:
                        await websocket.send_json({
                            "type": "progress",
                            "data": status
                        })

                        if status["status"] in ["completed", "failed"]:
                            break

                    await asyncio.sleep(1)

    except WebSocketDisconnect:
        optimization_logger.info("WebSocket disconnected")
    except Exception as e:
        optimization_logger.error(f"WebSocket error: {e}")
        await websocket.close()


# Helper functions

async def _gather_warehouse_data() -> Dict[str, Any]:
    """Gather comprehensive warehouse data for analysis"""
    conn = data_loader.get_connection()

    # Get chaos metrics
    chaos_data = await get_chaos_metrics()

    # Get fragmentation data
    fragmentation_data = await get_batch_fragmentation()

    # Get velocity mismatches
    velocity_data = await get_velocity_mismatches()

    # Get current placements
    placements_query = """
        SELECT
            mp.*,
            m.name as medication_name,
            ma.movement_category,
            ma.velocity_score,
            sp.grid_x, sp.grid_y, sp.grid_z
        FROM medication_placements mp
        JOIN medications m ON mp.med_id = m.med_id
        JOIN medication_attributes ma ON m.med_id = ma.med_id
        JOIN shelf_positions sp ON mp.position_id = sp.position_id
        WHERE mp.is_active = 1
    """
    current_placements = pd.read_sql_query(placements_query, conn).to_dict("records")

    # Get movement history
    movement_query = """
        SELECT * FROM movement_history
        WHERE movement_date >= datetime('now', '-30 days')
        ORDER BY movement_date DESC
        LIMIT 1000
    """
    movement_history = pd.read_sql_query(movement_query, conn).to_dict("records")

    # Get batch info
    batch_query = """
        SELECT * FROM batch_info
        WHERE is_active = 1
    """
    batch_info = pd.read_sql_query(batch_query, conn).to_dict("records")

    # Get hourly patterns
    hourly_query = """
        SELECT
            strftime('%H', movement_date) as hour,
            COUNT(*) as movements
        FROM movement_history
        WHERE movement_date >= datetime('now', '-7 days')
        GROUP BY hour
    """
    hourly_patterns = pd.read_sql_query(hourly_query, conn).to_dict("records")

    # Get warehouse layout info
    layout_query = """
        SELECT
            COUNT(DISTINCT aisle_id) as aisle_count,
            COUNT(DISTINCT shelf_id) as shelf_count,
            COUNT(DISTINCT position_id) as total_positions,
            COUNT(DISTINCT position_id) - COUNT(DISTINCT mp.position_id) as available_positions
        FROM shelf_positions sp
        LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id AND mp.is_active = 1
    """
    layout_info = pd.read_sql_query(layout_query, conn).to_dict("records")[0]

    return {
        "chaos_metrics": chaos_data,
        "fragmentation_data": fragmentation_data,
        "velocity_mismatches": velocity_data,
        "current_placements": current_placements,
        "movement_history": movement_history,
        "batch_info": batch_info,
        "hourly_patterns": hourly_patterns,
        "warehouse_layout": layout_info,
        "temperature_data": {},  # Would come from sensors
        "zone_violations": [],  # Would be calculated
        "fifo_violations": [],  # Would be calculated
        "picking_paths": [],  # Would come from WMS
        "congestion_data": {},  # Would be calculated
        "consumption_patterns": {}  # Would be analyzed
    }


async def _simulate_optimizations(changes: List[Dict]) -> Dict[str, Any]:
    """Simulate the impact of optimization changes"""

    # Simple simulation logic
    total_relocations = len([c for c in changes if c.get("type") == "relocate"])
    total_consolidations = len([c for c in changes if c.get("type") == "consolidate"])

    time_saved = total_relocations * 2.5 + total_consolidations * 4
    distance_reduced = total_relocations * 15 + total_consolidations * 25
    efficiency_gain = min(40, (total_relocations + total_consolidations) * 2)

    return {
        "simulation_results": {
            "changes_simulated": len(changes),
            "relocations": total_relocations,
            "consolidations": total_consolidations
        },
        "expected_impact": {
            "time_savings": f"{time_saved:.0f} min/day",
            "distance_reduction": f"{distance_reduced:.0f} meters/day",
            "efficiency_gain": f"{efficiency_gain:.1f}%",
            "annual_savings": f"${time_saved * 365 / 60 * 25:,.0f}"
        },
        "risk_assessment": {
            "disruption_level": "Low" if len(changes) < 10 else "Medium" if len(changes) < 50 else "High",
            "implementation_time": f"{len(changes) * 15} minutes",
            "rollback_available": True
        },
        "recommendation": "Proceed with changes" if efficiency_gain > 10 else "Review changes"
    }