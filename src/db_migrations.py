#!/usr/bin/env python3
"""
Database migration script to add purchase order tables and import supplier prices
"""

import os
import sqlite3

import pandas as pd


def get_db_path():
    """Get the database path relative to project root"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return os.path.join(project_root, "poc_supplychain.db")


def get_data_dir():
    """Get the data directory path"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return os.path.join(project_root, "data")


def create_tables(conn):
    """Create new tables for purchase orders and supplier prices"""
    cursor = conn.cursor()

    # Create med_supplier_prices table
    cursor.execute("""
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
        )
    """)

    # Create purchase_orders table
    cursor.execute("""
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
        )
    """)

    # Create purchase_order_items table
    cursor.execute("""
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
        )
    """)

    # Create AI metadata tables
    cursor.execute("""
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
        )
    """)

    cursor.execute("""
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
        )
    """)

    # Create indexes for better query performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_med_supplier_prices_med_id ON med_supplier_prices(med_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_med_supplier_prices_supplier_id ON med_supplier_prices(supplier_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON purchase_orders(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id ON purchase_orders(supplier_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_order_items_po_id ON purchase_order_items(po_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_order_items_med_id ON purchase_order_items(med_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_po_sessions_status ON ai_po_sessions(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_po_metadata_po_id ON ai_po_metadata(po_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_po_metadata_session_id ON ai_po_metadata(session_id)"
    )

    conn.commit()
    print("Tables created successfully")


def import_supplier_prices(conn):
    """Import med_supplier_prices.csv into the database"""
    cursor = conn.cursor()
    data_dir = get_data_dir()
    csv_path = os.path.join(data_dir, "med_supplier_prices.csv")

    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found, skipping supplier prices import")
        return

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM med_supplier_prices")
    count = cursor.fetchone()[0]
    if count > 0:
        print(
            f"ℹ️  med_supplier_prices table already contains {count} records, skipping import"
        )
        return

    # Read CSV and import
    df = pd.read_csv(csv_path)

    # Insert data
    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT OR IGNORE INTO med_supplier_prices (med_id, supplier_id, valid_from, price_per_unit)
            VALUES (?, ?, ?, ?)
        """,
            (
                row["med_id"],
                row["supplier_id"],
                row["valid_from"],
                row["price_per_unit"],
            ),
        )

    conn.commit()

    # Verify import
    cursor.execute("SELECT COUNT(*) FROM med_supplier_prices")
    imported_count = cursor.fetchone()[0]
    print(f"Imported {imported_count} supplier price records")


def verify_migration(conn):
    """Verify that migration was successful"""
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name IN ('med_supplier_prices', 'purchase_orders', 'purchase_order_items', 
                     'ai_po_sessions', 'ai_po_metadata')
    """)
    tables = cursor.fetchall()

    if len(tables) == 5:
        print("All required tables exist (including AI metadata tables)")
    else:
        print(f"Warning: Only {len(tables)} of 5 tables found")

    # Check supplier prices data
    cursor.execute("SELECT COUNT(*) FROM med_supplier_prices")
    price_count = cursor.fetchone()[0]
    print(f"med_supplier_prices contains {price_count} records")

    # Check if we have prices for multiple suppliers per medication
    cursor.execute("""
        SELECT med_id, COUNT(DISTINCT supplier_id) as supplier_count
        FROM med_supplier_prices
        GROUP BY med_id
        HAVING supplier_count > 1
        LIMIT 5
    """)
    multi_supplier_meds = cursor.fetchall()
    if multi_supplier_meds:
        print(
            f"✅ Found medications with multiple supplier prices (e.g., med_id {multi_supplier_meds[0][0]} has {multi_supplier_meds[0][1]} suppliers)"
        )


def main():
    """Run the migration"""
    print("Starting database migration...")

    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)

    try:
        # Create new tables
        create_tables(conn)

        # Import supplier prices
        import_supplier_prices(conn)

        # Verify migration
        verify_migration(conn)

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
