# Warehouse Chaos System Documentation

## Overview

This document describes the intentionally chaotic warehouse management system designed to simulate real-world warehouse inefficiencies. The system provides measurable chaos metrics, source-of-truth tables for optimization targets, and comprehensive visibility into warehouse problems.

## 1. Chaos Implementation

### 1.1 Types of Chaos Introduced

#### **Batch Fragmentation (40% chance)**

- Same lot numbers split across 3-5 random locations
- Creates inefficient picking patterns
- Increases inventory management complexity
- Current Rate: ~11% of batches fragmented

#### **Velocity Mismatch (30% chance)**

- Fast-moving items placed in back rows (grid_y=3)
- Slow-moving items occupying prime golden zones (grid_y=1)
- Medium-velocity items wasting premium space
- Current Rate: ~22% of placements mismatched

#### **FIFO Violations (25% chance)**

- Newer batches placed in front of older ones
- Older inventory blocked by newer stock
- Increases risk of expiry and waste
- Current Rate: 20 violations detected

#### **Zone Violations (10% chance)**

- Items placed in wrong temperature zones
- Non-critical items in restricted areas
- Temperature-sensitive items in ambient storage

#### **Capacity Imbalances**

- Some shelves overloaded while others empty
- Clustering creates hotspots
- 5% of items completely unassigned (orphaned)

### 1.2 Chaos Generation Code Location

- File: `src/utils/synthetic_data_generator.py`
- Function: `generate_medication_placements()` (lines 2675-2856)
- Key parameters:
  - Fragmentation chance: 40%
  - Velocity mismatch chance: 30%
  - FIFO violation chance: 25%

## 2. Source of Truth Tables

### 2.1 Database Tables

#### **optimal_batch_placement**

```sql
CREATE TABLE optimal_batch_placement (
    med_id INTEGER PRIMARY KEY,
    optimal_locations INTEGER DEFAULT 1,        -- Should be 1-2 max
    consolidation_strategy TEXT DEFAULT 'single_location',
    min_batch_quantity INTEGER DEFAULT 10
)
```

Purpose: Defines the ideal consolidation strategy for each medication

#### **velocity_zone_mapping**

```sql
CREATE TABLE velocity_zone_mapping (
    velocity_category TEXT PRIMARY KEY,
    optimal_grid_y INTEGER,      -- 1=front, 2=middle, 3=back
    optimal_shelf_level INTEGER, -- 0=lower, 1=upper
    accessibility_target REAL
)
```

Current Mapping:

- Fast: Front row (y=1), lower shelf, 100% accessibility
- Medium: Middle row (y=2), lower shelf, 80% accessibility
- Slow: Back row (y=3), upper shelf, 60% accessibility

#### **warehouse_chaos_metrics**

```sql
CREATE TABLE warehouse_chaos_metrics (
    metric_id INTEGER PRIMARY KEY,
    metric_name TEXT UNIQUE,
    current_chaos_score REAL,
    optimal_score REAL DEFAULT 0,
    improvement_potential REAL,
    last_measured TIMESTAMP,
    measurement_query TEXT
)
```

Purpose: Tracks current chaos levels and improvement potential

## 3. Chaos Visibility Endpoints

### 3.1 API Endpoints

#### **GET /api/warehouse/chaos/metrics**

Returns overall chaos metrics and scores

```json
{
    "chaos_metrics": [...],
    "overall_chaos_score": 17.82,
    "total_improvement_potential": 53.47
}
```

#### **GET /api/warehouse/chaos/batch-fragmentation**

Shows fragmented batches needing consolidation

```json
{
    "fragmented_batches": [...],
    "total_fragmented": 20,
    "total_batches": 180,
    "fragmentation_rate": 11.11,
    "consolidation_opportunity": "20 batches could be consolidated"
}
```

#### **GET /api/warehouse/chaos/velocity-mismatches**

Lists medications in wrong zones based on velocity

```json
{
    "velocity_mismatches": [...],
    "total_mismatches": 63,
    "optimal_mapping": [...],
    "relocation_opportunity": "63 items could be relocated"
}
```

### 3.2 Endpoint Implementation

- File: `src/api/warehouse_routes.py`
- Lines: 1017-1176
- Functions: `get_chaos_metrics()`, `get_batch_fragmentation()`, `get_velocity_mismatches()`

## 4. Warehouse Structure

### 4.1 Physical Layout

- **6 Aisles** (A-F) in 3x2 grid
- **8 Shelves** per aisle (16 total with 2 levels)
- **30 Positions** per shelf (10 wide × 3 deep)
- **Total Capacity**: 2,880 positions

### 4.2 Zone Distribution

| Aisle | Category | Temperature | Purpose |
|-------|----------|-------------|---------|
| A, B | General | 18-24°C | Standard pharmaceuticals |
| C, D | Refrigerated | 2-8°C | Temperature-sensitive meds |
| E | Controlled | 20-22°C | Restricted substances |
| F | Quarantine | 18-24°C | Isolated/problematic items |

## 5. Chaos Metrics & Scoring

### 5.1 Current Chaos Levels

| Metric | Formula | Current | Target | Improvement |
|--------|---------|---------|--------|-------------|
| Batch Fragmentation | (fragmented_batches / total_batches) × 100 | 11.11% | 0% | 11.11% |
| Velocity Mismatch | (misplaced_items / total_items) × 100 | 22.36% | 0% | 22.36% |
| FIFO Violations | count_violations × 10 | 20.00 | 0 | 20.00 |
| **Overall Chaos** | average(all_metrics) | 17.82% | 0% | 53.47% |

### 5.2 Measurement Queries

Stored in `warehouse_chaos_metrics.measurement_query` field for reproducibility

## 6. Data Generation Parameters

### 6.1 Default Configuration

```bash
python src/utils/synthetic_data_generator.py \
    --skus 50 \        # Number of medications
    --stores 3 \       # Number of stores
    --days 365         # Days of history
```

### 6.2 Generated Data Volume

- 54,750 consumption records
- 237 medication placements
- 583 movement records
- 180 batches
- 50 medications
- 3 stores

## 7. Optimization Opportunities

### 7.1 Problems to Solve

1. **Batch Consolidation**: Merge 20 fragmented batches
2. **Velocity Optimization**: Relocate 63 misplaced items
3. **FIFO Compliance**: Reorder shelves to fix violations
4. **Zone Correction**: Move items to proper temperature zones
5. **Capacity Balancing**: Redistribute from hotspots to empty areas

### 7.2 Success Metrics

- Reduce overall chaos score from 17.82% to <5%
- Achieve 0% batch fragmentation
- Correct all velocity mismatches
- Eliminate FIFO violations
- Balance capacity utilization to 60-80%

## 8. Testing Chaos Visibility

### 8.1 Quick Test Commands

```bash
# Start server
uv run python src/main.py

# Test chaos metrics
curl http://localhost:8000/api/warehouse/chaos/metrics | jq '.'

# Check fragmentation
curl http://localhost:8000/api/warehouse/chaos/batch-fragmentation | jq '.'

# View mismatches
curl http://localhost:8000/api/warehouse/chaos/velocity-mismatches | jq '.'
```

### 8.2 Database Queries

```sql
-- Check chaos metrics
SELECT * FROM warehouse_chaos_metrics;

-- Find fragmented batches
SELECT batch_id, COUNT(DISTINCT position_id) as locations
FROM medication_placements
WHERE is_active=1
GROUP BY batch_id
HAVING locations > 1;

-- Find velocity mismatches
SELECT m.name, ma.movement_category, sp.grid_y
FROM medication_placements mp
JOIN medications m ON mp.med_id = m.med_id
JOIN medication_attributes ma ON m.med_id = ma.med_id
JOIN shelf_positions sp ON mp.position_id = sp.position_id
WHERE mp.is_active=1
AND ((ma.movement_category='Fast' AND sp.grid_y=3)
     OR (ma.movement_category='Slow' AND sp.grid_y=1));
```

## 9. Algorithm Integration Guide

### 9.1 Reading Current State

1. Query `warehouse_chaos_metrics` for current scores
2. Use chaos endpoints to get detailed problem lists
3. Query placement tables for current positions

### 9.2 Using Source of Truth

1. Reference `optimal_batch_placement` for consolidation targets
2. Use `velocity_zone_mapping` for ideal placement rules
3. Compare current vs optimal to calculate moves

### 9.3 Measuring Improvement

1. Before: Record initial chaos scores
2. Execute: Apply optimization algorithm
3. After: Recalculate chaos metrics
4. Report: (Initial - Final) / Initial × 100 = % improvement

## 10. Key Files Reference

| Component | File | Purpose |
|-----------|------|---------|
| Data Generation | `src/utils/synthetic_data_generator.py` | Creates chaotic warehouse data |
| Chaos Endpoints | `src/api/warehouse_routes.py` | Exposes chaos visibility APIs |
| Frontend Service | `frontend/src/services/warehouse-api.ts` | Frontend API integration |
| Database Schema | Lines 687-725 in generator | Source of truth tables |

## Notes for Future Development

1. **Adjustable Chaos Levels**: Modify percentages in `generate_medication_placements()` to increase/decrease chaos
2. **Additional Metrics**: Add more chaos types by creating new measurement queries
3. **Real-time Updates**: Use WebSocket connections to show chaos changes live
4. **Optimization History**: Track improvement over time in new table
5. **Visualization**: Create heatmaps showing problem areas in warehouse

This chaotic warehouse system provides a realistic testing ground for optimization algorithms, with clear metrics to measure success and comprehensive visibility into all inefficiencies.
