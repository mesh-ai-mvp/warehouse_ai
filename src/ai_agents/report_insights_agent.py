"""
Report Insights Agent for analyzing report data and identifying patterns
Following the same structure as existing PO generation agents
"""

from typing import Any, Dict, List, Optional
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
import json


class ReportInsightsAgent:
    """Agent for analyzing report data and identifying key patterns and insights"""

    def __init__(self, llm: ChatOpenAI):
        self.name = "ReportInsightsAgent"
        self.llm = llm
        self.system_prompt = """You are a data analysis expert specializing in pharmaceutical warehouse operations.
        Your role is to analyze report data and identify:
        1. Key trends and patterns in the data
        2. Anomalies and outliers that require attention
        3. Performance metrics and their implications
        4. Critical issues that need immediate action

        Provide insights in a structured, actionable format that helps business decision-making.
        Focus on practical, measurable observations that can drive operational improvements."""

    async def _call_llm(self, messages: List[BaseMessage]) -> BaseMessage:
        """Call the LLM with messages"""
        try:
            response = await self.llm.ainvoke(messages)
            return response
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze report data and generate initial insights"""
        try:
            report_type = state.get("report_type", "")
            report_data = state.get("report_data", {})
            parameters = state.get("parameters", {})

            # Prepare data summary for analysis
            data_summary = self._prepare_data_summary(report_type, report_data)

            # Build analysis prompt based on report type
            prompt = self._build_analysis_prompt(report_type, data_summary, parameters)

            # Get AI analysis
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            response = await self._call_llm(messages)

            # Parse the response
            insights_data = self._parse_insights_response(response.content)

            # Update state with insights
            return {
                "insights": insights_data.get("insights", []),
                "patterns": insights_data.get("patterns", []),
                "anomalies": insights_data.get("anomalies", []),
                "key_metrics": insights_data.get("key_metrics", {}),
                "processing_stage": "insights_generated"
            }

        except Exception as e:
            logger.error(f"Error in ReportInsightsAgent: {str(e)}")
            return {
                "error": str(e),
                "processing_stage": "insights_failed"
            }

    def _prepare_data_summary(self, report_type: str, report_data: Dict) -> str:
        """Prepare a summary of the report data for analysis"""
        summary = f"Report Type: {report_type}\n\n"

        # Handle different report structures
        if isinstance(report_data, dict):
            for key, value in report_data.items():
                if isinstance(value, list) and len(value) > 0:
                    summary += f"{key}:\n"
                    summary += f"  - Number of records: {len(value)}\n"
                    if isinstance(value[0], dict):
                        summary += f"  - Sample record: {json.dumps(value[0], indent=2)}\n"
                    summary += f"  - First 5 records: {json.dumps(value[:5], indent=2)}\n\n"
                elif isinstance(value, dict):
                    summary += f"{key}: {json.dumps(value, indent=2)}\n\n"
                else:
                    summary += f"{key}: {value}\n\n"
        elif isinstance(report_data, list):
            summary += f"Total records: {len(report_data)}\n"
            if len(report_data) > 0:
                summary += f"Sample records: {json.dumps(report_data[:5], indent=2)}\n"

        return summary

    def _build_analysis_prompt(self, report_type: str, data_summary: str, parameters: Dict) -> str:
        """Build the analysis prompt based on report type"""

        type_specific_instructions = {
            "inventory": """
                Focus on:
                - Stock levels vs reorder points
                - Items at risk of stockout
                - Overstock situations
                - Category distribution
                - Supplier dependencies
                - Days supply analysis
            """,
            "financial": """
                Focus on:
                - Revenue trends and patterns
                - Cost analysis
                - Margin analysis
                - Order value trends
                - Period-over-period growth
                - Profitability indicators
            """,
            "supplier": """
                Focus on:
                - On-time delivery performance
                - Lead time variations
                - Quality scores and ratings
                - Cost competitiveness
                - Risk assessment
                - Performance trends
            """,
            "consumption": """
                Focus on:
                - Consumption patterns and trends
                - Seasonal variations
                - Forecast accuracy
                - Demand volatility
                - Category-wise consumption
                - Unusual consumption spikes
            """,
            "analytics_dashboard": """
                Focus on:
                - Overall KPI performance
                - Critical metrics requiring attention
                - Cross-functional insights
                - Operational efficiency
                - Risk indicators
                - Opportunity areas
            """
        }

        specific_focus = type_specific_instructions.get(report_type, "Provide comprehensive analysis")

        prompt = f"""
        Analyze the following {report_type} report data and provide structured insights.

        {specific_focus}

        Data Summary:
        {data_summary}

        Parameters/Filters Applied:
        {json.dumps(parameters, indent=2)}

        Please provide your analysis in the following JSON format:
        {{
            "insights": [
                "Key insight 1",
                "Key insight 2",
                "Key insight 3"
            ],
            "patterns": [
                {{
                    "type": "trend/seasonal/cyclic",
                    "description": "Pattern description",
                    "impact": "Business impact",
                    "confidence": "high/medium/low"
                }}
            ],
            "anomalies": [
                {{
                    "type": "outlier/deviation/unusual",
                    "description": "Anomaly description",
                    "severity": "critical/high/medium/low",
                    "affected_items": ["item1", "item2"]
                }}
            ],
            "key_metrics": {{
                "metric_name": {{
                    "value": "metric value",
                    "trend": "increasing/decreasing/stable",
                    "assessment": "good/warning/critical"
                }}
            }}
        }}

        Ensure all insights are:
        1. Data-driven and specific
        2. Actionable and practical
        3. Relevant to pharmaceutical warehouse operations
        4. Quantified where possible
        """

        return prompt

    def _parse_insights_response(self, response: str) -> Dict:
        """Parse the AI response into structured insights"""
        try:
            # Try to parse as JSON first
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "{" in response and "}" in response:
                # Extract JSON from response
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback to text parsing
                return self._parse_text_response(response)

        except Exception as e:
            logger.error(f"Error parsing insights response: {str(e)}")
            return self._parse_text_response(response)

    def _parse_text_response(self, response: str) -> Dict:
        """Fallback text parsing if JSON parsing fails"""
        lines = response.split("\n")

        insights = []
        patterns = []
        anomalies = []

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "insight" in line.lower() or "key finding" in line.lower():
                current_section = "insights"
            elif "pattern" in line.lower() or "trend" in line.lower():
                current_section = "patterns"
            elif "anomal" in line.lower() or "outlier" in line.lower():
                current_section = "anomalies"
            elif line.startswith("-") or line.startswith("•"):
                content = line[1:].strip()
                if current_section == "insights":
                    insights.append(content)
                elif current_section == "patterns":
                    patterns.append({"description": content, "type": "general"})
                elif current_section == "anomalies":
                    anomalies.append({"description": content, "severity": "medium"})

        return {
            "insights": insights if insights else ["Analysis complete - review data for details"],
            "patterns": patterns,
            "anomalies": anomalies,
            "key_metrics": {}
        }