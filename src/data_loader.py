"""
Data loader module for inventory management system
Now uses SQLite database instead of CSV files
"""

import os
import sqlite3
from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger


def clean_nan_values(data):
    """Recursively clean NaN values from data structures for JSON serialization"""
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif data is None:
        return None
    elif isinstance(data, (float, np.floating)):
        if pd.isna(data) or np.isnan(data) or np.isinf(data):
            return None
        else:
            return float(data)  # Convert numpy float types to Python float
    elif isinstance(data, (int, np.integer)):
        if pd.isna(data):
            return None
        else:
            return int(data)  # Convert numpy int types to Python int
    elif pd.isna(data):
        return None
    else:
        return data


class DataLoader:
    def __init__(self, db_path: str = None):
        # Get the database path
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Go up one level from src/
            self.db_path = os.path.join(project_root, "poc_supplychain.db")
            self.data_dir = os.path.join(project_root, "data")  # Keep for CSV fallback
        else:
            self.db_path = db_path
            self.data_dir = os.path.dirname(db_path)
        # Initialize data containers
        self.medications = {}
        self.suppliers = {}
        self.consumption_history = {}
        self.sku_meta = {}
        self.storage_locations = {}
        self.slot_assignments = {}
        self.drug_prices = {}
        self.med_supplier_prices = {}
        # New data structures for enhanced data
        self.current_inventory = {}
        self.batch_info = {}
        self.warehouse_zones = {}
        self.purchase_orders = {}

        # Database connection (will be created on demand)
        self._conn = None

    def get_connection(self):
        """Get a fresh database connection"""
        # Always return a new connection to avoid "closed database" errors
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def load_all_data(self):
        """Load all data from SQLite database"""
        try:
            conn = self.get_connection()

            # Load medications
            meds_df = pd.read_sql_query("SELECT * FROM medications", conn)
            self.medications = meds_df.set_index("med_id").to_dict("index")

            # Load suppliers
            suppliers_df = pd.read_sql_query("SELECT * FROM suppliers", conn)
            self.suppliers = suppliers_df.set_index("supplier_id").to_dict("index")

            # Load consumption history (get latest stock levels)
            consumption_df = pd.read_sql_query(
                """SELECT * FROM consumption_history 
                   ORDER BY date DESC, store_id, med_id""",
                conn,
            )
            consumption_df["date"] = pd.to_datetime(consumption_df["date"])

            # Get latest stock level for each medication at each store
            latest_stock = consumption_df.loc[
                consumption_df.groupby(["store_id", "med_id"])["date"].idxmax()
            ]
            self.consumption_history = latest_stock.set_index(
                ["store_id", "med_id"]
            ).to_dict("index")

            # Load SKU metadata
            sku_df = pd.read_sql_query("SELECT * FROM sku_meta", conn)
            self.sku_meta = sku_df.set_index("med_id").to_dict("index")

            # Load storage locations
            storage_df = pd.read_sql_query("SELECT * FROM storage_loc_simple", conn)
            self.storage_locations = storage_df.to_dict("records")

            # Load slot assignments
            slots_df = pd.read_sql_query(
                """SELECT sa.*, sl.zone_type, sl.distance_score 
                   FROM slot_assignment_simple sa
                   LEFT JOIN storage_loc_simple sl ON sa.location_id = sl.location_id""",
                conn,
            )
            # Handle duplicate med_id entries by keeping the first occurrence
            slots_df = slots_df.drop_duplicates(subset=["med_id"], keep="first")
            self.slot_assignments = slots_df.set_index("med_id").to_dict("index")

            # Load drug prices (latest price for each medication)
            prices_df = pd.read_sql_query(
                """SELECT dp1.* FROM drug_prices dp1
                   INNER JOIN (
                       SELECT med_id, MAX(valid_from) as max_date
                       FROM drug_prices
                       GROUP BY med_id
                   ) dp2 ON dp1.med_id = dp2.med_id AND dp1.valid_from = dp2.max_date""",
                conn,
            )
            self.drug_prices = prices_df.set_index("med_id").to_dict("index")

            # Load new enhanced data files (with error handling for missing files)
            try:
                # Load current inventory
                current_inventory_df = pd.read_csv(
                    os.path.join(self.data_dir, "current_inventory.csv")
                )
                self.current_inventory = current_inventory_df.set_index(
                    "med_id"
                ).to_dict("index")
            except FileNotFoundError:
                logger.warning("current_inventory.csv not found, using fallback data")
                self.current_inventory = {}

            try:
                # Load batch information
                batch_df = pd.read_csv(os.path.join(self.data_dir, "batch_info.csv"))
                # Group batches by medication ID (drop med_id column from results to avoid warning)
                self.batch_info = {}
                for med_id, group in batch_df.groupby("med_id"):
                    self.batch_info[med_id] = group.drop(columns=["med_id"]).to_dict(
                        "records"
                    )
            except FileNotFoundError:
                logger.warning("batch_info.csv not found, using fallback data")
                self.batch_info = {}

            try:
                # Load warehouse zones
                zones_df = pd.read_csv(
                    os.path.join(self.data_dir, "warehouse_zones.csv")
                )
                self.warehouse_zones = zones_df.to_dict("records")
            except FileNotFoundError:
                logger.warning("warehouse_zones.csv not found, using fallback data")
                self.warehouse_zones = []

            try:
                # Load purchase orders
                po_df = pd.read_csv(os.path.join(self.data_dir, "purchase_orders.csv"))
                # Group POs by medication ID (drop med_id column from results to avoid warning)
                self.purchase_orders = {}
                for med_id, group in po_df.groupby("med_id"):
                    self.purchase_orders[med_id] = group.drop(
                        columns=["med_id"]
                    ).to_dict("records")
            except FileNotFoundError:
                logger.warning("purchase_orders.csv not found, using fallback data")
                self.purchase_orders = {}

            # Load supplier-specific prices from database
            supplier_prices_df = pd.read_sql_query(
                """SELECT * FROM med_supplier_prices 
                   ORDER BY med_id, supplier_id""",
                conn,
            )

            # Group by medication
            self.med_supplier_prices = {}
            for med_id, group in supplier_prices_df.groupby("med_id"):
                self.med_supplier_prices[int(med_id)] = group.to_dict("records")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def get_inventory_data(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str = "",
        category: str = "",
        supplier: str = "",
        stock_level: str = "",
    ) -> Dict[str, Any]:
        """Get paginated and filtered inventory data"""

        # Combine all data for inventory view
        inventory_items = []

        for med_id, med_data in self.medications.items():
            # Get supplier info
            supplier_info = self.suppliers.get(med_data["supplier_id"], {})

            # Get SKU metadata
            sku_info = self.sku_meta.get(med_id, {})

            # Get current stock from enhanced inventory data or fallback to calculation
            inventory_info = self.current_inventory.get(med_id, {})
            if inventory_info:
                total_stock = inventory_info.get("current_stock", 0)
                stock_category = inventory_info.get("stock_status", "Unknown")
            else:
                # Fallback: Calculate current stock across all stores
                total_stock = 0
                for (
                    store_id,
                    med_id_key,
                ), consumption in self.consumption_history.items():
                    if med_id_key == med_id:
                        total_stock += consumption.get("on_hand", 0)

                # Determine stock level category (fallback method)
                avg_daily = sku_info.get("avg_daily_pick", 0)
                if total_stock == 0:
                    stock_category = "Out of Stock"
                elif total_stock < avg_daily * 7:  # Less than week supply
                    stock_category = "Low"
                elif total_stock < avg_daily * 21:  # Less than 3 week supply
                    stock_category = "Medium"
                else:
                    stock_category = "High"

            # Get storage location
            storage_info = self.slot_assignments.get(med_id, {})
            location_name = "Unassigned"
            if "location_id" in storage_info:
                loc_id = storage_info["location_id"]
                for location in self.storage_locations:
                    if location.get("location_id") == loc_id:
                        location_name = f"Zone {location.get('zone_type', 'Unknown')}"
                        break

            # Get latest price
            price_info = self.drug_prices.get(med_id, {})

            item = {
                "med_id": med_id,
                "name": med_data.get("name", ""),
                "category": med_data.get("category", ""),
                "current_stock": total_stock,
                "stock_category": stock_category,
                # Keep both keys for frontend compatibility
                "supplier": supplier_info.get("name", "Unknown"),
                "supplier_name": supplier_info.get("name", "Unknown"),
                "supplier_status": supplier_info.get("status", "Unknown"),
                "pack_size": med_data.get("pack_size", 0),
                "shelf_life_days": med_data.get("shelf_life_days", 0),
                "avg_daily_pick": sku_info.get("avg_daily_pick", 0),
                "case_volume_m3": sku_info.get("case_volume_m3", 0),
                "case_weight_kg": sku_info.get("case_weight_kg", 0),
                "is_cold_chain": sku_info.get("is_cold_chain", 0),
                "is_controlled": sku_info.get("is_controlled", 0),
                "storage_location": location_name,
                "current_price": price_info.get("price_per_unit", 0),
                "avg_lead_time": supplier_info.get("avg_lead_time", 0),
                "last_delivery_date": supplier_info.get("last_delivery_date", ""),
                # Enhanced inventory fields
                "reorder_point": inventory_info.get("reorder_point", 0),
                "max_stock": inventory_info.get("max_stock", 0),
                "safety_stock": inventory_info.get("safety_stock", 0),
                "days_until_stockout": inventory_info.get("days_until_stockout", 0),
                "last_updated": inventory_info.get("last_updated", ""),
            }
            # Computed totals & fallbacks
            price = item["current_price"] or 0
            item["total_value"] = float((item["current_stock"] or 0) * price)
            if not item["days_until_stockout"]:
                avg_daily = item.get("avg_daily_pick") or 0
                item["days_until_stockout"] = (
                    int(item["current_stock"] / avg_daily) if avg_daily > 0 else 0
                )
            # Clean NaN values before adding to inventory items
            inventory_items.append(clean_nan_values(item))

        # Apply filters
        filtered_items = inventory_items

        if search:
            filtered_items = [
                item
                for item in filtered_items
                if search.lower() in item["name"].lower()
            ]

        if category:
            filtered_items = [
                item for item in filtered_items if item["category"] == category
            ]

        if supplier:
            filtered_items = [
                item for item in filtered_items if item["supplier_name"] == supplier
            ]

        if stock_level:
            filtered_items = [
                item for item in filtered_items if item["stock_category"] == stock_level
            ]

        # Sort by name
        filtered_items.sort(key=lambda x: x["name"])

        # Paginate
        total_items = len(filtered_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = filtered_items[start_idx:end_idx]

        return {
            "items": paginated_items,
            "total": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
            "page": page,
            "page_size": page_size,
        }

    def get_medication_details(self, med_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific medication"""
        if med_id not in self.medications:
            return {}

        med_data = self.medications[med_id]
        supplier_info = self.suppliers.get(med_data["supplier_id"], {})
        sku_info = self.sku_meta.get(med_id, {})
        storage_info = self.slot_assignments.get(med_id, {})
        price_info = self.drug_prices.get(med_id, {})

        # Get consumption history for this medication
        consumption_data = []
        for (store_id, med_id_key), consumption in self.consumption_history.items():
            if med_id_key == med_id:
                consumption_data.append(
                    {
                        "store_id": store_id,
                        "on_hand": consumption.get("on_hand", 0),
                        "qty_dispensed": consumption.get("qty_dispensed", 0),
                        "censored": consumption.get("censored", 0),
                        "date": consumption.get("date", ""),
                    }
                )

        # Get storage location details
        location_details = {}
        if "location_id" in storage_info:
            loc_id = storage_info["location_id"]
            for location in self.storage_locations:
                if location.get("location_id") == loc_id:
                    location_details = location
                    break

        # Get enhanced inventory data
        inventory_info = self.current_inventory.get(med_id, {})

        # Get batch information
        batch_data = self.batch_info.get(med_id, [])

        # Get purchase order history
        po_data = self.purchase_orders.get(med_id, [])

        # Get zone information for storage location
        zone_info = {}
        if "location_id" in storage_info:
            loc_id = storage_info["location_id"]
            for zone in self.warehouse_zones:
                location_ids = zone.get("location_ids", "").split(",")
                if str(loc_id) in [lid.strip() for lid in location_ids]:
                    zone_info = zone
                    break

        result = {
            **med_data,
            "supplier": supplier_info,
            "sku_meta": sku_info,
            "storage": {**storage_info, **location_details},
            "price": price_info,
            "consumption_by_store": consumption_data,
            "total_stock": sum(c["on_hand"] for c in consumption_data),
            # Enhanced data
            "inventory_status": inventory_info,
            "batch_info": batch_data,
            "purchase_orders": po_data,
            "zone_info": zone_info,
        }

        # Clean NaN values to prevent JSON serialization errors
        return clean_nan_values(result)

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options"""
        categories = set()
        suppliers = set()
        stock_levels = {"Low", "Medium", "High", "Out of Stock"}

        for med_data in self.medications.values():
            categories.add(med_data.get("category", ""))

        for supplier_data in self.suppliers.values():
            suppliers.add(supplier_data.get("name", ""))

        return {
            "categories": sorted(list(categories)),
            "suppliers": sorted(list(suppliers)),
            "stock_levels": sorted(list(stock_levels)),
        }

    def get_medication_consumption_history(
        self, med_id: int, days: int = 365
    ) -> Dict[str, Any]:
        """Get historical consumption data and forecast for a specific medication"""
        try:
            # Load full consumption history for this medication
            consumption_df = pd.read_csv(
                os.path.join(self.data_dir, "consumption_history.csv")
            )
            consumption_df["date"] = pd.to_datetime(consumption_df["date"])

            # Filter for specific medication
            med_data = consumption_df[consumption_df["med_id"] == med_id].copy()

            if med_data.empty:
                return {"error": "No consumption data found for this medication"}

            # Sort by date and get the latest `days` records
            med_data = med_data.sort_values("date").tail(days)

            # Aggregate consumption across all stores by date
            daily_consumption = (
                med_data.groupby("date")
                .agg({"qty_dispensed": "sum", "on_hand": "sum"})
                .reset_index()
            )

            # Rename columns for consistency
            daily_consumption = daily_consumption.rename(
                columns={"qty_dispensed": "consumption", "on_hand": "current_stock"}
            )

            # Generate simple forecast (moving average for next 30-60 days)
            recent_consumption = daily_consumption.tail(30)["consumption"].mean()

            # Create forecast data points
            last_date = daily_consumption["date"].max()
            forecast_dates = [last_date + timedelta(days=i) for i in range(1, 61)]

            # Simple forecast with some variation
            np.random.seed(42)  # For consistent results
            base_forecast = recent_consumption
            forecast_values = []

            for i, date in enumerate(forecast_dates):
                # Add some seasonal variation and noise
                seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * i / 7)  # Weekly pattern
                noise = np.random.normal(0, 0.1)
                forecast_value = max(0, base_forecast * seasonal_factor * (1 + noise))
                forecast_values.append(forecast_value)

            # Calculate statistics
            avg_daily_consumption = daily_consumption["consumption"].mean()
            current_stock = (
                daily_consumption["current_stock"].iloc[-1]
                if len(daily_consumption) > 0
                else 0
            )
            days_until_stockout = (
                int(current_stock / avg_daily_consumption)
                if avg_daily_consumption > 0
                else 999
            )

            # Format data for chart
            historical_data = []
            for _, row in daily_consumption.iterrows():
                historical_data.append(
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "consumption": float(row["consumption"]),
                        "stock": float(row["current_stock"]),
                        "type": "historical",
                    }
                )

            forecast_data = []
            for i, date in enumerate(forecast_dates):
                forecast_data.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "consumption": float(forecast_values[i]),
                        "stock": max(0, current_stock - sum(forecast_values[: i + 1])),
                        "type": "forecast",
                    }
                )

            result = {
                "med_id": med_id,
                "historical_data": historical_data,
                "forecast_data": forecast_data,
                "statistics": {
                    "avg_daily_consumption": float(avg_daily_consumption),
                    "current_stock": float(current_stock),
                    "days_until_stockout": days_until_stockout,
                    "forecast_period_days": 60,
                    "data_period_days": len(daily_consumption),
                },
            }

            return clean_nan_values(result)

        except Exception as e:
            return {"error": f"Failed to load consumption history: {str(e)}"}

    def get_suppliers(self) -> List[Dict[str, Any]]:
        """Get all suppliers with their details"""
        suppliers_list = []
        for supplier_id, supplier_data in self.suppliers.items():
            supplier_dict = {"supplier_id": supplier_id, **supplier_data}
            suppliers_list.append(supplier_dict)

        # Sort by supplier_id for consistent ordering
        suppliers_list.sort(key=lambda x: x["supplier_id"])
        return clean_nan_values(suppliers_list)

    def get_medication_supplier_prices(self, med_id: int) -> Dict[str, Any]:
        """Get all supplier prices for a medication with supplier details"""
        prices = []

        # Get medication details
        med = self.medications.get(med_id)
        if not med:
            return {"prices": []}

        # Get supplier-specific prices from database
        conn = self.get_connection()
        query = """
            SELECT msp.*, s.name as supplier_name, s.avg_lead_time, s.status as supplier_status
            FROM med_supplier_prices msp
            JOIN suppliers s ON msp.supplier_id = s.supplier_id
            WHERE msp.med_id = ?
            ORDER BY msp.supplier_id
        """

        df = pd.read_sql_query(query, conn, params=(med_id,))

        if not df.empty:
            for _, row in df.iterrows():
                prices.append(
                    {
                        "supplier_id": row["supplier_id"],
                        "supplier_name": row["supplier_name"],
                        "price_per_unit": row["price_per_unit"],
                        "avg_lead_time": row["avg_lead_time"],
                        "supplier_status": row["supplier_status"],
                        "valid_from": row["valid_from"],
                    }
                )
        else:
            # Fallback to base price for primary supplier if no specific prices
            base_price = self.drug_prices.get(med_id, {}).get("price_per_unit", 0)
            primary_supplier = self.suppliers.get(med["supplier_id"], {})
            if primary_supplier:
                prices.append(
                    {
                        "supplier_id": med["supplier_id"],
                        "supplier_name": primary_supplier.get("name", "Unknown"),
                        "price_per_unit": base_price,
                        "avg_lead_time": primary_supplier.get("avg_lead_time", 7),
                        "supplier_status": primary_supplier.get("status", "Unknown"),
                        "valid_from": None,
                    }
                )

        return clean_nan_values({"prices": prices})

    def save_purchase_order(self, po_data: Dict[str, Any]) -> str:
        """Save a purchase order to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")

            # Insert main PO record
            cursor.execute(
                """
                INSERT INTO purchase_orders (
                    po_id, po_number, supplier_id, supplier_name, status,
                    total_amount, created_at, updated_at, requested_delivery_date,
                    notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    po_data["po_id"],
                    po_data["po_number"],
                    po_data["supplier_id"],
                    po_data["supplier_name"],
                    po_data["status"],
                    po_data["total_amount"],
                    po_data["created_at"],
                    po_data["updated_at"],
                    po_data.get("requested_delivery_date"),
                    po_data.get("notes"),
                    po_data.get("created_by", "system"),
                ),
            )

            # Insert PO items
            for item in po_data["items"]:
                cursor.execute(
                    """
                    INSERT INTO purchase_order_items (
                        po_id, med_id, med_name, quantity, 
                        unit_price, total_price, pack_size
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        po_data["po_id"],
                        item["med_id"],
                        item["med_name"],
                        item["quantity"],
                        item["unit_price"],
                        item["total_price"],
                        item.get("pack_size", 0),
                    ),
                )

            conn.commit()

            # Add to in-memory cache
            self.purchase_orders[po_data["po_id"]] = po_data

            return po_data["po_id"]

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_purchase_order(self, po_id: str) -> Optional[Dict[str, Any]]:
        """Get a purchase order by ID"""
        conn = self.get_connection()

        try:
            # Query PO with supplier contact information
            po_query = """
                SELECT po.*, 
                       s.contact_name as contact_person,
                       s.email,
                       s.phone,
                       s.address as supplier_address
                FROM purchase_orders po
                LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
                WHERE po.po_id = ?
            """
            po_df = pd.read_sql_query(po_query, conn, params=(po_id,))

            if po_df.empty:
                return None

            po = po_df.iloc[0].to_dict()

            # Query items
            items_query = """
                SELECT * FROM purchase_order_items WHERE po_id = ?
            """
            items_df = pd.read_sql_query(items_query, conn, params=(po_id,))

            po["items"] = items_df.to_dict("records") if not items_df.empty else []

            return clean_nan_values(po)
        finally:
            conn.close()

    def list_purchase_orders(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all purchase orders, optionally filtered by status"""
        conn = self.get_connection()

        try:
            # Build query
            if status:
                query = """
                    SELECT po.*, 
                           COUNT(CASE WHEN poi.item_id IS NOT NULL THEN 1 END) as item_count,
                           SUM(poi.quantity) as total_quantity,
                           s.avg_lead_time,
                           datetime(po.created_at, '+' || COALESCE(s.avg_lead_time, 7) || ' days') as expected_delivery_date
                    FROM purchase_orders po
                    LEFT JOIN purchase_order_items poi ON po.po_id = poi.po_id
                    LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
                    WHERE po.status = ?
                    GROUP BY po.po_id
                    ORDER BY po.created_at DESC
                """
                params = (status,)
            else:
                query = """
                    SELECT po.*, 
                           COUNT(CASE WHEN poi.item_id IS NOT NULL THEN 1 END) as item_count,
                           SUM(poi.quantity) as total_quantity,
                           s.avg_lead_time,
                           datetime(po.created_at, '+' || COALESCE(s.avg_lead_time, 7) || ' days') as expected_delivery_date
                    FROM purchase_orders po
                    LEFT JOIN purchase_order_items poi ON po.po_id = poi.po_id
                    LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
                    GROUP BY po.po_id
                    ORDER BY po.created_at DESC
                """
                params = ()

            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                return []

            pos = df.to_dict("records")
            return clean_nan_values(pos)
        finally:
            conn.close()

    def __del__(self):
        """Close database connection when object is destroyed"""
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()
