"""
API routes for inventory management
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add parent directory to path to import data_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader
from ai_agents.api_handler import AIPoHandler

# Initialize router
router = APIRouter()

# Global data loader instance
data_loader = DataLoader()

# Initialize AI PO handler
ai_po_handler = AIPoHandler(data_loader)

# Purchase orders are now stored in the database via data_loader


@router.get("/inventory")
async def get_inventory(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query("", description="Search term"),
    category: Optional[str] = Query("", description="Category filter"),
    supplier: Optional[str] = Query("", description="Supplier filter"),
    stock_level: Optional[str] = Query("", description="Stock level filter"),
):
    """Get paginated inventory data with filters"""
    try:
        result = data_loader.get_inventory_data(
            page=page,
            page_size=page_size,
            search=search,
            category=category,
            supplier=supplier,
            stock_level=stock_level,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/medication/{med_id}")
async def get_medication_details(med_id: int):
    """Get detailed information for a specific medication"""
    try:
        details = data_loader.get_medication_details(med_id)
        if not details:
            raise HTTPException(status_code=404, detail="Medication not found")
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters")
async def get_filter_options():
    """Get available filter options"""
    try:
        return data_loader.get_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/medication/{med_id}/consumption-history")
async def get_medication_consumption_history(
    med_id: int,
    days: int = Query(
        365, ge=30, le=730, description="Number of days of historical data"
    ),
):
    """Get historical consumption data and forecast for a specific medication"""
    try:
        result = data_loader.get_medication_consumption_history(med_id, days)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppliers")
async def list_suppliers():
    try:
        suppliers = data_loader.get_suppliers()
        return {"suppliers": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchase-orders")
async def list_purchase_orders():
    try:
        # Get POs from database
        all_pos = data_loader.list_purchase_orders()
        return {
            "purchase_orders": [
                {
                    "po_id": po["po_id"],
                    "po_number": po.get("po_number", po["po_id"]),
                    "supplier_id": po["supplier_id"],
                    "supplier_name": po["supplier_name"],
                    "status": po["status"],
                    "created_at": po["created_at"],
                    "total_lines": po.get("item_count", 0),
                    "total_amount": po.get("total_amount", 0),
                }
                for po in all_pos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchase-orders/{po_id}")
async def get_purchase_order(po_id: str):
    try:
        po = data_loader.get_purchase_order(po_id)
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        return po
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/purchase-orders")
async def create_purchase_orders(payload: dict):
    try:
        # Payload contract: {
        #   items: [{ med_id, total_quantity, allocations: [{ supplier_id, quantity, unit_price }] }],
        #   meta: { requested_delivery_date, notes, buyer }
        # }
        items = payload.get("items", [])
        meta = payload.get("meta", {})

        # Group allocations by supplier to create 1 PO per supplier
        supplier_to_lines = {}
        for item in items:
            med_id = int(item.get("med_id"))
            med_info = data_loader.medications.get(med_id, {})
            med_name = med_info.get("name", f"Medication {med_id}")
            pack_size = med_info.get("pack_size", 1)
            for alloc in item.get("allocations", []):
                supplier_id = int(alloc.get("supplier_id"))
                quantity = int(alloc.get("quantity", 0))
                unit_price = float(alloc.get("unit_price", 0))
                if quantity <= 0:
                    continue
                line = {
                    "med_id": med_id,
                    "med_name": med_name,
                    "quantity": quantity,
                    "pack_size": pack_size,
                    "unit_price": unit_price,
                    "total_price": quantity * unit_price,
                }
                supplier_to_lines.setdefault(supplier_id, []).append(line)

        created_pos = []
        now_iso = datetime.utcnow().isoformat() + "Z"

        # Generate unique PO number
        year = datetime.utcnow().year
        po_counter = len(data_loader.list_purchase_orders()) + 1

        for supplier_id, lines in supplier_to_lines.items():
            supplier = data_loader.suppliers.get(supplier_id, {})
            po_id = (
                f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
            )
            po_number = f"PO-{year}-{po_counter:05d}"

            total_amount = sum(line["total_price"] for line in lines)

            po_data = {
                "po_id": po_id,
                "po_number": po_number,
                "supplier_id": supplier_id,
                "supplier_name": supplier.get("name", f"Supplier {supplier_id}"),
                "status": "draft",
                "total_amount": total_amount,
                "created_at": now_iso,
                "updated_at": now_iso,
                "requested_delivery_date": meta.get("requested_delivery_date"),
                "notes": meta.get("notes"),
                "created_by": meta.get("buyer", "system"),
                "items": lines,
            }

            # Save to database
            data_loader.save_purchase_order(po_data)
            created_pos.append(po_data)
            po_counter += 1

        return {"created": [po["po_id"] for po in created_pos]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/medications/{med_id}/supplier-prices")
async def get_med_supplier_prices(med_id: int):
    try:
        med = data_loader.medications.get(med_id)
        if not med:
            raise HTTPException(status_code=404, detail="Medication not found")

        # Get supplier prices with details from database
        result = data_loader.get_medication_supplier_prices(med_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI PO Generation Endpoints


@router.post("/purchase-orders/generate-ai")
async def generate_po_with_ai(
    payload: Dict[str, Any], background_tasks: BackgroundTasks
):
    """Generate purchase orders using AI multi-agent system (async kickoff)"""
    try:
        medication_ids = payload.get("medication_ids", [])

        if not medication_ids:
            raise HTTPException(status_code=400, detail="No medications selected")

        # Start background generation and return session id immediately
        kick = ai_po_handler.start_generation_async(medication_ids, background_tasks)
        return kick

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchase-orders/ai-status/{session_id}")
async def get_ai_generation_status(session_id: str):
    """Check status of AI PO generation"""
    try:
        status = await ai_po_handler.get_status(session_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchase-orders/ai-result/{session_id}")
async def get_ai_generation_result(session_id: str):
    """Get result of completed AI PO generation"""
    try:
        result = await ai_po_handler.get_result(session_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/purchase-orders/create-from-ai")
async def create_po_from_ai_result(payload: Dict[str, Any]):
    """Create actual purchase orders from AI generation result"""
    try:
        ai_result = payload.get("ai_result", {})
        meta = payload.get("meta", {})

        # Transform AI result to PO format
        po_list = ai_po_handler.transform_to_po_format(ai_result)

        created_pos = []
        now_iso = datetime.utcnow().isoformat() + "Z"
        year = datetime.utcnow().year
        po_counter = len(data_loader.list_purchase_orders()) + 1

        for po_data in po_list:
            po_id = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}-AI"
            po_number = f"PO-{year}-{po_counter:05d}-AI"

            # Create PO record
            po_record = {
                "po_id": po_id,
                "po_number": po_number,
                "supplier_id": po_data["supplier_id"],
                "supplier_name": po_data["supplier_name"],
                "status": "draft",
                "total_amount": po_data["total_amount"],
                "created_at": now_iso,
                "updated_at": now_iso,
                "requested_delivery_date": meta.get("requested_delivery_date"),
                "notes": f"AI Generated - {meta.get('notes', '')}",
                "created_by": meta.get("buyer", "AI System"),
                "items": po_data["items"],
                "metadata": po_data.get("metadata", {}),
            }

            # Save to database
            data_loader.save_purchase_order(po_record)
            created_pos.append(po_record)
            po_counter += 1

        return {
            "created": [po["po_id"] for po in created_pos],
            "purchase_orders": created_pos,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/config-status")
async def get_ai_config_status():
    """Check if AI is properly configured"""
    try:
        from ai_agents.config import get_config

        config = get_config()

        has_api_key = bool(
            config.openai_api_key
            and config.openai_api_key != "your_openai_api_key_here"
        )

        return {
            "configured": has_api_key,
            "model": config.model_name if has_api_key else None,
            "features_enabled": {
                "forecasting": True,
                "adjustment": config.adjustment_factors_enabled,
                "order_splitting": config.enable_order_splitting,
                "caching": config.enable_cache,
            },
        }
    except Exception as e:
        return {"configured": False, "error": str(e)}
