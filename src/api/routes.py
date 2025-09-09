"""
API routes for inventory management
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any, List
import sys
import os
from datetime import datetime
from uuid import uuid4
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
        # Ensure contact fields are present if available in DB
        for s in suppliers:
            supplier_id = s.get("supplier_id")
            src = data_loader.suppliers.get(supplier_id, {})
            for key in ("email", "contact_name", "phone", "address"):
                if key in src and key not in s:
                    s[key] = src.get(key)
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


# ============ Email Utilities ============


def _slugify(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "" for ch in name) or "supplier"


def _render_supplier_email_html(
    supplier_name: str, po_lines: List[Dict[str, Any]], meta: Dict[str, Any]
) -> str:
    total = sum(line["unit_price"] * line["quantity"] for line in po_lines)
    requested = meta.get("requested_delivery_date") or "-"
    buyer = meta.get("buyer") or "-"
    notes = meta.get("notes") or "-"

    rows = "".join(
        f"""
        <tr>
            <td class='cell'>{line["med_name"]}</td>
            <td class='cell right'>{line["quantity"]}</td>
            <td class='cell right'>${line["unit_price"]:.2f}</td>
            <td class='cell right'>${line["total_price"]:.2f}</td>
        </tr>
        """
        for line in po_lines
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Purchase Order Request</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; background:#f6f7f9; color:#111827; margin:0; padding:24px; }}
  .card {{ max-width:720px; margin:0 auto; background:#ffffff; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,0.08); overflow:hidden; }}
  .header {{ padding:20px 24px; background:linear-gradient(180deg,#f9fafb,#ffffff); border-bottom:1px solid #e5e7eb; }}
  .title {{ margin:0; font-size:18px; font-weight:700; }}
  .subtitle {{ margin:6px 0 0 0; font-size:13px; color:#6b7280; }}
  .content {{ padding:24px; }}
  .meta-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; }}
  .meta {{ background:#f9fafb; border:1px solid #eef0f2; border-radius:8px; padding:12px; }}
  .meta .label {{ font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:.5px; }}
  .meta .value {{ font-size:14px; font-weight:600; margin-top:4px; }}
  table {{ width:100%; border-collapse:separate; border-spacing:0; margin-top:8px; }}
  thead th {{ background:#f3f4f6; color:#374151; font-size:12px; text-transform:uppercase; letter-spacing:.5px; padding:10px 12px; border-top:1px solid #e5e7eb; border-bottom:1px solid #e5e7eb; text-align:left; }}
  .cell {{ padding:10px 12px; border-bottom:1px solid #eef0f2; font-size:14px; }}
  .right {{ text-align:right; }}
  tfoot td {{ padding:12px; font-weight:800; }}
  .footer {{ padding:16px 24px; background:#fafafa; border-top:1px solid #e5e7eb; color:#6b7280; font-size:12px; }}
</style>
</head>
<body>
  <div class='card'>
    <div class='header'>
      <h1 class='title'>Purchase Order Request</h1>
      <p class='subtitle'>Supplier: {supplier_name}</p>
    </div>
    <div class='content'>
      <div class='meta-grid'>
        <div class='meta'>
          <div class='label'>Requested Delivery Date</div>
          <div class='value'>{requested}</div>
        </div>
        <div class='meta'>
          <div class='label'>Buyer</div>
          <div class='value'>{buyer}</div>
        </div>
      </div>
      <table role='presentation'>
        <thead>
          <tr><th>Medication</th><th class='right'>Quantity</th><th class='right'>Unit Price</th><th class='right'>Amount</th></tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
        <tfoot>
          <tr><td colspan='3' class='right'>Total</td><td class='right'>${total:.2f}</td></tr>
        </tfoot>
      </table>
      <div style='margin-top:12px; font-size:13px;'>
        <div class='label'>Notes</div>
        <div>{notes}</div>
      </div>
    </div>
    <div class='footer'>
      This is an automated request from the Inventory Management system. Please reply with confirmation and estimated delivery date.
    </div>
  </div>
</body>
</html>
"""


def _send_email_via_gmail(
    subject: str, html_body: str, to_email: str, bcc: Optional[str] = None
):
    user = os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    from_name = os.getenv("EMAIL_FROM_NAME", "Inventory Management")
    if not user or not app_password:
        raise HTTPException(
            status_code=500,
            detail="Email is not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env",
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email
    if bcc:
        msg["Bcc"] = bcc

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(user, app_password)
        server.send_message(msg)


@router.post("/purchase-orders/send-emails")
async def send_po_emails(payload: Dict[str, Any]):
    """Draft and send HTML PO request emails to all involved suppliers before PO submission."""
    try:
        items = payload.get("items", [])
        meta = payload.get("meta", {})

        # Group allocations by supplier similar to PO creation
        supplier_to_lines: Dict[int, List[Dict[str, Any]]] = {}
        for item in items:
            med_id = int(item.get("med_id"))
            med_info = data_loader.medications.get(med_id, {})
            med_name = med_info.get("name", f"Medication {med_id}")
            for alloc in item.get("allocations", []):
                supplier_id = int(alloc.get("supplier_id"))
                quantity = int(alloc.get("quantity", 0))
                unit_price = float(alloc.get("unit_price", 0))
                if quantity <= 0:
                    continue
                supplier_to_lines.setdefault(supplier_id, []).append(
                    {
                        "med_id": med_id,
                        "med_name": med_name,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_price": quantity * unit_price,
                    }
                )

        if not supplier_to_lines:
            return {"sent": 0}

        fallback_to = os.getenv("SUPPLIER_FALLBACK_EMAIL")
        bcc = os.getenv("EMAIL_BCC")

        sent_count = 0
        for supplier_id, lines in supplier_to_lines.items():
            supplier = data_loader.suppliers.get(supplier_id, {})
            supplier_name = supplier.get("name", f"Supplier {supplier_id}")
            # Determine recipient email
            to_email = supplier.get("email")
            if not to_email:
                if fallback_to:
                    to_email = fallback_to
                else:
                    # Derive a plausible test email if none configured
                    to_email = f"{_slugify(supplier_name)}@example.com"

            subject = f"Purchase Order Request - {supplier_name}"
            html_body = _render_supplier_email_html(supplier_name, lines, meta)
            _send_email_via_gmail(subject, html_body, to_email, bcc=bcc)
            sent_count += 1

        return {"sent": sent_count}

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

        # Before saving, send emails to suppliers represented in po_list
        fallback_to = os.getenv("SUPPLIER_FALLBACK_EMAIL")
        bcc = os.getenv("EMAIL_BCC")
        for po_data in po_list:
            supplier_id = po_data["supplier_id"]
            supplier_name = po_data["supplier_name"]
            # Build lines format compatible with renderer
            lines = [
                {
                    "med_id": it["med_id"],
                    "med_name": it["med_name"],
                    "quantity": it["quantity"],
                    "unit_price": it["unit_price"],
                    "total_price": it["subtotal"],
                }
                for it in po_data["items"]
            ]
            html_body = _render_supplier_email_html(supplier_name, lines, meta)
            to_email = data_loader.suppliers.get(supplier_id, {}).get("email")
            if not to_email:
                to_email = fallback_to or f"{_slugify(supplier_name)}@example.com"
            _send_email_via_gmail(
                f"Purchase Order Request - {supplier_name}",
                html_body,
                to_email,
                bcc=bcc,
            )

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
