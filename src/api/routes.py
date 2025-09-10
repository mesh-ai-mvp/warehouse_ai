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
from loguru import logger

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

# Logger for email flow - using loguru with context
email_logger = logger.bind(name="email")

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


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get inventory data using the same method as the inventory endpoint
        inventory_data = data_loader.get_inventory_data(page_size=100)
        medications = inventory_data["items"]
        
        # Calculate statistics
        total_medications = len(medications)
        
        low_stock_count = sum(
            1 for med in medications 
            if med["current_stock"] <= med["reorder_point"]
        )
        
        critical_stock_count = sum(
            1 for med in medications 
            if med["current_stock"] <= med["reorder_point"] * 0.5
        )
        
        total_value = sum(med["current_stock"] * med.get("current_price", 0) for med in medications)
        
        # For orders_today, we'll return 0 for now since PO tracking is not implemented
        orders_today = 0
        
        return {
            "total_medications": total_medications,
            "low_stock_count": low_stock_count,
            "critical_stock_count": critical_stock_count,
            "total_value": total_value,
            "orders_today": orders_today
        }
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
  :root {{ --bg:#f5f7fb; --card:#ffffff; --ink:#0f172a; --muted:#64748b; --accent:#2563eb; --soft:#eef2ff; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:760px; margin:0 auto; }}
  .card {{ background:var(--card); border-radius:12px; border:1px solid #e5e7eb; overflow:hidden; }}
  /* High-contrast header */
  .header {{ background:#0f172a; color:#ffffff; padding:20px 24px; }}
  .title {{ margin:0; font-size:20px; font-weight:800; letter-spacing:.2px; }}
  .subtitle {{ margin:6px 0 0 0; font-size:13px; color:#cbd5e1; }}
  .content {{ padding:20px 24px; }}
  .meta-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px; }}
  .meta {{ background:var(--soft); border:1px solid #e2e8f0; border-radius:8px; padding:10px 12px; }}
  .label {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }}
  .value {{ font-size:14px; font-weight:700; color:var(--ink); margin-top:3px; }}
  table {{ width:100%; border-collapse:separate; border-spacing:0; margin-top:6px; }}
  thead th {{ background: #eef2ff; color:#334155; border-top:1px solid #e5e7eb; border-bottom:1px solid #e5e7eb; font-size:12px; text-transform:uppercase; letter-spacing:.5px; padding:10px 12px; text-align:left; }}
  tbody tr:nth-child(odd) td {{ background:#fafafa; }}
  .cell {{ padding:10px 12px; border-bottom:1px solid #e9ecef; font-size:14px; color:#0f172a; }}
  .right {{ text-align:right; }}
  tfoot td {{ padding:12px; font-weight:800; }}
  .totals {{ display:flex; justify-content:flex-end; gap:16px; align-items:center; padding-top:8px; }}
  .totals-label {{ color:#334155; font-weight:700; }}
  .totals-amount {{ background: #eef2ff; color:#1e40af; border:1px solid #dbeafe; padding:8px 12px; border-radius:8px; font-weight:800; }}
  .footer {{ padding:14px 24px; background:#f8fafc; border-top:1px solid #e5e7eb; color:#64748b; font-size:12px; }}
  /* Remove outer glow/shadow entirely for a flat, professional look */
</style>
</head>
<body>
  <div class='wrap'>
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
        <table role='presentation' aria-label='Order Lines'>
          <thead>
            <tr><th>Medication</th><th class='right'>Quantity</th><th class='right'>Unit Price</th><th class='right'>Amount</th></tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
        <div class='totals'>
          <span class='totals-label'>Total</span>
          <span class='totals-amount'>${total:.2f}</span>
        </div>
        <div style='margin-top:12px; font-size:13px;'>
          <div class='label'>Notes</div>
          <div>{notes}</div>
        </div>
      </div>
      <div class='footer'>
        This is an automated request from the Inventory Management system. Please reply with confirmation and estimated delivery date.
      </div>
    </div>
  </div>
</body>
</html>
"""


def _smtp_settings() -> Dict[str, Any]:
    return {
        "host": os.getenv("SMTP_HOST", os.getenv("GMAIL_HOST", "smtp.zoho.com")),
        "port": int(os.getenv("SMTP_PORT", os.getenv("GMAIL_PORT", "465"))),
        "user": os.getenv("SMTP_USER", os.getenv("GMAIL_USER", "")),
        "password": os.getenv("SMTP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD", "")),
        "from_name": os.getenv("EMAIL_FROM_NAME", "Inventory Management"),
        "from_addr": os.getenv(
            "EMAIL_FROM_ADDRESS", os.getenv("SMTP_USER", os.getenv("GMAIL_USER", ""))
        ),
        "use_starttls": os.getenv("SMTP_STARTTLS", "false").lower() == "true",
        "use_ssl": os.getenv("SMTP_SSL", "true").lower() != "false",
    }


def _send_email_via_smtp(
    subject: str, html_body: str, to_email: str, bcc: Optional[str] = None
):
    cfg = _smtp_settings()
    if not cfg["user"] or not cfg["password"]:
        email_logger.error(
            "Email not configured: missing SMTP_USER/SMTP_PASSWORD (or GMAIL_*)"
        )
        raise HTTPException(
            status_code=500,
            detail="Email is not configured. Set SMTP_USER and SMTP_PASSWORD in .env",
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{cfg['from_name']} <{cfg['from_addr']}>"
    msg["To"] = to_email
    if bcc:
        msg["Bcc"] = bcc

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    email_logger.info(
        f"Email send start | host={cfg['host']} | port={cfg['port']} | to={to_email} | subject={subject}"
    )
    try:
        if cfg["use_starttls"]:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        elif cfg["use_ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        email_logger.info(f"Email send success | to={to_email} | subject={subject}")
    except smtplib.SMTPAuthenticationError as e:
        email_logger.exception(
            f"SMTP auth failed | host={cfg['host']} | user={cfg['user']} | error={e}"
        )
        raise HTTPException(
            status_code=500,
            detail="SMTP authentication failed. Check SMTP_USER/SMTP_PASSWORD and 2FA/app password settings.",
        )
    except Exception as e:
        email_logger.exception(
            f"Email send failed | host={cfg['host']} | to={to_email} | error={e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/purchase-orders/send-emails")
async def send_po_emails(payload: Dict[str, Any]):
    """Draft and send HTML PO request emails to all involved suppliers before PO submission."""
    try:
        items = payload.get("items", [])
        meta = payload.get("meta", {})
        email_logger.info(f"Pre-submit email flow start | items={len(items)}")

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
            email_logger.info("Pre-submit email flow: no suppliers to notify")
            return {"sent": 0}

        fallback_to = os.getenv("SUPPLIER_FALLBACK_EMAIL")
        bcc = os.getenv("EMAIL_BCC")

        sent_count = 0
        for supplier_id, lines in supplier_to_lines.items():
            supplier = data_loader.suppliers.get(supplier_id, {})
            supplier_name = supplier.get("name", f"Supplier {supplier_id}")
            to_email = (
                supplier.get("email")
                or fallback_to
                or f"{_slugify(supplier_name)}@example.com"
            )
            subject = f"Purchase Order Request - {supplier_name}"
            email_logger.info(
                f"Pre-submit email: composing | supplier_id={supplier_id} | supplier={supplier_name} | to={to_email} | lines={len(lines)}"
            )
            html_body = _render_supplier_email_html(supplier_name, lines, meta)
            _send_email_via_smtp(subject, html_body, to_email, bcc=bcc)
            sent_count += 1

        email_logger.info(
            f"Pre-submit email flow success | suppliers_notified={sent_count}"
        )
        return {"sent": sent_count}

    except HTTPException:
        raise
    except Exception as e:
        email_logger.exception(f"Pre-submit email flow failed: {e}")
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
        email_logger.info(f"AI-create email flow start | suppliers={len(po_list)}")
        for po_data in po_list:
            supplier_id = po_data["supplier_id"]
            supplier_name = po_data["supplier_name"]
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
            to_email = (
                data_loader.suppliers.get(supplier_id, {}).get("email")
                or fallback_to
                or f"{_slugify(supplier_name)}@example.com"
            )
            subject = f"Purchase Order Request - {supplier_name}"
            email_logger.info(
                f"AI-create email: composing | supplier_id={supplier_id} | supplier={supplier_name} | to={to_email} | lines={len(lines)}"
            )
            _send_email_via_smtp(subject, html_body, to_email, bcc=bcc)
        email_logger.info("AI-create email flow success")

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
        email_logger.exception(f"AI-create email flow failed: {e}")
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
