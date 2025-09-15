"""
Warehouse Chaos Analyzer Agent
Analyzes current chaos metrics and identifies warehouse inefficiencies
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
import json
import pandas as pd
from datetime import datetime


class WarehouseChaosAnalyzer:
    """Analyzes warehouse chaos metrics and identifies optimization opportunities"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the chaos analyzer with LLM"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )
        logger.info("WarehouseChaosAnalyzer initialized")

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze warehouse chaos metrics and identify problems

        Args:
            state: Contains chaos_metrics, fragmentation_data, velocity_mismatches, warehouse_layout

        Returns:
            Analysis results including problem areas, severity scores, and heat maps
        """
        try:
            chaos_metrics = state.get("chaos_metrics", {})
            fragmentation_data = state.get("fragmentation_data", {})
            velocity_mismatches = state.get("velocity_mismatches", {})
            fifo_violations = state.get("fifo_violations", [])
            warehouse_layout = state.get("warehouse_layout", {})

            system_prompt = """You are a warehouse efficiency expert analyzing chaos metrics.
            Your role is to identify inefficiencies, quantify their impact, and prioritize problems.

            Focus on:
            1. Batch fragmentation patterns and consolidation opportunities
            2. Velocity mismatch severity and relocation priorities
            3. FIFO compliance issues and expiry risks
            4. Capacity imbalances and hotspot identification
            5. Overall warehouse efficiency score

            Provide specific, measurable insights with severity scores (1-10).
            """

            analysis_prompt = f"""
            Analyze the following warehouse chaos metrics:

            CHAOS METRICS:
            - Overall Chaos Score: {chaos_metrics.get('overall_chaos_score', 0)}%
            - Improvement Potential: {chaos_metrics.get('total_improvement_potential', 0)}%
            - Individual Metrics: {json.dumps(chaos_metrics.get('chaos_metrics', []), indent=2)}

            BATCH FRAGMENTATION:
            - Fragmented Batches: {fragmentation_data.get('total_fragmented', 0)}
            - Total Batches: {fragmentation_data.get('total_batches', 0)}
            - Fragmentation Rate: {fragmentation_data.get('fragmentation_rate', 0)}%
            - Top Fragmented: {json.dumps(fragmentation_data.get('fragmented_batches', [])[:5], indent=2)}

            VELOCITY MISMATCHES:
            - Total Mismatches: {velocity_mismatches.get('total_mismatches', 0)}
            - Fast Items in Back: {len([m for m in velocity_mismatches.get('velocity_mismatches', []) if 'Fast item in back' in m.get('issue', '')])}
            - Slow Items in Front: {len([m for m in velocity_mismatches.get('velocity_mismatches', []) if 'Slow item in front' in m.get('issue', '')])}

            FIFO VIOLATIONS:
            - Total Violations: {len(fifo_violations)}
            - Items at Risk: {sum(1 for v in fifo_violations if v.get('days_until_expiry', 999) < 30)}

            Provide a comprehensive analysis including:
            1. TOP PROBLEMS: List the 5 most critical issues with severity scores
            2. HEAT MAP DATA: Identify problem zones in the warehouse (by aisle/shelf)
            3. FINANCIAL IMPACT: Estimate cost implications of current inefficiencies
            4. QUICK WINS: Identify easy optimizations with high impact
            5. RISK ASSESSMENT: Flag critical issues requiring immediate attention

            Format as JSON with clear structure.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                analysis = self._parse_text_response(response.content)

            # Generate heat map data based on problems
            heat_map = self._generate_heat_map(
                fragmentation_data,
                velocity_mismatches,
                warehouse_layout
            )

            # Calculate efficiency score
            efficiency_score = 100 - chaos_metrics.get('overall_chaos_score', 0)

            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "efficiency_score": efficiency_score,
                "chaos_breakdown": chaos_metrics.get('chaos_metrics', []),
                "top_problems": analysis.get("TOP_PROBLEMS", []),
                "heat_map_data": heat_map,
                "financial_impact": analysis.get("FINANCIAL_IMPACT", {}),
                "quick_wins": analysis.get("QUICK_WINS", []),
                "risk_assessment": analysis.get("RISK_ASSESSMENT", {}),
                "problem_zones": self._identify_problem_zones(
                    fragmentation_data,
                    velocity_mismatches
                ),
                "optimization_potential": {
                    "batch_consolidation": fragmentation_data.get('total_fragmented', 0),
                    "velocity_corrections": velocity_mismatches.get('total_mismatches', 0),
                    "fifo_fixes": len(fifo_violations),
                    "estimated_time_savings": self._estimate_time_savings(chaos_metrics)
                }
            }

        except Exception as e:
            logger.error(f"Error in chaos analysis: {str(e)}")
            return {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat(),
                "efficiency_score": 0,
                "chaos_breakdown": [],
                "top_problems": [],
                "heat_map_data": {},
                "financial_impact": {},
                "quick_wins": [],
                "risk_assessment": {},
                "problem_zones": [],
                "optimization_potential": {}
            }

    def _generate_heat_map(
        self,
        fragmentation_data: Dict,
        velocity_mismatches: Dict,
        warehouse_layout: Dict
    ) -> Dict[str, Any]:
        """Generate heat map data for warehouse visualization"""
        heat_map = {}

        # Process fragmented batches to identify hot zones
        for batch in fragmentation_data.get('fragmented_batches', []):
            locations = batch.get('locations', '').split(',')
            for loc in locations:
                if loc:
                    heat_map[loc] = heat_map.get(loc, 0) + 1

        # Process velocity mismatches
        for mismatch in velocity_mismatches.get('velocity_mismatches', []):
            location = mismatch.get('location', '')
            if location:
                heat_map[location] = heat_map.get(location, 0) + 2  # Higher weight

        # Normalize scores to 0-10 scale
        max_score = max(heat_map.values()) if heat_map else 1
        normalized_heat_map = {
            loc: min(10, (score / max_score) * 10)
            for loc, score in heat_map.items()
        }

        return {
            "zones": normalized_heat_map,
            "legend": {
                "0-3": "Low Problem Density",
                "4-6": "Medium Problem Density",
                "7-10": "High Problem Density"
            },
            "hotspots": sorted(
                normalized_heat_map.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def _identify_problem_zones(
        self,
        fragmentation_data: Dict,
        velocity_mismatches: Dict
    ) -> List[Dict[str, Any]]:
        """Identify specific warehouse zones with problems"""
        zones = []

        # Analyze fragmentation by zone
        zone_problems = {}
        for batch in fragmentation_data.get('fragmented_batches', []):
            locations = batch.get('locations', '').split(',')
            for loc in locations:
                if loc and '-' in loc:
                    aisle = loc.split('-')[0]
                    if aisle not in zone_problems:
                        zone_problems[aisle] = {
                            'fragmentation': 0,
                            'velocity_issues': 0,
                            'total_problems': 0
                        }
                    zone_problems[aisle]['fragmentation'] += 1
                    zone_problems[aisle]['total_problems'] += 1

        # Analyze velocity mismatches by zone
        for mismatch in velocity_mismatches.get('velocity_mismatches', []):
            location = mismatch.get('location', '')
            if location and '-' in location:
                aisle = location.split('-')[0]
                if aisle not in zone_problems:
                    zone_problems[aisle] = {
                        'fragmentation': 0,
                        'velocity_issues': 0,
                        'total_problems': 0
                    }
                zone_problems[aisle]['velocity_issues'] += 1
                zone_problems[aisle]['total_problems'] += 1

        # Convert to list with severity scores
        for aisle, problems in zone_problems.items():
            severity = min(10, problems['total_problems'] / 2)
            zones.append({
                'aisle': aisle,
                'fragmentation_count': problems['fragmentation'],
                'velocity_issues': problems['velocity_issues'],
                'total_problems': problems['total_problems'],
                'severity_score': round(severity, 1),
                'priority': 'High' if severity > 7 else 'Medium' if severity > 4 else 'Low'
            })

        return sorted(zones, key=lambda x: x['severity_score'], reverse=True)

    def _estimate_time_savings(self, chaos_metrics: Dict) -> Dict[str, float]:
        """Estimate time savings from optimization"""
        overall_chaos = chaos_metrics.get('overall_chaos_score', 0)

        # Rough estimates based on chaos score
        picking_time_reduction = overall_chaos * 1.5  # 1.5% per chaos point
        travel_distance_reduction = overall_chaos * 1.2  # 1.2% per chaos point
        inventory_check_reduction = overall_chaos * 0.8  # 0.8% per chaos point

        return {
            "picking_time_reduction_percent": round(picking_time_reduction, 1),
            "travel_distance_reduction_percent": round(travel_distance_reduction, 1),
            "inventory_check_reduction_percent": round(inventory_check_reduction, 1),
            "total_efficiency_gain_percent": round(
                (picking_time_reduction + travel_distance_reduction + inventory_check_reduction) / 3,
                1
            )
        }

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response if JSON parsing fails"""
        result = {
            "TOP_PROBLEMS": [],
            "FINANCIAL_IMPACT": {},
            "QUICK_WINS": [],
            "RISK_ASSESSMENT": {}
        }

        lines = text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if 'TOP PROBLEMS' in line.upper():
                current_section = 'TOP_PROBLEMS'
            elif 'FINANCIAL IMPACT' in line.upper():
                current_section = 'FINANCIAL_IMPACT'
            elif 'QUICK WINS' in line.upper():
                current_section = 'QUICK_WINS'
            elif 'RISK ASSESSMENT' in line.upper():
                current_section = 'RISK_ASSESSMENT'
            elif line and current_section:
                if current_section == 'TOP_PROBLEMS' and line.startswith(('-', '*', '•', '1', '2', '3', '4', '5')):
                    result['TOP_PROBLEMS'].append(line.lstrip('-*•0123456789. '))
                elif current_section == 'QUICK_WINS' and line.startswith(('-', '*', '•')):
                    result['QUICK_WINS'].append(line.lstrip('-*• '))

        return result