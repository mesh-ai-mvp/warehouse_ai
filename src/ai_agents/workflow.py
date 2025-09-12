"""LangGraph workflow orchestration for multi-agent PO generation"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .agents import AdjustmentAgent, ForecastAgent, SupplierAgent
from .config import get_config
from .logger import workflow_logger as logger
from .state import (
    POGenerationState,
    create_initial_state,
    finalize_state,
    update_progress,
)


class POGenerationWorkflow:
    """Orchestrates the multi-agent workflow for PO generation"""

    def __init__(self):
        logger.info("Initializing POGenerationWorkflow")
        self.config = get_config()
        self.forecast_agent = ForecastAgent()
        self.adjustment_agent = AdjustmentAgent()
        self.supplier_agent = SupplierAgent()
        self.workflow = self._build_workflow()

        # Cache for storing results temporarily
        self._cache = {}
        self._cache_ttl = self.config.cache_ttl_seconds

        # Progress callback for real-time updates
        self._progress_callback = None

        logger.info("POGenerationWorkflow initialized successfully")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        logger.debug("Building LangGraph workflow")

        # Create workflow with state type
        workflow = StateGraph(POGenerationState)

        # Add nodes (agents)
        workflow.add_node("forecast", self._run_forecast)
        workflow.add_node("adjust", self._run_adjust)
        workflow.add_node("supplier", self._run_supplier)
        workflow.add_node("finalize", self._finalize_workflow)

        # Define workflow edges (sequential flow)
        workflow.set_entry_point("forecast")
        workflow.add_edge("forecast", "adjust")
        workflow.add_edge("adjust", "supplier")
        workflow.add_edge("supplier", "finalize")
        workflow.add_edge("finalize", END)

        # Compile workflow with memory saver for state persistence
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def generate_po(
        self,
        medications: List[Dict[str, Any]],
        current_stock: Dict[int, float],
        consumption_history: Dict[int, Dict[str, Any]],
        suppliers: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        days_forecast: int = 30,
    ) -> Dict[str, Any]:
        """Generate purchase orders using multi-agent workflow"""

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid4())

        # Store progress callback for use in workflow nodes
        self._progress_callback = progress_callback

        logger.info(f"Starting PO generation for session {session_id}")
        logger.debug(
            f"Processing {len(medications)} medications with {len(suppliers)} suppliers"
        )

        # Check cache if enabled
        cache_key = self._get_cache_key(medications)
        if self.config.enable_cache and cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.info(f"Using cached result for session {session_id}")
                return cached_result["data"]

        # Create initial state
        logger.debug("Creating initial state")
        initial_state = create_initial_state(
            medications=medications,
            current_stock=current_stock,
            consumption_history=consumption_history,
            suppliers=suppliers,
            session_id=session_id,
            days_forecast=days_forecast,
        )

        try:
            # Update status
            initial_state["status"] = "processing"
            initial_state = update_progress(
                initial_state, "system", "Starting AI PO generation", 5
            )

            # Run workflow with timeout
            config = {"configurable": {"thread_id": session_id}}
            logger.info(
                f"Executing workflow with timeout of {self.config.request_timeout}s"
            )

            # Execute workflow
            final_state = await asyncio.wait_for(
                self._run_workflow(initial_state, config),
                timeout=self.config.request_timeout,
            )
            logger.info(f"Workflow execution completed for session {session_id}")

            # Transform to API response format
            result = self._transform_to_response(final_state)
            logger.debug(f"Generated {len(result.get('po_items', []))} PO items")

            # Save to database
            self._save_ai_session_to_db(final_state, result)

            # Cache result if enabled
            if self.config.enable_cache:
                self._cache[cache_key] = {
                    "data": result,
                    "timestamp": datetime.utcnow(),
                }
                logger.debug("Result cached for future use")

            return result

        except asyncio.TimeoutError:
            logger.error(
                f"Workflow timeout for session {session_id} after {self.config.request_timeout}s"
            )
            error_state = finalize_state(
                initial_state,
                success=False,
                error="Workflow timeout - generation took too long",
            )
            return self._transform_to_response(error_state)

        except Exception as e:
            logger.error(
                f"Workflow error for session {session_id}: {str(e)}", exc_info=True
            )
            error_state = finalize_state(
                initial_state, success=False, error=f"Workflow error: {str(e)}"
            )
            return self._transform_to_response(error_state)

    async def _run_workflow(
        self, initial_state: POGenerationState, config: Dict[str, Any]
    ) -> POGenerationState:
        """Execute the workflow asynchronously"""

        # Run workflow steps with progress updates
        state = initial_state

        # Forecast step
        state = update_progress(
            state, "forecast_agent", "Running demand forecasting", 15
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback at forecast start (15%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning("⚠️ No progress callback available at forecast start")

        # Execute the entire LangGraph workflow which will call individual node methods
        state = await asyncio.to_thread(self.workflow.invoke, state, config)

        # Ensure final completion
        state = update_progress(
            state, "finalize", "Purchase order generation complete", 100
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback at workflow completion (100%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning("⚠️ No progress callback available at workflow completion")

        return state

    def _run_forecast(self, state: POGenerationState) -> POGenerationState:
        state = update_progress(
            state, "forecast_agent", "Analyzing consumption patterns", 25
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback in forecast node (25%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning("⚠️ No progress callback available in forecast node (25%)")

        state = self.forecast_agent(state)
        state = update_progress(
            state, "forecast_agent", "Forecast generation complete", 33
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback in forecast node completion (33%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning(
                "⚠️ No progress callback available in forecast node completion (33%)"
            )

        return state

    def _run_adjust(self, state: POGenerationState) -> POGenerationState:
        state = update_progress(
            state, "adjustment_agent", "Applying US context adjustments", 50
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback in adjustment node (50%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning("⚠️ No progress callback available in adjustment node (50%)")

        state = self.adjustment_agent(state)
        state = update_progress(state, "adjustment_agent", "Adjustment complete", 66)
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback in adjustment node completion (66%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning(
                "⚠️ No progress callback available in adjustment node completion (66%)"
            )

        return state

    def _run_supplier(self, state: POGenerationState) -> POGenerationState:
        state = update_progress(
            state, "supplier_agent", "Optimizing supplier selection", 85
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback in supplier node (85%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning("⚠️ No progress callback available in supplier node (85%)")

        state = self.supplier_agent(state)
        state = update_progress(
            state, "supplier_agent", "Supplier optimization complete", 95
        )
        if self._progress_callback:
            logger.info(
                f"🔄 Invoking progress callback in supplier node completion (95%): {state['progress']}"
            )
            self._progress_callback(state["progress"])
        else:
            logger.warning(
                "⚠️ No progress callback available in supplier node completion (95%)"
            )

        return state

    def _finalize_workflow(self, state: POGenerationState) -> POGenerationState:
        """Finalize the workflow and prepare results"""

        # Check if all required data is present
        has_forecast = bool(state.get("forecast_data"))
        has_adjustments = bool(state.get("adjusted_quantities"))
        has_allocations = bool(state.get("supplier_allocations"))

        if has_forecast and has_adjustments and has_allocations:
            state = finalize_state(state, success=True)
            state = update_progress(
                state, "system", "PO generation completed successfully", 100
            )
            if self._progress_callback:
                logger.info(
                    f"🔄 Invoking progress callback in finalize (success 100%): {state['progress']}"
                )
                self._progress_callback(state["progress"])
            else:
                logger.warning("⚠️ No progress callback available in finalize (success)")
        else:
            missing = []
            if not has_forecast:
                missing.append("forecast")
            if not has_adjustments:
                missing.append("adjustments")
            if not has_allocations:
                missing.append("allocations")

            state = finalize_state(
                state,
                success=False,
                error=f"Missing required data: {', '.join(missing)}",
            )
            if self._progress_callback:
                logger.info(
                    f"🔄 Invoking progress callback in finalize (error): {state['progress']}"
                )
                self._progress_callback(state["progress"])
            else:
                logger.warning("⚠️ No progress callback available in finalize (error)")

        return state

    def _transform_to_response(self, state: POGenerationState) -> Dict[str, Any]:
        """Transform workflow state to API response format"""

        # Build PO items from allocations
        po_items = []

        for med_id, allocation_data in state.get("supplier_allocations", {}).items():
            med = next((m for m in state["medications"] if m["med_id"] == med_id), None)
            if not med:
                continue

            for alloc in allocation_data.get("allocations", []):
                po_items.append(
                    {
                        "med_id": med_id,
                        "med_name": med.get("name"),
                        "supplier_id": alloc.get("supplier_id"),
                        "supplier_name": alloc.get("supplier_name"),
                        "quantity": alloc.get("quantity"),
                        "unit_price": alloc.get("unit_price"),
                        "lead_time": alloc.get("lead_time"),
                        "subtotal": alloc.get("subtotal"),
                    }
                )

        # Build reasoning summary
        reasoning_summary = {}
        for agent_name, traces in state.get("reasoning", {}).items():
            if traces:
                latest = traces[-1] if isinstance(traces, list) else traces
                reasoning_summary[agent_name] = {
                    "summary": latest.get("output_summary", ""),
                    "confidence": latest.get("confidence", 0),
                    "decision_points": latest.get("decision_points", []),
                }

        # Build response
        response = {
            "session_id": state.get("session_id"),
            "status": state.get("status"),
            "error": state.get("error"),
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
            "po_items": po_items,
            "forecast_data": state.get("forecast_data", {}),
            "adjusted_quantities": state.get("adjusted_quantities", {}),
            "supplier_allocations": state.get("supplier_allocations", {}),
            "reasoning": reasoning_summary,
            "progress": state.get("progress", {}),
            "messages": state.get("messages", []),
            "metadata": {
                "total_items": len(po_items),
                "total_cost": sum(item["subtotal"] for item in po_items),
                "avg_lead_time": (
                    sum(item["lead_time"] * item["quantity"] for item in po_items)
                    / sum(item["quantity"] for item in po_items)
                    if po_items
                    else 0
                ),
                "ai_generated": True,
                "generation_time_ms": self._calculate_generation_time(state),
            },
        }

        return response

    def _get_cache_key(self, medications: List[Dict[str, Any]]) -> str:
        """Generate cache key from medications"""

        # Sort medication IDs for consistent key
        med_ids = sorted([m["med_id"] for m in medications])
        return f"po_gen_{':'.join(map(str, med_ids))}"

    def _is_cache_valid(self, cached_item: Dict[str, Any]) -> bool:
        """Check if cached item is still valid"""

        if not cached_item:
            return False

        timestamp = cached_item.get("timestamp")
        if not timestamp:
            return False

        age = (datetime.utcnow() - timestamp).total_seconds()
        return age < self._cache_ttl

    def _calculate_generation_time(self, state: POGenerationState) -> int:
        """Calculate generation time in milliseconds"""

        try:
            created = datetime.fromisoformat(
                state.get("created_at", "").replace("Z", "+00:00")
            )
            updated = datetime.fromisoformat(
                state.get("updated_at", "").replace("Z", "+00:00")
            )
            delta = updated - created
            return int(delta.total_seconds() * 1000)
        except Exception:
            return 0

    def clear_cache(self):
        """Clear the workflow cache"""
        self._cache.clear()

    def _save_ai_session_to_db(self, state: POGenerationState, result: Dict[str, Any]):
        """Save AI generation session to database"""
        try:
            # Get database path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            db_path = os.path.join(project_root, "poc_supplychain.db")

            if not os.path.exists(db_path):
                logger.warning(
                    f"Database not found at {db_path}, skipping AI session save"
                )
                return

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Prepare medication IDs
                medication_ids = [
                    str(m["med_id"]) for m in state.get("medications", [])
                ]

                # Prepare agent outputs
                agent_outputs = {
                    "forecast_data": state.get("forecast_data", {}),
                    "adjusted_quantities": state.get("adjusted_quantities", {}),
                    "supplier_allocations": state.get("supplier_allocations", {}),
                    "po_items": result.get("po_items", []),
                    "metadata": result.get("metadata", {}),
                }

                # Prepare reasoning
                reasoning_data = state.get("reasoning", {})

                # Calculate generation time
                generation_time = self._calculate_generation_time(state)

                # Insert into ai_po_sessions table
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ai_po_sessions (
                        session_id, created_at, updated_at, medications, 
                        agent_outputs, reasoning, status, error, generation_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        state.get("session_id"),
                        state.get("created_at"),
                        state.get("updated_at"),
                        json.dumps(medication_ids),
                        json.dumps(agent_outputs),
                        json.dumps(reasoning_data),
                        state.get("status"),
                        state.get("error"),
                        generation_time,
                    ),
                )

                conn.commit()
                logger.info(f"Saved AI session {state.get('session_id')} to database")

        except Exception as e:
            logger.error(f"Failed to save AI session to database: {str(e)}")

    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a workflow session"""

        # For now, return a simple status
        # In production, this would query the workflow state
        return {
            "session_id": session_id,
            "status": "unknown",
            "message": "Status tracking not implemented in POC",
        }
