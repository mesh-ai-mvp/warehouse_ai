"""
Data loader utilities for CSV files
"""

import pandas as pd
import os
import numpy as np
from typing import Dict, List, Any
from datetime import timedelta


def clean_nan_values(data):
    """Recursively clean NaN values from data structures for JSON serialization"""
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif data is None:
        return None
    elif isinstance(data, float):
        if pd.isna(data) or np.isnan(data) or np.isinf(data):
            return None
        else:
            return data
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
    def __init__(self, data_dir: str = None):
        # Get the directory where this script is located and find data directory
        if data_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Go up one level from src/
            self.data_dir = os.path.join(project_root, "data")
        else:
            self.data_dir = data_dir
        self.medications = {}
        self.suppliers = {}
        self.consumption_history = {}
        self.sku_meta = {}
        self.storage_locations = {}
        self.slot_assignments = {}
        self.drug_prices = {}
        # New data structures for enhanced data
        self.current_inventory = {}
        self.batch_info = {}
        self.warehouse_zones = {}
        self.purchase_orders = {}

    def load_all_data(self):
        """Load all CSV data into memory"""
        try:
            # Verify data directory exists
            if not os.path.exists(self.data_dir):
                raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

            # Load medications
            meds_df = pd.read_csv(os.path.join(self.data_dir, "medications.csv"))
            self.medications = meds_df.set_index("med_id").to_dict("index")

            # Load suppliers
            suppliers_df = pd.read_csv(os.path.join(self.data_dir, "suppliers.csv"))
            self.suppliers = suppliers_df.set_index("supplier_id").to_dict("index")

            # Load consumption history (get latest stock levels)
            consumption_df = pd.read_csv(
                os.path.join(self.data_dir, "consumption_history.csv")
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
            sku_df = pd.read_csv(os.path.join(self.data_dir, "sku_meta.csv"))
            self.sku_meta = sku_df.set_index("med_id").to_dict("index")

            # Load storage locations
            storage_df = pd.read_csv(
                os.path.join(self.data_dir, "storage_loc_simple.csv")
            )
            self.storage_locations = storage_df.to_dict("records")

            # Load slot assignments
            slots_df = pd.read_csv(os.path.join(self.data_dir, "slot_assignments.csv"))
            # Handle duplicate med_id entries by keeping the first occurrence
            slots_df = slots_df.drop_duplicates(subset=["med_id"], keep="first")
            self.slot_assignments = slots_df.set_index("med_id").to_dict("index")

            # Load drug prices (get latest prices)
            prices_df = pd.read_csv(os.path.join(self.data_dir, "drug_prices.csv"))
            prices_df["valid_from"] = pd.to_datetime(prices_df["valid_from"])
            latest_prices = prices_df.loc[
                prices_df.groupby("med_id")["valid_from"].idxmax()
            ]
            self.drug_prices = latest_prices.set_index("med_id").to_dict("index")

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
                print("Warning: current_inventory.csv not found, using fallback data")
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
                print("Warning: batch_info.csv not found, using fallback data")
                self.batch_info = {}

            try:
                # Load warehouse zones
                zones_df = pd.read_csv(
                    os.path.join(self.data_dir, "warehouse_zones.csv")
                )
                self.warehouse_zones = zones_df.to_dict("records")
            except FileNotFoundError:
                print("Warning: warehouse_zones.csv not found, using fallback data")
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
                print("Warning: purchase_orders.csv not found, using fallback data")
                self.purchase_orders = {}

        except Exception as e:
            print(f"Error loading data: {e}")
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
            "total_items": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
            "current_page": page,
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

    def get_medication_consumption_history(self, med_id: int, days: int = 365) -> Dict[str, Any]:
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
            daily_consumption = med_data.groupby("date").agg({
                "qty_dispensed": "sum",
                "on_hand": "sum"
            }).reset_index()
            
            # Rename columns for consistency
            daily_consumption = daily_consumption.rename(columns={
                "qty_dispensed": "consumption",
                "on_hand": "current_stock"
            })
            
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
            current_stock = daily_consumption["current_stock"].iloc[-1] if len(daily_consumption) > 0 else 0
            days_until_stockout = int(current_stock / avg_daily_consumption) if avg_daily_consumption > 0 else 999
            
            # Format data for chart
            historical_data = []
            for _, row in daily_consumption.iterrows():
                historical_data.append({
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "consumption": float(row["consumption"]),
                    "stock": float(row["current_stock"]),
                    "type": "historical"
                })
            
            forecast_data = []
            for i, date in enumerate(forecast_dates):
                forecast_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "consumption": float(forecast_values[i]),
                    "stock": max(0, current_stock - sum(forecast_values[:i+1])),
                    "type": "forecast"
                })
            
            result = {
                "med_id": med_id,
                "historical_data": historical_data,
                "forecast_data": forecast_data,
                "statistics": {
                    "avg_daily_consumption": float(avg_daily_consumption),
                    "current_stock": float(current_stock),
                    "days_until_stockout": days_until_stockout,
                    "forecast_period_days": 60,
                    "data_period_days": len(daily_consumption)
                }
            }
            
            return clean_nan_values(result)
            
        except Exception as e:
            return {"error": f"Failed to load consumption history: {str(e)}"}
