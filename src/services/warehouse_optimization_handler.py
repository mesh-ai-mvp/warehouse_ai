"""
Warehouse Optimization Handler Service
Manages AI workflow execution, caching, and async processing for warehouse optimization
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger
from langchain_openai import ChatOpenAI
import hashlib
from fastapi import BackgroundTasks

# Import warehouse optimization workflow
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agents.warehouse_optimization_workflow import WarehouseOptimizationWorkflow


class WarehouseOptimizationHandler:
    """Handles warehouse optimization analysis requests and manages AI workflow"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize handler with LLM and workflow"""
        # Use provided LLM or create default
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )

        # Initialize workflow
        self.workflow = WarehouseOptimizationWorkflow(self.llm)

        # Storage for async analyses
        self.analyses = {}  # analysis_id -> status/results

        # Quick insights cache (TTL: 15 minutes)
        self.quick_insights_cache = {}
        self.quick_insights_ttl = 900  # seconds

        # Results cache (TTL: 1 hour)
        self.results_cache = {}
        self.results_ttl = 3600  # seconds

        logger.info("WarehouseOptimizationHandler initialized")

    async def run_analysis(
        self,
        warehouse_data: Dict[str, Any],
        analysis_type: str = "full",
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run warehouse optimization analysis synchronously

        Args:
            warehouse_data: Current warehouse state data
            analysis_type: Type of analysis to run
            parameters: Additional analysis parameters

        Returns:
            Complete analysis results
        """
        try:
            logger.info(f"Running {analysis_type} warehouse optimization analysis")

            # Check cache for full analyses
            if analysis_type == "full":
                cache_key = self._generate_cache_key(warehouse_data, analysis_type, parameters)
                cached_result = self._get_cached_result(cache_key)

                if cached_result:
                    logger.info("Returning cached analysis results")
                    return cached_result

            # Run workflow
            results = await self.workflow.run_analysis(
                warehouse_data,
                analysis_type,
                parameters
            )

            # Cache results if successful
            if not results.get("error") and analysis_type == "full":
                self._cache_result(cache_key, results)

            # Add handler metadata
            results["handler_metadata"] = {
                "analysis_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "cached": False
            }

            return results

        except Exception as e:
            logger.error(f"Error in optimization analysis: {str(e)}")
            return {
                "error": str(e),
                "analysis_type": analysis_type,
                "status": "failed"
            }

    def start_async_analysis(
        self,
        warehouse_data: Dict[str, Any],
        analysis_type: str,
        background_tasks: BackgroundTasks
    ) -> str:
        """
        Start asynchronous warehouse optimization analysis

        Args:
            warehouse_data: Current warehouse state data
            analysis_type: Type of analysis to run
            background_tasks: FastAPI background tasks

        Returns:
            Analysis ID for tracking
        """
        analysis_id = str(uuid.uuid4())

        # Initialize analysis status
        self.analyses[analysis_id] = {
            "status": "queued",
            "analysis_type": analysis_type,
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "stage": "Initializing"
        }

        # Add background task
        background_tasks.add_task(
            self._run_async_analysis,
            analysis_id,
            warehouse_data,
            analysis_type
        )

        logger.info(f"Started async analysis {analysis_id}")
        return analysis_id

    async def _run_async_analysis(
        self,
        analysis_id: str,
        warehouse_data: Dict[str, Any],
        analysis_type: str
    ):
        """Run analysis asynchronously in background"""
        try:
            # Update status
            self.analyses[analysis_id]["status"] = "processing"
            self.analyses[analysis_id]["stage"] = "Gathering data"

            # Simulate progress updates
            for progress in [10, 30, 50, 70, 90]:
                await asyncio.sleep(2)  # Simulate processing time
                self.analyses[analysis_id]["progress"] = progress
                self.analyses[analysis_id]["stage"] = self._get_stage_for_progress(progress)

            # Run actual analysis
            results = await self.run_analysis(warehouse_data, analysis_type)

            # Store results
            self.analyses[analysis_id]["status"] = "completed"
            self.analyses[analysis_id]["progress"] = 100
            self.analyses[analysis_id]["stage"] = "Complete"
            self.analyses[analysis_id]["results"] = results
            self.analyses[analysis_id]["completed_at"] = datetime.now().isoformat()

            logger.info(f"Completed async analysis {analysis_id}")

        except Exception as e:
            logger.error(f"Error in async analysis {analysis_id}: {str(e)}")
            self.analyses[analysis_id]["status"] = "failed"
            self.analyses[analysis_id]["error"] = str(e)

    def get_analysis_status(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an ongoing analysis"""
        if analysis_id not in self.analyses:
            return None

        analysis = self.analyses[analysis_id]

        return {
            "analysis_id": analysis_id,
            "status": analysis["status"],
            "analysis_type": analysis["analysis_type"],
            "progress": analysis["progress"],
            "stage": analysis["stage"],
            "started_at": analysis["started_at"],
            "completed_at": analysis.get("completed_at"),
            "error": analysis.get("error")
        }

    def get_analysis_results(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get results of a completed analysis"""
        if analysis_id not in self.analyses:
            return None

        analysis = self.analyses[analysis_id]

        if analysis["status"] != "completed":
            return {
                "status": analysis["status"],
                "message": "Analysis not yet complete"
            }

        return analysis.get("results", {})

    async def get_quick_insights(self, warehouse_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get quick AI insights without full analysis

        Args:
            warehouse_data: Basic warehouse metrics

        Returns:
            Quick insights and recommendations
        """
        try:
            # Generate cache key
            cache_key = hashlib.md5(
                json.dumps(warehouse_data, sort_keys=True).encode()
            ).hexdigest()

            # Check cache
            if cache_key in self.quick_insights_cache:
                cached = self.quick_insights_cache[cache_key]
                if (datetime.now() - cached["timestamp"]).seconds < self.quick_insights_ttl:
                    return cached["insights"]

            # Generate quick insights using LLM
            insights = await self._generate_quick_insights(warehouse_data)

            # Cache insights
            self.quick_insights_cache[cache_key] = {
                "timestamp": datetime.now(),
                "insights": insights
            }

            return insights

        except Exception as e:
            logger.error(f"Error generating quick insights: {str(e)}")
            return {
                "insights": [],
                "summary": "Unable to generate insights",
                "error": str(e)
            }

    async def _generate_quick_insights(self, warehouse_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quick insights using LLM"""
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """You are a warehouse optimization expert providing quick insights.
        Analyze the metrics and provide 3-5 key insights and immediate actions.
        Be specific and actionable. Focus on the most impactful improvements."""

        human_prompt = f"""
        Analyze these warehouse metrics:
        - Overall Chaos Score: {warehouse_data.get('chaos_metrics', {}).get('overall_chaos_score', 0)}%
        - Fragmented Batches: {warehouse_data.get('fragmentation_data', {}).get('total_fragmented', 0)}
        - Velocity Mismatches: {warehouse_data.get('velocity_mismatches', {}).get('total_mismatches', 0)}
        - Movement Stats: {json.dumps(warehouse_data.get('movement_statistics', {}), indent=2)}
        - Compliance Issues: {json.dumps(warehouse_data.get('compliance_summary', {}), indent=2)}

        Provide:
        1. Top 3 insights about current warehouse state
        2. Top 3 immediate actions to improve efficiency
        3. Estimated impact of implementing these actions
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        response = await self.llm.ainvoke(messages)

        # Parse response
        try:
            # Try to parse as JSON
            insights_data = json.loads(response.content)
        except:
            # Fall back to text parsing
            insights_data = self._parse_text_insights(response.content)

        return {
            "insights": insights_data.get("insights", []),
            "actions": insights_data.get("actions", []),
            "impact": insights_data.get("impact", "Significant efficiency improvement expected"),
            "generated_at": datetime.now().isoformat()
        }

    def _parse_text_insights(self, text: str) -> Dict[str, Any]:
        """Parse text response into structured insights"""
        lines = text.split('\n')
        insights = []
        actions = []

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'insight' in line.lower():
                current_section = 'insights'
            elif 'action' in line.lower():
                current_section = 'actions'
            elif line.startswith(('1.', '2.', '3.', '-', '*', '•')):
                cleaned = line.lstrip('1234567890.-*• ')
                if current_section == 'insights':
                    insights.append(cleaned)
                elif current_section == 'actions':
                    actions.append(cleaned)

        return {
            "insights": insights[:3] if insights else ["Analysis in progress"],
            "actions": actions[:3] if actions else ["Further analysis recommended"],
            "impact": "Efficiency improvements identified"
        }

    def get_optimization_templates(self) -> List[Dict[str, Any]]:
        """Get available optimization analysis templates"""
        return [
            {
                "id": "full_optimization",
                "name": "Complete Warehouse Optimization",
                "description": "Comprehensive analysis of all warehouse aspects",
                "duration": "2-3 minutes",
                "agents": ["Chaos Analyzer", "Placement Optimizer", "Compliance Monitor", "Movement Analyzer", "Recommender"],
                "output": ["Executive Summary", "Detailed Recommendations", "ROI Analysis", "Implementation Roadmap"]
            },
            {
                "id": "quick_assessment",
                "name": "Quick Assessment",
                "description": "Fast analysis of key metrics",
                "duration": "30 seconds",
                "agents": ["Chaos Analyzer"],
                "output": ["Efficiency Score", "Top Issues", "Quick Wins"]
            },
            {
                "id": "placement_focus",
                "name": "Placement Optimization",
                "description": "Focus on product placement and consolidation",
                "duration": "1 minute",
                "agents": ["Placement Optimizer"],
                "output": ["Relocation Plan", "Consolidation Strategy", "Space Optimization"]
            },
            {
                "id": "compliance_audit",
                "name": "Compliance Audit",
                "description": "Detailed compliance and regulatory check",
                "duration": "1 minute",
                "agents": ["Compliance Monitor"],
                "output": ["Compliance Score", "Violations", "Corrective Actions"]
            },
            {
                "id": "movement_analysis",
                "name": "Movement Pattern Analysis",
                "description": "Analyze and optimize movement patterns",
                "duration": "1 minute",
                "agents": ["Movement Analyzer"],
                "output": ["Path Optimization", "Congestion Analysis", "Layout Recommendations"]
            }
        ]

    def generate_optimization_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate formatted optimization report from analysis results"""
        return {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now().isoformat(),
            "executive_summary": analysis_results.get("executive_summary", {}),
            "key_findings": self._extract_key_findings(analysis_results),
            "recommendations": {
                "immediate": self._filter_recommendations(analysis_results, "immediate"),
                "short_term": self._filter_recommendations(analysis_results, "short_term"),
                "long_term": self._filter_recommendations(analysis_results, "long_term")
            },
            "metrics": {
                "optimization_score": analysis_results.get("optimization_score", 0),
                "chaos_score": analysis_results.get("chaos_analysis", {}).get("efficiency_score", 0),
                "compliance_score": analysis_results.get("compliance_report", {}).get("compliance_scores", {}).get("overall", 0),
                "movement_efficiency": analysis_results.get("movement_analysis", {}).get("efficiency_metrics", {}).get("overall_efficiency", 0)
            },
            "roi_summary": analysis_results.get("roi_analysis", {}),
            "implementation_plan": analysis_results.get("implementation_roadmap", {}),
            "visualizations": self._generate_visualization_config(analysis_results)
        }

    def _extract_key_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract key findings from analysis results"""
        findings = []

        # From chaos analysis
        if results.get("chaos_analysis"):
            chaos = results["chaos_analysis"]
            findings.append(f"Warehouse operating at {chaos.get('efficiency_score', 0):.0f}% efficiency")

            top_problems = chaos.get("top_problems", [])
            if top_problems:
                findings.append(f"Top issue: {top_problems[0] if isinstance(top_problems[0], str) else top_problems[0].get('issue', 'Unknown')}")

        # From compliance report
        if results.get("compliance_report"):
            compliance = results["compliance_report"]
            score = compliance.get("compliance_scores", {}).get("overall", 0)
            if score < 80:
                findings.append(f"Compliance at risk with score of {score:.0f}%")

        # From placement optimization
        if results.get("placement_optimization"):
            placement = results["placement_optimization"]
            moves = len(placement.get("immediate_moves", []))
            if moves > 0:
                findings.append(f"{moves} items require immediate relocation")

        # From movement analysis
        if results.get("movement_analysis"):
            movement = results["movement_analysis"]
            efficiency = movement.get("efficiency_metrics", {}).get("overall_efficiency", "0%")
            findings.append(f"Movement efficiency at {efficiency}")

        return findings[:5]  # Top 5 findings

    def _filter_recommendations(self, results: Dict[str, Any], timeframe: str) -> List[Dict]:
        """Filter recommendations by timeframe"""
        all_recommendations = results.get("recommendations", [])

        if timeframe == "immediate":
            return [r for r in all_recommendations if r.get("priority") == "Critical"][:5]
        elif timeframe == "short_term":
            return [r for r in all_recommendations if r.get("priority") == "High"][:5]
        elif timeframe == "long_term":
            return [r for r in all_recommendations if r.get("priority") in ["Medium", "Low"]][:5]

        return []

    def _generate_visualization_config(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration for visualizations"""
        return {
            "heatmap": {
                "enabled": bool(results.get("chaos_analysis", {}).get("heat_map_data")),
                "data": results.get("chaos_analysis", {}).get("heat_map_data", {})
            },
            "efficiency_gauge": {
                "enabled": True,
                "value": results.get("optimization_score", 0),
                "target": 85
            },
            "savings_chart": {
                "enabled": bool(results.get("roi_analysis")),
                "data": results.get("roi_analysis", {}).get("annual_savings", {})
            },
            "timeline": {
                "enabled": bool(results.get("implementation_roadmap")),
                "milestones": results.get("implementation_roadmap", {}).get("milestones", [])
            }
        }

    def cleanup_old_analyses(self, hours: int = 24):
        """Clean up old analysis results to free memory"""
        cutoff = datetime.now() - timedelta(hours=hours)
        to_remove = []

        for analysis_id, analysis in self.analyses.items():
            if analysis.get("completed_at"):
                completed = datetime.fromisoformat(analysis["completed_at"])
                if completed < cutoff:
                    to_remove.append(analysis_id)

        for analysis_id in to_remove:
            del self.analyses[analysis_id]

        logger.info(f"Cleaned up {len(to_remove)} old analyses")

    def _generate_cache_key(
        self,
        warehouse_data: Dict[str, Any],
        analysis_type: str,
        parameters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for analysis results"""
        cache_data = {
            "type": analysis_type,
            "chaos_score": warehouse_data.get("chaos_metrics", {}).get("overall_chaos_score"),
            "fragmented": warehouse_data.get("fragmentation_data", {}).get("total_fragmented"),
            "mismatches": warehouse_data.get("velocity_mismatches", {}).get("total_mismatches"),
            "params": parameters or {}
        }

        return hashlib.md5(
            json.dumps(cache_data, sort_keys=True).encode()
        ).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired"""
        if cache_key in self.results_cache:
            cached = self.results_cache[cache_key]
            if (datetime.now() - cached["timestamp"]).seconds < self.results_ttl:
                logger.info("Using cached analysis results")
                result = cached["data"].copy()
                result["handler_metadata"] = {
                    "analysis_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "cached": True,
                    "cache_age": (datetime.now() - cached["timestamp"]).seconds
                }
                return result
            else:
                del self.results_cache[cache_key]

        return None

    def _cache_result(self, cache_key: str, results: Dict[str, Any]):
        """Cache analysis results"""
        self.results_cache[cache_key] = {
            "timestamp": datetime.now(),
            "data": results
        }

    def _get_stage_for_progress(self, progress: int) -> str:
        """Get stage description for progress percentage"""
        if progress < 20:
            return "Analyzing chaos metrics"
        elif progress < 40:
            return "Optimizing placement"
        elif progress < 60:
            return "Checking compliance"
        elif progress < 80:
            return "Analyzing movement patterns"
        elif progress < 95:
            return "Generating recommendations"
        else:
            return "Finalizing analysis"