"""
Optimized Warehouse API Routes with Performance Enhancements

Performance optimizations include:
- Response caching with TTL
- Query optimization and batching
- Connection pooling
- Lazy loading
- Response compression
- Pagination support
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import json
import asyncio
from functools import wraps
from src.utils.cache_manager import warehouse_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/warehouse/v2", tags=["warehouse-optimized"])


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


def cache_response(ttl_seconds: int = 30):
    """Decorator to cache API responses"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = warehouse_cache._generate_key(
                func.__name__,
                {'args': str(args), 'kwargs': str(kwargs)}
            )

            # Check cache
            cached_result = warehouse_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            warehouse_cache.set(cache_key, result, ttl_seconds)

            return result
        return wrapper
    return decorator


@router.get("/layout")
@cache_response(ttl_seconds=60)
async def get_warehouse_layout():
    """
    Optimized warehouse layout endpoint with caching and batch queries

    Performance optimizations:
    - Single query with JOINs instead of multiple queries
    - Result caching for 60 seconds
    - Indexed columns for faster lookups
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()

        # Optimized single query with all needed data
        layout_query = """
        WITH zone_data AS (
            SELECT
                z.zone_id,
                z.zone_name,
                z.zone_type,
                z.temperature_range,
                z.security_level,
                COUNT(DISTINCT a.aisle_id) as aisle_count
            FROM warehouse_zones z
            LEFT JOIN warehouse_aisles a ON z.zone_id = a.zone_id
            GROUP BY z.zone_id
        ),
        aisle_data AS (
            SELECT
                a.aisle_id,
                a.zone_id,
                a.aisle_code,
                a.aisle_name,
                a.position_x,
                a.position_z,
                a.temperature,
                a.humidity,
                a.category,
                COUNT(DISTINCT s.shelf_id) as shelf_count,
                AVG(s.utilization_percent) as avg_utilization
            FROM warehouse_aisles a
            LEFT JOIN warehouse_shelves s ON a.aisle_id = s.aisle_id
            GROUP BY a.aisle_id
        ),
        stats_data AS (
            SELECT
                COUNT(DISTINCT m.med_id) as total_medications,
                COUNT(DISTINCT a.aisle_id) as total_aisles,
                COUNT(DISTINCT s.shelf_id) as total_shelves,
                AVG(s.utilization_percent) as avg_utilization,
                SUM(CASE WHEN b.expiry_date <= date('now', '+30 days') THEN 1 ELSE 0 END) as expiring_soon,
                SUM(CASE WHEN b.expiry_date <= date('now', '+7 days') THEN 1 ELSE 0 END) as critical_alerts
            FROM medications m
            CROSS JOIN warehouse_aisles a
            CROSS JOIN warehouse_shelves s
            LEFT JOIN batch_info b ON 1=1
        )
        SELECT
            (SELECT json_group_array(json_object(
                'zone_id', zone_id,
                'zone_name', zone_name,
                'zone_type', zone_type,
                'temperature_range', temperature_range,
                'security_level', security_level,
                'aisle_count', aisle_count
            )) FROM zone_data) as zones,
            (SELECT json_group_array(json_object(
                'aisle_id', aisle_id,
                'zone_id', zone_id,
                'aisle_code', aisle_code,
                'aisle_name', aisle_name,
                'position_x', position_x,
                'position_z', position_z,
                'temperature', temperature,
                'humidity', humidity,
                'category', category,
                'shelf_count', shelf_count,
                'avg_utilization', avg_utilization
            )) FROM aisle_data) as aisles,
            (SELECT json_object(
                'total_medications', total_medications,
                'total_aisles', total_aisles,
                'total_shelves', total_shelves,
                'avg_utilization', avg_utilization,
                'expiring_soon', expiring_soon,
                'critical_alerts', critical_alerts,
                'temperature_alerts', 0
            ) FROM stats_data) as stats
        """

        # Execute optimized query
        cursor = conn.cursor()
        cursor.execute(layout_query)
        result = cursor.fetchone()

        # Parse JSON results
        zones = json.loads(result[0]) if result[0] else []
        aisles = json.loads(result[1]) if result[1] else []
        stats = json.loads(result[2]) if result[2] else {}

        return clean_nan_values({
            "zones": zones,
            "aisles": aisles,
            "stats": stats,
            "cached": False
        })

    except Exception as e:
        logger.error(f"Error fetching warehouse layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aisle/{aisle_id}")
@cache_response(ttl_seconds=45)
async def get_aisle_details(aisle_id: int):
    """
    Optimized aisle details with batched queries and caching
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()

        # Use a single optimized query with CTEs
        aisle_details_query = f"""
        WITH aisle_info AS (
            SELECT a.*, z.zone_name, z.temperature_range, z.security_level
            FROM warehouse_aisles a
            JOIN warehouse_zones z ON a.zone_id = z.zone_id
            WHERE a.aisle_id = {aisle_id}
        ),
        shelf_info AS (
            SELECT
                s.shelf_id,
                s.aisle_id,
                s.shelf_code,
                s.position,
                s.level,
                s.capacity_slots,
                s.utilization_percent,
                s.status,
                COUNT(DISTINCT mp.med_id) as medication_count,
                SUM(mp.quantity) as total_items,
                COUNT(DISTINCT mp.position_id) as occupied_positions
            FROM warehouse_shelves s
            LEFT JOIN shelf_positions sp ON s.shelf_id = sp.shelf_id
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            WHERE s.aisle_id = {aisle_id}
            GROUP BY s.shelf_id
        ),
        med_info AS (
            SELECT DISTINCT
                m.med_id,
                m.name,
                m.category,
                mp.quantity,
                sp.shelf_id,
                b.expiry_date,
                ma.velocity_score,
                ma.movement_category
            FROM medication_placements mp
            JOIN medications m ON mp.med_id = m.med_id
            JOIN shelf_positions sp ON mp.position_id = sp.position_id
            JOIN warehouse_shelves s ON sp.shelf_id = s.shelf_id
            LEFT JOIN batch_info b ON mp.batch_id = b.batch_id
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            WHERE s.aisle_id = {aisle_id} AND mp.is_active = 1
        ),
        temp_info AS (
            SELECT temperature, humidity, reading_time
            FROM temperature_readings
            WHERE aisle_id = {aisle_id}
            ORDER BY reading_time DESC
            LIMIT 1
        )
        SELECT
            (SELECT json_object(
                'aisle_id', aisle_id,
                'aisle_code', aisle_code,
                'aisle_name', aisle_name,
                'zone_id', zone_id,
                'zone_name', zone_name,
                'temperature_range', temperature_range,
                'security_level', security_level,
                'temperature', temperature,
                'humidity', humidity,
                'category', category
            ) FROM aisle_info) as aisle,
            (SELECT json_group_array(json_object(
                'shelf_id', shelf_id,
                'shelf_code', shelf_code,
                'position', position,
                'level', level,
                'capacity_slots', capacity_slots,
                'utilization_percent', utilization_percent,
                'medication_count', medication_count,
                'total_items', total_items,
                'occupied_positions', occupied_positions
            )) FROM shelf_info) as shelves,
            (SELECT json_group_array(json_object(
                'med_id', med_id,
                'name', name,
                'category', category,
                'quantity', quantity,
                'shelf_id', shelf_id,
                'expiry_date', expiry_date,
                'velocity_score', velocity_score,
                'movement_category', movement_category
            )) FROM med_info) as medications,
            (SELECT json_object(
                'temperature', temperature,
                'humidity', humidity,
                'reading_time', reading_time
            ) FROM temp_info) as temperature
        """

        cursor = conn.cursor()
        cursor.execute(aisle_details_query)
        result = cursor.fetchone()

        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Aisle not found")

        aisle = json.loads(result[0]) if result[0] else None
        shelves = json.loads(result[1]) if result[1] else []
        medications = json.loads(result[2]) if result[2] else []
        temperature = json.loads(result[3]) if result[3] else None

        return clean_nan_values({
            "aisle": aisle,
            "shelves": shelves,
            "medications": medications,
            "temperature": temperature,
            "total_medications": len(medications),
            "cached": False
        })

    except Exception as e:
        logger.error(f"Error fetching aisle details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shelf/{shelf_id}/optimized")
@cache_response(ttl_seconds=30)
async def get_shelf_inventory_optimized(
    shelf_id: int,
    include_positions: bool = Query(default=False, description="Include detailed position data")
):
    """
    Optimized shelf inventory with optional position loading
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()

        # Base query for shelf info
        base_query = f"""
        WITH shelf_summary AS (
            SELECT
                s.shelf_id,
                s.shelf_code,
                s.aisle_id,
                s.position,
                s.level,
                s.capacity_slots,
                s.utilization_percent,
                a.aisle_name,
                a.category,
                COUNT(DISTINCT mp.med_id) as unique_medications,
                SUM(mp.quantity) as total_quantity,
                COUNT(DISTINCT sp.position_id) as total_positions,
                COUNT(DISTINCT mp.position_id) as occupied_positions
            FROM warehouse_shelves s
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            LEFT JOIN shelf_positions sp ON s.shelf_id = sp.shelf_id
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            WHERE s.shelf_id = {shelf_id}
            GROUP BY s.shelf_id
        )
        SELECT json_object(
            'shelf_id', shelf_id,
            'shelf_code', shelf_code,
            'aisle_id', aisle_id,
            'aisle_name', aisle_name,
            'category', category,
            'position', position,
            'level', level,
            'capacity_slots', capacity_slots,
            'utilization_percent', utilization_percent,
            'unique_medications', unique_medications,
            'total_quantity', total_quantity,
            'total_positions', total_positions,
            'occupied_positions', occupied_positions
        ) FROM shelf_summary
        """

        cursor = conn.cursor()
        cursor.execute(base_query)
        result = cursor.fetchone()

        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Shelf not found")

        shelf_data = json.loads(result[0])

        # Optionally load position details
        position_data = None
        if include_positions:
            position_query = f"""
            SELECT json_group_array(json_object(
                'position_id', sp.position_id,
                'grid_x', sp.grid_x,
                'grid_y', sp.grid_y,
                'grid_label', CASE
                    WHEN sp.grid_y = 1 THEN 'F' || sp.grid_x
                    WHEN sp.grid_y = 2 THEN 'M' || sp.grid_x
                    WHEN sp.grid_y = 3 THEN 'B' || sp.grid_x
                END,
                'is_golden_zone', sp.is_golden_zone,
                'med_id', mp.med_id,
                'med_name', m.name,
                'quantity', mp.quantity,
                'expiry_date', mp.expiry_date
            ))
            FROM shelf_positions sp
            LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                AND mp.is_active = 1
            LEFT JOIN medications m ON mp.med_id = m.med_id
            WHERE sp.shelf_id = {shelf_id}
            ORDER BY sp.grid_y, sp.grid_x
            """
            cursor.execute(position_query)
            pos_result = cursor.fetchone()
            position_data = json.loads(pos_result[0]) if pos_result[0] else []

        response = {
            "shelf": shelf_data,
            "utilization": {
                "percent": shelf_data.get('utilization_percent', 0),
                "occupied": shelf_data.get('occupied_positions', 0),
                "total": shelf_data.get('total_positions', 0)
            },
            "cached": False
        }

        if position_data is not None:
            response["positions"] = position_data

        return clean_nan_values(response)

    except Exception as e:
        logger.error(f"Error fetching optimized shelf inventory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/summary")
@cache_response(ttl_seconds=15)
async def get_alerts_summary():
    """
    Optimized alerts summary with aggregated counts
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()

        # Single query for all alert counts
        alerts_query = """
        SELECT
            (SELECT COUNT(*) FROM temperature_readings
             WHERE alert_triggered = 1
             AND reading_time >= datetime('now', '-1 hour')) as temp_alerts,
            (SELECT COUNT(*) FROM batch_info b
             JOIN medication_placements mp ON b.batch_id = mp.batch_id
             WHERE mp.is_active = 1
             AND b.expiry_date <= date('now', '+7 days')) as critical_expiry,
            (SELECT COUNT(*) FROM batch_info b
             JOIN medication_placements mp ON b.batch_id = mp.batch_id
             WHERE mp.is_active = 1
             AND b.expiry_date > date('now', '+7 days')
             AND b.expiry_date <= date('now', '+30 days')) as warning_expiry,
            (SELECT COUNT(*) FROM warehouse_shelves
             WHERE utilization_percent > 90) as capacity_alerts,
            (SELECT COUNT(*) FROM warehouse_shelves
             WHERE utilization_percent < 20) as underutilized
        """

        cursor = conn.cursor()
        cursor.execute(alerts_query)
        result = cursor.fetchone()

        return {
            "temperature_alerts": result[0] or 0,
            "critical_expiry": result[1] or 0,
            "warning_expiry": result[2] or 0,
            "capacity_alerts": result[3] or 0,
            "underutilized_shelves": result[4] or 0,
            "total_alerts": sum(result[:4]),
            "cached": False
        }

    except Exception as e:
        logger.error(f"Error fetching alerts summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/invalidate")
async def invalidate_cache(pattern: Optional[str] = None):
    """
    Invalidate cache entries

    Args:
        pattern: Optional pattern to match cache keys
    """
    count = warehouse_cache.invalidate(pattern)
    return {
        "success": True,
        "invalidated_entries": count,
        "pattern": pattern or "all"
    }


@router.get("/cache/stats")
async def get_cache_statistics():
    """Get cache statistics"""
    return warehouse_cache.get_stats()


@router.get("/batch/medications")
async def get_medications_batch(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    velocity: Optional[str] = None
):
    """
    Get medications with pagination and filtering

    Performance optimizations:
    - Pagination to limit result size
    - Optional filtering to reduce data transfer
    - Indexed columns for faster queries
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()

        # Build WHERE clause
        where_conditions = ["mp.is_active = 1"]
        if category:
            where_conditions.append(f"m.category = '{category}'")
        if velocity:
            where_conditions.append(f"ma.movement_category = '{velocity}'")

        where_clause = " AND ".join(where_conditions)

        # Query with pagination
        query = f"""
        SELECT
            m.med_id,
            m.name,
            m.category,
            ma.movement_category,
            ma.velocity_score,
            SUM(mp.quantity) as total_stock,
            COUNT(DISTINCT sp.shelf_id) as shelf_count,
            MIN(b.expiry_date) as earliest_expiry
        FROM medications m
        LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
        LEFT JOIN medication_placements mp ON m.med_id = mp.med_id
        LEFT JOIN shelf_positions sp ON mp.position_id = sp.position_id
        LEFT JOIN batch_info b ON mp.batch_id = b.batch_id
        WHERE {where_clause}
        GROUP BY m.med_id
        ORDER BY ma.velocity_score DESC
        LIMIT {limit} OFFSET {offset}
        """

        medications = pd.read_sql_query(query, conn).to_dict('records')

        # Get total count for pagination
        count_query = f"""
        SELECT COUNT(DISTINCT m.med_id) as total
        FROM medications m
        LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
        LEFT JOIN medication_placements mp ON m.med_id = mp.med_id
        WHERE {where_clause}
        """
        total_count = pd.read_sql_query(count_query, conn).iloc[0]['total']

        return clean_nan_values({
            "medications": medications,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": int(total_count),
                "has_more": offset + limit < total_count
            }
        })

    except Exception as e:
        logger.error(f"Error fetching medications batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/move")
async def batch_move_medications(
    moves: List[MoveRequest],
    background_tasks: BackgroundTasks
):
    """
    Batch move multiple medications

    Performance optimization:
    - Process multiple moves in a single transaction
    - Background task for history recording
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()
        cursor = conn.cursor()

        successful_moves = []
        failed_moves = []

        # Start transaction
        cursor.execute("BEGIN TRANSACTION")

        try:
            for move in moves:
                try:
                    # Validate and execute each move
                    # (Similar logic to single move but batched)
                    check_query = """
                        SELECT mp.placement_id, mp.quantity, sp.position_id
                        FROM medication_placements mp
                        JOIN shelf_positions sp ON mp.position_id = sp.position_id
                        WHERE sp.shelf_id = ? AND mp.med_id = ? AND mp.is_active = 1
                        LIMIT 1
                    """
                    cursor.execute(check_query, (move.from_shelf, move.med_id))
                    source = cursor.fetchone()

                    if not source or source[1] < move.quantity:
                        failed_moves.append({
                            "med_id": move.med_id,
                            "reason": "Invalid source or insufficient quantity"
                        })
                        continue

                    # Find target position
                    target_query = """
                        SELECT sp.position_id
                        FROM shelf_positions sp
                        LEFT JOIN medication_placements mp ON sp.position_id = mp.position_id
                            AND mp.is_active = 1
                        WHERE sp.shelf_id = ? AND mp.position_id IS NULL
                        LIMIT 1
                    """
                    cursor.execute(target_query, (move.to_shelf,))
                    target = cursor.fetchone()

                    if not target:
                        failed_moves.append({
                            "med_id": move.med_id,
                            "reason": "No available position on target shelf"
                        })
                        continue

                    # Execute move
                    if source[1] == move.quantity:
                        cursor.execute(
                            "UPDATE medication_placements SET is_active = 0 WHERE placement_id = ?",
                            (source[0],)
                        )
                    else:
                        cursor.execute(
                            "UPDATE medication_placements SET quantity = quantity - ? WHERE placement_id = ?",
                            (move.quantity, source[0])
                        )

                    cursor.execute("""
                        INSERT INTO medication_placements
                        (position_id, med_id, quantity, placement_date, placement_reason, is_active)
                        VALUES (?, ?, ?, datetime('now'), ?, 1)
                    """, (target[0], move.med_id, move.quantity, move.reason))

                    successful_moves.append({
                        "med_id": move.med_id,
                        "quantity": move.quantity,
                        "from_shelf": move.from_shelf,
                        "to_shelf": move.to_shelf
                    })

                except Exception as e:
                    failed_moves.append({
                        "med_id": move.med_id,
                        "reason": str(e)
                    })

            # Commit transaction
            cursor.execute("COMMIT")

            # Record movements in background
            if successful_moves:
                background_tasks.add_task(
                    record_batch_movements,
                    successful_moves
                )

            # Invalidate related cache
            warehouse_cache.invalidate("shelf")

            return {
                "success": True,
                "successful_moves": successful_moves,
                "failed_moves": failed_moves,
                "total_processed": len(moves),
                "success_rate": len(successful_moves) / len(moves) * 100 if moves else 0
            }

        except Exception as e:
            cursor.execute("ROLLBACK")
            raise e

    except Exception as e:
        logger.error(f"Error in batch move: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def record_batch_movements(moves: List[Dict]):
    """Background task to record movement history"""
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()
        cursor = conn.cursor()

        for move in moves:
            cursor.execute("""
                INSERT INTO movement_history
                (med_id, movement_type, quantity, movement_date)
                VALUES (?, 'batch_relocate', ?, datetime('now'))
            """, (move['med_id'], move['quantity']))

        conn.commit()
        logger.info(f"Recorded {len(moves)} movements in history")

    except Exception as e:
        logger.error(f"Error recording movement history: {e}")


@router.get("/performance/report")
async def get_performance_report():
    """
    Get performance metrics and optimization suggestions
    """
    try:
        from api.routes import data_loader
        conn = data_loader.get_connection()

        # Analyze database performance
        db_stats_query = """
        SELECT
            (SELECT COUNT(*) FROM medications) as total_medications,
            (SELECT COUNT(*) FROM medication_placements WHERE is_active = 1) as active_placements,
            (SELECT COUNT(*) FROM movement_history) as total_movements,
            (SELECT COUNT(*) FROM batch_info) as total_batches,
            (SELECT COUNT(*) FROM warehouse_shelves) as total_shelves,
            (SELECT AVG(utilization_percent) FROM warehouse_shelves) as avg_utilization
        """

        cursor = conn.cursor()
        cursor.execute(db_stats_query)
        db_stats = cursor.fetchone()

        # Get cache statistics
        cache_stats = warehouse_cache.get_stats()

        # Calculate optimization suggestions
        suggestions = []

        if db_stats[5] and db_stats[5] < 50:
            suggestions.append("Consider consolidating inventory to improve space utilization")

        if cache_stats['expired_entries'] > cache_stats['valid_entries']:
            suggestions.append("Increase cache TTL for frequently accessed data")

        if db_stats[2] > 10000:
            suggestions.append("Consider archiving old movement history records")

        return {
            "database_metrics": {
                "total_medications": db_stats[0],
                "active_placements": db_stats[1],
                "total_movements": db_stats[2],
                "total_batches": db_stats[3],
                "total_shelves": db_stats[4],
                "avg_utilization": round(db_stats[5], 2) if db_stats[5] else 0
            },
            "cache_metrics": cache_stats,
            "optimization_suggestions": suggestions,
            "api_version": "2.0-optimized"
        }

    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))