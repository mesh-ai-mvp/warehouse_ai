"""
Placement Optimizer Agent
Optimizes product placement based on velocity, similarity, and warehouse constraints
"""

from typing import Dict, Any, List, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
import json
from datetime import datetime
import math


class PlacementOptimizer:
    """Optimizes warehouse product placement for efficiency"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the placement optimizer with LLM"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )
        logger.info("PlacementOptimizer initialized")

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and optimize product placement in warehouse

        Args:
            state: Contains current_placements, velocity_data, similarity_matrix, warehouse_layout

        Returns:
            Placement optimization recommendations and relocation plans
        """
        try:
            current_placements = state.get("current_placements", [])
            velocity_data = state.get("velocity_data", {})
            fragmentation_data = state.get("fragmentation_data", {})
            warehouse_layout = state.get("warehouse_layout", {})
            consumption_patterns = state.get("consumption_patterns", {})

            system_prompt = """You are a warehouse placement optimization expert.
            Your goal is to minimize picking time, travel distance, and operational costs.

            Optimization principles:
            1. VELOCITY-BASED PLACEMENT: Fast-moving items in front (grid_y=1), slow in back (grid_y=3)
            2. BATCH CONSOLIDATION: Same lot numbers should be together
            3. CATEGORY CLUSTERING: Similar items should be near each other
            4. GOLDEN ZONE: High-value, fast-moving items at optimal picking height
            5. WEIGHT DISTRIBUTION: Heavy items on lower shelves
            6. TEMPERATURE ZONES: Respect storage requirements

            Provide specific, actionable placement recommendations with ROI estimates.
            """

            analysis_prompt = f"""
            Analyze current warehouse placement and provide optimization recommendations:

            CURRENT PLACEMENT ISSUES:
            - Velocity Mismatches: {velocity_data.get('total_mismatches', 0)}
            - Fragmented Batches: {fragmentation_data.get('total_fragmented', 0)}
            - Fast Items in Back: {velocity_data.get('fast_in_back_count', 0)}
            - Slow Items in Front: {velocity_data.get('slow_in_front_count', 0)}

            WAREHOUSE CONSTRAINTS:
            - Total Positions: {warehouse_layout.get('total_positions', 2880)}
            - Available Positions: {warehouse_layout.get('available_positions', 0)}
            - Aisles: {warehouse_layout.get('aisle_count', 6)}
            - Temperature Zones: {json.dumps(warehouse_layout.get('temperature_zones', {}), indent=2)}

            TOP MISPLACED ITEMS:
            {json.dumps(velocity_data.get('velocity_mismatches', [])[:10], indent=2)}

            FRAGMENTED BATCHES:
            {json.dumps(fragmentation_data.get('fragmented_batches', [])[:10], indent=2)}

            Provide optimization plan including:
            1. IMMEDIATE_MOVES: Top 10 relocations with highest impact
            2. CONSOLIDATION_PLAN: Batch consolidation strategy
            3. ZONE_REORGANIZATION: Optimal zone allocation by velocity
            4. CLUSTERING_OPPORTUNITIES: Items that should be grouped
            5. ESTIMATED_SAVINGS: Time and cost savings from optimization

            Format as JSON with specific shelf positions and move sequences.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            try:
                optimization_plan = json.loads(response.content)
            except json.JSONDecodeError:
                optimization_plan = self._parse_text_response(response.content)

            # Generate specific relocation plan
            relocation_plan = self._generate_relocation_plan(
                current_placements,
                velocity_data,
                fragmentation_data,
                warehouse_layout
            )

            # Calculate optimization metrics
            optimization_metrics = self._calculate_optimization_metrics(
                velocity_data,
                fragmentation_data
            )

            # Generate clustering recommendations
            clustering_plan = self._generate_clustering_plan(
                current_placements,
                consumption_patterns
            )

            return {
                "optimization_timestamp": datetime.now().isoformat(),
                "immediate_moves": optimization_plan.get("IMMEDIATE_MOVES", []),
                "consolidation_plan": optimization_plan.get("CONSOLIDATION_PLAN", {}),
                "zone_reorganization": optimization_plan.get("ZONE_REORGANIZATION", {}),
                "clustering_opportunities": clustering_plan,
                "relocation_plan": relocation_plan,
                "optimization_metrics": optimization_metrics,
                "estimated_savings": {
                    "picking_time_reduction": optimization_metrics['potential_time_savings'],
                    "travel_distance_reduction": optimization_metrics['distance_reduction'],
                    "annual_cost_savings": optimization_metrics['estimated_annual_savings'],
                    "implementation_hours": optimization_metrics['implementation_effort']
                },
                "golden_zone_optimization": self._optimize_golden_zone(
                    current_placements,
                    velocity_data
                ),
                "abc_analysis": self._perform_abc_analysis(velocity_data),
                "move_sequence": self._generate_move_sequence(relocation_plan)
            }

        except Exception as e:
            logger.error(f"Error in placement optimization: {str(e)}")
            return {
                "error": str(e),
                "optimization_timestamp": datetime.now().isoformat(),
                "immediate_moves": [],
                "consolidation_plan": {},
                "zone_reorganization": {},
                "clustering_opportunities": [],
                "relocation_plan": [],
                "optimization_metrics": {},
                "estimated_savings": {},
                "golden_zone_optimization": {},
                "abc_analysis": {},
                "move_sequence": []
            }

    def _generate_relocation_plan(
        self,
        current_placements: List[Dict],
        velocity_data: Dict,
        fragmentation_data: Dict,
        warehouse_layout: Dict
    ) -> List[Dict[str, Any]]:
        """Generate specific relocation recommendations"""
        relocations = []

        # Priority 1: Fix velocity mismatches
        for mismatch in velocity_data.get('velocity_mismatches', [])[:20]:
            optimal_zone = self._get_optimal_zone(mismatch['movement_category'])
            relocations.append({
                'item': mismatch['medication_name'],
                'current_location': mismatch['location'],
                'recommended_location': optimal_zone,
                'reason': mismatch['issue'],
                'priority': 'High' if mismatch['movement_category'] == 'Fast' else 'Medium',
                'impact_score': self._calculate_impact_score(mismatch),
                'estimated_time_saving': f"{mismatch.get('velocity_score', 0) * 0.5:.1f} min/day"
            })

        # Priority 2: Consolidate fragmented batches
        for batch in fragmentation_data.get('fragmented_batches', [])[:10]:
            relocations.append({
                'item': batch['medication_name'],
                'batch_id': batch['batch_id'],
                'current_locations': batch['locations'].split(','),
                'recommended_action': 'Consolidate to single location',
                'reason': f"Batch split across {batch['num_locations']} locations",
                'priority': 'High' if batch['num_locations'] > 3 else 'Medium',
                'impact_score': batch['num_locations'] * 2,
                'quantity': batch['total_quantity']
            })

        # Sort by impact score
        relocations.sort(key=lambda x: x.get('impact_score', 0), reverse=True)

        return relocations[:30]  # Top 30 relocations

    def _calculate_optimization_metrics(
        self,
        velocity_data: Dict,
        fragmentation_data: Dict
    ) -> Dict[str, Any]:
        """Calculate metrics for optimization impact"""
        total_mismatches = velocity_data.get('total_mismatches', 0)
        total_fragmented = fragmentation_data.get('total_fragmented', 0)

        # Estimate time savings (minutes per day)
        velocity_time_saving = total_mismatches * 2.5  # 2.5 min per mismatch
        fragmentation_time_saving = total_fragmented * 4  # 4 min per fragmented batch
        total_time_saving = velocity_time_saving + fragmentation_time_saving

        # Estimate distance reduction (meters per day)
        distance_reduction = total_mismatches * 15 + total_fragmented * 25

        # Cost calculations (assuming $25/hour labor cost)
        hourly_cost = 25
        daily_hours_saved = total_time_saving / 60
        annual_savings = daily_hours_saved * hourly_cost * 365

        # Implementation effort (hours)
        moves_required = total_mismatches + (total_fragmented * 2)
        implementation_hours = moves_required * 0.25  # 15 min per move

        return {
            'total_optimizations': total_mismatches + total_fragmented,
            'potential_time_savings': f"{total_time_saving:.0f} min/day",
            'distance_reduction': f"{distance_reduction:.0f} meters/day",
            'estimated_annual_savings': f"${annual_savings:,.0f}",
            'implementation_effort': f"{implementation_hours:.1f} hours",
            'roi_days': max(1, int(implementation_hours * hourly_cost / (daily_hours_saved * hourly_cost))) if daily_hours_saved > 0 else 999,
            'efficiency_improvement': f"{min(40, (total_mismatches + total_fragmented) * 0.5):.1f}%"
        }

    def _generate_clustering_plan(
        self,
        current_placements: List[Dict],
        consumption_patterns: Dict
    ) -> List[Dict[str, Any]]:
        """Generate item clustering recommendations"""
        clusters = []

        # Identify frequently co-ordered items
        common_pairs = consumption_patterns.get('common_pairs', [])
        for pair in common_pairs[:10]:
            clusters.append({
                'items': pair['items'],
                'co_order_frequency': pair['frequency'],
                'current_distance': pair.get('current_distance', 'Unknown'),
                'recommendation': 'Place in adjacent positions',
                'estimated_benefit': f"{pair['frequency'] * 0.5:.1f} min/week saved"
            })

        # Group by therapeutic category
        categories = {}
        for placement in current_placements:
            category = placement.get('category', 'Unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(placement.get('medication_name'))

        for category, items in categories.items():
            if len(items) > 3:
                clusters.append({
                    'category': category,
                    'items_count': len(items),
                    'recommendation': f"Create dedicated zone for {category}",
                    'benefit': 'Improved picking efficiency and inventory management'
                })

        return clusters

    def _optimize_golden_zone(
        self,
        current_placements: List[Dict],
        velocity_data: Dict
    ) -> Dict[str, Any]:
        """Optimize golden zone placement for high-value fast movers"""
        golden_zone_items = []

        # Golden zone is typically shelf level 1 (waist to shoulder height)
        for item in velocity_data.get('velocity_mismatches', []):
            if item['movement_category'] == 'Fast':
                golden_zone_items.append({
                    'item': item['medication_name'],
                    'velocity_score': item['velocity_score'],
                    'current_position': item['location'],
                    'optimal_height': 'Shelf Level 1 (Golden Zone)',
                    'expected_picks_per_day': int(item['velocity_score'] * 10)
                })

        golden_zone_items.sort(key=lambda x: x['velocity_score'], reverse=True)

        return {
            'total_golden_zone_candidates': len(golden_zone_items),
            'top_candidates': golden_zone_items[:20],
            'expected_efficiency_gain': f"{len(golden_zone_items) * 1.2:.1f}%",
            'ergonomic_benefit': 'Reduced bending and reaching'
        }

    def _perform_abc_analysis(self, velocity_data: Dict) -> Dict[str, Any]:
        """Perform ABC analysis for inventory classification"""
        items = velocity_data.get('all_items', [])
        total_items = len(items)

        # ABC Classification
        a_items = int(total_items * 0.2)  # 20% of items (80% of movement)
        b_items = int(total_items * 0.3)  # 30% of items (15% of movement)
        c_items = total_items - a_items - b_items  # 50% of items (5% of movement)

        return {
            'classification': {
                'A_items': {
                    'count': a_items,
                    'percentage': 20,
                    'placement': 'Front zone (grid_y=1)',
                    'strategy': 'Prime locations, frequent cycle counting'
                },
                'B_items': {
                    'count': b_items,
                    'percentage': 30,
                    'placement': 'Middle zone (grid_y=2)',
                    'strategy': 'Standard locations, regular monitoring'
                },
                'C_items': {
                    'count': c_items,
                    'percentage': 50,
                    'placement': 'Back zone (grid_y=3)',
                    'strategy': 'High-density storage, periodic review'
                }
            },
            'optimization_potential': 'Proper ABC placement can reduce picking time by 25-35%'
        }

    def _generate_move_sequence(self, relocation_plan: List[Dict]) -> List[Dict[str, Any]]:
        """Generate optimal sequence for executing moves"""
        sequence = []

        # Group moves by priority and location
        high_priority = [m for m in relocation_plan if m.get('priority') == 'High']
        medium_priority = [m for m in relocation_plan if m.get('priority') == 'Medium']

        # Phase 1: Clear space for high-priority moves
        phase = 1
        for move in high_priority[:10]:
            sequence.append({
                'phase': phase,
                'step': len(sequence) + 1,
                'action': f"Relocate {move.get('item', 'item')}",
                'from': move.get('current_location', 'current'),
                'to': move.get('recommended_location', 'optimal zone'),
                'estimated_time': '15 minutes',
                'resources_needed': '1 operator, 1 forklift'
            })

        # Phase 2: Consolidation moves
        phase = 2
        for move in relocation_plan:
            if 'batch_id' in move:
                sequence.append({
                    'phase': phase,
                    'step': len(sequence) + 1,
                    'action': f"Consolidate batch {move['batch_id']}",
                    'locations': move.get('current_locations', []),
                    'estimated_time': '30 minutes',
                    'resources_needed': '2 operators, 1 pallet jack'
                })

        return sequence[:20]  # Limit to 20 steps for initial implementation

    def _get_optimal_zone(self, movement_category: str) -> str:
        """Get optimal zone based on movement category"""
        zones = {
            'Fast': 'A1-S1-P1 (Front, Lower, First Position)',
            'Medium': 'B1-S1-P5 (Middle, Lower, Mid Position)',
            'Slow': 'C1-S2-P8 (Back, Upper, Deep Position)'
        }
        return zones.get(movement_category, 'B1-S1-P5')

    def _calculate_impact_score(self, mismatch: Dict) -> float:
        """Calculate impact score for a placement issue"""
        base_score = mismatch.get('velocity_score', 0)

        # Multiply by severity factor
        if 'Fast item in back' in mismatch.get('issue', ''):
            return base_score * 3
        elif 'Slow item in front' in mismatch.get('issue', ''):
            return base_score * 2
        else:
            return base_score * 1.5

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response if JSON parsing fails"""
        result = {
            "IMMEDIATE_MOVES": [],
            "CONSOLIDATION_PLAN": {},
            "ZONE_REORGANIZATION": {},
            "CLUSTERING_OPPORTUNITIES": [],
            "ESTIMATED_SAVINGS": {}
        }

        lines = text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if 'IMMEDIATE MOVES' in line.upper():
                current_section = 'IMMEDIATE_MOVES'
            elif 'CONSOLIDATION' in line.upper():
                current_section = 'CONSOLIDATION_PLAN'
            elif 'ZONE' in line.upper():
                current_section = 'ZONE_REORGANIZATION'
            elif 'CLUSTERING' in line.upper():
                current_section = 'CLUSTERING_OPPORTUNITIES'
            elif 'SAVINGS' in line.upper():
                current_section = 'ESTIMATED_SAVINGS'
            elif line and current_section:
                if current_section == 'IMMEDIATE_MOVES' and line.startswith(('-', '*', '•', '1', '2', '3')):
                    result['IMMEDIATE_MOVES'].append(line.lstrip('-*•0123456789. '))

        return result