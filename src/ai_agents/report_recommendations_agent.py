"""
Report Recommendations Agent for generating actionable recommendations
Following the same structure as existing PO generation agents
"""

from typing import Any, Dict, List, Optional
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
import json


class ReportRecommendationsAgent:
    """Agent for generating actionable recommendations and executive summary"""

    def __init__(self, llm: ChatOpenAI):
        self.name = "ReportRecommendationsAgent"
        self.llm = llm
        self.system_prompt = """You are a pharmaceutical supply chain strategist and operations expert.
        Based on analysis, predictions, and identified opportunities, generate:
        1. Specific, actionable recommendations with clear implementation steps
        2. Prioritized action items with timelines and owners
        3. Executive summary highlighting critical findings and decisions needed
        4. Cost-benefit analysis for major recommendations
        5. Quick wins vs strategic initiatives

        Focus on practical, implementable solutions that deliver measurable business value.
        Recommendations should be specific to pharmaceutical warehouse operations."""

    async def _call_llm(self, messages: List[BaseMessage]) -> BaseMessage:
        """Call the LLM with messages"""
        try:
            response = await self.llm.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise

    async def generate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations and executive summary"""
        try:
            report_type = state.get("report_type", "")
            insights = state.get("insights", [])
            patterns = state.get("patterns", [])
            anomalies = state.get("anomalies", [])
            predictions = state.get("predictions", [])
            risk_assessment = state.get("risk_assessment", {})
            opportunities = state.get("opportunities", [])

            # Build comprehensive context for recommendations
            context = self._build_recommendation_context(
                report_type, insights, patterns, anomalies,
                predictions, risk_assessment, opportunities
            )

            # Generate recommendations prompt
            prompt = self._build_recommendations_prompt(report_type, context)

            # Get AI recommendations
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            response = await self._call_llm(messages)

            # Parse recommendations
            recommendations_data = self._parse_recommendations_response(response.content)

            # Update state with final recommendations
            return {
                "recommendations": recommendations_data.get("recommendations", []),
                "executive_summary": recommendations_data.get("executive_summary", ""),
                "action_items": recommendations_data.get("action_items", []),
                "quick_wins": recommendations_data.get("quick_wins", []),
                "strategic_initiatives": recommendations_data.get("strategic_initiatives", []),
                "processing_stage": "recommendations_completed"
            }

        except Exception as e:
            logger.error(f"Error in ReportRecommendationsAgent: {str(e)}")
            return {
                "error": str(e),
                "processing_stage": "recommendations_failed"
            }

    def _build_recommendation_context(
        self,
        report_type: str,
        insights: List,
        patterns: List,
        anomalies: List,
        predictions: List,
        risk_assessment: Dict,
        opportunities: List
    ) -> str:
        """Build context for generating recommendations"""

        context = f"""
        Report Type: {report_type}

        KEY INSIGHTS:
        {self._format_list(insights)}

        PATTERNS IDENTIFIED:
        {self._format_patterns(patterns)}

        ANOMALIES REQUIRING ATTENTION:
        {self._format_anomalies(anomalies)}

        PREDICTIONS:
        {self._format_predictions(predictions)}

        RISK ASSESSMENT:
        Overall Risk Level: {risk_assessment.get('overall_risk_level', 'Not assessed')}
        Risk Score: {risk_assessment.get('risk_score', 'N/A')}
        Key Risk Factors:
        {self._format_risk_factors(risk_assessment.get('risk_factors', []))}

        OPPORTUNITIES IDENTIFIED:
        {self._format_opportunities(opportunities)}
        """

        return context

    def _format_list(self, items: List) -> str:
        """Format a list of items for context"""
        if not items:
            return "None identified"
        return "\n".join(f"- {item}" for item in items)

    def _format_patterns(self, patterns: List[Dict]) -> str:
        """Format patterns for context"""
        if not patterns:
            return "No patterns identified"

        formatted = []
        for pattern in patterns:
            if isinstance(pattern, dict):
                desc = pattern.get('description', 'Unknown pattern')
                conf = pattern.get('confidence', 'unknown')
                formatted.append(f"- {desc} (Confidence: {conf})")
            else:
                formatted.append(f"- {pattern}")

        return "\n".join(formatted)

    def _format_anomalies(self, anomalies: List[Dict]) -> str:
        """Format anomalies for context"""
        if not anomalies:
            return "No anomalies detected"

        formatted = []
        for anomaly in anomalies:
            if isinstance(anomaly, dict):
                desc = anomaly.get('description', 'Unknown anomaly')
                sev = anomaly.get('severity', 'unknown')
                formatted.append(f"- [{sev.upper()}] {desc}")
            else:
                formatted.append(f"- {anomaly}")

        return "\n".join(formatted)

    def _format_predictions(self, predictions: List[Dict]) -> str:
        """Format predictions for context"""
        if not predictions:
            return "No predictions available"

        formatted = []
        for pred in predictions:
            if isinstance(pred, dict):
                desc = pred.get('prediction', 'Unknown prediction')
                time = pred.get('timeframe', 'unknown')
                conf = pred.get('confidence', 'unknown')
                formatted.append(f"- {desc} (Timeframe: {time}, Confidence: {conf})")
            else:
                formatted.append(f"- {pred}")

        return "\n".join(formatted)

    def _format_risk_factors(self, risk_factors: List[Dict]) -> str:
        """Format risk factors for context"""
        if not risk_factors:
            return "No specific risk factors identified"

        formatted = []
        for risk in risk_factors:
            if isinstance(risk, dict):
                factor = risk.get('factor', 'Unknown risk')
                severity = risk.get('severity', 'unknown')
                formatted.append(f"- [{severity.upper()}] {factor}")
            else:
                formatted.append(f"- {risk}")

        return "\n".join(formatted)

    def _format_opportunities(self, opportunities: List[Dict]) -> str:
        """Format opportunities for context"""
        if not opportunities:
            return "No specific opportunities identified"

        formatted = []
        for opp in opportunities:
            if isinstance(opp, dict):
                desc = opp.get('opportunity', 'Unknown opportunity')
                savings = opp.get('potential_savings', 'TBD')
                effort = opp.get('implementation_effort', 'unknown')
                formatted.append(f"- {desc} (Savings: {savings}, Effort: {effort})")
            else:
                formatted.append(f"- {opp}")

        return "\n".join(formatted)

    def _build_recommendations_prompt(self, report_type: str, context: str) -> str:
        """Build prompt for generating recommendations"""

        type_specific_focus = {
            "inventory": """
                Focus recommendations on:
                - Optimal stock levels and reorder points
                - Inventory turnover improvements
                - Storage optimization
                - Expiry management
                - ABC classification adjustments
                - Safety stock optimization
            """,
            "financial": """
                Focus recommendations on:
                - Cost reduction strategies
                - Revenue optimization
                - Cash flow improvements
                - Margin enhancement
                - Budget allocation
                - Investment priorities
            """,
            "supplier": """
                Focus recommendations on:
                - Supplier consolidation
                - Performance improvement plans
                - Contract renegotiation
                - Risk mitigation strategies
                - Alternative sourcing
                - Lead time optimization
            """,
            "consumption": """
                Focus recommendations on:
                - Demand planning improvements
                - Forecast accuracy enhancement
                - Order optimization
                - Waste reduction
                - Consumption pattern adjustments
                - Seasonal planning
            """,
            "analytics_dashboard": """
                Focus recommendations on:
                - Critical KPI improvements
                - Cross-functional optimization
                - System-wide efficiencies
                - Strategic priorities
                - Operational excellence
                - Performance management
            """
        }

        specific_focus = type_specific_focus.get(report_type, "Provide comprehensive recommendations")

        prompt = f"""
        Based on the following analysis context, generate actionable recommendations and an executive summary.

        Context:
        {context}

        {specific_focus}

        Provide your recommendations in the following JSON format:
        {{
            "executive_summary": "2-3 paragraph executive summary highlighting the most critical findings, risks, and recommended actions. Be concise but comprehensive.",

            "recommendations": [
                "Specific recommendation 1 with clear action steps",
                "Specific recommendation 2 with measurable outcomes",
                "Specific recommendation 3 with timeline"
            ],

            "action_items": [
                {{
                    "action": "Specific action to take",
                    "priority": "critical/high/medium/low",
                    "owner": "Department/Role responsible",
                    "timeline": "Immediate/1 week/1 month/3 months",
                    "expected_outcome": "Measurable result",
                    "resources_needed": "What's required"
                }}
            ],

            "quick_wins": [
                {{
                    "action": "Quick win action",
                    "impact": "Expected impact",
                    "effort": "low",
                    "timeline": "1-7 days"
                }}
            ],

            "strategic_initiatives": [
                {{
                    "initiative": "Strategic initiative description",
                    "business_case": "Why this matters",
                    "investment": "Required investment",
                    "roi": "Expected return",
                    "timeline": "3-12 months"
                }}
            ]
        }}

        Ensure recommendations are:
        1. Specific and actionable (not generic advice)
        2. Prioritized by impact and urgency
        3. Include clear success metrics
        4. Feasible within pharmaceutical warehouse constraints
        5. Backed by data from the analysis
        """

        return prompt

    def _parse_recommendations_response(self, response: str) -> Dict:
        """Parse the AI recommendations response"""
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
                return self._create_default_recommendations()

        except Exception as e:
            logger.error(f"Error parsing recommendations response: {str(e)}")
            return self._create_default_recommendations()

    def _create_default_recommendations(self) -> Dict:
        """Create default recommendations if parsing fails"""
        return {
            "executive_summary": "Analysis complete. Please review the detailed findings and recommendations below.",
            "recommendations": [
                "Review and optimize current operational processes",
                "Implement continuous monitoring of key metrics",
                "Establish regular review cycles for performance improvement"
            ],
            "action_items": [
                {
                    "action": "Review report findings with team",
                    "priority": "high",
                    "owner": "Management",
                    "timeline": "1 week",
                    "expected_outcome": "Action plan developed",
                    "resources_needed": "Team meeting time"
                }
            ],
            "quick_wins": [],
            "strategic_initiatives": []
        }