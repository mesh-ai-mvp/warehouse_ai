"""
Report Analysis Agent for deep analysis and trend prediction
Following the same structure as existing PO generation agents
"""

from typing import Any, Dict, List, Optional
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
import json


class ReportAnalysisAgent:
    """Agent for deep analysis, trend prediction, and risk assessment"""

    def __init__(self, llm: ChatOpenAI):
        self.name = "ReportAnalysisAgent"
        self.llm = llm
        self.system_prompt = """You are a predictive analytics expert specializing in pharmaceutical supply chain.
        Based on historical data, patterns, and identified insights:
        1. Forecast future trends and their business impact
        2. Identify optimization opportunities for cost and efficiency
        3. Calculate risk scores for various operational aspects
        4. Predict potential issues before they occur
        5. Quantify improvement opportunities

        Use statistical thinking and data-driven analysis to provide accurate predictions.
        All predictions should include confidence levels and time horizons."""

    async def _call_llm(self, messages: List[BaseMessage]) -> BaseMessage:
        """Call the LLM with messages"""
        try:
            response = await self.llm.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Perform deep analysis and generate predictions"""
        try:
            report_type = state.get("report_type", "")
            report_data = state.get("report_data", {})
            insights = state.get("insights", [])
            patterns = state.get("patterns", [])
            anomalies = state.get("anomalies", [])

            # Build comprehensive analysis context
            context = self._build_analysis_context(
                report_type, report_data, insights, patterns, anomalies
            )

            # Generate analysis prompt
            prompt = self._build_prediction_prompt(report_type, context)

            # Get AI analysis
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            response = await self._call_llm(messages)

            # Parse predictions and analysis
            analysis_data = self._parse_analysis_response(response.content)

            # Update state with analysis results
            return {
                "predictions": analysis_data.get("predictions", []),
                "risk_assessment": analysis_data.get("risk_assessment", {}),
                "opportunities": analysis_data.get("opportunities", []),
                "trend_analysis": analysis_data.get("trend_analysis", {}),
                "processing_stage": "analysis_completed"
            }

        except Exception as e:
            logger.error(f"Error in ReportAnalysisAgent: {str(e)}")
            return {
                "error": str(e),
                "processing_stage": "analysis_failed"
            }

    def _build_analysis_context(
        self,
        report_type: str,
        report_data: Dict,
        insights: List,
        patterns: List,
        anomalies: List
    ) -> str:
        """Build context for deep analysis"""

        context = f"""
        Report Type: {report_type}

        Key Insights Identified:
        {json.dumps(insights, indent=2)}

        Patterns Detected:
        {json.dumps(patterns, indent=2)}

        Anomalies Found:
        {json.dumps(anomalies, indent=2)}

        Data Statistics:
        """

        # Add data statistics based on report type
        if isinstance(report_data, dict):
            for key, value in report_data.items():
                if isinstance(value, list) and len(value) > 0:
                    context += f"\n{key}: {len(value)} records"
                    # Calculate basic stats if numeric data
                    numeric_fields = self._extract_numeric_stats(value)
                    if numeric_fields:
                        context += f"\n  Statistics: {json.dumps(numeric_fields, indent=2)}"

        return context

    def _extract_numeric_stats(self, data_list: List) -> Dict:
        """Extract basic statistics from numeric fields"""
        stats = {}

        if not data_list or not isinstance(data_list[0], dict):
            return stats

        # Identify numeric fields
        sample = data_list[0]
        for key, value in sample.items():
            if isinstance(value, (int, float)):
                values = [item.get(key, 0) for item in data_list if isinstance(item.get(key), (int, float))]
                if values:
                    stats[key] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "count": len(values)
                    }

        return stats

    def _build_prediction_prompt(self, report_type: str, context: str) -> str:
        """Build prompt for predictions and deep analysis"""

        type_specific_analysis = {
            "inventory": """
                Predict:
                - Items likely to stockout in next 7, 14, 30 days
                - Optimal reorder points based on consumption patterns
                - Inventory holding cost optimization opportunities
                - Space utilization improvements
                - Slow-moving inventory risks
            """,
            "financial": """
                Predict:
                - Revenue for next 1, 3, 6 months
                - Cost trends and potential savings
                - Cash flow projections
                - Margin improvement opportunities
                - Budget variance risks
            """,
            "supplier": """
                Predict:
                - Supplier reliability trends
                - Delivery delay probabilities
                - Cost negotiation opportunities
                - Supplier consolidation benefits
                - Quality issue risks
            """,
            "consumption": """
                Predict:
                - Demand for next 7, 30, 90 days
                - Seasonal demand adjustments needed
                - Consumption volatility risks
                - Waste reduction opportunities
                - Optimal order quantities
            """,
            "analytics_dashboard": """
                Predict:
                - Overall operational performance trajectory
                - Critical KPIs likely to deteriorate
                - Cross-functional optimization opportunities
                - System-wide risk factors
                - Strategic improvement areas
            """
        }

        specific_analysis = type_specific_analysis.get(report_type, "Provide comprehensive predictions")

        prompt = f"""
        Based on the following analysis context, provide deep predictions and risk assessments.

        Context:
        {context}

        {specific_analysis}

        Provide your analysis in the following JSON format:
        {{
            "predictions": [
                {{
                    "prediction": "Specific prediction description",
                    "timeframe": "7 days/30 days/3 months",
                    "confidence": "high/medium/low",
                    "probability": 0.75,
                    "impact": "Impact description",
                    "factors": ["factor1", "factor2"]
                }}
            ],
            "risk_assessment": {{
                "overall_risk_level": "low/medium/high/critical",
                "risk_factors": [
                    {{
                        "factor": "Risk factor description",
                        "severity": "low/medium/high/critical",
                        "probability": 0.6,
                        "mitigation": "Suggested mitigation"
                    }}
                ],
                "risk_score": 7.5
            }},
            "opportunities": [
                {{
                    "opportunity": "Opportunity description",
                    "potential_savings": "$X or X%",
                    "implementation_effort": "low/medium/high",
                    "timeframe": "immediate/short-term/long-term",
                    "confidence": "high/medium/low"
                }}
            ],
            "trend_analysis": {{
                "short_term": "1-30 days trend description",
                "medium_term": "1-3 months trend description",
                "long_term": "3+ months trend description",
                "inflection_points": ["Description of trend changes"]
            }}
        }}

        Ensure predictions are:
        1. Quantified with specific numbers/percentages
        2. Time-bound with clear horizons
        3. Based on identified patterns and data
        4. Actionable for business decisions
        """

        return prompt

    def _parse_analysis_response(self, response: str) -> Dict:
        """Parse the AI analysis response"""
        try:
            # Try to parse as JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "{" in response and "}" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return self._create_default_analysis()

        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")
            return self._create_default_analysis()

    def _create_default_analysis(self) -> Dict:
        """Create default analysis structure if parsing fails"""
        return {
            "predictions": [
                {
                    "prediction": "Analysis in progress",
                    "timeframe": "30 days",
                    "confidence": "medium",
                    "probability": 0.5,
                    "impact": "To be determined",
                    "factors": []
                }
            ],
            "risk_assessment": {
                "overall_risk_level": "medium",
                "risk_factors": [],
                "risk_score": 5.0
            },
            "opportunities": [],
            "trend_analysis": {
                "short_term": "Stable",
                "medium_term": "Stable",
                "long_term": "To be determined",
                "inflection_points": []
            }
        }