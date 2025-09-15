"""
Report AI Handler Service
Handles AI insight generation for reports, following the pattern of api_handler.py
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os
import sys
from loguru import logger
from langchain_openai import ChatOpenAI

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import workflow
from ai_agents.report_insights_workflow import (
    ReportInsightsWorkflow,
    ReportInsightState,
)


class ReportAIHandler:
    """Handles AI insight generation for reports"""

    def __init__(self):
        """Initialize the AI handler with workflow and caching"""
        # Initialize LLM
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not found, AI insights will use fallback mode"
            )
            self.workflow = None
        else:
            try:
                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.3,
                    max_tokens=2000,
                    api_key=api_key,
                )
                self.workflow = ReportInsightsWorkflow(llm=llm)
                logger.info("ReportAIHandler initialized with OpenAI gpt-4o-mini")
            except Exception as e:
                logger.error(f"Failed to initialize AI workflow: {str(e)}")
                self.workflow = None

        # Simple in-memory cache
        self._cache = {}
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour

        logger.info("ReportAIHandler initialized")

    async def generate_insights_for_report(
        self,
        report_type: str,
        report_data: Dict[str, Any],
        parameters: Dict[str, Any] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate AI insights for a report

        Args:
            report_type: Type of report (inventory, financial, supplier, etc.)
            report_data: The report data to analyze
            parameters: Additional parameters for analysis
            use_cache: Whether to use cached results if available

        Returns:
            Dictionary containing AI-generated insights
        """
        # Check cache if enabled
        cache_key = self._get_cache_key(report_type, parameters)
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached["expires_at"] > datetime.now():
                logger.info(f"Using cached insights for {report_type} report")
                return cached["data"]

        # If workflow not available, return fallback insights
        if not self.workflow:
            logger.warning("AI workflow not available, using fallback insights")
            return self._generate_fallback_insights(report_type, report_data)

        # Generate new insights
        logger.info(f"Generating AI insights for {report_type} report")

        try:
            # Call workflow
            result: ReportInsightState = await self.workflow.generate_insights(
                report_type=report_type, report_data=report_data, parameters=parameters
            )

            # Check for errors
            if result.get("error"):
                logger.error(f"Error in AI workflow: {result['error']}")
                return self._generate_fallback_insights(report_type, report_data)

            # Format response
            insights_response = {
                "executive_summary": result.get("executive_summary", ""),
                "insights": result.get("insights", []),
                "patterns": result.get("patterns", []),
                "anomalies": result.get("anomalies", []),
                "predictions": result.get("predictions", []),
                "risk_assessment": result.get("risk_assessment", {}),
                "opportunities": result.get("opportunities", []),
                "recommendations": result.get("recommendations", []),
                "action_items": result.get("action_items", []),
                "quick_wins": result.get("quick_wins", []),
                "strategic_initiatives": result.get("strategic_initiatives", []),
                "confidence_score": result.get("confidence_score", 0.5),
                "generated_at": result.get("timestamp", datetime.now().isoformat()),
                "processing_time_ms": result.get("processing_time_ms", 0),
            }

            # Cache the result if caching is enabled
            if use_cache:
                self._cache[cache_key] = {
                    "data": insights_response,
                    "expires_at": datetime.now() + self._cache_ttl,
                }
                logger.info(f"Cached insights for {report_type} report")

            logger.info(
                f"AI insights generated successfully in {insights_response['processing_time_ms']}ms"
            )
            return insights_response

        except Exception as e:
            logger.error(f"Exception generating AI insights: {str(e)}")
            return self._generate_fallback_insights(report_type, report_data)

    def _get_cache_key(self, report_type: str, parameters: Optional[Dict]) -> str:
        """Generate a cache key for the report insights"""
        params_str = json.dumps(parameters or {}, sort_keys=True)
        return f"{report_type}:{params_str}"

    def _generate_fallback_insights(
        self, report_type: str, report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fallback insights when AI is not available"""
        logger.info(f"Generating fallback insights for {report_type}")

        # Calculate basic statistics from data
        stats = self._calculate_basic_stats(report_data)

        # Type-specific fallback insights
        type_insights = {
            "inventory": {
                "summary": "Inventory analysis shows current stock levels and reorder requirements.",
                "insights": [
                    f"Total inventory items tracked: {stats.get('total_items', 'N/A')}",
                    "Monitor items approaching reorder points for timely replenishment",
                    "Consider ABC classification for optimized inventory management",
                ],
                "recommendations": [
                    "Review and adjust reorder points based on consumption patterns",
                    "Implement automated alerts for low stock items",
                    "Optimize safety stock levels to reduce carrying costs",
                ],
            },
            "financial": {
                "summary": "Financial report provides revenue and cost analysis for the reporting period.",
                "insights": [
                    f"Total revenue tracked: ${stats.get('total_revenue', 0):,.2f}",
                    "Review order patterns for revenue optimization opportunities",
                    "Monitor cost trends for budget management",
                ],
                "recommendations": [
                    "Analyze high-value orders for growth opportunities",
                    "Review supplier costs for negotiation possibilities",
                    "Implement cost control measures for improved margins",
                ],
            },
            "supplier": {
                "summary": "Supplier performance metrics indicate delivery and quality standards.",
                "insights": [
                    f"Total suppliers analyzed: {stats.get('total_suppliers', 'N/A')}",
                    "Track on-time delivery rates for performance management",
                    "Monitor lead time variations for planning accuracy",
                ],
                "recommendations": [
                    "Establish performance improvement plans for underperforming suppliers",
                    "Consider supplier consolidation for volume discounts",
                    "Implement supplier scorecards for regular evaluation",
                ],
            },
            "consumption": {
                "summary": "Consumption analysis reveals usage patterns and demand trends.",
                "insights": [
                    f"Average daily consumption: {stats.get('avg_consumption', 'N/A')} units",
                    "Identify seasonal patterns for improved forecasting",
                    "Monitor consumption volatility for safety stock adjustments",
                ],
                "recommendations": [
                    "Adjust forecasting models based on recent consumption trends",
                    "Implement demand planning processes for better accuracy",
                    "Review slow-moving items for inventory optimization",
                ],
            },
            "analytics_dashboard": {
                "summary": "Dashboard analytics provide comprehensive operational overview.",
                "insights": [
                    "Key performance indicators show overall system health",
                    "Cross-functional metrics indicate areas for improvement",
                    "Trend analysis reveals operational patterns",
                ],
                "recommendations": [
                    "Focus on KPIs showing negative trends",
                    "Implement cross-functional optimization initiatives",
                    "Establish regular performance review cycles",
                ],
            },
        }

        # Get type-specific content or use default
        type_content = type_insights.get(
            report_type,
            {
                "summary": f"Analysis complete for {report_type} report.",
                "insights": ["Data has been analyzed", "Review detailed metrics below"],
                "recommendations": [
                    "Continue monitoring key metrics",
                    "Implement suggested improvements",
                ],
            },
        )

        # Return fallback insights
        return {
            "executive_summary": type_content["summary"],
            "insights": type_content["insights"],
            "patterns": [
                {
                    "type": "general",
                    "description": "Standard operational patterns observed",
                    "confidence": "medium",
                }
            ],
            "anomalies": [],
            "predictions": [
                {
                    "prediction": "Trends expected to continue based on historical data",
                    "timeframe": "30 days",
                    "confidence": "medium",
                }
            ],
            "risk_assessment": {
                "overall_risk_level": "medium",
                "risk_factors": [],
                "risk_score": 5.0,
            },
            "opportunities": [
                "Process optimization potential identified",
                "Cost reduction opportunities available",
            ],
            "recommendations": type_content["recommendations"],
            "action_items": [
                {
                    "action": "Review report findings with team",
                    "priority": "high",
                    "owner": "Operations Team",
                    "timeline": "1 week",
                    "expected_outcome": "Action plan developed",
                }
            ],
            "quick_wins": [],
            "strategic_initiatives": [],
            "confidence_score": 0.3,  # Lower confidence for fallback
            "generated_at": datetime.now().isoformat(),
            "processing_time_ms": 100,
        }

    def _calculate_basic_stats(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate basic statistics from report data"""
        stats = {}

        try:
            # Handle different data structures
            if isinstance(report_data, dict):
                # Count total items
                for key, value in report_data.items():
                    if isinstance(value, list):
                        stats[f"total_{key}"] = len(value)

                        # Calculate numeric stats if applicable
                        if value and isinstance(value[0], dict):
                            for field_key in value[0].keys():
                                if isinstance(value[0][field_key], (int, float)):
                                    values = [
                                        item.get(field_key, 0)
                                        for item in value
                                        if isinstance(item.get(field_key), (int, float))
                                    ]
                                    if values:
                                        stats[f"total_{field_key}"] = sum(values)
                                        stats[f"avg_{field_key}"] = sum(values) / len(
                                            values
                                        )

            elif isinstance(report_data, list):
                stats["total_items"] = len(report_data)

        except Exception as e:
            logger.error(f"Error calculating basic stats: {str(e)}")

        return stats

    def clear_cache(self):
        """Clear the insights cache"""
        self._cache.clear()
        logger.info("Insights cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        valid_entries = sum(
            1 for entry in self._cache.values() if entry["expires_at"] > datetime.now()
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
        }
