# Pharmacy Warehouse Management Database Documentation

## Overview

This database supports a Proof-of-Concept (POC) for pharmacy supply chain and warehouse optimization. It simulates a realistic, **intentionally disorganized** warehouse scenario to provide a baseline for testing optimization algorithms.

### Key Features

- **Synthetic data generation** for 50 medications across 3 pharmacy stores
- **365 days** of historical consumption patterns with realistic demand profiles
- **Messy warehouse simulation** with fragmented storage, zone violations, and clustering
- **Pre-computed forecasts** using Holt-Winters exponential smoothing
- **Inventory simulation** with lead times, reorder points, and stockout tracking

---

## Database Schema

### 1. Master Data Tables

#### **suppliers**

*Pharmaceutical suppliers that provide medications to the pharmacy chain*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `supplier_id` | INTEGER (PK) | Unique supplier identifier | 1, 2, 3... |
| `name` | TEXT | Supplier company name | "Acme Pharma", "MedCo Pharma" |
| `status` | TEXT | Current supplier status | "OK" (92%), "Shortage" (8%) |
| `avg_lead_time` | REAL | Average delivery time in days | 4.5, 7.2, 9.0 |
| `last_delivery_date` | DATE | Most recent delivery | "2025-08-15" |

**Notes:** Lead times follow normal distribution (mean=7, std=2.5 days)

---

#### **medications**

*Complete catalog of pharmaceutical products*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `med_id` | INTEGER (PK) | Unique medication identifier | 1, 2, 3... |
| `name` | TEXT | Medication name and strength | "Metformin 500mg", "Insulin Vial" |
| `category` | TEXT | Demand pattern category | "Chronic" (45%), "Intermittent" (35%), "Sporadic" (20%) |
| `pack_size` | INTEGER | Units per package | 10, 20, 30, 60, 100 |
| `shelf_life_days` | INTEGER | Product expiration period | 180, 365, 720 days |
| `supplier_id` | INTEGER (FK) | Link to suppliers table | References suppliers.supplier_id |

**Categories Explained:**

- **Chronic**: Daily medications (diabetes, hypertension) - consistent high demand
- **Intermittent**: Pain relievers, common OTC - moderate variable demand  
- **Sporadic**: Antibiotics, specialized drugs - low irregular demand

---

#### **stores**

*Pharmacy retail locations*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `store_id` | INTEGER (PK) | Unique store identifier | 1, 2, 3 |
| `name` | TEXT | Store name | "Downtown Pharmacy", "Westside Pharmacy" |
| `location` | TEXT | Physical address | "123 Main St, City, State" |

---

### 2. Transactional Data Tables

#### **consumption_history**

*Daily medication dispensing records with inventory tracking*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `id` | INTEGER (PK) | Unique record identifier | Auto-increment |
| `store_id` | INTEGER (FK) | Store that dispensed | References stores.store_id |
| `med_id` | INTEGER (FK) | Medication dispensed | References medications.med_id |
| `date` | DATE | Dispensing date | "2025-01-15" |
| `qty_dispensed` | INTEGER | Units actually dispensed | 0-150 (capped by inventory) |
| `on_hand` | INTEGER | Inventory level after dispensing | 0-2000 units |
| `censored` | INTEGER | Stockout indicator (0/1) | 1 if demand > on_hand |

**Data Characteristics:**

- ~54,750 records (365 days × 3 stores × 50 medications)
- Stockout rate: ~0.8-1.5% (realistic pharmacy performance)
- Demand patterns include weekly/monthly seasonality and random spikes

---

#### **drug_prices**

*Historical medication pricing with temporal changes*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `price_id` | INTEGER (PK) | Unique price record | Auto-increment |
| `med_id` | INTEGER (FK) | Medication | References medications.med_id |
| `valid_from` | DATE | Price effective date | "2024-06-01" |
| `price_per_unit` | REAL | Unit price in currency | 5.99, 125.50, 450.00 |

**Pricing Patterns:**

- Price updates every 6-18 months (pharmaceutical market reality)
- Annual drift: ±1.5% (inflation/deflation)
- Volatility: ±0.8% per adjustment

---

#### **forecasts**

*Pre-computed demand forecasts using time-series models*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `forecast_id` | INTEGER (PK) | Unique forecast record | Auto-increment |
| `store_id` | INTEGER (FK) | Store location | References stores.store_id |
| `med_id` | INTEGER (FK) | Medication | References medications.med_id |
| `model` | TEXT | Forecasting model used | "ExponentialSmoothing" |
| `horizon_days` | INTEGER | Forecast period | 28 days |
| `forecast_mean` | TEXT | JSON array of daily forecasts | "[12.5, 13.2, 11.8, ...]" |
| `forecast_samples` | TEXT | JSON array of Monte Carlo samples | "[[12.1, 13.5, ...], ...]" |
| `timestamp` | DATETIME | Forecast generation time | "2025-01-15 14:30:00" |

**Forecast Details:**

- Holt-Winters with weekly seasonality
- 50 Monte Carlo samples for uncertainty quantification
- 28-day rolling horizon

---

### 3. Warehouse Storage Tables

#### **sku_meta**

*SKU physical characteristics and velocity metrics for warehouse operations*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `med_id` | INTEGER (PK, FK) | Links to medications | References medications.med_id |
| `name` | TEXT | SKU name (redundant for convenience) | "Metformin 500mg" |
| `avg_daily_pick` | REAL | Average daily picking volume | 0.1-120 units/day |
| `case_volume_m3` | REAL | Physical case volume | 0.01-0.09 m³ |
| `case_weight_kg` | REAL | Case weight | 0.8-1.8 kg |
| `is_cold_chain` | INTEGER | Requires refrigeration (0/1) | 1 for insulin, vaccines (8%) |
| `is_controlled` | INTEGER | Restricted substance (0/1) | 1 for narcotics (5%) |

---

#### **storage_loc_simple**

*Warehouse storage locations with **intentionally fragmented** zones*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `location_id` | INTEGER (PK) | Unique location identifier | Auto-increment |
| `zone_type` | TEXT | Storage zone classification | "ambient" (65%), "cold" (20%), "restricted" (15%) |
| `capacity_volume_m3` | REAL | Volume capacity | 0.2-15.0 m³ (highly variable) |
| `capacity_weight_kg` | REAL | Weight capacity | Proportional to volume |
| `distance_score` | REAL | Distance from dispatch (0=close, 1=far) | 0.0-1.0 (randomly distributed) |

**Messy Warehouse Characteristics:**

- **Fragmented zones**: Cold/restricted zones scattered randomly (not grouped)
- **Inconsistent capacities**: 15% tiny (<1m³), 25% oversized (>8m³)
- **Poor distance logic**: 20% of locations have inverted distance scores

---

#### **slot_assignment_simple**

*Current SKU-to-location assignments (**INTENTIONALLY DISORGANIZED**)*

| Column | Type | Description | Example Data |
|--------|------|-------------|--------------|
| `assignment_id` | INTEGER (PK) | Unique assignment record | Auto-increment |
| `med_id` | INTEGER (FK) | SKU/medication | References sku_meta.med_id |
| `location_id` | INTEGER (FK) | Storage location | References storage_loc_simple.location_id |
| `assigned_at` | TIMESTAMP | Assignment timestamp | "2025-01-15 10:30:00" |

**Messy Assignment Patterns:**

- **30% SKU fragmentation**: Same medication split across 2-3 locations
- **10% zone violations**: Non-critical items in wrong zones
- **70% clustering**: Most items concentrated in 30% of locations
- **5% orphaned items**: Medications with no assigned location
- **Random placement**: Fast movers often in distant locations

---

## Data Quality Metrics

### Expected Validation Results

| Metric | Expected Range | Purpose |
|--------|---------------|---------|
| **SKU Fragmentation Rate** | 25-35% | Items split across multiple locations |
| **Max Items per Location** | 8-15 | Over-concentration in popular spots |
| **Empty Locations** | 3-6 | Underutilized storage areas |
| **Location Utilization** | 70-85% | Percentage of locations in use |
| **Orphaned Items** | 2-3 | Items without storage assignment |
| **Zone Violations** | 5-10% | Items in incorrect storage zones |

### Validation Warnings Expected

- "Extreme slot over-concentration: X locations with >10 items"
- "Chronic medication 'X' has unusually low consumption" (for sporadic-like chronics)
- "SKU fragmentation detected for fast-moving items"

---

## Use Case Scenarios

### 1. **Warehouse Optimization Algorithm Testing**

The messy warehouse provides a realistic baseline for testing:

- Slotting optimization (velocity-based placement)
- Zone consolidation algorithms
- SKU defragmentation strategies
- Capacity balancing solutions

### 2. **Inventory Management Analysis**

- Lead time optimization per supplier
- Reorder point calculations
- Safety stock requirements
- Stockout prevention strategies

### 3. **Demand Forecasting Evaluation**

- Compare forecast accuracy against actual consumption
- Analyze seasonal patterns by medication category
- Identify demand spikes and anomalies

---

## Data Generation Parameters

Default configuration (`main.py`):

- **Suppliers**: 10
- **Medications**: 50
- **Stores**: 3
- **History**: 365 days
- **Storage Locations**: 24
- **Forecast Horizon**: 28 days
- **Monte Carlo Samples**: 50

Command: `python main.py --skus 50 --stores 3 --days 365`

---

## Files Generated

| File | Description |
|------|-------------|
| `poc_supplychain.db` | SQLite database with all tables |
| `static/suppliers.csv` | Supplier master data |
| `static/medications.csv` | Medication catalog |
| `static/stores.csv` | Store locations |
| `static/consumption_history.csv` | Full consumption records |
| `static/drug_prices.csv` | Price history |
| `static/forecasts.csv` | Pre-computed forecasts |
| `static/sku_meta.csv` | SKU warehouse metadata |
| `static/storage_loc_simple.csv` | Storage locations |
| `static/slot_assignments.csv` | Current assignments |
| `static/receipts_sim.csv` | Simulated purchase orders |
| `static/validation_report.json` | Data quality metrics |

---

## Notes on Messy Warehouse Simulation

The warehouse storage simulation intentionally creates disorganization to mimic real-world legacy warehouses that have grown organically without optimization:

1. **Historical Accumulation**: Simulates years of ad-hoc placement decisions
2. **Human Factors**: Random placement mimics rushed or untrained staff decisions
3. **System Limitations**: Fragmentation from lack of warehouse management systems
4. **Business Constraints**: Zone violations from space pressure or emergencies

This provides an excellent testing ground for optimization algorithms that need to:

- Reorganize existing inventory
- Establish better placement rules
- Reduce picking distances
- Consolidate fragmented SKUs
- Balance capacity utilization

---

*Generated by Warehouse POC Data Generator v1.0*
