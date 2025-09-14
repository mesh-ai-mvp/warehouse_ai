"""
Report Insights Workflow using LangGraph
Orchestrates AI agents for generating report insights, following PO workflow structure
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
import asyncio
from datetime import datetime
from loguru import logger
import hashlib
import json

# Import our agents
from .report_insights_agent import ReportInsightsAgent
from .report_analysis_agent import ReportAnalysisAgent
from .report_recommendations_agent import ReportRecommendationsAgent


class ReportInsightState(TypedDict):
    """State for report insight generation workflow"""

    # Input parameters
    report_type: str
    report_data: Dict[str, Any]
    parameters: Dict[str, Any]

    # Analysis results from insights agent
    insights: List[str]
    patterns: List[Dict]
    anomalies: List[Dict]
    key_metrics: Dict[str, Any]

    # Predictions from analysis agent
    predictions: List[Dict]
    risk_assessment: Dict
    opportunities: List[str]
    trend_analysis: Dict

    # Final outputs from recommendations agent
    recommendations: List[str]
    executive_summary: str
    action_items: List[Dict]
    quick_wins: List[Dict]
    strategic_initiatives: List[Dict]

    # Workflow metadata
    confidence_score: float
    processing_stage: str
    error: Optional[str]
    timestamp: str
    processing_time_ms: Optional[int]


class ReportInsightsWorkflow:
    """Orchestrates AI agents for report insight generation"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize workflow with LLM and agents"""
        # Use provided LLM or create default
        self.llm = llm or ChatOpenAI(
            model="gpt-5-mini", temperature=0.3, max_tokens=2000
        )

        # Initialize agents (same pattern as PO workflow)
        self.insights_agent = ReportInsightsAgent(self.llm)
        self.analysis_agent = ReportAnalysisAgent(self.llm)
        self.recommendations_agent = ReportRecommendationsAgent(self.llm)

        # Build workflow graph
        self.workflow = self._build_workflow()

        logger.info("ReportInsightsWorkflow initialized")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create workflow with our state type
        workflow = StateGraph(ReportInsightState)

        # Add nodes (each node is a step in the workflow)
        workflow.add_node("analyze_data", self._analyze_data)
        workflow.add_node("deep_analysis", self._deep_analysis)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("finalize", self._finalize)

        # Add edges (define the flow between nodes)
        workflow.add_edge("analyze_data", "deep_analysis")
        workflow.add_edge("deep_analysis", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "finalize")

        # Set entry point
        workflow.set_entry_point("analyze_data")

        # Compile and return
        compiled = workflow.compile()
        logger.info("Workflow graph compiled successfully")

        return compiled

    async def _analyze_data(self, state: ReportInsightState) -> ReportInsightState:
        """Initial data analysis step"""
        logger.info(f"Starting data analysis for {state['report_type']} report")
        state["processing_stage"] = "analyzing_data"

        try:
            # Call insights agent
            result = await self.insights_agent.analyze(state)

            # Update state with results
            state["insights"] = result.get("insights", [])
            state["patterns"] = result.get("patterns", [])
            state["anomalies"] = result.get("anomalies", [])
            state["key_metrics"] = result.get("key_metrics", {})

            logger.info(
                f"Data analysis completed: {len(state['insights'])} insights found"
            )

        except Exception as e:
            logger.error(f"Error in data analysis: {str(e)}")
            state["error"] = f"Data analysis failed: {str(e)}"

        return state

    async def _deep_analysis(self, state: ReportInsightState) -> ReportInsightState:
        """Deep analysis and predictions step"""
        logger.info("Starting deep analysis and predictions")
        state["processing_stage"] = "deep_analysis"

        try:
            # Call analysis agent
            result = await self.analysis_agent.analyze(state)

            # Update state with predictions
            state["predictions"] = result.get("predictions", [])
            state["risk_assessment"] = result.get("risk_assessment", {})
            state["opportunities"] = result.get("opportunities", [])
            state["trend_analysis"] = result.get("trend_analysis", {})

            logger.info(
                f"Deep analysis completed: {len(state['predictions'])} predictions generated"
            )

        except Exception as e:
            logger.error(f"Error in deep analysis: {str(e)}")
            state["error"] = f"Deep analysis failed: {str(e)}"

        return state

    async def _generate_recommendations(
        self, state: ReportInsightState
    ) -> ReportInsightState:
        """Generate recommendations step"""
        logger.info("Generating recommendations and executive summary")
        state["processing_stage"] = "generating_recommendations"

        try:
            # Call recommendations agent
            result = await self.recommendations_agent.generate(state)

            # Update state with recommendations
            state["recommendations"] = result.get("recommendations", [])
            state["executive_summary"] = result.get("executive_summary", "")
            state["action_items"] = result.get("action_items", [])
            state["quick_wins"] = result.get("quick_wins", [])
            state["strategic_initiatives"] = result.get("strategic_initiatives", [])

            logger.info(
                f"Recommendations generated: {len(state['recommendations'])} recommendations"
            )

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            state["error"] = f"Recommendations generation failed: {str(e)}"

        return state

    async def _finalize(self, state: ReportInsightState) -> ReportInsightState:
        """Finalize the report insights"""
        logger.info("Finalizing report insights")
        state["processing_stage"] = "completed"
        state["timestamp"] = datetime.now().isoformat()

        # Calculate confidence score based on completeness
        state["confidence_score"] = self._calculate_confidence(state)

        # Log summary
        logger.info(f"""
        Report Insights Generation Complete:
        - Type: {state["report_type"]}
        - Insights: {len(state["insights"])}
        - Predictions: {len(state["predictions"])}
        - Recommendations: {len(state["recommendations"])}
        - Confidence Score: {state["confidence_score"]:.2f}
        """)

        return state

    def _calculate_confidence(self, state: ReportInsightState) -> float:
        """Calculate confidence score based on analysis completeness"""
        score = 0.0
        max_score = 100.0

        # Check for insights (30 points)
        if state.get("insights"):
            score += min(30, len(state["insights"]) * 10)

        # Check for patterns (20 points)
        if state.get("patterns"):
            score += min(20, len(state["patterns"]) * 10)

        # Check for predictions (20 points)
        if state.get("predictions"):
            score += min(20, len(state["predictions"]) * 5)

        # Check for recommendations (20 points)
        if state.get("recommendations"):
            score += min(20, len(state["recommendations"]) * 5)

        # Check for executive summary (10 points)
        if state.get("executive_summary") and len(state["executive_summary"]) > 50:
            score += 10

        # Normalize to 0-1 range
        confidence = score / max_score

        # Reduce confidence if there were errors
        if state.get("error"):
            confidence *= 0.5

        return min(1.0, max(0.0, confidence))

    async def generate_insights(
        self,
        report_type: str,
        report_data: Dict[str, Any],
        parameters: Dict[str, Any] = None,
    ) -> ReportInsightState:
        """
        Main entry point for generating insights

        Args:
            report_type: Type of report (inventory, financial, supplier, etc.)
            report_data: The report data to analyze
            parameters: Additional parameters for analysis

        Returns:
            ReportInsightState with complete analysis and recommendations
        """
        start_time = datetime.now()

        # Initialize state
        initial_state = ReportInsightState(
            report_type=report_type,
            report_data=report_data,
            parameters=parameters or {},
            insights=[],
            patterns=[],
            anomalies=[],
            key_metrics={},
            predictions=[],
            risk_assessment={},
            opportunities=[],
            trend_analysis={},
            recommendations=[],
            executive_summary="",
            action_items=[],
            quick_wins=[],
            strategic_initiatives=[],
            confidence_score=0.0,
            processing_stage="initializing",
            error=None,
            timestamp="",
            processing_time_ms=None,
        )

        try:
            logger.info(f"Starting insight generation for {report_type} report")

            # Run workflow with timeout (same as PO workflow)
            final_state = await asyncio.wait_for(
                self.workflow.ainvoke(initial_state),
                timeout=300.0,  # 300 second timeout
            )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            final_state["processing_time_ms"] = int(processing_time)

            logger.info(f"Insight generation completed in {processing_time:.0f}ms")
            return final_state

        except asyncio.TimeoutError:
            logger.error("Workflow timeout after 300 seconds")
            initial_state["error"] = "Workflow timeout - analysis took too long"
            initial_state["processing_stage"] = "failed"
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            initial_state["processing_time_ms"] = int(processing_time)
            return initial_state

        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            initial_state["error"] = str(e)
            initial_state["processing_stage"] = "failed"
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            initial_state["processing_time_ms"] = int(processing_time)
            return initial_state

    def get_cache_key(self, report_type: str, parameters: Dict) -> str:
        """Generate cache key for insights"""
        # Create deterministic key from report type and parameters
        key_data = f"{report_type}:{json.dumps(parameters, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
