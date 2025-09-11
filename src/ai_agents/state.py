"""State management for multi-agent PO generation workflow"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


class MedicationData(BaseModel):
    """Medication information for PO generation"""

    med_id: int
    name: str
    current_stock: float
    reorder_point: float
    safety_stock: float
    max_stock: float
    avg_daily_consumption: float
    pack_size: int
    category: str
    supplier_id: int


class ConsumptionHistory(BaseModel):
    """Historical consumption data"""

    med_id: int
    daily_consumption: List[float]
    dates: List[str]
    avg_consumption: float
    trend: str  # increasing, decreasing, stable
    seasonality_factor: float


class ForecastData(BaseModel):
    """Forecast output from forecast agent"""

    med_id: int
    forecast_quantity: float
    forecast_months: int
    confidence_score: float
    method_used: str
    reasoning: str


class AdjustedQuantity(BaseModel):
    """Adjusted quantity from adjustment agent"""

    med_id: int
    original_quantity: float
    adjusted_quantity: float
    adjustment_factors: Dict[str, float]
    total_adjustment_factor: float
    reasoning: str


class SupplierAllocation(BaseModel):
    """Supplier allocation from supplier agent"""

    med_id: int
    allocations: List[
        Dict[str, Any]
    ]  # [{supplier_id, quantity, unit_price, lead_time}]
    total_cost: float
    avg_lead_time: float
    reasoning: str


class AgentReasoning(BaseModel):
    """Reasoning trace from an agent"""

    agent_name: str
    timestamp: str
    input_summary: str
    decision_points: List[str]
    output_summary: str
    confidence: float


class POGenerationState(TypedDict):
    """State shared across all agents in the workflow"""

    # Input data
    medications: List[Dict[str, Any]]  # Selected medications with details
    current_stock: Dict[int, float]  # Current inventory levels by med_id
    consumption_history: Dict[int, Dict[str, Any]]  # Historical consumption by med_id
    suppliers: List[Dict[str, Any]]  # Available suppliers

    # Agent outputs
    forecast_data: Dict[int, Dict[str, Any]]  # Forecast by med_id
    adjusted_quantities: Dict[int, Dict[str, Any]]  # Adjusted quantities by med_id
    supplier_allocations: Dict[int, Dict[str, Any]]  # Supplier allocations by med_id

    # Reasoning and metadata
    reasoning: Dict[str, List[Dict[str, Any]]]  # Agent reasoning traces
    metadata: Dict[str, Any]  # Additional context

    # Workflow control
    current_step: str  # Current workflow step
    status: str  # pending, processing, completed, failed
    error: Optional[str]  # Error message if failed
    session_id: str  # Unique session identifier
    created_at: str  # Timestamp
    updated_at: str  # Last update timestamp

    # Progress tracking
    progress: Dict[str, Any]  # Progress information for UI
    messages: List[Dict[str, Any]]  # Status messages for UI


class WorkflowProgress(BaseModel):
    """Progress tracking for UI updates"""

    current_agent: str = Field(default="")
    current_action: str = Field(default="")
    percent_complete: int = Field(default=0)
    steps_completed: List[str] = Field(default_factory=list)
    steps_remaining: List[str] = Field(default_factory=list)
    estimated_time_remaining: int = Field(default=0)  # seconds


def create_initial_state(
    medications: List[Dict[str, Any]],
    current_stock: Dict[int, float],
    consumption_history: Dict[int, Dict[str, Any]],
    suppliers: List[Dict[str, Any]],
    session_id: str,
) -> POGenerationState:
    """Create initial state for workflow"""

    now = datetime.utcnow().isoformat()

    return POGenerationState(
        # Input data
        medications=medications,
        current_stock=current_stock,
        consumption_history=consumption_history,
        suppliers=suppliers,
        # Agent outputs (empty initially)
        forecast_data={},
        adjusted_quantities={},
        supplier_allocations={},
        # Reasoning and metadata
        reasoning={"forecast_agent": [], "adjustment_agent": [], "supplier_agent": []},
        metadata={"user_preferences": {}, "constraints": {}, "context": {}},
        # Workflow control
        current_step="initialization",
        status="pending",
        error=None,
        session_id=session_id,
        created_at=now,
        updated_at=now,
        # Progress tracking
        progress={
            "current_agent": "",
            "current_action": "Initializing workflow",
            "percent_complete": 0,
            "steps_completed": [],
            "steps_remaining": ["forecast", "adjustment", "supplier"],
            "estimated_time_remaining": 10,
        },
        messages=[],
    )


def update_progress(
    state: POGenerationState,
    agent_name: str,
    action: str,
    percent_complete: int,
    message: Optional[str] = None,
) -> POGenerationState:
    """Update workflow progress"""

    state["progress"]["current_agent"] = agent_name
    state["progress"]["current_action"] = action
    state["progress"]["percent_complete"] = percent_complete
    state["updated_at"] = datetime.utcnow().isoformat()

    if message:
        state["messages"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent_name,
                "message": message,
                "type": "info",
            }
        )

    # Update steps completed/remaining
    if agent_name == "forecast_agent" and percent_complete >= 100:
        state["progress"]["steps_completed"].append("forecast")
        if "forecast" in state["progress"]["steps_remaining"]:
            state["progress"]["steps_remaining"].remove("forecast")
    elif agent_name == "adjustment_agent" and percent_complete >= 100:
        state["progress"]["steps_completed"].append("adjustment")
        if "adjustment" in state["progress"]["steps_remaining"]:
            state["progress"]["steps_remaining"].remove("adjustment")
    elif agent_name == "supplier_agent" and percent_complete >= 100:
        state["progress"]["steps_completed"].append("supplier")
        if "supplier" in state["progress"]["steps_remaining"]:
            state["progress"]["steps_remaining"].remove("supplier")

    # Estimate remaining time
    total_steps = 3
    completed_steps = len(state["progress"]["steps_completed"])
    avg_time_per_step = 3  # seconds
    state["progress"]["estimated_time_remaining"] = (
        total_steps - completed_steps
    ) * avg_time_per_step

    return state


def add_reasoning(
    state: POGenerationState, agent_name: str, reasoning: AgentReasoning
) -> POGenerationState:
    """Add agent reasoning to state"""

    state["reasoning"][agent_name].append(reasoning.model_dump())
    state["updated_at"] = datetime.utcnow().isoformat()

    return state


def finalize_state(
    state: POGenerationState, success: bool = True, error: Optional[str] = None
) -> POGenerationState:
    """Finalize the workflow state"""

    state["status"] = "completed" if success else "failed"
    state["error"] = error
    state["updated_at"] = datetime.utcnow().isoformat()
    state["progress"]["percent_complete"] = (
        100 if success else state["progress"]["percent_complete"]
    )

    if success:
        state["messages"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "system",
                "message": "PO generation completed successfully",
                "type": "success",
            }
        )
    else:
        state["messages"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "system",
                "message": f"PO generation failed: {error}",
                "type": "error",
            }
        )

    return state
