"""
Warehouse API Routes

This module provides API endpoints for warehouse management including:
- Warehouse layout and zone information
- Aisle navigation and shelf details
- Medication placement and inventory tracking
- Real-time temperature and alerts
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


class WarehouseStats(BaseModel):
    total_medications: int
    total_aisles: int
    total_shelves: int
    avg_utilization: float
    critical_alerts: int
    expiring_soon: int
    temperature_alerts: int


class MoveRequest(BaseModel):
    med_id: int
    from_shelf: int
    to_shelf: int
    quantity: int
    reason: Optional[str] = "manual_movement"


class PlacementRecommendation(BaseModel):
    med_id: int
    recommended_positions: List[Dict[str, Any]]
    placement_score: float
    reasoning: str


def clean_nan_values(data: Any) -> Any:
    """Clean NaN values from response data"""
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, float):
        if pd.isna(data):
            return None
        return data
    return data


@router.get("/layout")
async def get_warehouse_layout():
    """
    Get complete warehouse layout with zones and aisles

    Returns:
        - Zones with temperature ranges and security levels
        - Aisles with shelf counts and utilization
        - Overall warehouse statistics
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Get zones with aisle count
        zones_query = """
            SELECT z.*, COUNT(DISTINCT a.aisle_id) as aisle_count
            FROM warehouse_zones z
            LEFT JOIN warehouse_aisles a ON z.zone_id = a.zone_id
            GROUP BY z.zone_id
        """
        zones = pd.read_sql_query(zones_query, conn).to_dict("records")

        # Get aisles with shelf count and utilization
        aisles_query = """
            SELECT a.*, COUNT(s.shelf_id) as shelf_count,
                   AVG(s.utilization_percent) as avg_utilization
            FROM warehouse_aisles a
            LEFT JOIN warehouse_shelves s ON a.aisle_id = s.aisle_id
            GROUP BY a.aisle_id
        """
        aisles = pd.read_sql_query(aisles_query, conn).to_dict("records")

        # Calculate warehouse statistics
        stats_query = """
            SELECT
                COUNT(DISTINCT m.med_id) as total_medications,
                COUNT(DISTINCT a.aisle_id) as total_aisles,
                COUNT(DISTINCT s.shelf_id) as total_shelves,
                AVG(s.utilization_percent) as avg_utilization
            FROM medications m
            LEFT JOIN warehouse_aisles a ON 1=1
            LEFT JOIN warehouse_shelves s ON 1=1
        """
        stats = pd.read_sql_query(stats_query, conn).to_dict("records")[0]

        # Get alert counts
        alerts_query = """
            SELECT
                COUNT(CASE WHEN b.expiry_date <= date('now', '+30 days') THEN 1 END) as expiring_soon,
                COUNT(CASE WHEN b.expiry_date <= date('now', '+7 days') THEN 1 END) as critical_alerts,
                COUNT(CASE WHEN t.alert_triggered = 1 THEN 1 END) as temperature_alerts
            FROM batch_info b
            LEFT JOIN temperature_readings t ON t.reading_time >= datetime('now', '-1 hour')
        """
        alerts = pd.read_sql_query(alerts_query, conn).to_dict("records")[0]

        stats.update(alerts)

        return clean_nan_values(
            {"zones": zones, "aisles": aisles, "stats": WarehouseStats(**stats).dict()}
        )

    except Exception as e:
        logger.error(f"Error fetching warehouse layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aisle/{aisle_id}")
async def get_aisle_details(aisle_id: int):
    """
    Get detailed aisle information with shelves and medications

    Returns:
        - Aisle details with zone information
        - All shelves in the aisle with utilization
        - Medications currently stored in the aisle
        - Temperature and humidity readings
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Get aisle information
        aisle_query = """
            SELECT a.*, z.zone_name, z.temperature_range, z.security_level
            FROM warehouse_aisles a
            JOIN warehouse_zones z ON a.zone_id = z.zone_id
            WHERE a.aisle_id = ?
        """
        aisle = pd.read_sql_query(aisle_query, conn, params=[aisle_id]).to_dict(
            "records"
        )

        if not aisle:
            raise HTTPException(status_code=404, detail="Aisle not found")

        aisle = aisle[0]

        # Get shelves with medication count
        shelves_query = """
            SELECT s.*,
                   COUNT(DISTINCT mp.med_id) as medication_count,
                   SUM(mp.quantity) as total_items,
                   COUNT(mp.position_id) as occupied_positions
            FROM warehouse_shelves s
            LEFT JOIN shelf_positions sp ON s.shelf_id = sp.shelf_id
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            WHERE s.aisle_id = ?
            GROUP BY s.shelf_id
            ORDER BY s.position, s.level
        """
        shelves = pd.read_sql_query(shelves_query, conn, params=[aisle_id]).to_dict(
            "records"
        )

        # Get medications in this aisle
        meds_query = """
            SELECT DISTINCT m.*, mp.quantity, mp.batch_id, sp.shelf_id, b.expiry_date,
                   b.lot_number as batch_number,
                   ma.velocity_score, ma.movement_category
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            LEFT JOIN batch_info b ON mp.batch_id = b.batch_id
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            WHERE s.aisle_id = ? AND mp.is_active = 1
        """
        medications = pd.read_sql_query(meds_query, conn, params=[aisle_id]).to_dict(
            "records"
        )

        # Get latest temperature reading
        temp_query = """
            SELECT temperature, humidity, reading_time
            FROM temperature_readings
            WHERE aisle_id = ?
            ORDER BY reading_time DESC
            LIMIT 1
        """
        temperature = pd.read_sql_query(temp_query, conn, params=[aisle_id]).to_dict(
            "records"
        )

        return clean_nan_values(
            {
                "aisle": aisle,
                "shelves": shelves,
                "medications": medications,
                "temperature": temperature[0] if temperature else None,
                "total_medications": len(medications),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching aisle details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shelf/{shelf_id}")
async def get_shelf_inventory(shelf_id: int):
    """
    Get detailed shelf inventory with simple medication list

    Returns:
        - Shelf information with capacity metrics
        - List of medications with quantities
        - Batch information and expiry dates
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Get shelf information
        shelf_query = """
            SELECT s.*, a.aisle_name, a.category
            FROM warehouse_shelves s
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE s.shelf_id = ?
        """
        shelf = pd.read_sql_query(shelf_query, conn, params=[shelf_id]).to_dict(
            "records"
        )

        if not shelf:
            raise HTTPException(status_code=404, detail="Shelf not found")

        shelf = shelf[0]

        # Get medications on this shelf
        medications_query = """
            SELECT m.med_id, m.name, m.category,
                   SUM(mp.quantity) as total_quantity,
                   COUNT(DISTINCT mp.batch_id) as batch_count,
                   MIN(b.expiry_date) as earliest_expiry,
                   ma.movement_category
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            LEFT JOIN batch_info b ON mp.batch_id = b.batch_id
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            WHERE sp.shelf_id = ? AND mp.is_active = 1
            GROUP BY m.med_id, m.name, m.category
        """
        medications = pd.read_sql_query(
            medications_query, conn, params=[shelf_id]
        ).to_dict("records")

        # Get batch details
        batches_query = """
            SELECT b.batch_id, b.lot_number, b.expiry_date,
                   mp.quantity, m.name as medication_name
            FROM medication_placements mp
            JOIN batch_info b ON mp.batch_id = b.batch_id
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            WHERE sp.shelf_id = ? AND mp.is_active = 1
            ORDER BY b.expiry_date
        """
        batches = pd.read_sql_query(batches_query, conn, params=[shelf_id]).to_dict(
            "records"
        )

        # Calculate capacity
        capacity_query = """
            SELECT
                COUNT(*) as total_positions,
                COUNT(CASE WHEN mp.position_id IS NOT NULL THEN 1 END) as occupied_positions
            FROM shelf_positions sp
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            WHERE sp.shelf_id = ?
        """
        capacity = pd.read_sql_query(capacity_query, conn, params=[shelf_id]).to_dict(
            "records"
        )[0]

        return clean_nan_values(
            {
                "shelf": shelf,
                "medications": medications,
                "batches": batches,
                "capacity": capacity,
                "utilization_percent": round(
                    (capacity["occupied_positions"] / capacity["total_positions"])
                    * 100,
                    1,
                )
                if capacity["total_positions"] > 0
                else 0,
            }
        )

    except Exception as e:
        logger.error(f"Error fetching shelf inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shelf/{shelf_id}/detailed")
async def get_detailed_shelf_layout(shelf_id: int):
    """
    Get comprehensive shelf layout with all positions and medications in a 3D grid

    Returns:
        - Detailed position grid (10x3 layout)
        - Medication placement with FIFO organization
        - Position relationships (front/middle/back)
        - Placement strategy and alerts
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Get shelf information
        shelf_query = """
            SELECT s.*, a.aisle_name, a.category, a.temperature
            FROM warehouse_shelves s
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE s.shelf_id = ?
        """
        shelf = pd.read_sql_query(shelf_query, conn, params=[shelf_id])

        if shelf.empty:
            raise HTTPException(status_code=404, detail="Shelf not found")

        # Get all positions for this shelf with medications
        positions_query = """
            SELECT p.*,
                   mp.med_id, mp.batch_id, mp.quantity, mp.expiry_date,
                   m.name as med_name, m.category as med_category,
                   ma.velocity_score, ma.movement_category,
                   b.lot_number,
                   CASE
                       WHEN p.grid_y = 1 THEN 'F' || p.grid_x
                       WHEN p.grid_y = 2 THEN 'M' || p.grid_x
                       WHEN p.grid_y = 3 THEN 'B' || p.grid_x
                   END as grid_label
            FROM shelf_positions p
            LEFT JOIN medication_placements mp ON p.position_id = mp.position_id
                AND mp.is_active = 1
            LEFT JOIN medications m ON mp.med_id = m.med_id
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            LEFT JOIN batch_info b ON mp.batch_id = b.batch_id
            WHERE p.shelf_id = ?
            ORDER BY p.grid_y, p.grid_x
        """
        positions = pd.read_sql_query(positions_query, conn, params=[shelf_id])

        # Ensure unique column names to avoid pandas warnings when converting to dict
        def _dedupe_cols(cols):
            seen = {}
            out = []
            for c in cols:
                if c not in seen:
                    seen[c] = 0
                    out.append(c)
                else:
                    seen[c] += 1
                    out.append(f"{c}.{seen[c]}")
            return out

        positions.columns = _dedupe_cols(list(positions.columns))

        # Structure the response
        shelf_data = shelf.to_dict("records")[0] if not shelf.empty else {}

        # Group positions by row
        front_row = positions.loc[positions["grid_y"] == 1].to_dict("records")
        middle_row = positions.loc[positions["grid_y"] == 2].to_dict("records")
        back_row = positions.loc[positions["grid_y"] == 3].to_dict("records")

        # Calculate statistics
        total_positions = len(positions)
        occupied_positions = int(positions["med_id"].notna().sum())

        # Build position map
        position_map = {}
        for _, pos in positions.iterrows():
            if pd.notna(pos["med_id"]):
                position_map[pos["grid_label"]] = {
                    "med_name": pos["med_name"],
                    "quantity": int(pos["quantity"])
                    if pd.notna(pos["quantity"])
                    else 0,
                    "expiry": pos["expiry_date"],
                    "velocity": pos["movement_category"],
                }

        # Add relationships for front row items
        for pos in front_row:
            grid_x = pos["grid_x"]
            behind_label = f"M{grid_x}"
            further_back_label = f"B{grid_x}"

            if behind_label in position_map:
                pos["behind"] = position_map[behind_label]["med_name"]
            if further_back_label in position_map:
                pos["further_back"] = position_map[further_back_label]["med_name"]

        # Check for alerts
        alerts = []
        for _, pos in positions.iterrows():
            if pd.notna(pos["expiry_date"]):
                expiry_date = pd.to_datetime(pos["expiry_date"])
                days_until_expiry = (expiry_date - pd.Timestamp.now()).days

                if days_until_expiry <= 7:
                    alerts.append(
                        {
                            "type": "critical_expiry",
                            "position": pos["grid_label"],
                            "message": f"{pos['med_name']} expires in {days_until_expiry} days",
                            "severity": "critical",
                        }
                    )
                elif days_until_expiry <= 30:
                    alerts.append(
                        {
                            "type": "expiry",
                            "position": pos["grid_label"],
                            "message": f"{pos['med_name']} expires in {days_until_expiry} days",
                            "severity": "warning",
                        }
                    )

        response = {
            "shelf": shelf_data,
            "dimensions": {
                "width_slots": 10,
                "depth_rows": 3,
                "total_positions": total_positions,
                "occupied_positions": int(occupied_positions),
                "utilization_percent": round(
                    (occupied_positions / max(total_positions, 1)) * 100, 1
                ),
            },
            "rows": {"front": front_row, "middle": middle_row, "back": back_row},
            "placement_strategy": {
                "front_row": "Fast-moving items, items expiring soon, high-pick frequency",
                "middle_row": "Medium velocity items, standard stock",
                "back_row": "Slow-moving items, overstock, newer batches",
            },
            "position_map": position_map,
            "alerts": alerts,
        }

        # Add capacity snapshot derived from grid (10 x 3)
        try:
            total_capacity_slots = int(total_positions)
            available_slots = int(total_capacity_slots - occupied_positions)
            response["capacity"] = {
                "total_slots": total_capacity_slots,
                "used_slots": int(occupied_positions),
                "available_slots": max(0, available_slots),
                "utilization_percent": response["dimensions"]["utilization_percent"],
            }
        except Exception:
            pass

        return clean_nan_values(response)

    except Exception as e:
        logger.error(f"Error fetching detailed shelf layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/move")
async def move_medication(move_request: MoveRequest):
    """
    Move medication between shelves

    Records the movement in history and updates placement records
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()
        cursor = conn.cursor()

        # Import WebSocket manager for real-time updates
        from src.api.websocket_manager import ws_manager

        # Validate source shelf has the medication
        check_query = """
            SELECT mp.placement_id, mp.quantity, sp.position_id
            FROM medication_placements mp
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            WHERE sp.shelf_id = ? AND mp.med_id = ? AND mp.is_active = 1
            LIMIT 1
        """
        cursor.execute(check_query, (move_request.from_shelf, move_request.med_id))
        source = cursor.fetchone()

        if not source:
            raise HTTPException(
                status_code=400, detail="Medication not found on source shelf"
            )

        if source[1] < move_request.quantity:
            raise HTTPException(
                status_code=400, detail="Insufficient quantity on source shelf"
            )

        # Find available position on target shelf
        target_query = """
            SELECT sp.position_id
            FROM shelf_positions sp
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            WHERE sp.shelf_id = ? AND mp.position_id IS NULL
            LIMIT 1
        """
        cursor.execute(target_query, (move_request.to_shelf,))
        target = cursor.fetchone()

        if not target:
            raise HTTPException(
                status_code=400, detail="No available position on target shelf"
            )

        # Update source placement
        if source[1] == move_request.quantity:
            # Moving all quantity - deactivate source placement
            cursor.execute(
                "UPDATE medication_placements SET is_active = 0 WHERE placement_id = ?",
                (source[0],),
            )
        else:
            # Partial move - reduce quantity
            cursor.execute(
                "UPDATE medication_placements SET quantity = quantity - ? WHERE placement_id = ?",
                (move_request.quantity, source[0]),
            )

        # Create new placement on target shelf
        cursor.execute(
            """
            INSERT INTO medication_placements
            (position_id, med_id, quantity, placement_date, placement_reason, is_active)
            VALUES (?, ?, ?, datetime('now'), ?, 1)
        """,
            (
                target[0],
                move_request.med_id,
                move_request.quantity,
                move_request.reason,
            ),
        )

        # Record movement in history
        cursor.execute(
            """
            INSERT INTO movement_history
            (med_id, position_id, movement_type, quantity, movement_date)
            VALUES (?, ?, 'relocate', ?, datetime('now'))
        """,
            (move_request.med_id, target[0], move_request.quantity),
        )

        conn.commit()

        # Broadcast movement via WebSocket
        import asyncio

        asyncio.create_task(
            ws_manager.broadcast_inventory_movement(
                move_request.med_id,
                move_request.from_shelf,
                move_request.to_shelf,
                move_request.quantity,
            )
        )

        return {
            "success": True,
            "message": f"Moved {move_request.quantity} units of medication {move_request.med_id}",
            "from_shelf": move_request.from_shelf,
            "to_shelf": move_request.to_shelf,
        }

    except Exception as e:
        logger.error(f"Error moving medication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_warehouse_alerts():
    """
    Get all active warehouse alerts

    Returns temperature, expiry, and capacity alerts
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        alerts = []

        # Temperature alerts
        temp_alerts_query = """
            SELECT t.*, a.aisle_name
            FROM temperature_readings t
            JOIN warehouse_aisles a ON t.aisle_id = a.aisle_id
            WHERE t.alert_triggered = 1
                AND t.reading_time >= datetime('now', '-1 hour')
        """
        temp_alerts = pd.read_sql_query(temp_alerts_query, conn).to_dict("records")

        for alert in temp_alerts:
            alerts.append(
                {
                    "type": "temperature",
                    "severity": "warning",
                    "location": alert["aisle_name"],
                    "message": f"Temperature out of range: {alert['temperature']}°C",
                    "timestamp": alert["reading_time"],
                }
            )

        # Expiry alerts
        expiry_query = """
            SELECT m.name, b.lot_number, b.expiry_date,
                   s.shelf_code, a.aisle_name,
                   julianday(b.expiry_date) - julianday('now') as days_until_expiry
            FROM batch_info b
            JOIN medication_placements mp ON b.batch_id = mp.batch_id
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mp.is_active = 1
                AND b.expiry_date <= date('now', '+30 days')
            ORDER BY b.expiry_date
        """
        expiry_alerts = pd.read_sql_query(expiry_query, conn).to_dict("records")

        for alert in expiry_alerts:
            days = int(alert["days_until_expiry"])
            severity = "critical" if days <= 7 else "warning"

            alerts.append(
                {
                    "type": "expiry",
                    "severity": severity,
                    "location": f"{alert['aisle_name']} - {alert['shelf_code']}",
                    "message": f"{alert['name']} (Lot: {alert['lot_number']}) expires in {days} days",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Capacity alerts
        capacity_query = """
            SELECT s.shelf_id, s.shelf_code, a.aisle_name,
                   s.utilization_percent
            FROM warehouse_shelves s
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE s.utilization_percent > 90
        """
        capacity_alerts = pd.read_sql_query(capacity_query, conn).to_dict("records")

        for alert in capacity_alerts:
            alerts.append(
                {
                    "type": "capacity",
                    "severity": "info",
                    "location": f"{alert['aisle_name']} - {alert['shelf_code']}",
                    "message": f"Shelf at {alert['utilization_percent']:.1f}% capacity",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return clean_nan_values(
            {
                "alerts": alerts,
                "total_count": len(alerts),
                "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
                "warning_count": sum(1 for a in alerts if a["severity"] == "warning"),
                "info_count": sum(1 for a in alerts if a["severity"] == "info"),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching warehouse alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/placement/recommend/{med_id}")
async def get_placement_recommendation(med_id: int):
    """
    Get optimal placement recommendations for a medication

    Uses velocity, weight, expiry, and ABC classification to suggest best positions
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Get medication attributes
        med_query = """
            SELECT m.*, ma.*
            FROM medications m
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            WHERE m.med_id = ?
        """
        medication_df = pd.read_sql_query(med_query, conn, params=[med_id])

        def _dedupe_cols(cols):
            seen = {}
            out = []
            for c in cols:
                if c not in seen:
                    seen[c] = 0
                    out.append(c)
                else:
                    seen[c] += 1
                    out.append(f"{c}.{seen[c]}")
            return out

        medication_df.columns = _dedupe_cols(list(medication_df.columns))
        medication = medication_df.to_dict("records")

        if not medication:
            raise HTTPException(status_code=404, detail="Medication not found")

        med = medication[0]

        # Find available positions
        available_query = """
            SELECT sp.*, s.shelf_code, s.level, a.aisle_name, a.category as aisle_category
            FROM shelf_positions sp
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            WHERE mp.position_id IS NULL
        """
        available_positions = pd.read_sql_query(available_query, conn)

        if available_positions.empty:
            return {
                "med_id": med_id,
                "medication_name": med["name"],
                "recommended_positions": [],
                "reasoning": "No available positions in warehouse",
            }

        # Calculate scores for each position
        recommendations = []

        for _, pos in available_positions.iterrows():
            score = 0
            reasons = []

            # Velocity-based scoring
            if med.get("movement_category") == "Fast" and pos["grid_y"] == 1:
                score += 40
                reasons.append("Front row for fast-moving item")
            elif med.get("movement_category") == "Medium" and pos["grid_y"] == 2:
                score += 30
                reasons.append("Middle row for medium velocity")
            elif med.get("movement_category") == "Slow" and pos["grid_y"] == 3:
                score += 30
                reasons.append("Back row for slow-moving item")

            # Golden zone bonus
            if pos["is_golden_zone"] and med.get("abc_classification") == "A":
                score += 20
                reasons.append("Golden zone for A-class item")

            # Category matching
            if (
                med.get("requires_refrigeration")
                and "refrigerat" in pos["aisle_category"].lower()
            ):
                score += 50
                reasons.append("Refrigerated aisle required")
            elif (
                med.get("requires_security")
                and "controlled" in pos["aisle_category"].lower()
            ):
                score += 50
                reasons.append("Controlled substance area")

            # Accessibility scoring
            score += pos["accessibility"] * 10

            if score > 0:
                recommendations.append(
                    {
                        "position_id": int(pos["position_id"]),
                        "location": f"{pos['aisle_name']} - {pos['shelf_code']} - {pos['grid_label']}",
                        "score": score,
                        "reasons": reasons,
                    }
                )

        # Sort by score and return top 5
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        top_recommendations = recommendations[:5]

        # Generate overall reasoning
        if top_recommendations:
            best = top_recommendations[0]
            reasoning = f"Best position based on: {', '.join(best['reasons'])}"
        else:
            reasoning = "No suitable positions found matching medication requirements"

        return clean_nan_values(
            {
                "med_id": med_id,
                "medication_name": med["name"],
                "recommended_positions": top_recommendations,
                "placement_score": top_recommendations[0]["score"]
                if top_recommendations
                else 0,
                "reasoning": reasoning,
            }
        )

    except Exception as e:
        logger.error(f"Error getting placement recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fifo/validate")
async def validate_fifo_compliance():
    """
    Validate FIFO compliance across the warehouse

    Checks if older batches are positioned in front of newer batches
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Find FIFO violations
        violations_query = """
            WITH batch_positions AS (
                SELECT
                    m.med_id,
                    m.name as med_name,
                    b.batch_id,
                    b.lot_number,
                    b.expiry_date,
                    sp.grid_y,
                    sp.grid_x,
                    s.shelf_id,
                    s.shelf_code,
                    a.aisle_name
                FROM medication_placements mp
                JOIN batch_info b ON mp.batch_id = b.batch_id
                JOIN medications m ON mp.med_id = m.med_id
                JOIN shelf_positions sp ON mp.position_id = sp.position_id
                JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
                JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
                WHERE mp.is_active = 1
            )
            SELECT
                bp1.med_name,
                bp1.lot_number as older_batch,
                bp1.expiry_date as older_expiry,
                bp1.grid_y as older_position_y,
                bp2.lot_number as newer_batch,
                bp2.expiry_date as newer_expiry,
                bp2.grid_y as newer_position_y,
                bp1.aisle_name,
                bp1.shelf_code
            FROM batch_positions bp1
            JOIN batch_positions bp2 ON bp1.med_id = bp2.med_id
                AND bp1.shelf_id = bp2.shelf_id
                AND bp1.batch_id != bp2.batch_id
            WHERE bp1.expiry_date < bp2.expiry_date
                AND bp1.grid_y > bp2.grid_y
        """
        violations = pd.read_sql_query(violations_query, conn).to_dict("records")

        # Calculate compliance rate
        total_query = """
            SELECT COUNT(DISTINCT batch_id) as total_batches
            FROM medication_placements
            WHERE is_active = 1
        """
        total = pd.read_sql_query(total_query, conn).to_dict("records")[0]

        compliance_rate = 100.0
        if total["total_batches"] > 0:
            violation_count = len(violations)
            compliance_rate = (
                (total["total_batches"] - violation_count) / total["total_batches"]
            ) * 100

        return clean_nan_values(
            {
                "fifo_compliant": len(violations) == 0,
                "compliance_rate": round(compliance_rate, 1),
                "violations": violations[:10],  # Return top 10 violations
                "total_violations": len(violations),
                "total_batches": total["total_batches"],
                "recommendation": "Reorganize items with older batches to front positions"
                if violations
                else "FIFO compliance maintained",
            }
        )

    except Exception as e:
        logger.error(f"Error validating FIFO compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/movement")
async def get_movement_statistics(
    days: int = Query(default=7, description="Number of days to analyze"),
):
    """
    Get movement statistics for the warehouse

    Analyzes pick frequency, movement patterns, and velocity trends
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Movement by type
        movement_types_query = f"""
            SELECT
                movement_type,
                COUNT(*) as count,
                SUM(quantity) as total_quantity
            FROM movement_history
            WHERE movement_date >= datetime('now', '-{days} days')
            GROUP BY movement_type
        """
        movement_types = pd.read_sql_query(movement_types_query, conn).to_dict(
            "records"
        )

        # Top moved medications
        top_meds_query = f"""
            SELECT
                m.name,
                COUNT(mh.movement_id) as movement_count,
                SUM(mh.quantity) as total_quantity_moved,
                ma.movement_category
            FROM movement_history mh
            JOIN medications m ON mh.med_id = m.med_id
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            WHERE mh.movement_date >= datetime('now', '-{days} days')
            GROUP BY m.med_id, m.name
            ORDER BY movement_count DESC
            LIMIT 10
        """
        top_medications = pd.read_sql_query(top_meds_query, conn).to_dict("records")

        # Movement by hour
        hourly_query = f"""
            SELECT
                strftime('%H', movement_date) as hour,
                COUNT(*) as movements
            FROM movement_history
            WHERE movement_date >= datetime('now', '-{days} days')
            GROUP BY hour
            ORDER BY hour
        """
        hourly_pattern = pd.read_sql_query(hourly_query, conn).to_dict("records")

        # Calculate peak hours
        if hourly_pattern:
            peak_hour = max(hourly_pattern, key=lambda x: x["movements"])
        else:
            peak_hour = None

        return clean_nan_values(
            {
                "period_days": days,
                "movement_types": movement_types,
                "top_medications": top_medications,
                "hourly_pattern": hourly_pattern,
                "peak_hour": peak_hour["hour"] if peak_hour else None,
                "total_movements": sum(mt["count"] for mt in movement_types),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching movement statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chaos/metrics")
async def get_chaos_metrics():
    """
    Get current chaos metrics for the warehouse

    Returns metrics showing warehouse inefficiencies and optimization potential
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Get all chaos metrics
        metrics_query = """
            SELECT
                metric_name,
                current_chaos_score,
                optimal_score,
                improvement_potential
            FROM warehouse_chaos_metrics
            ORDER BY improvement_potential DESC
        """
        metrics = pd.read_sql_query(metrics_query, conn).to_dict('records')

        # Calculate overall chaos score
        overall_chaos = 0
        if metrics:
            overall_chaos = sum(m['current_chaos_score'] for m in metrics if m['current_chaos_score']) / len(metrics)

        return clean_nan_values({
            "chaos_metrics": metrics,
            "overall_chaos_score": round(overall_chaos, 2),
            "total_improvement_potential": sum(m['improvement_potential'] for m in metrics if m['improvement_potential'])
        })

    except Exception as e:
        logger.error(f"Error fetching chaos metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chaos/batch-fragmentation")
async def get_batch_fragmentation():
    """
    Get details of fragmented batches that need consolidation

    Shows batches split across multiple locations
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Find fragmented batches
        fragmentation_query = """
            SELECT
                b.lot_number,
                m.name as medication_name,
                b.batch_id,
                COUNT(DISTINCT mp.position_id) as num_locations,
                SUM(mp.quantity) as total_quantity,
                GROUP_CONCAT(DISTINCT a.aisle_code || '-' || s.shelf_code) as locations,
                b.expiry_date
            FROM medication_placements mp
            JOIN batch_info b ON mp.batch_id = b.batch_id
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mp.is_active = 1
            GROUP BY b.batch_id
            HAVING num_locations > 1
            ORDER BY num_locations DESC, b.expiry_date
        """

        fragmented_batches = pd.read_sql_query(fragmentation_query, conn).to_dict('records')

        # Calculate fragmentation statistics
        total_batches_query = "SELECT COUNT(DISTINCT batch_id) as total FROM batch_info"
        total_batches = pd.read_sql_query(total_batches_query, conn).iloc[0]['total']

        fragmentation_rate = (len(fragmented_batches) / total_batches * 100) if total_batches > 0 else 0

        return clean_nan_values({
            "fragmented_batches": fragmented_batches[:20],  # Top 20 most fragmented
            "total_fragmented": len(fragmented_batches),
            "total_batches": int(total_batches),  # Convert numpy int64 to regular int
            "fragmentation_rate": round(fragmentation_rate, 2),
            "consolidation_opportunity": f"{len(fragmented_batches)} batches could be consolidated"
        })

    except Exception as e:
        logger.error(f"Error fetching batch fragmentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chaos/velocity-mismatches")
async def get_velocity_mismatches():
    """
    Get medications placed in wrong zones based on velocity

    Shows fast-moving items in back zones and slow-moving items in prime locations
    """
    try:
        from api.routes import data_loader

        conn = data_loader.get_connection()

        # Find velocity mismatches
        mismatch_query = """
            SELECT
                m.name as medication_name,
                ma.movement_category,
                ma.velocity_score,
                sp.grid_y,
                CASE sp.grid_y
                    WHEN 1 THEN 'Front'
                    WHEN 2 THEN 'Middle'
                    WHEN 3 THEN 'Back'
                END as row_position,
                a.aisle_code || '-' || s.shelf_code || '-' || sp.grid_label as location,
                mp.quantity,
                CASE
                    WHEN ma.movement_category = 'Fast' AND sp.grid_y = 3 THEN 'Fast item in back'
                    WHEN ma.movement_category = 'Slow' AND sp.grid_y = 1 THEN 'Slow item in front'
                    WHEN ma.movement_category = 'Medium' AND sp.is_golden_zone = 1 THEN 'Medium item in golden zone'
                END as issue
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN medication_attributes ma ON m.med_id = ma.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE mp.is_active = 1
            AND (
                (ma.movement_category = 'Fast' AND sp.grid_y = 3)
                OR (ma.movement_category = 'Slow' AND sp.grid_y = 1)
                OR (ma.movement_category = 'Medium' AND sp.is_golden_zone = 1)
            )
            ORDER BY ma.velocity_score DESC
        """

        mismatches = pd.read_sql_query(mismatch_query, conn).to_dict('records')

        # Get optimal placement reference
        optimal_query = """
            SELECT * FROM velocity_zone_mapping
            ORDER BY velocity_category
        """
        optimal_mapping = pd.read_sql_query(optimal_query, conn).to_dict('records')

        return clean_nan_values({
            "velocity_mismatches": mismatches[:30],  # Top 30 mismatches
            "total_mismatches": len(mismatches),
            "optimal_mapping": optimal_mapping,
            "relocation_opportunity": f"{len(mismatches)} items could be relocated for better efficiency"
        })

    except Exception as e:
        logger.error(f"Error fetching velocity mismatches: {e}")
        raise HTTPException(status_code=500, detail=str(e))
