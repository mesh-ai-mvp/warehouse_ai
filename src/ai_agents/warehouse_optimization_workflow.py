"""
Warehouse Optimization Workflow using LangGraph
Orchestrates multiple AI agents for comprehensive warehouse analysis and optimization
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
import asyncio
from datetime import datetime
from loguru import logger
import hashlib
import json

# Import warehouse optimization agents
from .warehouse_chaos_analyzer import WarehouseChaosAnalyzer
from .placement_optimizer import PlacementOptimizer
from .compliance_monitor import ComplianceMonitor
from .movement_pattern_analyzer import MovementPatternAnalyzer
from .optimization_recommender import OptimizationRecommender


class WarehouseOptimizationState(TypedDict):
    """State for warehouse optimization workflow"""

    # Input parameters
    analysis_type: str  # 'full', 'placement', 'compliance', 'movement', 'quick'
    warehouse_data: Dict[str, Any]
    parameters: Dict[str, Any]

    # Chaos analysis results
    chaos_metrics: Dict[str, Any]
    fragmentation_data: Dict[str, Any]
    velocity_mismatches: Dict[str, Any]
    fifo_violations: List[Dict]
    warehouse_layout: Dict[str, Any]

    # Agent outputs
    chaos_analysis: Dict[str, Any]
    placement_optimization: Dict[str, Any]
    compliance_report: Dict[str, Any]
    movement_analysis: Dict[str, Any]

    # Final recommendations
    recommendations: Dict[str, Any]
    executive_summary: Dict[str, Any]
    implementation_roadmap: Dict[str, Any]
    roi_analysis: Dict[str, Any]
    success_metrics: Dict[str, Any]

    # Workflow metadata
    optimization_score: float
    processing_stage: str
    progress_percentage: int
    error: Optional[str]
    timestamp: str
    processing_time_ms: Optional[int]
    cache_key: Optional[str]


class WarehouseOptimizationWorkflow:
    """Orchestrates AI agents for warehouse optimization analysis"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize workflow with LLM and agents"""
        # Use provided LLM or create default
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )

        # Initialize all agents
        self.chaos_analyzer = WarehouseChaosAnalyzer(self.llm)
        self.placement_optimizer = PlacementOptimizer(self.llm)
        self.compliance_monitor = ComplianceMonitor(self.llm)
        self.movement_analyzer = MovementPatternAnalyzer(self.llm)
        self.optimization_recommender = OptimizationRecommender(self.llm)

        # Build workflow graph
        self.workflow = self._build_workflow()

        # Cache for results (TTL: 1 hour)
        self.cache = {}
        self.cache_ttl = 3600  # seconds

        logger.info("WarehouseOptimizationWorkflow initialized")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create workflow with our state type
        workflow = StateGraph(WarehouseOptimizationState)

        # Add nodes (each node is a step in the workflow)
        workflow.add_node("prepare_data", self._prepare_data)
        workflow.add_node("analyze_chaos", self._analyze_chaos)
        workflow.add_node("optimize_placement", self._optimize_placement)
        workflow.add_node("check_compliance", self._check_compliance)
        workflow.add_node("analyze_movement", self._analyze_movement)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("finalize", self._finalize)

        # Add conditional edges based on analysis type
        workflow.add_conditional_edges(
            "prepare_data",
            self._determine_analysis_path,
            {
                "full": "analyze_chaos",
                "quick": "analyze_chaos",
                "placement": "optimize_placement",
                "compliance": "check_compliance",
                "movement": "analyze_movement"
            }
        )

        # Add edges for full analysis flow
        workflow.add_edge("analyze_chaos", "optimize_placement")
        workflow.add_edge("optimize_placement", "check_compliance")
        workflow.add_edge("check_compliance", "analyze_movement")
        workflow.add_edge("analyze_movement", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "finalize")

        # Set entry point
        workflow.set_entry_point("prepare_data")

        # Compile and return
        compiled = workflow.compile()
        logger.info("Warehouse optimization workflow compiled successfully")

        return compiled

    def _determine_analysis_path(self, state: WarehouseOptimizationState) -> str:
        """Determine which analysis path to take based on type"""
        analysis_type = state.get("analysis_type", "full")

        if analysis_type in ["full", "quick"]:
            return "full"
        elif analysis_type == "placement":
            return "placement"
        elif analysis_type == "compliance":
            return "compliance"
        elif analysis_type == "movement":
            return "movement"
        else:
            return "full"

    async def _prepare_data(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Prepare and validate input data"""
        logger.info(f"Preparing data for {state.get('analysis_type', 'full')} analysis")
        state["processing_stage"] = "preparing_data"
        state["progress_percentage"] = 5
        state["timestamp"] = datetime.now().isoformat()

        try:
            # Extract warehouse data
            warehouse_data = state.get("warehouse_data", {})

            # Parse and prepare specific data structures
            state["chaos_metrics"] = warehouse_data.get("chaos_metrics", {})
            state["fragmentation_data"] = warehouse_data.get("fragmentation_data", {})
            state["velocity_mismatches"] = warehouse_data.get("velocity_mismatches", {})
            state["fifo_violations"] = warehouse_data.get("fifo_violations", [])
            state["warehouse_layout"] = warehouse_data.get("warehouse_layout", {})

            # Generate cache key for result caching
            cache_data = json.dumps({
                "type": state.get("analysis_type"),
                "metrics": state["chaos_metrics"],
                "params": state.get("parameters", {})
            }, sort_keys=True)
            state["cache_key"] = hashlib.md5(cache_data.encode()).hexdigest()

            # Check cache
            cached_result = self._get_cached_result(state["cache_key"])
            if cached_result:
                logger.info("Using cached optimization results")
                state.update(cached_result)
                state["processing_stage"] = "completed_from_cache"
                state["progress_percentage"] = 100
                return state

            logger.info("Data preparation completed")
            state["progress_percentage"] = 10

        except Exception as e:
            logger.error(f"Error in data preparation: {str(e)}")
            state["error"] = f"Data preparation failed: {str(e)}"

        return state

    async def _analyze_chaos(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Analyze warehouse chaos metrics"""
        logger.info("Starting chaos analysis")
        state["processing_stage"] = "analyzing_chaos"
        state["progress_percentage"] = 20

        try:
            # Call chaos analyzer agent
            result = await self.chaos_analyzer.analyze(state)
            state["chaos_analysis"] = result

            logger.info(f"Chaos analysis completed: Efficiency score {result.get('efficiency_score', 0)}%")
            state["progress_percentage"] = 30

        except Exception as e:
            logger.error(f"Error in chaos analysis: {str(e)}")
            state["error"] = f"Chaos analysis failed: {str(e)}"
            # Continue with empty analysis
            state["chaos_analysis"] = {}

        return state

    async def _optimize_placement(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Optimize product placement"""
        logger.info("Starting placement optimization")
        state["processing_stage"] = "optimizing_placement"
        state["progress_percentage"] = 40

        try:
            # Prepare placement data
            placement_state = {
                "current_placements": state.get("warehouse_data", {}).get("current_placements", []),
                "velocity_data": state.get("velocity_mismatches", {}),
                "fragmentation_data": state.get("fragmentation_data", {}),
                "warehouse_layout": state.get("warehouse_layout", {}),
                "consumption_patterns": state.get("warehouse_data", {}).get("consumption_patterns", {})
            }

            # Call placement optimizer agent
            result = await self.placement_optimizer.analyze(placement_state)
            state["placement_optimization"] = result

            logger.info(f"Placement optimization completed: {len(result.get('immediate_moves', []))} moves recommended")
            state["progress_percentage"] = 50

        except Exception as e:
            logger.error(f"Error in placement optimization: {str(e)}")
            state["error"] = f"Placement optimization failed: {str(e)}"
            state["placement_optimization"] = {}

        return state

    async def _check_compliance(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Check compliance status"""
        logger.info("Starting compliance check")
        state["processing_stage"] = "checking_compliance"
        state["progress_percentage"] = 60

        try:
            # Prepare compliance data
            compliance_state = {
                "fifo_violations": state.get("fifo_violations", []),
                "temperature_data": state.get("warehouse_data", {}).get("temperature_data", {}),
                "batch_info": state.get("warehouse_data", {}).get("batch_info", []),
                "zone_violations": state.get("warehouse_data", {}).get("zone_violations", []),
                "regulatory_requirements": state.get("parameters", {}).get("regulatory_requirements", {})
            }

            # Call compliance monitor agent
            result = await self.compliance_monitor.analyze(compliance_state)
            state["compliance_report"] = result

            logger.info(f"Compliance check completed: Score {result.get('compliance_scores', {}).get('overall', 0)}%")
            state["progress_percentage"] = 70

        except Exception as e:
            logger.error(f"Error in compliance check: {str(e)}")
            state["error"] = f"Compliance check failed: {str(e)}"
            state["compliance_report"] = {}

        return state

    async def _analyze_movement(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Analyze movement patterns"""
        logger.info("Starting movement pattern analysis")
        state["processing_stage"] = "analyzing_movement"
        state["progress_percentage"] = 80

        try:
            # Prepare movement data
            movement_state = {
                "movement_history": state.get("warehouse_data", {}).get("movement_history", []),
                "picking_paths": state.get("warehouse_data", {}).get("picking_paths", []),
                "congestion_data": state.get("warehouse_data", {}).get("congestion_data", {}),
                "layout_info": state.get("warehouse_layout", {}),
                "hourly_patterns": state.get("warehouse_data", {}).get("hourly_patterns", [])
            }

            # Call movement analyzer agent
            result = await self.movement_analyzer.analyze(movement_state)
            state["movement_analysis"] = result

            logger.info("Movement analysis completed")
            state["progress_percentage"] = 85

        except Exception as e:
            logger.error(f"Error in movement analysis: {str(e)}")
            state["error"] = f"Movement analysis failed: {str(e)}"
            state["movement_analysis"] = {}

        return state

    async def _generate_recommendations(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Generate final optimization recommendations"""
        logger.info("Generating optimization recommendations")
        state["processing_stage"] = "generating_recommendations"
        state["progress_percentage"] = 90

        try:
            # Call optimization recommender agent
            result = await self.optimization_recommender.analyze(state)

            # Extract key results
            state["recommendations"] = result.get("comprehensive_recommendations", [])
            state["executive_summary"] = result.get("executive_summary", {})
            state["implementation_roadmap"] = result.get("implementation_roadmap", {})
            state["roi_analysis"] = result.get("roi_analysis", {})
            state["success_metrics"] = result.get("success_metrics", {})
            state["optimization_score"] = result.get("optimization_score", 0)

            logger.info(f"Recommendations generated: Optimization score {state['optimization_score']}%")
            state["progress_percentage"] = 95

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            state["error"] = f"Recommendation generation failed: {str(e)}"
            state["recommendations"] = []
            state["optimization_score"] = 0

        return state

    async def _finalize(self, state: WarehouseOptimizationState) -> WarehouseOptimizationState:
        """Finalize the optimization analysis"""
        logger.info("Finalizing warehouse optimization analysis")
        state["processing_stage"] = "completed"
        state["progress_percentage"] = 100

        # Calculate processing time
        if state.get("timestamp"):
            start_time = datetime.fromisoformat(state["timestamp"])
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            state["processing_time_ms"] = int(processing_time)

        # Cache results if successful
        if not state.get("error") and state.get("cache_key"):
            self._cache_result(state["cache_key"], state)

        # Log summary
        logger.info(f"""
        Warehouse Optimization Analysis Complete:
        - Type: {state.get('analysis_type', 'full')}
        - Optimization Score: {state.get('optimization_score', 0)}%
        - Recommendations: {len(state.get('recommendations', []))}
        - Processing Time: {state.get('processing_time_ms', 0)}ms
        - Status: {'Success' if not state.get('error') else 'Failed'}
        """)

        return state

    async def run_analysis(
        self,
        warehouse_data: Dict[str, Any],
        analysis_type: str = "full",
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run warehouse optimization analysis

        Args:
            warehouse_data: Current warehouse state data
            analysis_type: Type of analysis ('full', 'quick', 'placement', 'compliance', 'movement')
            parameters: Additional parameters for analysis

        Returns:
            Complete optimization analysis results
        """
        try:
            # Initialize state
            initial_state = WarehouseOptimizationState(
                analysis_type=analysis_type,
                warehouse_data=warehouse_data,
                parameters=parameters or {},
                chaos_metrics={},
                fragmentation_data={},
                velocity_mismatches={},
                fifo_violations=[],
                warehouse_layout={},
                chaos_analysis={},
                placement_optimization={},
                compliance_report={},
                movement_analysis={},
                recommendations={},
                executive_summary={},
                implementation_roadmap={},
                roi_analysis={},
                success_metrics={},
                optimization_score=0.0,
                processing_stage="initializing",
                progress_percentage=0,
                error=None,
                timestamp=datetime.now().isoformat(),
                processing_time_ms=None,
                cache_key=None
            )

            # Run workflow with timeout
            timeout = parameters.get("timeout", 120)  # 2 minutes default
            final_state = await asyncio.wait_for(
                self.workflow.ainvoke(initial_state),
                timeout=timeout
            )

            # Return cleaned results
            return self._clean_results(final_state)

        except asyncio.TimeoutError:
            logger.error(f"Workflow timeout after {timeout} seconds")
            return {
                "error": f"Analysis timeout after {timeout} seconds",
                "processing_stage": "timeout",
                "optimization_score": 0
            }
        except Exception as e:
            logger.error(f"Workflow execution error: {str(e)}")
            return {
                "error": str(e),
                "processing_stage": "error",
                "optimization_score": 0
            }

    def _clean_results(self, state: WarehouseOptimizationState) -> Dict[str, Any]:
        """Clean and format final results"""
        return {
            "analysis_type": state.get("analysis_type", "full"),
            "optimization_score": state.get("optimization_score", 0),
            "executive_summary": state.get("executive_summary", {}),
            "chaos_analysis": state.get("chaos_analysis", {}),
            "placement_optimization": state.get("placement_optimization", {}),
            "compliance_report": state.get("compliance_report", {}),
            "movement_analysis": state.get("movement_analysis", {}),
            "recommendations": state.get("recommendations", []),
            "implementation_roadmap": state.get("implementation_roadmap", {}),
            "roi_analysis": state.get("roi_analysis", {}),
            "success_metrics": state.get("success_metrics", {}),
            "processing_time_ms": state.get("processing_time_ms"),
            "timestamp": state.get("timestamp"),
            "error": state.get("error")
        }

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired"""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached["timestamp"]).seconds < self.cache_ttl:
                return cached["data"]
            else:
                del self.cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, state: WarehouseOptimizationState):
        """Cache analysis results"""
        self.cache[cache_key] = {
            "timestamp": datetime.now(),
            "data": {
                "chaos_analysis": state.get("chaos_analysis"),
                "placement_optimization": state.get("placement_optimization"),
                "compliance_report": state.get("compliance_report"),
                "movement_analysis": state.get("movement_analysis"),
                "recommendations": state.get("recommendations"),
                "executive_summary": state.get("executive_summary"),
                "implementation_roadmap": state.get("implementation_roadmap"),
                "roi_analysis": state.get("roi_analysis"),
                "success_metrics": state.get("success_metrics"),
                "optimization_score": state.get("optimization_score")
            }
        }

    def get_progress(self, state: WarehouseOptimizationState) -> Dict[str, Any]:
        """Get current workflow progress"""
        return {
            "stage": state.get("processing_stage", "unknown"),
            "percentage": state.get("progress_percentage", 0),
            "message": self._get_progress_message(state.get("processing_stage", ""))
        }

    def _get_progress_message(self, stage: str) -> str:
        """Get user-friendly progress message"""
        messages = {
            "preparing_data": "Preparing warehouse data for analysis...",
            "analyzing_chaos": "Analyzing warehouse chaos metrics...",
            "optimizing_placement": "Optimizing product placement...",
            "checking_compliance": "Checking compliance status...",
            "analyzing_movement": "Analyzing movement patterns...",
            "generating_recommendations": "Generating optimization recommendations...",
            "completed": "Analysis complete!",
            "completed_from_cache": "Results retrieved from cache.",
            "error": "An error occurred during analysis.",
            "timeout": "Analysis timed out."
        }
        return messages.get(stage, "Processing...")


# Utility function for standalone usage
async def analyze_warehouse(
    warehouse_data: Dict[str, Any],
    analysis_type: str = "full",
    llm: Optional[ChatOpenAI] = None
) -> Dict[str, Any]:
    """
    Convenience function to run warehouse analysis

    Args:
        warehouse_data: Warehouse state data
        analysis_type: Type of analysis to run
        llm: Optional LLM instance

    Returns:
        Optimization analysis results
    """
    workflow = WarehouseOptimizationWorkflow(llm)
    return await workflow.run_analysis(warehouse_data, analysis_type)