#!/usr/bin/env python3
"""
generate_full_poc_data.py

Generate a realistic synthetic dataset for a pharmacy supply-chain PoC,
populate an SQLite DB and export CSVs into ./data/.

Includes:
 - suppliers
 - medications
 - stores
 - consumption_history (time-series, with stockout censoring)
 - drug_prices (historical pricing)
 - forecasts (Holt-Winters mean + MC samples)
 - simplified storage tables for slotting:
     sku_meta (minimal SKU physical + velocity)
     storage_loc_simple (locations with zone & capacities)
     slot_assignment_simple (initial greedy assignment)
 - receipts_sim.csv (simulated receipts/PO arrivals)

Usage:
  python generate_full_poc_data.py --skus 50 --stores 3 --days 365

Default config aims for ~50k consumption rows.

Author: ChatGPT
Date: 2025-09-05
"""

import argparse
import json
import math
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from faker import Faker
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from tqdm import tqdm

# -----------------------
# Configuration / seed
# -----------------------
fake = Faker()
DEFAULT_SEED = 42
np.random.seed(DEFAULT_SEED)
random.seed(DEFAULT_SEED)


# -----------------------
# Helpers
# -----------------------
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def create_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables(conn):
    cur = conn.cursor()
    cur.executescript("""
    -- Suppliers, Medications, Stores (master data)
    CREATE TABLE IF NOT EXISTS suppliers (
      supplier_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      status TEXT,
      avg_lead_time REAL,
      last_delivery_date DATE,
      email TEXT,
      contact_name TEXT,
      phone TEXT,
      address TEXT
    );

    CREATE TABLE IF NOT EXISTS medications (
      med_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      category TEXT,
      pack_size INTEGER,
      shelf_life_days INTEGER,
      supplier_id INTEGER,
      FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    );

    CREATE TABLE IF NOT EXISTS stores (
      store_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      location TEXT
    );

    -- Historical / time-series consumption with simple censoring
    CREATE TABLE IF NOT EXISTS consumption_history (
      id INTEGER PRIMARY KEY,
      store_id INTEGER,
      med_id INTEGER,
      date DATE,
      qty_dispensed INTEGER,
      on_hand INTEGER,
      censored INTEGER DEFAULT 0,
      FOREIGN KEY (store_id) REFERENCES stores(store_id),
      FOREIGN KEY (med_id) REFERENCES medications(med_id)
    );

    -- Drug prices (history)
    CREATE TABLE IF NOT EXISTS drug_prices (
      price_id INTEGER PRIMARY KEY,
      med_id INTEGER,
      valid_from DATE,
      price_per_unit REAL,
      FOREIGN KEY (med_id) REFERENCES medications(med_id)
    );

    -- Precomputed forecasts (store x med x model)
    CREATE TABLE IF NOT EXISTS forecasts (
      forecast_id INTEGER PRIMARY KEY,
      store_id INTEGER,
      med_id INTEGER,
      model TEXT,
      horizon_days INTEGER,
      forecast_mean TEXT,
      forecast_samples TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (store_id) REFERENCES stores(store_id),
      FOREIGN KEY (med_id) REFERENCES medications(med_id)
    );

    -- Medication-level aggregated forecasts (6 months horizon)
    CREATE TABLE IF NOT EXISTS forecasts_med (
      forecast_id INTEGER PRIMARY KEY,
      med_id INTEGER,
      model TEXT,
      horizon_days INTEGER,
      forecast_mean TEXT,
      forecast_samples TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (med_id) REFERENCES medications(med_id)
    );

    -- Simplified storage / slotting tables (minimal)
    CREATE TABLE IF NOT EXISTS sku_meta (
      med_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      avg_daily_pick REAL,
      case_volume_m3 REAL,
      case_weight_kg REAL,
      is_cold_chain INTEGER,   -- 0/1
      is_controlled INTEGER    -- 0/1
    );

    CREATE TABLE IF NOT EXISTS storage_loc_simple (
      location_id INTEGER PRIMARY KEY AUTOINCREMENT,
      zone_type TEXT,
      capacity_volume_m3 REAL,
      capacity_weight_kg REAL,
      distance_score REAL
    );

    CREATE TABLE IF NOT EXISTS slot_assignment_simple (
      assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
      med_id INTEGER,
      location_id INTEGER,
      assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (med_id) REFERENCES sku_meta(med_id),
      FOREIGN KEY (location_id) REFERENCES storage_loc_simple(location_id)
    );

    -- ========== PURCHASE ORDER AND AI TABLES ==========
    -- Supplier-specific medication prices
    CREATE TABLE IF NOT EXISTS med_supplier_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        valid_from DATE NOT NULL,
        price_per_unit REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (med_id) REFERENCES medications(med_id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
        UNIQUE(med_id, supplier_id, valid_from)
    );

    -- Purchase orders table
    CREATE TABLE IF NOT EXISTS purchase_orders (
        po_id TEXT PRIMARY KEY,
        po_number TEXT UNIQUE NOT NULL,
        supplier_id INTEGER NOT NULL,
        supplier_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        total_amount REAL NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        requested_delivery_date DATE,
        actual_delivery_date DATE,
        notes TEXT,
        created_by TEXT,
        approved_by TEXT,
        approved_at TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    );

    -- Purchase order items table
    CREATE TABLE IF NOT EXISTS purchase_order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id TEXT NOT NULL,
        med_id INTEGER NOT NULL,
        med_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        pack_size INTEGER,
        FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
        FOREIGN KEY (med_id) REFERENCES medications(med_id)
    );

    -- AI metadata tables
    CREATE TABLE IF NOT EXISTS ai_po_sessions (
        session_id TEXT PRIMARY KEY,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP,
        medications TEXT NOT NULL,  -- JSON array of medication IDs
        agent_outputs TEXT,  -- JSON with all agent outputs
        reasoning TEXT,  -- JSON reasoning traces
        status TEXT NOT NULL DEFAULT 'pending',
        error TEXT,
        generation_time_ms INTEGER
    );

    CREATE TABLE IF NOT EXISTS ai_po_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        ai_generated BOOLEAN DEFAULT 1,
        generation_time_ms INTEGER,
        confidence_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES ai_po_sessions(session_id)
    );

    -- ========== ANALYTICS AND REPORTS TABLES ==========
    -- Pre-aggregated dashboard tables for chart performance
    CREATE TABLE IF NOT EXISTS dashboard_daily_aggregates (
        date DATE PRIMARY KEY,
        total_consumption INTEGER NOT NULL DEFAULT 0,
        total_orders INTEGER NOT NULL DEFAULT 0,
        unique_medications INTEGER NOT NULL DEFAULT 0,
        stockout_events INTEGER NOT NULL DEFAULT 0,
        avg_stock_level REAL NOT NULL DEFAULT 0.0,
        total_value REAL NOT NULL DEFAULT 0.0,
        critical_stock_count INTEGER NOT NULL DEFAULT 0,
        low_stock_count INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Category-level daily aggregates for breakdown charts
    CREATE TABLE IF NOT EXISTS category_daily_aggregates (
        date DATE NOT NULL,
        category TEXT NOT NULL,
        total_consumption INTEGER NOT NULL DEFAULT 0,
        medication_count INTEGER NOT NULL DEFAULT 0,
        avg_stock_level REAL NOT NULL DEFAULT 0.0,
        total_value REAL NOT NULL DEFAULT 0.0,
        stockout_events INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (date, category)
    );

    -- Hourly consumption patterns for intraday analysis
    CREATE TABLE IF NOT EXISTS hourly_consumption (
        datetime TIMESTAMP NOT NULL,
        med_id INTEGER NOT NULL,
        store_id INTEGER NOT NULL,
        hour INTEGER NOT NULL CHECK(hour >= 0 AND hour <= 23),
        qty_dispensed INTEGER NOT NULL DEFAULT 0,
        on_hand INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (datetime, med_id, store_id),
        FOREIGN KEY (med_id) REFERENCES medications(med_id),
        FOREIGN KEY (store_id) REFERENCES stores(store_id)
    );

    -- Pre-calculated analytics metrics cache
    CREATE TABLE IF NOT EXISTS analytics_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_key TEXT NOT NULL UNIQUE,
        metric_value TEXT NOT NULL, -- JSON data
        time_range TEXT NOT NULL,
        filters TEXT, -- JSON filters applied
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL
    );

    -- Analytics metrics for dashboard KPIs
    CREATE TABLE IF NOT EXISTS analytics_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_name TEXT NOT NULL,
        metric_value REAL NOT NULL,
        metric_date DATE NOT NULL,
        category TEXT,
        metadata TEXT, -- JSON additional data
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Report templates
    CREATE TABLE IF NOT EXISTS report_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        type TEXT NOT NULL CHECK(type IN ('inventory', 'financial', 'supplier', 'consumption', 'custom')),
        template_data TEXT NOT NULL, -- JSON configuration
        fields_config TEXT NOT NULL, -- JSON field configuration
        chart_config TEXT, -- JSON chart settings
        format TEXT NOT NULL DEFAULT 'pdf' CHECK(format IN ('pdf', 'excel', 'csv')),
        frequency TEXT DEFAULT 'manual' CHECK(frequency IN ('manual', 'daily', 'weekly', 'monthly')),
        recipients TEXT, -- JSON array of email addresses
        parameters TEXT, -- JSON default parameters
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );

    -- Report execution history
    CREATE TABLE IF NOT EXISTS report_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parameters TEXT, -- JSON parameters used
        status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
        file_path TEXT, -- Path to generated file
        file_size INTEGER,
        execution_time_ms INTEGER,
        error_message TEXT,
        executed_by TEXT,
        FOREIGN KEY (template_id) REFERENCES report_templates(id)
    );

    -- Report schedules
    CREATE TABLE IF NOT EXISTS report_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        cron_expression TEXT NOT NULL, -- Cron format for scheduling
        next_run TIMESTAMP,
        last_run TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (template_id) REFERENCES report_templates(id)
    );

    -- Supplier performance metrics
    CREATE TABLE IF NOT EXISTS supplier_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,
        total_orders INTEGER DEFAULT 0,
        on_time_deliveries INTEGER DEFAULT 0,
        late_deliveries INTEGER DEFAULT 0,
        avg_delay_days REAL DEFAULT 0,
        total_value REAL DEFAULT 0,
        quality_score REAL DEFAULT 0,
        rating REAL DEFAULT 0,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    );

    -- Category performance tracking
    CREATE TABLE IF NOT EXISTS category_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,
        total_medications INTEGER DEFAULT 0,
        total_consumption INTEGER DEFAULT 0,
        total_value REAL DEFAULT 0,
        avg_turnover REAL DEFAULT 0,
        low_stock_count INTEGER DEFAULT 0,
        critical_stock_count INTEGER DEFAULT 0,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create indexes for better query performance
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_med_supplier_prices_med_id ON med_supplier_prices(med_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_med_supplier_prices_supplier_id ON med_supplier_prices(supplier_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON purchase_orders(status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id ON purchase_orders(supplier_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_order_items_po_id ON purchase_order_items(po_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_order_items_med_id ON purchase_order_items(med_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_po_sessions_status ON ai_po_sessions(status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_po_metadata_po_id ON ai_po_metadata(po_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_po_metadata_session_id ON ai_po_metadata(session_id)"
    )

    # Analytics and reports indexes
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_cache_metric_key ON analytics_cache(metric_key)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires ON analytics_cache(expires_at)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_metrics_name_date ON analytics_metrics(metric_name, metric_date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_templates_type ON report_templates(type)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_template ON report_history(template_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_status ON report_history(status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_schedules_next_run ON report_schedules(next_run)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_performance_supplier_period ON supplier_performance(supplier_id, period_start, period_end)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_category_metrics_category_period ON category_metrics(category, period_start, period_end)"
    )

    # Chart performance optimization indexes
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_date ON consumption_history(date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_med_date ON consumption_history(med_id, date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_store_date ON consumption_history(store_id, date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_med_store_date ON consumption_history(med_id, store_id, date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_forecasts_med_timestamp ON forecasts_med(med_id, timestamp)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_drug_prices_med_date ON drug_prices(med_id, valid_from)"
    )

    # Pre-aggregated table indexes
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_dashboard_daily_date ON dashboard_daily_aggregates(date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_category_daily_date_cat ON category_daily_aggregates(date, category)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_hourly_consumption_datetime ON hourly_consumption(datetime)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_hourly_consumption_med_datetime ON hourly_consumption(med_id, datetime)"
    )

    # Ensure new supplier contact columns exist on older DBs
    cur.execute("PRAGMA table_info(suppliers)")
    cols = {row[1] for row in cur.fetchall()}
    for col_name, col_type in (
        ("email", "TEXT"),
        ("contact_name", "TEXT"),
        ("phone", "TEXT"),
        ("address", "TEXT"),
    ):
        if col_name not in cols:
            cur.execute(f"ALTER TABLE suppliers ADD COLUMN {col_name} {col_type}")

    conn.commit()


# -----------------------
# Domain generation
# -----------------------

# Global medication profiles for consistent categorization
MEDICATION_PROFILES = [
    {"name": "Metformin 500mg", "category": "Chronic", "base_daily_demand": (15, 80)},
    {"name": "Atorvastatin 20mg", "category": "Chronic", "base_daily_demand": (12, 65)},
    {"name": "Lisinopril 10mg", "category": "Chronic", "base_daily_demand": (10, 55)},
    {"name": "Amlodipine 5mg", "category": "Chronic", "base_daily_demand": (8, 45)},
    {"name": "Omeprazole 20mg", "category": "Chronic", "base_daily_demand": (12, 60)},
    {
        "name": "Ibuprofen 200mg",
        "category": "Intermittent",
        "base_daily_demand": (3, 15),
    },
    {
        "name": "Paracetamol 500mg",
        "category": "Intermittent",
        "base_daily_demand": (5, 20),
    },
    {"name": "Salbutamol Inhaler", "category": "Chronic", "base_daily_demand": (6, 25)},
    {"name": "Insulin Vial", "category": "Chronic", "base_daily_demand": (4, 18)},
    {
        "name": "Hydrocortisone 2%",
        "category": "Sporadic",
        "base_daily_demand": (0.5, 4),
    },
    {
        "name": "Amoxicillin 500mg",
        "category": "Sporadic",
        "base_daily_demand": (0.8, 6),
    },
    {"name": "Ceftriaxone 1g", "category": "Sporadic", "base_daily_demand": (0.2, 2)},
]


def generate_suppliers(n_suppliers, seed=DEFAULT_SEED):
    random.seed(seed)
    suppliers = []
    for i in range(n_suppliers):
        name = fake.company() + " Pharma"
        avg_lead_time = max(1.0, float(round(np.random.normal(loc=7.0, scale=2.5), 2)))
        status = "OK" if random.random() > 0.08 else "Shortage"
        last_delivery = (
            datetime.now(timezone.utc) - timedelta(days=int(np.random.randint(1, 30)))
        ).date()
        contact_name = fake.name()
        # Use fixed email for all suppliers
        email = "siddhesh.dongare@neutrinotechlabs.com"
        phone = fake.phone_number()
        address = fake.address().replace("\n", ", ")
        suppliers.append(
            {
                "supplier_id": i + 1,
                "name": name,
                "status": status,
                "avg_lead_time": avg_lead_time,
                "last_delivery_date": str(last_delivery),
                "email": email,
                "contact_name": contact_name,
                "phone": phone,
                "address": address,
            }
        )
    return suppliers


def generate_medications(n_meds, suppliers, seed=DEFAULT_SEED + 1):
    random.seed(seed)
    meds = []

    for i in range(n_meds):
        profile = MEDICATION_PROFILES[i % len(MEDICATION_PROFILES)]
        base_name = profile["name"]

        name = (
            f"{base_name} (GEN-{i + 1})" if i >= len(MEDICATION_PROFILES) else base_name
        )

        # Use predefined category instead of random assignment
        category = profile["category"]

        # For generated variants, maintain similar category distribution but add some variation
        if i >= len(MEDICATION_PROFILES):
            # Use weighted random for generated medications beyond the base set
            categories = ["Chronic", "Intermittent", "Sporadic"]
            category = random.choices(categories, weights=[0.45, 0.35, 0.20])[0]
        pack_size = random.choice([10, 20, 30, 60, 100])
        shelf_life = random.choice([180, 365, 720])
        supplier = random.choice(suppliers)
        meds.append(
            {
                "med_id": i + 1,
                "name": name,
                "category": category,
                "pack_size": pack_size,
                "shelf_life_days": shelf_life,
                "supplier_id": supplier["supplier_id"],
            }
        )
    return meds


def generate_stores(n_stores, seed=DEFAULT_SEED + 2):
    random.seed(seed)
    stores = []
    for i in range(n_stores):
        name = fake.city() + " Pharmacy"
        location = fake.address().replace("\n", ", ")
        stores.append({"store_id": i + 1, "name": name, "location": location})
    return stores


# -----------------------
# Time-series demand construction
# -----------------------
def base_daily_pattern(
    days,
    base,
    trend_slope=0.0,
    weekly_amp=0.12,
    monthly_amp=0.05,
    noise_std=1.0,
    seed=None,
):
    if seed is not None:
        np.random.seed(seed)
    t = np.arange(days)
    trend = base * (1.0 + trend_slope * (t / max(1, days)))
    weekly = 1.0 + weekly_amp * np.sin(2 * np.pi * (t % 7) / 7)
    monthly = 1.0 + monthly_amp * np.sin(2 * np.pi * (t % 30) / 30)
    noise = np.random.normal(loc=0.0, scale=noise_std, size=days)
    series = trend * weekly * monthly + noise
    series = np.clip(series, 0.0, None)
    return series


def intermittent_process(days, avg_when_occurs=3, p_occurrence=0.08, seed=None):
    if seed is not None:
        np.random.seed(seed)
    occ = np.random.rand(days) < p_occurrence
    sizes = np.random.poisson(lam=max(1, avg_when_occurs), size=days)
    return (occ * sizes).astype(int)


def inject_spikes(
    series, spike_chance=0.01, spike_multiplier=3, max_extra=4, seed=None
):
    if seed is not None:
        np.random.seed(seed)
    days = len(series)
    spikes = np.random.rand(days) < spike_chance
    for i in np.where(spikes)[0]:
        multi = spike_multiplier + np.random.randint(0, max_extra)
        series[i] = series[i] * multi
    return series


# -----------------------
# Inventory simulation (censoring + receipts)
# -----------------------
def sample_lead_time(avg_lead):
    mean = max(1.0, float(avg_lead))
    k = np.random.uniform(1.5, 3.0)
    theta = mean / k
    samp = np.random.gamma(shape=k, scale=theta)
    return max(1, int(round(samp)))


def simulate_inventory_and_history(
    store_id,
    med,
    start_date,
    days,
    demand_series,
    pack_size,
    avg_lead_time,
    reorder_buffer_days=14,
    seed=None,
):
    random.seed(seed)
    np.random.seed(seed + 1 if seed is not None else None)
    rows = []
    receipts = []
    today = pd.Timestamp(start_date)
    avg_daily = max(1.0, np.mean(demand_series))
    initial_on_hand = int(
        math.ceil((avg_daily * (avg_lead_time + reorder_buffer_days)) / pack_size)
        * pack_size
    )
    on_hand = initial_on_hand
    target_inventory = initial_on_hand
    scheduled_receipts = []
    for day_idx in range(days):
        date = (today + pd.Timedelta(days=day_idx)).date()
        # arrivals
        new_sched = []
        for arr_date, qty in scheduled_receipts:
            if arr_date == date:
                on_hand += qty
            else:
                new_sched.append((arr_date, qty))
        scheduled_receipts = new_sched

        demand = int(round(demand_series[day_idx]))
        qty_dispensed = min(on_hand, demand)
        censored = 1 if demand > on_hand else 0

        rows.append(
            {
                "store_id": store_id,
                "med_id": med["med_id"],
                "date": str(date),
                "qty_dispensed": int(qty_dispensed),
                "on_hand": int(on_hand),
                "censored": int(censored),
            }
        )

        on_hand -= qty_dispensed

        reorder_point = int(max(1, avg_daily * avg_lead_time * 0.6))
        if on_hand <= reorder_point:
            qty_needed = max(0, target_inventory - on_hand)
            packs = int(math.ceil(qty_needed / pack_size))
            if packs <= 0:
                packs = 1
            qty_order = packs * pack_size
            lt = sample_lead_time(avg_lead_time)
            arrival_date = (today + pd.Timedelta(days=day_idx + lt)).date()
            scheduled_receipts.append((arrival_date, qty_order))
            receipts.append(
                {
                    "store_id": store_id,
                    "med_id": med["med_id"],
                    "order_date": str(date),
                    "qty_ordered": int(qty_order),
                    "arrival_date": str(arrival_date),
                    "lead_time_days": int(lt),
                }
            )
    return rows, receipts


# -----------------------
# Price history generator
# -----------------------
def generate_price_history_for_med(med_id, start_date, days):
    # Base prices adjusted to realistic pharmaceutical wholesale ranges (USD per unit)
    # Defaults if we cannot infer from name/category
    base_price = round(np.random.uniform(1.5, 25.0), 2)
    price_rows = []
    t = 0

    # More realistic pharmaceutical pricing: small, infrequent changes
    annual_price_drift = np.random.normal(0.0, 0.01)  # ~1% annual drift

    while t < days:
        valid_from = (pd.Timestamp(start_date) + pd.Timedelta(days=t)).date()

        # Calculate time-based price adjustment (gradual changes)
        time_factor = t / 365.0
        trend_adjustment = 1.0 + (annual_price_drift * time_factor)

        # Less frequent price updates (every 9-18 months)
        if t == 0 or np.random.random() < 0.08:
            # Category-aware baseline could be applied by caller if needed; here keep small variance
            change_factor = 1.0 + np.random.normal(0.0, 0.005)  # 0.5% volatility
            base_price = round(
                max(0.1, base_price * change_factor * trend_adjustment), 2
            )

            price_rows.append(
                {
                    "med_id": med_id,
                    "valid_from": str(valid_from),
                    "price_per_unit": float(base_price),
                }
            )

        # Next update in 270-540 days
        t += int(np.random.randint(270, 541))

    # Ensure at least one price record
    if not price_rows:
        price_rows.append(
            {
                "med_id": med_id,
                "valid_from": str(pd.Timestamp(start_date).date()),
                "price_per_unit": float(base_price),
            }
        )

    return price_rows


def _estimate_base_price_for_med(name: str, category: str) -> float:
    n = name.lower()
    # Common low-cost generics
    if "ibuprofen" in n or "paracetamol" in n or "amoxicillin" in n:
        return float(round(np.random.uniform(0.05, 0.50), 2))
    if (
        "atorvastatin" in n
        or "lisinopril" in n
        or "amlodipine" in n
        or "omeprazole" in n
    ):
        return float(round(np.random.uniform(0.05, 0.60), 2))
    if "ceftriaxone" in n:
        return float(round(np.random.uniform(0.50, 3.00), 2))
    if "insulin" in n:
        # Per-unit here can represent per mL or per vial component; keep realistic order-of-magnitude
        return float(round(np.random.uniform(5.00, 25.00), 2))
    if "salbutamol" in n:
        return float(round(np.random.uniform(0.80, 3.00), 2))

    # Category fallback ranges
    if category == "Chronic":
        return float(round(np.random.uniform(0.10, 2.00), 2))
    if category == "Intermittent":
        return float(round(np.random.uniform(0.10, 3.00), 2))
    # Sporadic/rare
    return float(round(np.random.uniform(0.20, 5.00), 2))


def generate_supplier_prices_for_meds(
    medications, suppliers, drug_prices_rows, seed=DEFAULT_SEED + 44
):
    """
    Create supplier-specific current prices with realistic variation.
    Base prices derived from medication name/category; limited variance.
    """
    random.seed(seed)
    np.random.seed(seed)

    # Build latest base price per med; if not present, estimate from name/category
    latest_base_price = {}
    by_med = {}
    for row in sorted(drug_prices_rows, key=lambda r: pd.to_datetime(r["valid_from"])):
        latest_base_price[row["med_id"]] = float(row["price_per_unit"]) or 1.0
        by_med.setdefault(row["med_id"], []).append(row)

    supplier_ids = [s["supplier_id"] for s in suppliers]
    offers = []
    today = datetime.now(timezone.utc).date().isoformat()

    # Supplier pricing tendencies (reduced variance)
    supplier_profiles = {}
    for s in suppliers:
        sid = s["supplier_id"]
        strategy_rand = random.random()
        if strategy_rand < 0.25:
            profile = {
                "strategy": "discount",
                "mult": np.random.uniform(0.90, 0.98),
                "var": 0.02,
            }
        elif strategy_rand < 0.50:
            profile = {
                "strategy": "premium",
                "mult": np.random.uniform(1.02, 1.10),
                "var": 0.02,
            }
        else:
            profile = {
                "strategy": "competitive",
                "mult": np.random.uniform(0.97, 1.03),
                "var": 0.02,
            }
        supplier_profiles[sid] = profile

    for med in medications:
        med_id = med["med_id"]
        med_category = med["category"]
        name = med["name"]
        base_price = latest_base_price.get(med_id)
        if base_price is None:
            base_price = _estimate_base_price_for_med(name, med_category)

        primary_supplier = med["supplier_id"]
        offers.append(
            {
                "med_id": med_id,
                "supplier_id": primary_supplier,
                "valid_from": today,
                "price_per_unit": float(
                    round(base_price * np.random.uniform(0.98, 1.02), 2)
                ),
            }
        )

        alternates = [sid for sid in supplier_ids if sid != primary_supplier]
        num_alternates = random.randint(2, min(4, len(alternates)))
        selected_alternates = random.sample(alternates, num_alternates)

        # 20% chance of identical competitive prices
        create_identical = random.random() < 0.20
        match_price = None

        for i, sid in enumerate(selected_alternates):
            profile = supplier_profiles[sid]
            if create_identical and i == 0:
                match_price = round(base_price * np.random.uniform(0.97, 1.03), 2)
                alt_price = match_price
            elif create_identical and match_price and random.random() < 0.6:
                alt_price = match_price
            else:
                mult = profile["mult"]
                var = profile["var"]
                # Light specialty tweaks
                if med_category == "Chronic" and profile["strategy"] == "discount":
                    mult *= 0.98
                elif med_category == "Sporadic" and profile["strategy"] == "premium":
                    mult *= 1.02
                alt_price = round(
                    base_price * mult * np.random.uniform(1 - var, 1 + var), 2
                )

            # Clamp to within 50%..+150% of base
            alt_price = max(
                round(base_price * 0.5, 2), min(round(base_price * 1.5, 2), alt_price)
            )

            offers.append(
                {
                    "med_id": med_id,
                    "supplier_id": sid,
                    "valid_from": today,
                    "price_per_unit": float(alt_price),
                }
            )

    return offers


# -----------------------
# Forecast baseline (Holt-Winters) with MC samples
# -----------------------
def compute_forecast_from_series(
    history_series, horizon=28, seasonal_periods=7, n_samples=50
):
    try:
        ser = np.asarray(history_series, dtype=float)
        if len(ser) < max(2 * seasonal_periods, 10):
            mean_forecast = [float(max(0.0, np.mean(ser))) for _ in range(horizon)]
            residual_std = float(np.std(ser - np.mean(ser))) if len(ser) > 1 else 1.0
        else:
            try:
                model = ExponentialSmoothing(
                    ser, trend="add", seasonal="add", seasonal_periods=seasonal_periods
                )
                fit = model.fit(optimized=True, use_boxcox=False, remove_bias=False)
                mean_forecast = fit.forecast(horizon).tolist()
                residuals = ser - fit.fittedvalues
                residual_std = float(np.std(residuals))
            except Exception:
                model = ExponentialSmoothing(ser, trend="add", seasonal=None)
                fit = model.fit(optimized=True)
                mean_forecast = fit.forecast(horizon).tolist()
                residuals = ser - fit.fittedvalues
                residual_std = float(np.std(residuals))
    except Exception:
        mean_forecast = [0.0] * horizon
        residual_std = 1.0

    rng = np.random.default_rng()
    samples = []
    for _ in range(n_samples):
        # Base noise with increased volatility for more realistic variation
        noise = rng.normal(0.0, residual_std * 1.2, size=horizon)

        # Add occasional spikes (2% chance per day)
        spike_mask = rng.random(horizon) < 0.02
        spike_multipliers = np.where(spike_mask, rng.uniform(1.5, 3.0, horizon), 1.0)

        # Apply spikes to mean forecast first, then add noise
        spiked_forecast = np.array(mean_forecast) * spike_multipliers
        samp = np.clip(spiked_forecast + noise, 0.0, None).astype(float).tolist()
        samples.append(samp)

    return [float(x) for x in mean_forecast], samples


# -----------------------
# Simplified storage data (minimal)
# -----------------------
def compute_sku_storage_meta(med_list, consumption_agg, seed=DEFAULT_SEED + 10):
    """
    Build sku_meta rows with:
     - avg_daily_pick (derived from consumption or synthetic)
     - case_volume_m3 (small realistic random range)
     - case_weight_kg estimated from volume
     - is_cold_chain (small fraction)
     - is_controlled (small fraction)
    consumption_agg: dict med_id -> avg_daily (if available)
    """
    random.seed(seed)
    sku_rows = []
    for med in med_list:
        med_id = med["med_id"]
        name = med["name"]
        avg = consumption_agg.get(med_id, None)
        if avg is None or avg <= 0:
            # generate synthetic avg daily (match category tendency)
            if med["category"] == "Chronic":
                avg = float(round(np.random.uniform(20, 120), 2))
            elif med["category"] == "Intermittent":
                avg = float(round(np.random.uniform(2, 12), 2))
            else:
                avg = float(round(np.random.uniform(0.1, 3.0), 2))
        # case volume: random 0.01 - 0.1 m3
        vol = round(np.random.uniform(0.01, 0.09), 4)
        wt = round(vol * random.uniform(8.0, 18.0), 2)
        is_cold = 1 if "Insulin" in name or random.random() < 0.08 else 0
        is_ctrl = (
            1
            if "Hydrocortisone" in name and random.random() < 0.2
            else (1 if random.random() < 0.05 else 0)
        )
        sku_rows.append(
            {
                "med_id": med_id,
                "name": name,
                "avg_daily_pick": float(round(avg, 3)),
                "case_volume_m3": float(vol),
                "case_weight_kg": float(wt),
                "is_cold_chain": int(is_cold),
                "is_controlled": int(is_ctrl),
            }
        )
    return sku_rows


def generate_storage_locations(n_locs=24, seed=DEFAULT_SEED + 11):
    """
    Generate fragmented storage locations that simulate a disorganized warehouse:
    - Mixed zone types scattered randomly
    - Inconsistent capacities (some tiny, some huge)
    - Poor distance organization
    - Some inefficient/obsolete locations
    """
    random.seed(seed)

    # Create more fragmented zone distribution
    zones = []

    # Calculate actual counts that add up to n_locs
    ambient_count = int(n_locs * 0.65)  # 65% ambient
    cold_count = max(2, int(n_locs * 0.20))  # 20% cold (min 2)
    restricted_count = max(1, int(n_locs * 0.15))  # 15% restricted (min 1)

    # Adjust to ensure we have exactly n_locs
    total_assigned = ambient_count + cold_count + restricted_count
    if total_assigned < n_locs:
        ambient_count += n_locs - total_assigned  # Give remainder to ambient
    elif total_assigned > n_locs:
        # Reduce ambient count if we're over
        ambient_count = n_locs - cold_count - restricted_count
        ambient_count = max(1, ambient_count)  # Ensure at least 1 ambient

    # Build the zones list
    zones.extend(["ambient"] * ambient_count)
    zones.extend(["cold"] * cold_count)
    zones.extend(["restricted"] * restricted_count)

    # Shuffle to fragment zones (no logical grouping)
    random.shuffle(zones)

    # Verify we have exactly n_locs
    assert len(zones) == n_locs, f"Zone count mismatch: {len(zones)} != {n_locs}"

    rows = []
    for i in range(n_locs):
        zone = zones[i]

        # Create highly inconsistent capacities (realistic warehouse chaos)
        if random.random() < 0.15:  # 15% tiny locations
            cap_vol = round(random.uniform(0.2, 1.0), 2)
        elif random.random() < 0.25:  # 25% oversized locations
            cap_vol = round(random.uniform(8.0, 15.0), 2)
        else:  # Normal but still varied
            cap_vol = round(random.uniform(1.5, 6.5), 2)

        # Weight capacity with more realistic variation
        if cap_vol < 1.0:  # Small locations get proportionally less weight capacity
            cap_wt = round(cap_vol * random.uniform(15, 25), 1)
        else:
            cap_wt = round(cap_vol * random.uniform(8, 18), 1)

        # Distance scores that don't follow logical patterns
        # Some far locations have good scores, some close ones have bad scores
        if random.random() < 0.20:  # 20% have inverted distance logic
            dist = round(random.uniform(0.8, 1.0), 3)  # Far but marked as close
        elif random.random() < 0.30:  # 30% clustered around middle distances
            dist = round(random.uniform(0.4, 0.7), 3)
        else:
            dist = round(random.uniform(0.0, 1.0), 3)

        rows.append(
            {
                "zone_type": zone,
                "capacity_volume_m3": float(cap_vol),
                "capacity_weight_kg": float(cap_wt),
                "distance_score": float(dist),
            }
        )

    return rows


def messy_warehouse_assignment(sku_rows, loc_rows, seed=DEFAULT_SEED + 30):
    """
    Create a disorganized, realistic warehouse assignment that simulates:
    - Random placement without velocity optimization
    - SKU fragmentation across multiple locations
    - Zone violations for non-critical items
    - Clustering hotspots and capacity imbalances
    - Some unassigned items (orphaned inventory)
    """
    random.seed(seed)
    np.random.seed(seed)

    # Copy capacities with tracking
    loc_caps = [
        {
            "location_id": i + 1,
            "zone_type": loc_rows[i]["zone_type"],
            "capacity_volume_m3": loc_rows[i]["capacity_volume_m3"],
            "capacity_weight_kg": loc_rows[i]["capacity_weight_kg"],
            "distance_score": loc_rows[i]["distance_score"],
            "item_count": 0,
        }
        for i in range(len(loc_rows))
    ]

    assignments = []
    # Shuffle SKUs randomly (no velocity-based sorting)
    skus_shuffled = random.sample(sku_rows, len(sku_rows))

    for sku in skus_shuffled:
        vol = sku["case_volume_m3"]
        wt = sku["case_weight_kg"]
        cold = sku["is_cold_chain"]
        ctrl = sku["is_controlled"]

        # 5% chance this item gets orphaned (unassigned)
        if random.random() < 0.05:
            assignments.append({"med_id": sku["med_id"], "location_id": None})
            continue

        # 30% chance to split this SKU across multiple locations
        split_sku = random.random() < 0.30
        locations_to_assign = random.randint(2, 3) if split_sku else 1

        for split_idx in range(locations_to_assign):
            # Find compatible locations with some rule violations
            compatible_locs = []
            for loc in loc_caps:
                # Check capacity constraints
                if loc["capacity_volume_m3"] < vol or loc["capacity_weight_kg"] < wt:
                    continue

                # Zone rule violations for non-critical items (10% chance)
                zone_violation = False
                if not (cold or ctrl) and random.random() < 0.10:
                    zone_violation = True  # Allow violation for regular items

                if not zone_violation:
                    # Normal zone rules
                    if cold and loc["zone_type"] != "cold":
                        continue
                    if ctrl and loc["zone_type"] != "restricted":
                        continue

                compatible_locs.append(loc)

            if compatible_locs:
                # Create hotspots: 70% chance to pick from most-used locations (clustering)
                if random.random() < 0.70 and any(
                    loc["item_count"] > 0 for loc in compatible_locs
                ):
                    # Prefer locations that already have items (creates clustering)
                    weighted_locs = [
                        loc for loc in compatible_locs if loc["item_count"] > 0
                    ]
                    if weighted_locs:
                        # Bias towards already-used locations
                        weights = [loc["item_count"] + 1 for loc in weighted_locs]
                        chosen_loc = random.choices(weighted_locs, weights=weights)[0]
                    else:
                        chosen_loc = random.choice(compatible_locs)
                else:
                    # 30% chance for truly random placement
                    chosen_loc = random.choice(compatible_locs)

                # Assign to chosen location
                chosen_loc["capacity_volume_m3"] -= vol
                chosen_loc["capacity_weight_kg"] -= wt
                chosen_loc["item_count"] += 1
                assignments.append(
                    {"med_id": sku["med_id"], "location_id": chosen_loc["location_id"]}
                )
            else:
                # No compatible location found - force assign to random ambient if exists
                ambient_locs = [
                    loc
                    for loc in loc_caps
                    if loc["zone_type"] == "ambient"
                    and loc["capacity_volume_m3"] >= vol
                    and loc["capacity_weight_kg"] >= wt
                ]
                if ambient_locs:
                    fallback_loc = random.choice(ambient_locs)
                    fallback_loc["capacity_volume_m3"] -= vol
                    fallback_loc["capacity_weight_kg"] -= wt
                    fallback_loc["item_count"] += 1
                    assignments.append(
                        {
                            "med_id": sku["med_id"],
                            "location_id": fallback_loc["location_id"],
                        }
                    )
                else:
                    # Truly orphaned
                    assignments.append({"med_id": sku["med_id"], "location_id": None})

    return assignments


# -----------------------
# Data validation functions
# -----------------------
def validate_generated_data(conn, meds, output_dir):
    """
    Validate the generated data for logical consistency and quality issues.
    Returns a validation report with warnings and errors.
    """
    validation_report = {"errors": [], "warnings": [], "summary": {}}

    cur = conn.cursor()

    # 1. Check medication category consistency
    category_issues = []
    chronic_meds = [med for med in meds if med["category"] == "Chronic"]
    if chronic_meds:
        # Check consumption patterns for chronic medications
        chronic_med_ids = [str(med["med_id"]) for med in chronic_meds]
        cur.execute(f"""
            SELECT med_id, AVG(qty_dispensed) as avg_daily, 
                   COUNT(CASE WHEN qty_dispensed = 0 THEN 1 END) as zero_days,
                   COUNT(*) as total_days
            FROM consumption_history 
            WHERE med_id IN ({",".join(chronic_med_ids)})
            GROUP BY med_id
        """)

        for med_id, avg_daily, zero_days, total_days in cur.fetchall():
            med_name = next(
                (m["name"] for m in meds if m["med_id"] == med_id), f"Med {med_id}"
            )
            zero_pct = (zero_days / total_days) * 100 if total_days > 0 else 0

            if avg_daily < 5:
                category_issues.append(
                    f"Chronic medication '{med_name}' has unusually low consumption: {avg_daily:.1f} units/day"
                )
            if zero_pct > 15:
                category_issues.append(
                    f"Chronic medication '{med_name}' has {zero_pct:.1f}% zero-demand days (should be <15%)"
                )

    validation_report["warnings"].extend(category_issues)

    # 2. Check price volatility
    cur.execute("""
        SELECT med_id, COUNT(*) as price_changes,
               MAX(price_per_unit) - MIN(price_per_unit) as price_range,
               AVG(price_per_unit) as avg_price
        FROM drug_prices 
        GROUP BY med_id
    """)

    price_issues = []
    for med_id, _changes, price_range, avg_price in cur.fetchall():
        volatility_pct = (price_range / avg_price) * 100 if avg_price > 0 else 0
        if volatility_pct > 25:  # More than 25% price variation
            med_name = next(
                (m["name"] for m in meds if m["med_id"] == med_id), f"Med {med_id}"
            )
            price_issues.append(
                f"Medication '{med_name}' has high price volatility: {volatility_pct:.1f}%"
            )

    validation_report["warnings"].extend(price_issues)

    # 3. Check slot assignment distribution
    cur.execute("""
        SELECT location_id, COUNT(*) as item_count
        FROM slot_assignment_simple
        GROUP BY location_id
        ORDER BY item_count DESC
    """)

    slot_distribution = cur.fetchall()
    if slot_distribution:
        # Adjusted threshold for messy warehouse (expect more concentration)
        over_concentrated = [loc for loc, count in slot_distribution if count > 10]

        if over_concentrated:
            validation_report["warnings"].append(
                f"Extreme slot over-concentration: {len(over_concentrated)} locations with >10 items (messy warehouse expected)"
            )

        # Add new metrics for messiness analysis
        if slot_distribution:
            max_items = max(count for _, count in slot_distribution)
            empty_locations = len(
                [loc for loc, count in slot_distribution if count == 0]
            )

            validation_report["summary"]["max_items_per_location"] = max_items
            validation_report["summary"]["empty_locations"] = empty_locations
            validation_report["summary"]["location_utilization_pct"] = (
                round(
                    (
                        (len(slot_distribution) - empty_locations)
                        / len(slot_distribution)
                    )
                    * 100,
                    1,
                )
                if len(slot_distribution) > 0
                else 0
            )

    # 4. Check inventory simulation realism
    cur.execute("""
        SELECT 
            AVG(CASE WHEN censored = 1 THEN 1.0 ELSE 0.0 END) * 100 as stockout_rate,
            AVG(on_hand) as avg_inventory
        FROM consumption_history
    """)

    stockout_rate, avg_inventory = cur.fetchone()
    if stockout_rate > 15:  # >15% stockout rate is unrealistic
        validation_report["warnings"].append(
            f"High stockout rate: {stockout_rate:.1f}% (should be <15%)"
        )

    # 5. Generate summary statistics
    cur.execute("SELECT COUNT(DISTINCT med_id) FROM consumption_history")
    total_meds = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT store_id) FROM consumption_history")
    total_stores = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM consumption_history")
    total_records = cur.fetchone()[0]

    # 6. Check SKU fragmentation (split across multiple locations)
    cur.execute("""
        SELECT med_id, COUNT(DISTINCT location_id) as location_count
        FROM slot_assignment_simple
        GROUP BY med_id
        HAVING location_count > 1
    """)
    fragmented_skus = cur.fetchall()
    fragmentation_rate = (
        len(fragmented_skus) / total_meds * 100 if total_meds > 0 else 0
    )

    # 7. Count orphaned items (unassigned)
    cur.execute(
        "SELECT COUNT(*) FROM sku_meta WHERE med_id NOT IN (SELECT med_id FROM slot_assignment_simple)"
    )
    orphaned_items = cur.fetchone()[0]

    validation_report["summary"] = {
        "total_medications": total_meds,
        "total_stores": total_stores,
        "total_consumption_records": total_records,
        "stockout_rate_pct": round(stockout_rate, 2) if stockout_rate else 0,
        "avg_inventory_level": round(avg_inventory, 1) if avg_inventory else 0,
        "price_changes_per_med": round(
            sum(
                count
                for _, count in cur.execute(
                    "SELECT med_id, COUNT(*) FROM drug_prices GROUP BY med_id"
                ).fetchall()
            )
            / total_meds,
            1,
        )
        if total_meds > 0
        else 0,
        "sku_fragmentation_rate_pct": round(fragmentation_rate, 1),
        "fragmented_skus_count": len(fragmented_skus),
        "orphaned_items_count": orphaned_items,
    }

    return validation_report


# -----------------------
# Additional data generators for enhanced POC
# -----------------------


def generate_current_inventory_levels(
    medications, consumption_history, sku_meta, suppliers, seed=DEFAULT_SEED + 40
):
    """
    Generate current inventory levels with realistic stock distribution
    Ensures 30-40% of items are in low/critical stock status
    """
    random.seed(seed)
    np.random.seed(seed)

    inventory_rows = []

    # Get latest stock levels from consumption history
    df_consumption = pd.DataFrame(consumption_history)
    df_consumption["date"] = pd.to_datetime(df_consumption["date"])
    latest_stock = df_consumption.loc[df_consumption.groupby("med_id")["date"].idxmax()]

    # Create a mapping of med_id to total current stock
    stock_by_med = latest_stock.groupby("med_id")["on_hand"].sum().to_dict()

    # Create supplier lookup
    supplier_lookup = {s["supplier_id"]: s for s in suppliers}

    for med in medications:
        med_id = med["med_id"]
        category = med["category"]

        # Get SKU metadata
        sku_info = next((s for s in sku_meta if s["med_id"] == med_id), {})
        avg_daily_pick = sku_info.get("avg_daily_pick", 10.0)

        # Get supplier info for lead times
        supplier = supplier_lookup.get(med["supplier_id"], {})
        avg_lead_time = supplier.get("avg_lead_time", 7.0)

        # Calculate base stock parameters
        current_stock = stock_by_med.get(med_id, 100)  # Fallback if not found

        # Calculate safety stock based on category
        if category == "Chronic":
            safety_days = 7
        elif category == "Intermittent":
            safety_days = 14
        else:  # Sporadic
            safety_days = 21

        # Calculate reorder point and max stock
        reorder_point = int(avg_daily_pick * (avg_lead_time + safety_days))
        max_stock = int(reorder_point * 2.5)

        # Calculate days of supply
        days_supply = current_stock / max(avg_daily_pick, 0.1)

        # Determine stock status
        if days_supply <= 3:
            stock_status = "Critical"
        elif days_supply <= 7:
            stock_status = "Low"
        elif days_supply <= 21:
            stock_status = "Medium"
        else:
            stock_status = "High"

        # Calculate days until stockout (assuming constant consumption)
        days_until_stockout = max(0, int(current_stock / max(avg_daily_pick, 0.1)))

        inventory_rows.append(
            {
                "med_id": med_id,
                "current_stock": int(current_stock),
                "reorder_point": reorder_point,
                "max_stock": max_stock,
                "last_updated": (
                    datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))
                ).isoformat(),
                "stock_status": stock_status,
                "days_until_stockout": days_until_stockout,
                "safety_stock": int(avg_daily_pick * safety_days),
            }
        )

    # Adjust distribution to ensure 30-40% low/critical stock
    total_meds = len(inventory_rows)
    target_critical = int(total_meds * 0.15)  # 15% critical
    target_low = int(total_meds * 0.20)  # 20% low

    # Sort by current days supply and adjust the lowest stock items
    inventory_rows.sort(key=lambda x: x["days_until_stockout"])

    # Force adjust the lowest items to be critical/low
    for i in range(target_critical):
        if i < len(inventory_rows):
            row = inventory_rows[i]
            # Set to critical levels (1-3 days supply)
            new_stock = int(row["reorder_point"] * random.uniform(0.1, 0.3))
            row["current_stock"] = max(1, new_stock)
            row["days_until_stockout"] = max(
                1, int(new_stock / max(row["safety_stock"] / 7, 0.1))
            )
            row["stock_status"] = "Critical"

    for i in range(target_critical, target_critical + target_low):
        if i < len(inventory_rows):
            row = inventory_rows[i]
            # Set to low levels (3-7 days supply)
            new_stock = int(row["reorder_point"] * random.uniform(0.3, 0.7))
            row["current_stock"] = max(1, new_stock)
            row["days_until_stockout"] = max(
                3, int(new_stock / max(row["safety_stock"] / 7, 0.1))
            )
            row["stock_status"] = "Low"

    return inventory_rows


def generate_batch_info(
    medications, inventory_levels, receipts_data, seed=DEFAULT_SEED + 41
):
    """
    Generate batch/lot information with FIFO tracking
    Creates 3-5 batches per medication with realistic expiry dates
    """
    random.seed(seed)
    np.random.seed(seed)

    batch_rows = []
    batch_counter = 1

    # Create inventory lookup
    inventory_lookup = {inv["med_id"]: inv for inv in inventory_levels}

    for med in medications:
        med_id = med["med_id"]
        shelf_life_days = med.get("shelf_life_days", 365)
        current_stock = inventory_lookup.get(med_id, {}).get("current_stock", 100)

        # Generate 3-5 batches per medication
        num_batches = random.randint(3, 5)

        # Distribute current stock across batches
        remaining_stock = current_stock
        batch_quantities = []

        for i in range(num_batches - 1):
            if remaining_stock > 0:
                batch_qty = random.randint(1, max(1, remaining_stock // 2))
                batch_quantities.append(batch_qty)
                remaining_stock -= batch_qty
            else:
                batch_quantities.append(0)

        batch_quantities.append(max(0, remaining_stock))  # Remainder in last batch

        for i, quantity in enumerate(batch_quantities):
            if quantity <= 0:
                continue

            # Generate lot number
            now = datetime.now(timezone.utc)
            manufacture_date = now - timedelta(
                days=random.randint(30, min(shelf_life_days - 60, 300))
            )
            lot_number = (
                f"LOT-{manufacture_date.strftime('%Y%m')}-{med_id:03d}-{i + 1:02d}"
            )

            # Calculate expiry date
            expiry_date = manufacture_date + timedelta(days=shelf_life_days)

            # Calculate received date (sometime after manufacture)
            received_date = manufacture_date + timedelta(days=random.randint(7, 30))

            # Determine status
            days_until_expiry = (expiry_date.date() - now.date()).days
            if days_until_expiry < 0:
                status = "expired"
            elif days_until_expiry < 30:
                status = "near_expiry"
            elif random.random() < 0.02:  # 2% chance of quarantine
                status = "quarantine"
            else:
                status = "active"

            batch_rows.append(
                {
                    "batch_id": batch_counter,
                    "med_id": med_id,
                    "lot_number": lot_number,
                    "manufacture_date": manufacture_date.date().isoformat(),
                    "expiry_date": expiry_date.date().isoformat(),
                    "quantity": quantity,
                    "received_date": received_date.date().isoformat(),
                    "remaining_quantity": quantity if status == "active" else 0,
                    "status": status,
                }
            )
            batch_counter += 1

    return batch_rows


def generate_warehouse_zones(storage_locations, seed=DEFAULT_SEED + 42):
    """
    Generate enhanced warehouse zone information
    Groups storage locations into logical zones with environmental controls
    """
    random.seed(seed)

    zones = []
    zone_id = 1

    # Group locations by zone type
    location_groups = {}
    for i, loc in enumerate(storage_locations):
        zone_type = loc["zone_type"]
        if zone_type not in location_groups:
            location_groups[zone_type] = []
        location_groups[zone_type].append(i + 1)  # location_id starts from 1

    # Generate zone details
    for zone_type, location_ids in location_groups.items():
        # Create sub-zones if there are many locations of same type
        locations_per_zone = 6 if zone_type == "ambient" else 4
        sub_zones = [
            location_ids[i : i + locations_per_zone]
            for i in range(0, len(location_ids), locations_per_zone)
        ]

        for i, sub_zone_locations in enumerate(sub_zones):
            if zone_type == "ambient":
                zone_name = f"Zone A{i + 1}"
                temp_range = "15-25°C"
                humidity_range = "30-70%"
                security_level = 1
            elif zone_type == "cold":
                zone_name = f"Zone C{i + 1}"
                temp_range = "2-8°C"
                humidity_range = "35-60%"
                security_level = 2
            elif zone_type == "restricted":
                zone_name = f"Zone R{i + 1}"
                temp_range = "15-25°C"
                humidity_range = "30-70%"
                security_level = 3
            else:
                zone_name = f"Zone {zone_type.upper()}{i + 1}"
                temp_range = "15-25°C"
                humidity_range = "30-70%"
                security_level = 1

            # Calculate capacity utilization
            utilization = random.uniform(0.60, 0.85)  # 60-85% utilization

            zones.append(
                {
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "zone_type": zone_type,
                    "temperature_range": temp_range,
                    "humidity_range": humidity_range,
                    "security_level": security_level,
                    "location_ids": ",".join(map(str, sub_zone_locations)),
                    "capacity_utilization": round(utilization, 3),
                }
            )
            zone_id += 1

    return zones


def generate_purchase_orders(
    medications,
    suppliers,
    inventory_levels,
    receipts_data,
    drug_prices,
    seed=DEFAULT_SEED + 43,
):
    """
    Generate comprehensive purchase order history
    Creates realistic PO patterns with various statuses
    """
    random.seed(seed)
    np.random.seed(seed)

    po_rows = []
    po_counter = 1

    # Create lookups
    supplier_lookup = {s["supplier_id"]: s for s in suppliers}
    price_lookup = {}
    for price in drug_prices:
        med_id = price["med_id"]
        if med_id not in price_lookup:
            price_lookup[med_id] = []
        price_lookup[med_id].append(price)

    # Sort prices by date for each medication
    for med_id in price_lookup:
        price_lookup[med_id].sort(key=lambda x: x["valid_from"])

    # Process receipts to create completed orders
    for receipt in receipts_data:
        med_id = receipt["med_id"]
        med = next((m for m in medications if m["med_id"] == med_id), None)
        if not med:
            continue

        supplier = supplier_lookup.get(med["supplier_id"], {})

        # Get price for this date
        order_date = pd.to_datetime(receipt["order_date"]).date()
        unit_price = 10.0  # Default fallback

        if med_id in price_lookup:
            # Find the most recent price before order date
            applicable_prices = [
                p
                for p in price_lookup[med_id]
                if pd.to_datetime(p["valid_from"]).date() <= order_date
            ]
            if applicable_prices:
                unit_price = applicable_prices[-1]["price_per_unit"]

        quantity = receipt["qty_ordered"]
        total_amount = round(quantity * unit_price, 2)

        # Generate PO number
        year = pd.to_datetime(receipt["order_date"]).year
        po_number = f"PO-{year}-{po_counter:05d}"

        # Payment terms
        payment_terms = random.choice(["NET30", "NET45", "NET60", "COD", "NET15"])

        po_rows.append(
            {
                "po_id": po_counter,
                "po_number": po_number,
                "med_id": med_id,
                "supplier_id": med["supplier_id"],
                "quantity_ordered": quantity,
                "unit_price": unit_price,
                "total_amount": total_amount,
                "order_date": receipt["order_date"],
                "expected_delivery": receipt["arrival_date"],
                "actual_delivery": receipt["arrival_date"],  # Matches receipts
                "status": "completed",
                "payment_terms": payment_terms,
                "notes": "Regular replenishment order",
            }
        )
        po_counter += 1

    # Generate additional pending/in-transit orders (15% pending, 10% in-transit)
    current_orders_count = len(po_rows)
    additional_orders = int(current_orders_count * 0.35)  # 35% more orders

    for _ in range(additional_orders):
        med = random.choice(medications)
        med_id = med["med_id"]
        supplier = supplier_lookup.get(med["supplier_id"], {})

        # Generate order details
        order_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
        lead_time = supplier.get("avg_lead_time", 7)
        expected_delivery = order_date + timedelta(days=int(lead_time))

        # Determine status
        status_rand = random.random()
        if status_rand < 0.05:  # 5% cancelled
            status = "cancelled"
            actual_delivery = None
            notes = random.choice(
                [
                    "Cancelled due to supplier shortage",
                    "Order cancelled - alternative source found",
                    "Product discontinued by supplier",
                ]
            )
        elif status_rand < 0.15:  # 10% in transit
            status = "in_transit"
            actual_delivery = None
            notes = "Order shipped - in transit"
        else:  # 15% pending
            status = "pending"
            actual_delivery = None
            notes = "Order confirmed - awaiting shipment"

        # Get inventory info for quantity
        inv_info = next(
            (inv for inv in inventory_levels if inv["med_id"] == med_id), {}
        )
        reorder_point = inv_info.get("reorder_point", 100)
        quantity = random.randint(reorder_point // 2, reorder_point * 2)

        # Get current price
        unit_price = 10.0
        if med_id in price_lookup and price_lookup[med_id]:
            unit_price = price_lookup[med_id][-1]["price_per_unit"]

        total_amount = round(quantity * unit_price, 2)

        year = order_date.year
        po_number = f"PO-{year}-{po_counter:05d}"
        payment_terms = random.choice(["NET30", "NET45", "NET60"])

        po_rows.append(
            {
                "po_id": po_counter,
                "po_number": po_number,
                "med_id": med_id,
                "supplier_id": med["supplier_id"],
                "quantity_ordered": quantity,
                "unit_price": unit_price,
                "total_amount": total_amount,
                "order_date": order_date.date().isoformat(),
                "expected_delivery": expected_delivery.date().isoformat(),
                "actual_delivery": actual_delivery.date().isoformat()
                if actual_delivery
                else None,
                "status": status,
                "payment_terms": payment_terms,
                "notes": notes,
            }
        )
        po_counter += 1

    return po_rows


# -----------------------
# Pre-aggregated data generation functions
# -----------------------
def generate_dashboard_daily_aggregates(
    consumption_history,
    medications,
    inventory_levels,
    drug_prices,
    seed=DEFAULT_SEED + 50,
):
    """
    Generate pre-aggregated dashboard metrics by date for fast chart rendering
    """
    random.seed(seed)
    np.random.seed(seed)

    df_consumption = pd.DataFrame(consumption_history)
    df_consumption["date"] = pd.to_datetime(df_consumption["date"]).dt.date

    # Create medication and pricing lookups
    price_lookup = {}
    for price in drug_prices:
        med_id = price["med_id"]
        if med_id not in price_lookup:
            price_lookup[med_id] = []
        price_lookup[med_id].append(price)

    # Sort prices by date
    for med_id in price_lookup:
        price_lookup[med_id].sort(key=lambda x: x["valid_from"])

    # Get inventory lookup
    inventory_lookup = {inv["med_id"]: inv for inv in inventory_levels}

    dashboard_aggregates = []

    # Group by date and calculate aggregates
    daily_groups = df_consumption.groupby("date")

    for date, group in daily_groups:
        date_str = date.isoformat()

        # Basic consumption metrics
        total_consumption = int(group["qty_dispensed"].sum())
        total_orders = len(group)
        unique_medications = int(group["med_id"].nunique())
        stockout_events = int(group["censored"].sum())
        avg_stock_level = float(group["on_hand"].mean())

        # Calculate total value for the date
        total_value = 0.0
        critical_stock_count = 0
        low_stock_count = 0

        for _, row in group.iterrows():
            med_id = row["med_id"]

            # Get price for this date
            if med_id in price_lookup:
                applicable_prices = [
                    p
                    for p in price_lookup[med_id]
                    if pd.to_datetime(p["valid_from"]).date() <= date
                ]
                if applicable_prices:
                    unit_price = applicable_prices[-1]["price_per_unit"]
                    total_value += row["qty_dispensed"] * unit_price

            # Check stock status
            inv_info = inventory_lookup.get(med_id, {})
            current_stock = row["on_hand"]
            reorder_point = inv_info.get("reorder_point", 100)

            if current_stock <= reorder_point * 0.25:
                critical_stock_count += 1
            elif current_stock <= reorder_point * 0.5:
                low_stock_count += 1

        dashboard_aggregates.append(
            {
                "date": date_str,
                "total_consumption": total_consumption,
                "total_orders": total_orders,
                "unique_medications": unique_medications,
                "stockout_events": stockout_events,
                "avg_stock_level": round(avg_stock_level, 2),
                "total_value": round(total_value, 2),
                "critical_stock_count": critical_stock_count,
                "low_stock_count": low_stock_count,
            }
        )

    return dashboard_aggregates


def generate_category_daily_aggregates(
    consumption_history,
    medications,
    inventory_levels,
    drug_prices,
    seed=DEFAULT_SEED + 51,
):
    """
    Generate category-level daily aggregates for breakdown charts
    """
    random.seed(seed)
    np.random.seed(seed)

    df_consumption = pd.DataFrame(consumption_history)
    df_consumption["date"] = pd.to_datetime(df_consumption["date"]).dt.date

    # Add category information
    med_category_lookup = {med["med_id"]: med["category"] for med in medications}
    df_consumption["category"] = df_consumption["med_id"].map(med_category_lookup)

    # Create pricing lookup
    price_lookup = {}
    for price in drug_prices:
        med_id = price["med_id"]
        if med_id not in price_lookup:
            price_lookup[med_id] = []
        price_lookup[med_id].append(price)

    for med_id in price_lookup:
        price_lookup[med_id].sort(key=lambda x: x["valid_from"])


    category_aggregates = []

    # Group by date and category
    daily_category_groups = df_consumption.groupby(["date", "category"])

    for (date, category), group in daily_category_groups:
        date_str = date.isoformat()

        total_consumption = int(group["qty_dispensed"].sum())
        medication_count = int(group["med_id"].nunique())
        avg_stock_level = float(group["on_hand"].mean())
        stockout_events = int(group["censored"].sum())

        # Calculate category value
        total_value = 0.0
        for _, row in group.iterrows():
            med_id = row["med_id"]
            if med_id in price_lookup:
                applicable_prices = [
                    p
                    for p in price_lookup[med_id]
                    if pd.to_datetime(p["valid_from"]).date() <= date
                ]
                if applicable_prices:
                    unit_price = applicable_prices[-1]["price_per_unit"]
                    total_value += row["qty_dispensed"] * unit_price

        category_aggregates.append(
            {
                "date": date_str,
                "category": category,
                "total_consumption": total_consumption,
                "medication_count": medication_count,
                "avg_stock_level": round(avg_stock_level, 2),
                "total_value": round(total_value, 2),
                "stockout_events": stockout_events,
            }
        )

    return category_aggregates


def generate_hourly_consumption_patterns(
    consumption_history, medications, seed=DEFAULT_SEED + 52
):
    """
    Generate realistic hourly consumption patterns for intraday analysis
    """
    random.seed(seed)
    np.random.seed(seed)

    hourly_patterns = []

    # Define hourly distribution patterns (pharmacy operating hours)
    # Higher activity during business hours, minimal at night
    hourly_weights = {
        0: 0.01,
        1: 0.01,
        2: 0.01,
        3: 0.01,
        4: 0.01,
        5: 0.01,
        6: 0.02,
        7: 0.05,
        8: 0.12,
        9: 0.15,
        10: 0.14,
        11: 0.12,
        12: 0.08,
        13: 0.10,
        14: 0.12,
        15: 0.08,
        16: 0.06,
        17: 0.04,
        18: 0.03,
        19: 0.02,
        20: 0.01,
        21: 0.01,
        22: 0.01,
        23: 0.01,
    }

    # Sample 20% of consumption history for hourly breakdown
    sample_size = max(1000, len(consumption_history) // 5)
    sampled_history = random.sample(
        consumption_history, min(sample_size, len(consumption_history))
    )

    for record in sampled_history:
        if record["qty_dispensed"] == 0:
            continue

        date = pd.to_datetime(record["date"])
        med_id = record["med_id"]
        store_id = record["store_id"]
        total_daily_qty = record["qty_dispensed"]

        # Distribute daily quantity across hours based on pharmacy patterns
        remaining_qty = total_daily_qty

        for hour in range(24):
            if remaining_qty <= 0:
                break

            # Calculate expected hourly quantity
            expected_hourly = int(total_daily_qty * hourly_weights[hour])

            # Add some randomness
            if expected_hourly > 0:
                hourly_qty = max(
                    0, min(remaining_qty, int(np.random.poisson(expected_hourly)))
                )
            else:
                hourly_qty = 1 if remaining_qty > 0 and random.random() < 0.1 else 0

            if hourly_qty > 0:
                datetime_str = date.replace(hour=hour, minute=0, second=0).isoformat()

                hourly_patterns.append(
                    {
                        "datetime": datetime_str,
                        "med_id": med_id,
                        "store_id": store_id,
                        "hour": hour,
                        "qty_dispensed": hourly_qty,
                        "on_hand": record[
                            "on_hand"
                        ],  # Simplified - same for all hours of day
                    }
                )

                remaining_qty -= hourly_qty

    return hourly_patterns


# -----------------------
# Orchestrator
# -----------------------
def generate_all(
    conn,
    output_dir,
    n_suppliers=10,
    n_meds=50,
    n_stores=3,
    days=365,
    start_date=None,
    n_forecast_samples=50,
    forecast_horizon=180,
    n_storage_locs=24,
    seed=DEFAULT_SEED,
):
    ensure_dir(output_dir)
    if start_date is None:
        # Exclude current incomplete day to avoid zero consumption entries
        start_date = (datetime.now(timezone.utc) - relativedelta(days=days + 1)).date()
    else:
        start_date = pd.Timestamp(start_date).date()

    # Master data
    suppliers = generate_suppliers(n_suppliers, seed=seed)
    meds = generate_medications(n_meds, suppliers, seed=seed + 1)
    stores = generate_stores(n_stores, seed=seed + 2)

    cur = conn.cursor()
    cur.executemany(
        "INSERT OR REPLACE INTO suppliers (supplier_id, name, status, avg_lead_time, last_delivery_date, email, contact_name, phone, address) VALUES (:supplier_id, :name, :status, :avg_lead_time, :last_delivery_date, :email, :contact_name, :phone, :address);",
        suppliers,
    )
    cur.executemany(
        "INSERT OR REPLACE INTO medications (med_id, name, category, pack_size, shelf_life_days, supplier_id) VALUES (:med_id, :name, :category, :pack_size, :shelf_life_days, :supplier_id);",
        meds,
    )
    cur.executemany(
        "INSERT OR REPLACE INTO stores (store_id, name, location) VALUES (:store_id, :name, :location);",
        stores,
    )
    conn.commit()

    pd.DataFrame(suppliers).to_csv(
        os.path.join(output_dir, "suppliers.csv"), index=False
    )
    pd.DataFrame(meds).to_csv(os.path.join(output_dir, "medications.csv"), index=False)
    pd.DataFrame(stores).to_csv(os.path.join(output_dir, "stores.csv"), index=False)

    # Price history
    all_price_rows = []
    for med in meds:
        rows = generate_price_history_for_med(med["med_id"], start_date, days)
        all_price_rows.extend(rows)
    cur.executemany(
        "INSERT INTO drug_prices (med_id, valid_from, price_per_unit) VALUES (:med_id, :valid_from, :price_per_unit);",
        all_price_rows,
    )
    conn.commit()
    pd.DataFrame(all_price_rows).to_csv(
        os.path.join(output_dir, "drug_prices.csv"), index=False
    )

    # Supplier-specific current prices for each medication
    supplier_price_rows = generate_supplier_prices_for_meds(
        meds, suppliers, all_price_rows, seed=seed + 44
    )

    # Insert supplier prices into database
    print("Writing supplier prices to DB …")
    cur.executemany(
        "INSERT INTO med_supplier_prices (med_id, supplier_id, valid_from, price_per_unit) VALUES (:med_id, :supplier_id, :valid_from, :price_per_unit);",
        supplier_price_rows,
    )
    conn.commit()

    pd.DataFrame(supplier_price_rows).to_csv(
        os.path.join(output_dir, "med_supplier_prices.csv"), index=False
    )

    # Consumption & receipts & forecasts
    all_history_rows = []
    all_receipts = []
    all_forecast_rows = []

    print("Generating consumption history and forecasts (this may take a few minutes)…")
    for store in tqdm(stores, desc="stores"):
        for med in tqdm(meds, desc=f"meds (store {store['store_id']})", leave=False):
            # Get medication profile if available (for base medications)
            med_name_base = med["name"].split(" (GEN-")[0]  # Remove generated suffix
            profile = None
            for p in MEDICATION_PROFILES:
                if p["name"] == med_name_base:
                    profile = p
                    break

            # parameters based on category with more realistic ranges
            cat = med["category"]
            if cat == "Chronic":
                if profile:
                    # Use predefined realistic demand range
                    base = float(
                        np.random.uniform(
                            profile["base_daily_demand"][0],
                            profile["base_daily_demand"][1],
                        )
                    )
                else:
                    # For generated chronic medications
                    base = float(np.random.uniform(15, 85))
                trend_slope = np.random.uniform(-0.01, 0.03)  # More conservative trends
                noise = max(1.0, base * 0.06)  # Reduced noise for chronic meds
                p_occ = 1.0  # Chronic medications are dispensed daily
            elif cat == "Intermittent":
                if profile:
                    base = float(
                        np.random.uniform(
                            profile["base_daily_demand"][0],
                            profile["base_daily_demand"][1],
                        )
                    )
                else:
                    base = float(np.random.uniform(3, 18))
                trend_slope = np.random.uniform(-0.01, 0.02)
                noise = max(0.5, base * 0.4)
                p_occ = np.random.uniform(0.08, 0.25)  # Slightly higher occurrence rate
            else:  # Sporadic
                if profile:
                    base = float(
                        np.random.uniform(
                            profile["base_daily_demand"][0],
                            profile["base_daily_demand"][1],
                        )
                    )
                else:
                    base = float(np.random.uniform(0.2, 4.0))
                trend_slope = np.random.uniform(-0.005, 0.01)
                noise = max(0.2, base * 0.8)
                p_occ = np.random.uniform(0.02, 0.12)

            base_series = base_daily_pattern(
                days,
                base,
                trend_slope=trend_slope,
                weekly_amp=0.12,
                monthly_amp=0.04,
                noise_std=noise,
            )
            if cat == "Chronic":
                demand_series = np.round(base_series).astype(int)
            else:
                intermittent = intermittent_process(
                    days, avg_when_occurs=max(1, int(round(base))), p_occurrence=p_occ
                )
                season = base_daily_pattern(
                    days, 1.0, weekly_amp=0.12, monthly_amp=0.04, noise_std=0.3
                )
                demand_series = np.round(intermittent * season).astype(int)

            demand_series = inject_spikes(
                demand_series, spike_chance=0.01, spike_multiplier=3, max_extra=6
            )

            supplier = next(
                s for s in suppliers if s["supplier_id"] == med["supplier_id"]
            )
            avg_lt = supplier["avg_lead_time"]

            hist_rows, receipts = simulate_inventory_and_history(
                store["store_id"],
                med,
                start_date,
                days,
                demand_series,
                med["pack_size"],
                avg_lt,
                reorder_buffer_days=14,
                seed=seed,
            )
            all_history_rows.extend(hist_rows)
            all_receipts.extend(receipts)

            qty_hist = [r["qty_dispensed"] for r in hist_rows]
            mean_fc, samples = compute_forecast_from_series(
                qty_hist,
                horizon=forecast_horizon,
                seasonal_periods=7,
                n_samples=n_forecast_samples,
            )
            all_forecast_rows.append(
                {
                    "store_id": store["store_id"],
                    "med_id": med["med_id"],
                    "model": "ExponentialSmoothing",
                    "horizon_days": forecast_horizon,
                    "forecast_mean": json.dumps(mean_fc),
                    "forecast_samples": json.dumps(samples),
                }
            )

    # bulk write consumption_history
    df_hist = pd.DataFrame(all_history_rows)
    df_hist.to_csv(os.path.join(output_dir, "consumption_history.csv"), index=False)

    # insert in chunks
    print("Writing consumption_history to DB …")
    cur = conn.cursor()
    insert_sql = "INSERT INTO consumption_history (store_id, med_id, date, qty_dispensed, on_hand, censored) VALUES (?, ?, ?, ?, ?, ?);"
    rows_tuple = [
        (
            r["store_id"],
            r["med_id"],
            r["date"],
            r["qty_dispensed"],
            r["on_hand"],
            r["censored"],
        )
        for r in all_history_rows
    ]
    batch = 2000
    for i in tqdm(range(0, len(rows_tuple), batch), desc="inserting history"):
        cur.executemany(insert_sql, rows_tuple[i : i + batch])
        conn.commit()

    # receipts
    if all_receipts:
        pd.DataFrame(all_receipts).to_csv(
            os.path.join(output_dir, "receipts_sim.csv"), index=False
        )

    # forecasts
    print("Writing forecasts to DB …")
    df_forecasts = pd.DataFrame(all_forecast_rows)
    df_forecasts.to_csv(os.path.join(output_dir, "forecasts.csv"), index=False)
    cur.executemany(
        "INSERT INTO forecasts (store_id, med_id, model, horizon_days, forecast_mean, forecast_samples) VALUES (:store_id, :med_id, :model, :horizon_days, :forecast_mean, :forecast_samples);",
        all_forecast_rows,
    )
    conn.commit()

    # Medication-level aggregated forecasts (6 months), averaged across stores
    print("Writing medication-level 6-month forecasts to DB …")
    forecasts_med_rows = []
    # Build mapping: (store_id, med_id) -> forecast arrays already computed in all_forecast_rows
    by_med = {}
    for fr in all_forecast_rows:
        med_id = fr["med_id"]
        mean_arr = (
            json.loads(fr["forecast_mean"])
            if isinstance(fr["forecast_mean"], str)
            else fr["forecast_mean"]
        )
        samp_arr = (
            json.loads(fr["forecast_samples"])
            if isinstance(fr["forecast_samples"], str)
            else fr["forecast_samples"]
        )
        by_med.setdefault(med_id, []).append((mean_arr, samp_arr))

    for med in meds:
        med_id = med["med_id"]
        if med_id not in by_med:
            continue
        means = [np.array(m) for m, _ in by_med[med_id] if m]
        if not means:
            continue
        # Average means across stores; concatenate samples from all stores
        avg_mean = np.mean(means, axis=0).tolist()
        # Flatten and cap number of samples to keep payload reasonable
        all_samples = []
        for _, samples in by_med[med_id]:
            if samples:
                all_samples.extend(samples)
        # Optionally subsample to 50
        if len(all_samples) > 50:
            all_samples = all_samples[:50]

        forecasts_med_rows.append(
            {
                "med_id": med_id,
                "model": "ExponentialSmoothing-avg",
                "horizon_days": forecast_horizon,
                "forecast_mean": json.dumps([float(x) for x in avg_mean]),
                "forecast_samples": json.dumps(all_samples),
            }
        )

    if forecasts_med_rows:
        pd.DataFrame(forecasts_med_rows).to_csv(
            os.path.join(output_dir, "forecasts_med.csv"), index=False
        )
        cur.executemany(
            "INSERT INTO forecasts_med (med_id, model, horizon_days, forecast_mean, forecast_samples) VALUES (:med_id, :model, :horizon_days, :forecast_mean, :forecast_samples);",
            forecasts_med_rows,
        )
        conn.commit()

    # Storage meta & locations & simple assignment
    print("Generating simplified storage metadata and slot assignments …")
    # compute avg_daily pick per med from history (aggregate across stores to get SKU-level velocity)
    df_hist_agg = df_hist.groupby("med_id")["qty_dispensed"].mean().to_dict()
    sku_rows = compute_sku_storage_meta(meds, df_hist_agg, seed=seed + 20)
    loc_rows = generate_storage_locations(n_locs=n_storage_locs, seed=seed + 21)

    # insert sku_meta
    cur.executemany(
        "INSERT INTO sku_meta (med_id, name, avg_daily_pick, case_volume_m3, case_weight_kg, is_cold_chain, is_controlled) VALUES (:med_id, :name, :avg_daily_pick, :case_volume_m3, :case_weight_kg, :is_cold_chain, :is_controlled);",
        sku_rows,
    )
    # insert storage locations
    cur.executemany(
        "INSERT INTO storage_loc_simple (zone_type, capacity_volume_m3, capacity_weight_kg, distance_score) VALUES (:zone_type, :capacity_volume_m3, :capacity_weight_kg, :distance_score);",
        loc_rows,
    )
    conn.commit()

    pd.DataFrame(sku_rows).to_csv(os.path.join(output_dir, "sku_meta.csv"), index=False)
    pd.DataFrame(loc_rows).to_csv(
        os.path.join(output_dir, "storage_loc_simple.csv"), index=False
    )

    # initial messy assignment (simulating disorganized warehouse)
    assignments = messy_warehouse_assignment(sku_rows, loc_rows, seed=seed + 30)
    assign_rows = []
    for a in assignments:
        if a["location_id"] is not None:
            assign_rows.append({"med_id": a["med_id"], "location_id": a["location_id"]})
    if assign_rows:
        cur.executemany(
            "INSERT INTO slot_assignment_simple (med_id, location_id) VALUES (:med_id, :location_id);",
            assign_rows,
        )
        conn.commit()
    pd.DataFrame(assign_rows).to_csv(
        os.path.join(output_dir, "slot_assignments.csv"), index=False
    )

    # Generate additional datasets
    print("Generating current inventory levels…")
    current_inventory = generate_current_inventory_levels(
        meds, all_history_rows, sku_rows, suppliers, seed=seed + 40
    )
    # Enrich with supplier name and valuation
    supplier_lookup = {s["supplier_id"]: s for s in suppliers}
    latest_price_lookup = {}
    # Build latest price by med
    for row in all_price_rows:
        latest_price_lookup[row["med_id"]] = row["price_per_unit"]
    valuation_rows = []
    for inv in current_inventory:
        med = next((m for m in meds if m["med_id"] == inv["med_id"]), None)
        if not med:
            continue
        supplier_name = supplier_lookup.get(med["supplier_id"], {}).get(
            "name", "Unknown"
        )
        price = float(latest_price_lookup.get(inv["med_id"], 0) or 0)
        total_value = float(price * inv.get("current_stock", 0))
        inv["supplier_name"] = supplier_name
        inv["current_price"] = price
        inv["total_value"] = total_value
        # Ensure days_until_stockout exists
        if not inv.get("days_until_stockout"):
            avg_daily = max(0.1, inv.get("safety_stock", 1) / 7)
            inv["days_until_stockout"] = int(inv.get("current_stock", 0) / avg_daily)
        valuation_rows.append(
            {
                "med_id": inv["med_id"],
                "current_stock": inv["current_stock"],
                "current_price": price,
                "total_value": total_value,
                "supplier_name": supplier_name,
            }
        )
    pd.DataFrame(current_inventory).to_csv(
        os.path.join(output_dir, "current_inventory.csv"), index=False
    )
    # Write valuation view for quick diagnostics
    pd.DataFrame(valuation_rows).to_csv(
        os.path.join(output_dir, "inventory_valuation.csv"), index=False
    )

    print("Generating batch information…")
    batch_info = generate_batch_info(
        meds, current_inventory, all_receipts, seed=seed + 41
    )
    pd.DataFrame(batch_info).to_csv(
        os.path.join(output_dir, "batch_info.csv"), index=False
    )

    print("Generating enhanced warehouse zones…")
    warehouse_zones = generate_warehouse_zones(loc_rows, seed=seed + 42)
    pd.DataFrame(warehouse_zones).to_csv(
        os.path.join(output_dir, "warehouse_zones.csv"), index=False
    )

    print("Generating purchase order history…")
    purchase_orders = generate_purchase_orders(
        meds, suppliers, current_inventory, all_receipts, all_price_rows, seed=seed + 43
    )
    pd.DataFrame(purchase_orders).to_csv(
        os.path.join(output_dir, "purchase_orders.csv"), index=False
    )

    # Generate pre-aggregated data for fast chart performance
    print("Generating pre-aggregated analytics data …")

    # Dashboard daily aggregates
    dashboard_aggregates = generate_dashboard_daily_aggregates(
        all_history_rows, meds, current_inventory, all_price_rows, seed=seed + 50
    )
    if dashboard_aggregates:
        cur.executemany(
            "INSERT INTO dashboard_daily_aggregates (date, total_consumption, total_orders, unique_medications, stockout_events, avg_stock_level, total_value, critical_stock_count, low_stock_count) VALUES (:date, :total_consumption, :total_orders, :unique_medications, :stockout_events, :avg_stock_level, :total_value, :critical_stock_count, :low_stock_count);",
            dashboard_aggregates,
        )
        pd.DataFrame(dashboard_aggregates).to_csv(
            os.path.join(output_dir, "dashboard_daily_aggregates.csv"), index=False
        )
        print(
            f"Generated {len(dashboard_aggregates)} dashboard daily aggregate records"
        )

    # Category daily aggregates
    category_aggregates = generate_category_daily_aggregates(
        all_history_rows, meds, current_inventory, all_price_rows, seed=seed + 51
    )
    if category_aggregates:
        cur.executemany(
            "INSERT INTO category_daily_aggregates (date, category, total_consumption, medication_count, avg_stock_level, total_value, stockout_events) VALUES (:date, :category, :total_consumption, :medication_count, :avg_stock_level, :total_value, :stockout_events);",
            category_aggregates,
        )
        pd.DataFrame(category_aggregates).to_csv(
            os.path.join(output_dir, "category_daily_aggregates.csv"), index=False
        )
        print(f"Generated {len(category_aggregates)} category daily aggregate records")

    # Hourly consumption patterns
    hourly_patterns = generate_hourly_consumption_patterns(
        all_history_rows, meds, seed=seed + 52
    )
    if hourly_patterns:
        cur.executemany(
            "INSERT INTO hourly_consumption (datetime, med_id, store_id, hour, qty_dispensed, on_hand) VALUES (:datetime, :med_id, :store_id, :hour, :qty_dispensed, :on_hand);",
            hourly_patterns,
        )
        pd.DataFrame(hourly_patterns).to_csv(
            os.path.join(output_dir, "hourly_consumption.csv"), index=False
        )
        print(f"Generated {len(hourly_patterns)} hourly consumption pattern records")

    conn.commit()
    print("Pre-aggregated data generation completed")

    # final: export key CSVs (masters already done)
    print("Exporting CSVs and finishing …")
    # Ensure forecasts CSV already done
    # Export consumption histogram summary for quick UI display
    df_summary = (
        df_hist.groupby("med_id")
        .agg(
            total_dispensed=("qty_dispensed", "sum"),
            avg_daily=("qty_dispensed", "mean"),
        )
        .reset_index()
    )
    df_summary.to_csv(
        os.path.join(output_dir, "consumption_summary_by_med.csv"), index=False
    )
    # receipts already saved

    # Run data validation and generate report
    print("Running data validation checks …")
    validation_report = validate_generated_data(conn, meds, output_dir)

    # Save validation report
    with open(os.path.join(output_dir, "validation_report.json"), "w") as f:
        json.dump(validation_report, f, indent=2)

    # Print validation summary
    print("\n" + "=" * 50)
    print("DATA VALIDATION REPORT")
    print("=" * 50)
    print(
        f"Total Records: {validation_report['summary']['total_consumption_records']:,}"
    )
    print(f"Medications: {validation_report['summary']['total_medications']}")
    print(f"Stores: {validation_report['summary']['total_stores']}")
    print(f"Stockout Rate: {validation_report['summary']['stockout_rate_pct']}%")
    print(f"Avg Inventory Level: {validation_report['summary']['avg_inventory_level']}")
    print("\n--- STORAGE ANALYSIS (MESSY WAREHOUSE) ---")
    print(
        f"SKU Fragmentation Rate: {validation_report['summary']['sku_fragmentation_rate_pct']}%"
    )
    print(f"Fragmented SKUs: {validation_report['summary']['fragmented_skus_count']}")
    print(f"Orphaned Items: {validation_report['summary']['orphaned_items_count']}")
    if "max_items_per_location" in validation_report["summary"]:
        print(
            f"Max Items Per Location: {validation_report['summary']['max_items_per_location']}"
        )
        print(
            f"Location Utilization: {validation_report['summary']['location_utilization_pct']}%"
        )

    if validation_report["errors"]:
        print(f"\n⚠️  ERRORS ({len(validation_report['errors'])}):")
        for error in validation_report["errors"]:
            print(f"  - {error}")

    if validation_report["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(validation_report['warnings'])}):")
        for warning in validation_report["warnings"]:
            print(f"  - {warning}")

    if not validation_report["errors"] and not validation_report["warnings"]:
        print("\n✅ All validation checks passed!")

    print("=" * 50)
    print(
        "Validation report saved to:",
        os.path.join(output_dir, "validation_report.json"),
    )

    # All done
    print("Done. CSVs written to:", output_dir)


# -----------------------
# CLI
# -----------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Generate full PoC synthetic data for pharmacy supply chain (incl. minimal storage metadata)."
    )
    p.add_argument("--db", default="poc_supplychain.db", help="Output sqlite DB file")
    p.add_argument("--out", default="data", help="Output CSV directory")
    p.add_argument("--suppliers", type=int, default=10, help="Number of suppliers")
    p.add_argument("--skus", type=int, default=50, help="Number of SKUs/medications")
    p.add_argument("--stores", type=int, default=3, help="Number of stores")
    p.add_argument(
        "--days", type=int, default=365, help="Days of history per store-SKU"
    )
    p.add_argument(
        "--forecast_samples",
        type=int,
        default=50,
        help="Monte-Carlo forecast samples per forecast",
    )
    p.add_argument(
        "--forecast_horizon",
        type=int,
        default=180,
        help="Forecast horizon in days (e.g., 180 for 6 months)",
    )
    p.add_argument(
        "--storage_locs",
        type=int,
        default=24,
        help="Number of simplified storage locations",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    np.random.seed(args.seed)
    random.seed(args.seed)
    ensure_dir(args.out)

    conn = create_connection(args.db)
    create_tables(conn)
    generate_all(
        conn,
        args.out,
        n_suppliers=args.suppliers,
        n_meds=args.skus,
        n_stores=args.stores,
        days=args.days,
        start_date=None,
        n_forecast_samples=args.forecast_samples,
        forecast_horizon=args.forecast_horizon,
        n_storage_locs=args.storage_locs,
        seed=args.seed,
    )
    conn.close()
    print("SQLite DB:", args.db)
    print("CSV directory:", args.out)
