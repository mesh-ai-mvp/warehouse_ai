"""API handler for AI PO generation"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException

from .config import get_config
from .logger import api_logger as logger
from .workflow import POGenerationWorkflow


class AIPoHandler:
    """Handles AI PO generation API requests"""

    def __init__(self, data_loader):
        logger.info("Initializing AIPoHandler")
        self.data_loader = data_loader
        self.workflow = POGenerationWorkflow()
        self.config = get_config()

        # Store for tracking active generations
        self.active_sessions = {}

        # Ensure data is loaded if not already
        if not self.data_loader.medications:
            logger.debug("Medications not loaded, attempting to load data")
            try:
                self.data_loader.load_all_data()
                logger.info(
                    f"Successfully loaded {len(self.data_loader.medications)} medications"
                )
            except Exception as e:
                logger.error(f"Failed to load data in AIPoHandler: {e}")

    async def generate_po(
        self,
        medication_ids: List[int],
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, Any]:
        """Generate PO using AI agents synchronously (existing behavior)"""

        logger.info(
            f"Starting AI PO generation for {len(medication_ids)} medications: {medication_ids}"
        )

        # Validate inputs
        if not medication_ids:
            logger.error("No medications selected")
            raise HTTPException(status_code=400, detail="No medications selected")

        if len(medication_ids) > 50:
            logger.error(f"Too many medications selected: {len(medication_ids)}")
            raise HTTPException(status_code=400, detail="Too many medications (max 50)")

        # Check OpenAI API key
        if (
            not self.config.openai_api_key
            or self.config.openai_api_key == "your_openai_api_key_here"
        ):
            logger.error("OpenAI API key not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file",
            )

        # Gather medication data
        logger.info("Gathering medication data")
        medications = []
        current_stock = {}
        consumption_history = {}

        for med_id in medication_ids:
            logger.debug(f"Processing medication ID: {med_id}")
            # Get medication details
            med_details = self.data_loader.get_medication_details(med_id)
            if not med_details:
                logger.warning(f"No details found for medication ID: {med_id}")
                continue

            # Convert numpy types to Python native types
            def to_native(val):
                import numpy as np
                import pandas as pd

                if isinstance(val, (np.integer, np.int64)):
                    return int(val)
                elif isinstance(val, (np.floating, np.float64)):
                    return float(val)
                elif pd.isna(val):
                    return None
                return val

            medications.append(
                {
                    "med_id": int(med_id),
                    "name": med_details.get("name"),
                    "category": med_details.get("category"),
                    "supplier_id": to_native(
                        med_details.get("supplier", {}).get("supplier_id")
                    ),
                    "pack_size": to_native(med_details.get("pack_size", 1)),
                    "current_stock": to_native(med_details.get("current_stock", 0)),
                    "reorder_point": to_native(med_details.get("reorder_point", 0)),
                    "safety_stock": to_native(med_details.get("safety_stock", 0)),
                    "max_stock": to_native(med_details.get("max_stock", float("inf"))),
                    "avg_daily_consumption": to_native(
                        med_details.get("avg_daily_pick", 0)
                    ),
                    "price": {
                        k: to_native(v) for k, v in med_details.get("price", {}).items()
                    },
                }
            )

            current_stock[med_id] = to_native(med_details.get("current_stock", 0))
            logger.debug(
                f"Medication {med_id}: {med_details.get('name')} - Stock: {current_stock[med_id]}"
            )

            # Get consumption history
            history = self.data_loader.get_medication_consumption_history(
                med_id, days=90
            )
            if not history.get("error"):
                consumption_history[med_id] = history
                logger.debug(f"Loaded consumption history for medication {med_id}")
            else:
                logger.warning(
                    f"Failed to load consumption history for {med_id}: {history.get('error')}"
                )

        if not medications:
            logger.error("No valid medications found after processing")
            raise HTTPException(status_code=404, detail="No valid medications found")

        logger.info(f"Successfully gathered data for {len(medications)} medications")

        # Get suppliers
        suppliers = self.data_loader.get_suppliers()
        logger.info(f"Loaded {len(suppliers)} suppliers")

        try:
            # Run workflow
            logger.info("Starting AI workflow execution")
            result = await self.workflow.generate_po(
                medications=medications,
                current_stock=current_stock,
                consumption_history=consumption_history,
                suppliers=suppliers,
            )
            logger.info(f"Workflow completed with status: {result.get('status')}")

            # Store session for tracking
            session_id = result.get("session_id")
            self.active_sessions[session_id] = {
                "status": result.get("status"),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at"),
                "result": result,
                "progress": result.get("progress", {}),
            }
            logger.info(
                f"Stored session {session_id} with {len(result.get('po_items', []))} PO items"
            )

            # Clean up old sessions (keep last 100)
            if len(self.active_sessions) > 100:
                oldest_sessions = sorted(
                    self.active_sessions.items(),
                    key=lambda x: x[1].get("created_at", ""),
                )[: len(self.active_sessions) - 100]
                for session_id, _ in oldest_sessions:
                    del self.active_sessions[session_id]

            return result

        except Exception as e:
            logger.error(f"AI PO generation failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"AI PO generation failed: {str(e)}"
            )

    # I will add an async starter that returns immediately and runs generation in background

    def start_generation_async(
        self,
        medication_ids: List[int],
        background_tasks: BackgroundTasks,
        days_forecast: int = 30,
    ) -> Dict[str, Any]:
        """Kick off generation in the background and return a session id immediately"""
        # Minimal validation here; the heavy validation will happen in the background task
        now_iso = datetime.utcnow().isoformat() + "Z"
        # Create tentative session placeholder; the real session_id will be produced by the workflow
        # We'll track by a temporary id until workflow completes; for simplicity, we reuse a generated id
        import uuid

        temp_session_id = str(uuid.uuid4())
        self.active_sessions[temp_session_id] = {
            "status": "processing",
            "created_at": now_iso,
            "updated_at": now_iso,
            "result": None,
            "progress": {
                "current_agent": "",
                "current_action": "Initializing",
                "percent_complete": 1,
                "steps_completed": [],
                "steps_remaining": ["forecast", "adjustment", "optimization"],
            },
            "medication_ids": medication_ids,
        }

        background_tasks.add_task(
            self._background_generate, temp_session_id, days_forecast
        )
        return {"session_id": temp_session_id, "status": "processing"}

    def _prepare_inputs(self, medication_ids: List[int]):
        """Prepare inputs for generation (shared by sync/async paths)"""
        medications = []
        current_stock = {}
        consumption_history = {}

        for med_id in medication_ids:
            med_details = self.data_loader.get_medication_details(med_id)
            if not med_details:
                continue

            def to_native(val):
                import numpy as np
                import pandas as pd

                if isinstance(val, (np.integer, np.int64)):
                    return int(val)
                elif isinstance(val, (np.floating, np.float64)):
                    return float(val)
                elif pd.isna(val):
                    return None
                return val

            medications.append(
                {
                    "med_id": int(med_id),
                    "name": med_details.get("name"),
                    "category": med_details.get("category"),
                    "supplier_id": to_native(
                        med_details.get("supplier", {}).get("supplier_id")
                    ),
                    "pack_size": to_native(med_details.get("pack_size", 1)),
                    "current_stock": to_native(med_details.get("current_stock", 0)),
                    "reorder_point": to_native(med_details.get("reorder_point", 0)),
                    "safety_stock": to_native(med_details.get("safety_stock", 0)),
                    "max_stock": to_native(med_details.get("max_stock", float("inf"))),
                    "avg_daily_consumption": to_native(
                        med_details.get("avg_daily_pick", 0)
                    ),
                    "price": {
                        k: to_native(v) for k, v in med_details.get("price", {}).items()
                    },
                }
            )

            current_stock[med_id] = to_native(med_details.get("current_stock", 0))

            history = self.data_loader.get_medication_consumption_history(
                med_id, days=90
            )
            if not history.get("error"):
                consumption_history[med_id] = history

        suppliers = self.data_loader.get_suppliers()
        return medications, current_stock, consumption_history, suppliers

    def _background_generate(self, temp_session_id: str, days_forecast: int = 30):
        """Background task that runs the workflow and stores the result"""
        try:
            entry = self.active_sessions.get(temp_session_id)
            if not entry:
                return
            medication_ids = entry.get("medication_ids", [])

            # Prepare inputs
            medications, current_stock, consumption_history, suppliers = (
                self._prepare_inputs(medication_ids)
            )

            # Define progress callback to update active_sessions in real-time
            def progress_callback(progress_data):
                logger.info(
                    f"🔄 Progress callback invoked: session={temp_session_id}, data={progress_data}"
                )
                if temp_session_id in self.active_sessions:
                    self.active_sessions[temp_session_id]["progress"] = progress_data
                    self.active_sessions[temp_session_id]["updated_at"] = (
                        datetime.utcnow().isoformat() + "Z"
                    )
                    logger.info(f"📊 Updated session progress: {progress_data}")
                else:
                    logger.warning(
                        f"⚠️ Session {temp_session_id} not found in active_sessions"
                    )

            # Run workflow (synchronously inside this task)
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.workflow.generate_po(
                    medications=medications,
                    current_stock=current_stock,
                    consumption_history=consumption_history,
                    suppliers=suppliers,
                    session_id=temp_session_id,  # CRITICAL: Use same session ID
                    progress_callback=progress_callback,
                    days_forecast=days_forecast,
                )
            )
            loop.close()

            # Store final result under the temporary session id for retrieval
            self.active_sessions[temp_session_id] = {
                "status": result.get("status"),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at"),
                "result": result,
                "progress": result.get("progress", {}),
            }
        except Exception as e:
            logger.error(f"Background generation failed: {e}", exc_info=True)
            now_iso = datetime.utcnow().isoformat() + "Z"
            self.active_sessions[temp_session_id] = {
                "status": "failed",
                "created_at": now_iso,
                "updated_at": now_iso,
                "result": {
                    "status": "failed",
                    "error": str(e),
                    "session_id": temp_session_id,
                },
                "progress": {
                    "percent_complete": 0,
                },
            }

    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of AI PO generation session"""

        # Check active sessions
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            return {
                "session_id": session_id,
                "status": session.get("status", "processing"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "has_result": session.get("result") is not None,
                "progress": session.get("progress", {}),
            }

        # Fallback to workflow status (POC)
        status = await self.workflow.get_status(session_id)
        return status

    async def get_result(self, session_id: str) -> Dict[str, Any]:
        """Get result of completed AI PO generation"""

        if session_id not in self.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = self.active_sessions[session_id]
        if "result" not in session or not session["result"]:
            raise HTTPException(status_code=202, detail="Generation still in progress")

        return session["result"]

    def transform_to_po_format(self, ai_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform AI result to PO creation format"""

        # Group items by supplier
        supplier_pos = {}

        for item in ai_result.get("po_items", []):
            supplier_id = item.get("supplier_id")
            if supplier_id not in supplier_pos:
                supplier_pos[supplier_id] = {
                    "supplier_id": supplier_id,
                    "supplier_name": item.get("supplier_name"),
                    "items": [],
                    "total_amount": 0,
                    "avg_lead_time": item.get("lead_time", 7),
                }

            supplier_pos[supplier_id]["items"].append(
                {
                    "med_id": item.get("med_id"),
                    "med_name": item.get("med_name"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "subtotal": item.get("subtotal"),
                }
            )

            supplier_pos[supplier_id]["total_amount"] += item.get("subtotal", 0)

        # Convert to list
        po_list = []
        for supplier_id, po_data in supplier_pos.items():
            po_list.append(
                {
                    "supplier_id": supplier_id,
                    "supplier_name": po_data["supplier_name"],
                    "items": po_data["items"],
                    "total_amount": po_data["total_amount"],
                    "metadata": {
                        "ai_generated": True,
                        "session_id": ai_result.get("session_id"),
                        "generation_time_ms": ai_result.get("metadata", {}).get(
                            "generation_time_ms", 0
                        ),
                        "avg_lead_time": po_data["avg_lead_time"],
                    },
                }
            )

        return po_list

    def clear_cache(self):
        """Clear workflow cache"""
        self.workflow.clear_cache()

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.active_sessions)
