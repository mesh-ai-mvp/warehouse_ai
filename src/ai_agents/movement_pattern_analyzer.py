"""
Movement Pattern Analyzer Agent
Analyzes historical movement data to identify inefficiencies and optimization opportunities
"""

from typing import Dict, Any, List, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
import json
from datetime import datetime, timedelta
import statistics


class MovementPatternAnalyzer:
    """Analyzes warehouse movement patterns for efficiency optimization"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the movement pattern analyzer with LLM"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )
        logger.info("MovementPatternAnalyzer initialized")

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze movement patterns and identify optimization opportunities

        Args:
            state: Contains movement_history, picking_paths, congestion_data, layout_info

        Returns:
            Movement pattern analysis with optimization recommendations
        """
        try:
            movement_history = state.get("movement_history", [])
            picking_paths = state.get("picking_paths", [])
            congestion_data = state.get("congestion_data", {})
            layout_info = state.get("layout_info", {})
            hourly_patterns = state.get("hourly_patterns", [])

            system_prompt = """You are a warehouse movement optimization expert.
            Your goal is to minimize travel distance, reduce congestion, and optimize picking paths.

            Analysis focus:
            1. PICKING PATH EFFICIENCY: Identify suboptimal routes
            2. CONGESTION PATTERNS: Find bottlenecks and peak times
            3. TRAVEL DISTANCE: Calculate and reduce unnecessary movement
            4. LAYOUT OPTIMIZATION: Suggest layout changes for better flow
            5. TIME-BASED PATTERNS: Optimize based on hourly/daily patterns

            Provide specific, measurable recommendations with expected improvements.
            """

            analysis_prompt = f"""
            Analyze warehouse movement patterns and provide optimization recommendations:

            MOVEMENT STATISTICS:
            - Total Movements (30 days): {len(movement_history)}
            - Average Daily Movements: {len(movement_history) / 30:.0f}
            - Peak Hour: {self._identify_peak_hour(hourly_patterns)}
            - Most Accessed Zones: {json.dumps(self._get_top_zones(movement_history), indent=2)}

            PICKING PATH ANALYSIS:
            - Average Path Length: {self._calculate_avg_path_length(picking_paths)} meters
            - Backtracking Instances: {self._count_backtracking(picking_paths)}
            - Cross-Aisle Movements: {self._count_cross_aisle(picking_paths)}

            CONGESTION DATA:
            - Bottleneck Zones: {json.dumps(congestion_data.get('bottlenecks', []), indent=2)}
            - Peak Congestion Times: {congestion_data.get('peak_times', [])}
            - Average Wait Time: {congestion_data.get('avg_wait_time', 0)} seconds

            HOURLY PATTERNS:
            {json.dumps(hourly_patterns[:24], indent=2)}

            Provide optimization analysis including:
            1. PATH_OPTIMIZATION: Improved picking routes with distance savings
            2. CONGESTION_MITIGATION: Strategies to reduce bottlenecks
            3. LAYOUT_RECOMMENDATIONS: Physical layout changes for better flow
            4. SCHEDULING_OPTIMIZATION: Time-based strategies for efficiency
            5. TECHNOLOGY_SUGGESTIONS: Tools/systems to improve movement

            Format as JSON with specific metrics and expected improvements.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            try:
                movement_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                movement_analysis = self._parse_text_response(response.content)

            # Generate detailed movement analysis
            detailed_analysis = self._perform_detailed_analysis(
                movement_history,
                picking_paths,
                hourly_patterns
            )

            # Calculate optimization opportunities
            optimization_opportunities = self._calculate_optimization_opportunities(
                picking_paths,
                congestion_data,
                detailed_analysis
            )

            # Generate picking strategy recommendations
            picking_strategies = self._generate_picking_strategies(
                picking_paths,
                layout_info
            )

            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "movement_statistics": detailed_analysis,
                "path_optimization": movement_analysis.get("PATH_OPTIMIZATION", {}),
                "congestion_mitigation": movement_analysis.get("CONGESTION_MITIGATION", {}),
                "layout_recommendations": self._generate_layout_recommendations(
                    movement_history,
                    congestion_data
                ),
                "scheduling_optimization": self._optimize_scheduling(hourly_patterns),
                "technology_suggestions": movement_analysis.get("TECHNOLOGY_SUGGESTIONS", []),
                "picking_strategies": picking_strategies,
                "optimization_opportunities": optimization_opportunities,
                "efficiency_metrics": self._calculate_efficiency_metrics(
                    picking_paths,
                    congestion_data
                ),
                "heat_flow_map": self._generate_heat_flow_map(movement_history),
                "recommended_zones": self._recommend_zone_changes(
                    movement_history,
                    congestion_data
                )
            }

        except Exception as e:
            logger.error(f"Error in movement pattern analysis: {str(e)}")
            return {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat(),
                "movement_statistics": {},
                "path_optimization": {},
                "congestion_mitigation": {},
                "layout_recommendations": [],
                "scheduling_optimization": {},
                "technology_suggestions": [],
                "picking_strategies": {},
                "optimization_opportunities": {},
                "efficiency_metrics": {},
                "heat_flow_map": {},
                "recommended_zones": []
            }

    def _identify_peak_hour(self, hourly_patterns: List[Dict]) -> str:
        """Identify peak movement hour"""
        if not hourly_patterns:
            return "Unknown"

        peak = max(hourly_patterns, key=lambda x: x.get('movements', 0))
        return f"{peak.get('hour', 'Unknown')}:00"

    def _get_top_zones(self, movement_history: List[Dict]) -> List[Dict]:
        """Get most accessed zones"""
        zone_counts = {}

        for movement in movement_history:
            from_zone = movement.get('from_zone', '')
            to_zone = movement.get('to_zone', '')

            if from_zone:
                zone_counts[from_zone] = zone_counts.get(from_zone, 0) + 1
            if to_zone:
                zone_counts[to_zone] = zone_counts.get(to_zone, 0) + 1

        # Sort by count and return top 5
        sorted_zones = sorted(zone_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {'zone': zone, 'access_count': count, 'percentage': count * 100 / len(movement_history)}
            for zone, count in sorted_zones[:5]
        ]

    def _calculate_avg_path_length(self, picking_paths: List[Dict]) -> float:
        """Calculate average picking path length"""
        if not picking_paths:
            return 0

        total_length = sum(path.get('distance', 0) for path in picking_paths)
        return round(total_length / len(picking_paths), 1)

    def _count_backtracking(self, picking_paths: List[Dict]) -> int:
        """Count instances of backtracking in picking paths"""
        backtrack_count = 0

        for path in picking_paths:
            stops = path.get('stops', [])
            for i in range(2, len(stops)):
                # Check if we're going back to a previously visited aisle
                current_aisle = stops[i].get('aisle')
                if current_aisle in [stops[j].get('aisle') for j in range(i-1)]:
                    backtrack_count += 1

        return backtrack_count

    def _count_cross_aisle(self, picking_paths: List[Dict]) -> int:
        """Count cross-aisle movements"""
        cross_count = 0

        for path in picking_paths:
            stops = path.get('stops', [])
            for i in range(1, len(stops)):
                prev_aisle = stops[i-1].get('aisle', '')
                curr_aisle = stops[i].get('aisle', '')
                if prev_aisle and curr_aisle and prev_aisle != curr_aisle:
                    cross_count += 1

        return cross_count

    def _perform_detailed_analysis(
        self,
        movement_history: List[Dict],
        picking_paths: List[Dict],
        hourly_patterns: List[Dict]
    ) -> Dict[str, Any]:
        """Perform detailed movement analysis"""

        # Calculate movement metrics
        total_movements = len(movement_history)
        avg_daily = total_movements / 30 if total_movements > 0 else 0

        # Distance analysis
        distances = [m.get('distance', 0) for m in movement_history if m.get('distance')]
        avg_distance = statistics.mean(distances) if distances else 0
        total_distance = sum(distances)

        # Time analysis
        times = [m.get('time_minutes', 0) for m in movement_history if m.get('time_minutes')]
        avg_time = statistics.mean(times) if times else 0
        total_time = sum(times)

        # Peak analysis
        peak_hour_data = max(hourly_patterns, key=lambda x: x.get('movements', 0)) if hourly_patterns else {}
        off_peak_avg = statistics.mean([h.get('movements', 0) for h in hourly_patterns if h.get('hour') not in ['10', '11', '14', '15']]) if hourly_patterns else 0

        return {
            'total_movements_30d': total_movements,
            'average_daily_movements': round(avg_daily, 0),
            'total_distance_traveled': f"{total_distance:.0f} meters",
            'average_movement_distance': f"{avg_distance:.1f} meters",
            'total_time_spent': f"{total_time:.0f} minutes",
            'average_movement_time': f"{avg_time:.1f} minutes",
            'peak_hour_movements': peak_hour_data.get('movements', 0),
            'off_peak_average': round(off_peak_avg, 0),
            'efficiency_score': self._calculate_movement_efficiency(distances, times)
        }

    def _calculate_optimization_opportunities(
        self,
        picking_paths: List[Dict],
        congestion_data: Dict,
        detailed_analysis: Dict
    ) -> Dict[str, Any]:
        """Calculate specific optimization opportunities"""

        # Path optimization potential
        current_avg_path = self._calculate_avg_path_length(picking_paths)
        optimal_path = current_avg_path * 0.7  # Assume 30% reduction possible
        path_savings = current_avg_path - optimal_path

        # Congestion reduction potential
        wait_time = congestion_data.get('avg_wait_time', 0)
        congestion_reduction = wait_time * 0.5  # Assume 50% reduction possible

        # Calculate annual savings
        movements_per_year = detailed_analysis['average_daily_movements'] * 365
        time_saved_per_movement = (path_savings / 10) + (congestion_reduction / 60)  # Convert to minutes
        annual_time_savings = movements_per_year * time_saved_per_movement
        annual_cost_savings = (annual_time_savings / 60) * 25  # $25/hour labor

        return {
            'path_optimization': {
                'current_avg_distance': f"{current_avg_path:.1f} meters",
                'optimal_avg_distance': f"{optimal_path:.1f} meters",
                'distance_reduction': f"{path_savings:.1f} meters per pick",
                'percentage_improvement': f"{(path_savings/current_avg_path*100):.1f}%"
            },
            'congestion_reduction': {
                'current_wait_time': f"{wait_time:.0f} seconds",
                'reduced_wait_time': f"{wait_time*0.5:.0f} seconds",
                'time_saved': f"{congestion_reduction:.0f} seconds per movement"
            },
            'annual_impact': {
                'time_savings': f"{annual_time_savings:.0f} minutes",
                'cost_savings': f"${annual_cost_savings:,.0f}",
                'productivity_gain': f"{(time_saved_per_movement/10*100):.1f}%"
            }
        }

    def _generate_picking_strategies(
        self,
        picking_paths: List[Dict],
        layout_info: Dict
    ) -> Dict[str, Any]:
        """Generate optimal picking strategies"""

        strategies = {
            'batch_picking': {
                'description': 'Group multiple orders for simultaneous picking',
                'suitable_for': 'Small items with high order frequency',
                'expected_improvement': '35-40% reduction in travel time',
                'implementation': 'Group 4-6 orders with overlapping SKUs'
            },
            'zone_picking': {
                'description': 'Assign pickers to specific warehouse zones',
                'suitable_for': 'Large warehouse with diverse product types',
                'expected_improvement': '25-30% reduction in congestion',
                'implementation': 'Divide warehouse into 4 zones with dedicated pickers'
            },
            'wave_picking': {
                'description': 'Schedule picking in waves throughout the day',
                'suitable_for': 'Operations with predictable order patterns',
                'expected_improvement': '20-25% improvement in throughput',
                'implementation': 'Schedule 4 waves: 8am, 11am, 2pm, 5pm'
            },
            'optimal_routing': {
                'description': 'Use S-shape or return routing patterns',
                'current_pattern': self._identify_current_pattern(picking_paths),
                'recommended_pattern': 'S-shape for narrow aisles, Return for wide aisles',
                'expected_improvement': '15-20% reduction in travel distance'
            }
        }

        return strategies

    def _generate_layout_recommendations(
        self,
        movement_history: List[Dict],
        congestion_data: Dict
    ) -> List[Dict[str, Any]]:
        """Generate warehouse layout recommendations"""

        recommendations = []

        # Check for cross-traffic issues
        bottlenecks = congestion_data.get('bottlenecks', [])
        if bottlenecks:
            recommendations.append({
                'type': 'Cross-Aisle Addition',
                'location': bottlenecks[0] if bottlenecks else 'Center warehouse',
                'description': 'Add cross-aisle to reduce congestion',
                'expected_benefit': '30% reduction in travel distance',
                'implementation_cost': 'Low',
                'priority': 'High'
            })

        # Check for frequently accessed items placement
        top_zones = self._get_top_zones(movement_history)
        if top_zones and top_zones[0]['percentage'] > 30:
            recommendations.append({
                'type': 'Forward Pick Area',
                'location': 'Near shipping area',
                'description': 'Create forward pick area for fast movers',
                'expected_benefit': '40% reduction in picking time for A-items',
                'implementation_cost': 'Medium',
                'priority': 'High'
            })

        # Check for staging area optimization
        recommendations.append({
            'type': 'Staging Area Expansion',
            'location': 'Between picking and shipping',
            'description': 'Expand staging area to reduce congestion',
            'expected_benefit': '20% improvement in order processing',
            'implementation_cost': 'Low',
            'priority': 'Medium'
        })

        return recommendations

    def _optimize_scheduling(self, hourly_patterns: List[Dict]) -> Dict[str, Any]:
        """Optimize scheduling based on hourly patterns"""

        # Find peak and off-peak hours
        sorted_hours = sorted(hourly_patterns, key=lambda x: x.get('movements', 0), reverse=True)
        peak_hours = [h['hour'] for h in sorted_hours[:4]]
        off_peak_hours = [h['hour'] for h in sorted_hours[-4:]]

        return {
            'peak_hours': peak_hours,
            'off_peak_hours': off_peak_hours,
            'recommendations': [
                {
                    'strategy': 'Staggered Shifts',
                    'description': f"Add extra staff during peak hours: {', '.join(peak_hours)}:00",
                    'expected_benefit': '25% reduction in wait times'
                },
                {
                    'strategy': 'Off-Peak Activities',
                    'description': f"Schedule replenishment during: {', '.join(off_peak_hours)}:00",
                    'expected_benefit': '15% improvement in picking efficiency'
                },
                {
                    'strategy': 'Dynamic Slotting',
                    'description': 'Adjust fast-mover locations based on hourly demand',
                    'expected_benefit': '20% reduction in congestion'
                }
            ],
            'optimal_staff_schedule': self._generate_staff_schedule(hourly_patterns)
        }

    def _calculate_efficiency_metrics(
        self,
        picking_paths: List[Dict],
        congestion_data: Dict
    ) -> Dict[str, Any]:
        """Calculate movement efficiency metrics"""

        # Path efficiency
        optimal_paths = sum(1 for p in picking_paths if p.get('is_optimal', False))
        path_efficiency = (optimal_paths / len(picking_paths) * 100) if picking_paths else 0

        # Time efficiency
        avg_wait = congestion_data.get('avg_wait_time', 0)
        time_efficiency = max(0, 100 - (avg_wait / 60 * 10))  # Deduct 10% per minute of wait

        # Overall efficiency
        overall_efficiency = (path_efficiency + time_efficiency) / 2

        return {
            'path_efficiency': f"{path_efficiency:.1f}%",
            'time_efficiency': f"{time_efficiency:.1f}%",
            'overall_efficiency': f"{overall_efficiency:.1f}%",
            'benchmark_comparison': 'Below industry average' if overall_efficiency < 75 else 'At industry average' if overall_efficiency < 85 else 'Above industry average'
        }

    def _generate_heat_flow_map(self, movement_history: List[Dict]) -> Dict[str, Any]:
        """Generate heat flow map of movement patterns"""

        flow_map = {}

        for movement in movement_history:
            from_zone = movement.get('from_zone', '')
            to_zone = movement.get('to_zone', '')

            if from_zone and to_zone:
                flow_key = f"{from_zone}->{to_zone}"
                flow_map[flow_key] = flow_map.get(flow_key, 0) + 1

        # Normalize to 0-10 scale
        max_flow = max(flow_map.values()) if flow_map else 1
        normalized_flow = {
            route: min(10, (count / max_flow) * 10)
            for route, count in flow_map.items()
        }

        # Get top routes
        top_routes = sorted(flow_map.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'flow_intensity': normalized_flow,
            'top_routes': [
                {'route': route, 'frequency': count, 'intensity': normalized_flow.get(route, 0)}
                for route, count in top_routes
            ],
            'bottleneck_routes': [
                route for route, intensity in normalized_flow.items()
                if intensity > 7
            ]
        }

    def _recommend_zone_changes(
        self,
        movement_history: List[Dict],
        congestion_data: Dict
    ) -> List[Dict[str, Any]]:
        """Recommend zone configuration changes"""

        recommendations = []

        # Analyze zone access patterns
        zone_access = {}
        for movement in movement_history:
            zone = movement.get('to_zone', '')
            if zone:
                zone_access[zone] = zone_access.get(zone, 0) + 1

        # High-traffic zones
        high_traffic = [z for z, count in zone_access.items() if count > len(movement_history) * 0.1]

        for zone in high_traffic:
            recommendations.append({
                'zone': zone,
                'current_issue': 'High traffic volume',
                'recommendation': 'Widen aisles or add parallel paths',
                'expected_improvement': '20% reduction in congestion',
                'priority': 'High'
            })

        # Low-traffic zones
        low_traffic = [z for z, count in zone_access.items() if count < len(movement_history) * 0.02]

        for zone in low_traffic:
            recommendations.append({
                'zone': zone,
                'current_issue': 'Underutilized space',
                'recommendation': 'Relocate slow movers here or consolidate zone',
                'expected_improvement': '15% better space utilization',
                'priority': 'Medium'
            })

        return recommendations

    def _calculate_movement_efficiency(self, distances: List[float], times: List[float]) -> float:
        """Calculate overall movement efficiency score"""
        if not distances or not times:
            return 0

        # Calculate speed efficiency (meters per minute)
        speeds = [d/t for d, t in zip(distances, times) if t > 0]
        avg_speed = statistics.mean(speeds) if speeds else 0

        # Industry benchmark: 50 meters/minute is good
        efficiency = min(100, (avg_speed / 50) * 100)

        return round(efficiency, 1)

    def _identify_current_pattern(self, picking_paths: List[Dict]) -> str:
        """Identify current picking pattern"""
        # Simplified pattern detection
        if not picking_paths:
            return "Unknown"

        # Check for common patterns
        s_shape_count = sum(1 for p in picking_paths if p.get('pattern') == 's_shape')
        return_count = sum(1 for p in picking_paths if p.get('pattern') == 'return')

        if s_shape_count > return_count:
            return "S-shape"
        elif return_count > s_shape_count:
            return "Return"
        else:
            return "Mixed/Random"

    def _generate_staff_schedule(self, hourly_patterns: List[Dict]) -> Dict[str, int]:
        """Generate optimal staff schedule based on patterns"""
        schedule = {}

        for hour_data in hourly_patterns:
            hour = hour_data.get('hour', '')
            movements = hour_data.get('movements', 0)

            # Calculate staff needed (1 staff per 20 movements)
            staff_needed = max(2, movements // 20)

            schedule[f"{hour}:00"] = staff_needed

        return schedule

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response if JSON parsing fails"""
        result = {
            "PATH_OPTIMIZATION": {},
            "CONGESTION_MITIGATION": {},
            "LAYOUT_RECOMMENDATIONS": [],
            "SCHEDULING_OPTIMIZATION": {},
            "TECHNOLOGY_SUGGESTIONS": []
        }

        lines = text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if 'PATH' in line.upper():
                current_section = 'PATH_OPTIMIZATION'
            elif 'CONGESTION' in line.upper():
                current_section = 'CONGESTION_MITIGATION'
            elif 'LAYOUT' in line.upper():
                current_section = 'LAYOUT_RECOMMENDATIONS'
            elif 'SCHEDULING' in line.upper():
                current_section = 'SCHEDULING_OPTIMIZATION'
            elif 'TECHNOLOGY' in line.upper():
                current_section = 'TECHNOLOGY_SUGGESTIONS'
            elif line and current_section:
                if current_section in ['LAYOUT_RECOMMENDATIONS', 'TECHNOLOGY_SUGGESTIONS']:
                    if line.startswith(('-', '*', '•')):
                        result[current_section].append(line.lstrip('-*• '))

        return result