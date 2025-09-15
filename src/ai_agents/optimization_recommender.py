"""
Optimization Recommender Agent
Synthesizes outputs from all agents and generates actionable optimization plans
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
import json
from datetime import datetime, timedelta


class OptimizationRecommender:
    """Synthesizes all analyses and generates comprehensive optimization recommendations"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the optimization recommender with LLM"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2500
        )
        logger.info("OptimizationRecommender initialized")

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize all agent outputs and generate final recommendations

        Args:
            state: Contains outputs from all other agents

        Returns:
            Comprehensive optimization plan with prioritized actions
        """
        try:
            # Extract outputs from other agents
            chaos_analysis = state.get("chaos_analysis", {})
            placement_optimization = state.get("placement_optimization", {})
            compliance_report = state.get("compliance_report", {})
            movement_analysis = state.get("movement_analysis", {})

            system_prompt = """You are a warehouse optimization strategist synthesizing insights from multiple analyses.
            Your role is to create a comprehensive, actionable optimization plan.

            Synthesis principles:
            1. PRIORITIZATION: Rank recommendations by ROI and effort
            2. INTEGRATION: Ensure recommendations work together cohesively
            3. FEASIBILITY: Consider resource constraints and implementation complexity
            4. MEASUREMENT: Define clear KPIs and success metrics
            5. PHASING: Create logical implementation phases

            Provide a complete optimization roadmap with clear timelines and expected outcomes.
            """

            synthesis_prompt = f"""
            Synthesize the following analyses into a comprehensive optimization plan:

            CHAOS ANALYSIS SUMMARY:
            - Efficiency Score: {chaos_analysis.get('efficiency_score', 0)}%
            - Top Problems: {json.dumps(chaos_analysis.get('top_problems', [])[:3], indent=2)}
            - Quick Wins: {json.dumps(chaos_analysis.get('quick_wins', [])[:3], indent=2)}

            PLACEMENT OPTIMIZATION SUMMARY:
            - Immediate Moves: {len(placement_optimization.get('immediate_moves', []))}
            - Estimated Savings: {json.dumps(placement_optimization.get('estimated_savings', {}), indent=2)}
            - Consolidation Opportunities: {len(placement_optimization.get('consolidation_plan', {}).get('batches', []))}

            COMPLIANCE STATUS:
            - Overall Score: {compliance_report.get('compliance_scores', {}).get('overall', 0)}%
            - Critical Violations: {len(compliance_report.get('critical_violations', []))}
            - Items at Risk: {compliance_report.get('expiry_risk_assessment', {}).get('total_at_risk', 0)}

            MOVEMENT OPTIMIZATION:
            - Path Efficiency: {movement_analysis.get('efficiency_metrics', {}).get('overall_efficiency', 0)}
            - Congestion Points: {len(movement_analysis.get('congestion_mitigation', {}).get('bottlenecks', []))}
            - Layout Changes Needed: {len(movement_analysis.get('layout_recommendations', []))}

            Create an integrated optimization plan including:
            1. EXECUTIVE_SUMMARY: High-level overview and expected impact
            2. IMMEDIATE_ACTIONS: Actions for next 24-48 hours
            3. SHORT_TERM_PLAN: 1-2 week implementation plan
            4. LONG_TERM_STRATEGY: 1-3 month transformation roadmap
            5. SUCCESS_METRICS: KPIs and measurement framework
            6. RESOURCE_REQUIREMENTS: People, technology, and budget needs

            Format as JSON with specific actions, timelines, and expected outcomes.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=synthesis_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            try:
                optimization_plan = json.loads(response.content)
            except json.JSONDecodeError:
                optimization_plan = self._parse_text_response(response.content)

            # Generate comprehensive recommendations
            recommendations = self._generate_comprehensive_recommendations(
                chaos_analysis,
                placement_optimization,
                compliance_report,
                movement_analysis
            )

            # Create implementation roadmap
            roadmap = self._create_implementation_roadmap(
                recommendations,
                chaos_analysis,
                compliance_report
            )

            # Calculate ROI and prioritization
            roi_analysis = self._calculate_roi_analysis(
                placement_optimization,
                movement_analysis,
                compliance_report
            )

            # Generate success metrics
            success_metrics = self._define_success_metrics(
                chaos_analysis,
                compliance_report,
                movement_analysis
            )

            return {
                "recommendation_timestamp": datetime.now().isoformat(),
                "executive_summary": self._generate_executive_summary(
                    chaos_analysis,
                    roi_analysis,
                    recommendations
                ),
                "immediate_actions": self._prioritize_immediate_actions(
                    compliance_report,
                    placement_optimization,
                    recommendations
                ),
                "short_term_plan": roadmap['short_term'],
                "long_term_strategy": roadmap['long_term'],
                "comprehensive_recommendations": recommendations,
                "implementation_roadmap": roadmap,
                "roi_analysis": roi_analysis,
                "success_metrics": success_metrics,
                "resource_requirements": self._estimate_resource_requirements(
                    recommendations,
                    roadmap
                ),
                "risk_mitigation": self._identify_implementation_risks(
                    recommendations,
                    compliance_report
                ),
                "monitoring_plan": self._create_monitoring_plan(success_metrics),
                "optimization_score": self._calculate_optimization_score(
                    chaos_analysis,
                    compliance_report,
                    movement_analysis
                )
            }

        except Exception as e:
            logger.error(f"Error in optimization recommendation: {str(e)}")
            return {
                "error": str(e),
                "recommendation_timestamp": datetime.now().isoformat(),
                "executive_summary": {},
                "immediate_actions": [],
                "short_term_plan": {},
                "long_term_strategy": {},
                "comprehensive_recommendations": [],
                "implementation_roadmap": {},
                "roi_analysis": {},
                "success_metrics": {},
                "resource_requirements": {},
                "risk_mitigation": [],
                "monitoring_plan": {},
                "optimization_score": 0
            }

    def _generate_comprehensive_recommendations(
        self,
        chaos_analysis: Dict,
        placement_optimization: Dict,
        compliance_report: Dict,
        movement_analysis: Dict
    ) -> List[Dict[str, Any]]:
        """Generate comprehensive recommendations from all analyses"""

        recommendations = []

        # Priority 1: Compliance critical issues
        if compliance_report.get('compliance_scores', {}).get('overall', 100) < 80:
            recommendations.append({
                'category': 'Compliance',
                'priority': 'Critical',
                'recommendation': 'Immediate FIFO and temperature compliance remediation',
                'actions': [
                    'Relocate expired/near-expiry items',
                    'Fix temperature zone violations',
                    'Implement daily compliance audits'
                ],
                'timeline': '24-48 hours',
                'effort': 'High',
                'impact': 'Prevent regulatory violations and product loss',
                'roi': 'Risk mitigation - potential fine avoidance',
                'resources': '3-4 operators, compliance officer',
                'success_criteria': 'Compliance score > 90%'
            })

        # Priority 2: Quick wins from chaos analysis
        for quick_win in chaos_analysis.get('quick_wins', [])[:3]:
            recommendations.append({
                'category': 'Quick Win',
                'priority': 'High',
                'recommendation': quick_win if isinstance(quick_win, str) else quick_win.get('action', ''),
                'timeline': '1-3 days',
                'effort': 'Low',
                'impact': 'Immediate efficiency improvement',
                'roi': 'High - minimal investment',
                'success_criteria': '10-15% efficiency gain'
            })

        # Priority 3: Placement optimization
        if placement_optimization.get('immediate_moves'):
            recommendations.append({
                'category': 'Placement',
                'priority': 'High',
                'recommendation': 'Execute top placement optimizations',
                'actions': [
                    f"Relocate {len(placement_optimization['immediate_moves'])} misplaced items",
                    'Consolidate fragmented batches',
                    'Optimize golden zone placement'
                ],
                'timeline': '1 week',
                'effort': 'Medium',
                'impact': placement_optimization.get('estimated_savings', {}).get('picking_time_reduction', 'Significant'),
                'roi': placement_optimization.get('estimated_savings', {}).get('annual_cost_savings', '$50,000+'),
                'resources': '2-3 operators, warehouse supervisor',
                'success_criteria': '25% reduction in picking time'
            })

        # Priority 4: Movement optimization
        if movement_analysis.get('path_optimization'):
            recommendations.append({
                'category': 'Movement',
                'priority': 'Medium',
                'recommendation': 'Implement optimized picking strategies',
                'actions': [
                    'Deploy batch picking for small items',
                    'Implement zone picking in high-traffic areas',
                    'Optimize picking routes using S-shape pattern'
                ],
                'timeline': '2 weeks',
                'effort': 'Medium',
                'impact': '30% reduction in travel distance',
                'roi': movement_analysis.get('optimization_opportunities', {}).get('annual_impact', {}).get('cost_savings', '$30,000'),
                'resources': 'IT support, training team',
                'success_criteria': 'Path efficiency > 85%'
            })

        # Priority 5: Layout changes
        for layout_rec in movement_analysis.get('layout_recommendations', [])[:2]:
            recommendations.append({
                'category': 'Infrastructure',
                'priority': 'Low-Medium',
                'recommendation': layout_rec.get('description', 'Layout optimization'),
                'timeline': '1-3 months',
                'effort': 'High',
                'impact': layout_rec.get('expected_benefit', '20% improvement'),
                'roi': 'Medium-term payback',
                'resources': 'Construction team, layout designer',
                'success_criteria': 'Congestion reduction by 30%'
            })

        return sorted(recommendations, key=lambda x: self._get_priority_score(x['priority']), reverse=True)

    def _create_implementation_roadmap(
        self,
        recommendations: List[Dict],
        chaos_analysis: Dict,
        compliance_report: Dict
    ) -> Dict[str, Any]:
        """Create phased implementation roadmap"""

        roadmap = {
            'immediate': {
                'phase': 'Immediate (24-48 hours)',
                'focus': 'Critical compliance and safety issues',
                'actions': [],
                'expected_outcome': 'Risk mitigation and compliance restoration',
                'success_metrics': ['Zero critical violations', 'Compliance score > 85%']
            },
            'short_term': {
                'phase': 'Short Term (1-2 weeks)',
                'focus': 'Quick wins and high-impact optimizations',
                'actions': [],
                'expected_outcome': '15-20% efficiency improvement',
                'success_metrics': ['Chaos score < 10%', 'Path efficiency > 80%']
            },
            'medium_term': {
                'phase': 'Medium Term (1 month)',
                'focus': 'Process optimization and system improvements',
                'actions': [],
                'expected_outcome': '25-30% overall improvement',
                'success_metrics': ['All KPIs meeting targets', 'ROI positive']
            },
            'long_term': {
                'phase': 'Long Term (3 months)',
                'focus': 'Infrastructure and technology upgrades',
                'actions': [],
                'expected_outcome': 'World-class warehouse operations',
                'success_metrics': ['Industry-leading efficiency', 'Fully optimized operations']
            }
        }

        # Distribute recommendations across phases
        for rec in recommendations:
            if rec['priority'] == 'Critical':
                roadmap['immediate']['actions'].append(rec['recommendation'])
            elif rec['priority'] == 'High' and rec['effort'] == 'Low':
                roadmap['short_term']['actions'].append(rec['recommendation'])
            elif rec['priority'] == 'High' and rec['effort'] == 'Medium':
                roadmap['medium_term']['actions'].append(rec['recommendation'])
            else:
                roadmap['long_term']['actions'].append(rec['recommendation'])

        # Add specific milestones
        roadmap['milestones'] = [
            {'week': 1, 'milestone': 'Compliance restored', 'checkpoint': 'Audit readiness assessment'},
            {'week': 2, 'milestone': 'Quick wins implemented', 'checkpoint': 'Efficiency measurement'},
            {'week': 4, 'milestone': 'Major optimizations complete', 'checkpoint': 'ROI validation'},
            {'week': 12, 'milestone': 'Full transformation', 'checkpoint': 'Performance benchmark'}
        ]

        return roadmap

    def _calculate_roi_analysis(
        self,
        placement_optimization: Dict,
        movement_analysis: Dict,
        compliance_report: Dict
    ) -> Dict[str, Any]:
        """Calculate comprehensive ROI analysis"""

        # Extract savings estimates
        placement_savings = self._parse_currency(
            placement_optimization.get('estimated_savings', {}).get('annual_cost_savings', '$0')
        )
        movement_savings = self._parse_currency(
            movement_analysis.get('optimization_opportunities', {}).get('annual_impact', {}).get('cost_savings', '$0')
        )

        # Estimate compliance savings (fine avoidance)
        compliance_risk = 50000 if compliance_report.get('compliance_scores', {}).get('overall', 100) < 70 else 0

        # Calculate implementation costs
        implementation_hours = self._parse_hours(
            placement_optimization.get('estimated_savings', {}).get('implementation_hours', '0 hours')
        )
        hourly_rate = 25
        implementation_cost = implementation_hours * hourly_rate

        # Technology costs (estimated)
        technology_cost = 10000  # WMS updates, training, etc.

        total_savings = placement_savings + movement_savings + compliance_risk
        total_costs = implementation_cost + technology_cost

        roi_percentage = ((total_savings - total_costs) / total_costs * 100) if total_costs > 0 else 0
        payback_months = (total_costs / (total_savings / 12)) if total_savings > 0 else 999

        return {
            'annual_savings': {
                'placement_optimization': f"${placement_savings:,.0f}",
                'movement_optimization': f"${movement_savings:,.0f}",
                'compliance_risk_mitigation': f"${compliance_risk:,.0f}",
                'total': f"${total_savings:,.0f}"
            },
            'implementation_costs': {
                'labor': f"${implementation_cost:,.0f}",
                'technology': f"${technology_cost:,.0f}",
                'training': '$2,000',
                'total': f"${total_costs + 2000:,.0f}"
            },
            'roi_metrics': {
                'roi_percentage': f"{roi_percentage:.1f}%",
                'payback_period': f"{payback_months:.1f} months",
                'npv_3_years': f"${(total_savings * 3 - total_costs):,.0f}",
                'break_even': f"Month {int(payback_months) + 1}"
            },
            'sensitivity_analysis': {
                'best_case': f"${total_savings * 1.3:,.0f} (30% above estimate)",
                'expected': f"${total_savings:,.0f}",
                'worst_case': f"${total_savings * 0.7:,.0f} (30% below estimate)"
            }
        }

    def _define_success_metrics(
        self,
        chaos_analysis: Dict,
        compliance_report: Dict,
        movement_analysis: Dict
    ) -> Dict[str, Any]:
        """Define comprehensive success metrics"""

        current_chaos = chaos_analysis.get('efficiency_score', 0)
        current_compliance = compliance_report.get('compliance_scores', {}).get('overall', 0)
        current_efficiency = float(
            movement_analysis.get('efficiency_metrics', {}).get('overall_efficiency', '0%').rstrip('%')
        )

        return {
            'primary_kpis': [
                {
                    'metric': 'Overall Chaos Score',
                    'current': f"{100 - current_chaos:.1f}%",
                    'target': '<5%',
                    'measurement': 'Weekly automated report',
                    'owner': 'Warehouse Manager'
                },
                {
                    'metric': 'Compliance Score',
                    'current': f"{current_compliance:.1f}%",
                    'target': '>95%',
                    'measurement': 'Daily compliance audit',
                    'owner': 'Compliance Officer'
                },
                {
                    'metric': 'Movement Efficiency',
                    'current': f"{current_efficiency:.1f}%",
                    'target': '>85%',
                    'measurement': 'Real-time tracking',
                    'owner': 'Operations Manager'
                }
            ],
            'operational_metrics': [
                {
                    'metric': 'Picking Time per Order',
                    'target': '< 5 minutes',
                    'measurement': 'WMS tracking'
                },
                {
                    'metric': 'Inventory Accuracy',
                    'target': '>99.5%',
                    'measurement': 'Cycle counting'
                },
                {
                    'metric': 'Space Utilization',
                    'target': '>80%',
                    'measurement': 'Monthly analysis'
                }
            ],
            'financial_metrics': [
                {
                    'metric': 'Cost per Pick',
                    'target': '15% reduction',
                    'baseline': '$2.50',
                    'measurement': 'Monthly calculation'
                },
                {
                    'metric': 'Labor Productivity',
                    'target': '25% improvement',
                    'measurement': 'Units per hour'
                }
            ],
            'quality_metrics': [
                {
                    'metric': 'Order Accuracy',
                    'target': '>99.8%',
                    'measurement': 'Order verification'
                },
                {
                    'metric': 'Damage Rate',
                    'target': '<0.1%',
                    'measurement': 'Incident tracking'
                }
            ]
        }

    def _generate_executive_summary(
        self,
        chaos_analysis: Dict,
        roi_analysis: Dict,
        recommendations: List[Dict]
    ) -> Dict[str, Any]:
        """Generate executive summary"""

        critical_actions = len([r for r in recommendations if r['priority'] == 'Critical'])
        high_priority = len([r for r in recommendations if r['priority'] == 'High'])

        return {
            'situation': f"Warehouse operating at {chaos_analysis.get('efficiency_score', 0):.0f}% efficiency with significant optimization opportunities",
            'opportunity': f"Identified {len(recommendations)} optimization initiatives with potential annual savings of {roi_analysis['annual_savings']['total']}",
            'recommendation': f"Implement {critical_actions} critical and {high_priority} high-priority actions within 2 weeks",
            'expected_outcome': {
                'efficiency_gain': '30-40%',
                'cost_reduction': roi_analysis['annual_savings']['total'],
                'compliance_improvement': 'Full regulatory compliance',
                'roi': roi_analysis['roi_metrics']['roi_percentage']
            },
            'investment_required': roi_analysis['implementation_costs']['total'],
            'payback_period': roi_analysis['roi_metrics']['payback_period'],
            'risk_level': 'Low - proven optimization techniques',
            'recommendation_confidence': 'High - based on comprehensive analysis'
        }

    def _prioritize_immediate_actions(
        self,
        compliance_report: Dict,
        placement_optimization: Dict,
        recommendations: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Prioritize immediate actions for next 24-48 hours"""

        immediate_actions = []

        # Add critical compliance actions
        if compliance_report.get('critical_violations'):
            for violation in compliance_report['critical_violations'][:3]:
                immediate_actions.append({
                    'action': f"Resolve: {violation if isinstance(violation, str) else violation.get('issue', 'compliance violation')}",
                    'priority': 'Critical',
                    'timeline': '4 hours',
                    'assigned_to': 'Compliance team',
                    'expected_result': 'Eliminate compliance risk'
                })

        # Add top placement moves
        for move in placement_optimization.get('immediate_moves', [])[:5]:
            immediate_actions.append({
                'action': f"Relocate {move.get('item', 'item')} from {move.get('current_location', '')} to {move.get('recommended_location', '')}",
                'priority': 'High',
                'timeline': '24 hours',
                'assigned_to': 'Warehouse operators',
                'expected_result': move.get('estimated_time_saving', 'Efficiency improvement')
            })

        # Add quick wins
        for quick_win in recommendations:
            if quick_win['priority'] in ['Critical', 'High'] and quick_win['effort'] == 'Low':
                immediate_actions.append({
                    'action': quick_win['recommendation'],
                    'priority': quick_win['priority'],
                    'timeline': quick_win['timeline'],
                    'assigned_to': 'Operations team',
                    'expected_result': quick_win['impact']
                })
                if len(immediate_actions) >= 10:
                    break

        return immediate_actions[:10]  # Limit to top 10 actions

    def _estimate_resource_requirements(
        self,
        recommendations: List[Dict],
        roadmap: Dict
    ) -> Dict[str, Any]:
        """Estimate resource requirements for implementation"""

        # Count resources needed
        operators_needed = 0
        it_support_needed = False
        training_needed = False
        external_consultants = False

        for rec in recommendations:
            resources = rec.get('resources', '')
            if 'operator' in resources.lower():
                operators_needed = max(operators_needed, 4)
            if 'it' in resources.lower():
                it_support_needed = True
            if 'training' in resources.lower():
                training_needed = True
            if 'consultant' in resources.lower() or 'designer' in resources.lower():
                external_consultants = True

        return {
            'personnel': {
                'warehouse_operators': f"{operators_needed} FTE for 2 weeks",
                'warehouse_supervisor': '1 FTE dedicated',
                'compliance_officer': '0.5 FTE for 1 month',
                'it_support': '1 FTE for 2 weeks' if it_support_needed else 'As needed',
                'total_hours': operators_needed * 80 + 120  # 2 weeks estimate
            },
            'technology': {
                'wms_updates': 'Required' if it_support_needed else 'Optional',
                'reporting_tools': 'Enhanced dashboards needed',
                'mobile_devices': '5 additional scanners',
                'software_licenses': '$2,000 estimated'
            },
            'training': {
                'required': training_needed,
                'duration': '2 days per operator' if training_needed else 'None',
                'topics': ['New picking strategies', 'Compliance procedures', 'System updates']
            },
            'external_support': {
                'consultants': 'Layout optimization specialist' if external_consultants else 'None',
                'estimated_cost': '$10,000' if external_consultants else '$0'
            },
            'budget_summary': {
                'labor': f"${operators_needed * 80 * 25:,.0f}",
                'technology': '$12,000',
                'training': '$2,000' if training_needed else '$0',
                'external': '$10,000' if external_consultants else '$0',
                'contingency': '$5,000',
                'total': f"${operators_needed * 80 * 25 + 12000 + (2000 if training_needed else 0) + (10000 if external_consultants else 0) + 5000:,.0f}"
            }
        }

    def _identify_implementation_risks(
        self,
        recommendations: List[Dict],
        compliance_report: Dict
    ) -> List[Dict[str, Any]]:
        """Identify and plan for implementation risks"""

        risks = []

        # Operational disruption risk
        if len([r for r in recommendations if r['priority'] in ['Critical', 'High']]) > 5:
            risks.append({
                'risk': 'Operational disruption during implementation',
                'probability': 'Medium',
                'impact': 'High',
                'mitigation': 'Implement changes during off-peak hours, maintain buffer inventory',
                'contingency': 'Rollback plan for each change'
            })

        # Compliance risk
        if compliance_report.get('compliance_scores', {}).get('overall', 100) < 70:
            risks.append({
                'risk': 'Regulatory action during transition',
                'probability': 'Low',
                'impact': 'Critical',
                'mitigation': 'Prioritize compliance fixes, document all changes',
                'contingency': 'Legal team on standby'
            })

        # Resource availability risk
        risks.append({
            'risk': 'Insufficient resources for implementation',
            'probability': 'Medium',
            'impact': 'Medium',
            'mitigation': 'Cross-train staff, hire temporary workers if needed',
            'contingency': 'Phase implementation over longer period'
        })

        # Technology integration risk
        if any('technology' in r.get('category', '').lower() for r in recommendations):
            risks.append({
                'risk': 'System integration issues',
                'probability': 'Low',
                'impact': 'Medium',
                'mitigation': 'Thorough testing in staging environment',
                'contingency': 'Manual workarounds prepared'
            })

        # Change resistance risk
        risks.append({
            'risk': 'Staff resistance to new processes',
            'probability': 'Medium',
            'impact': 'Medium',
            'mitigation': 'Clear communication, training, incentives',
            'contingency': 'Gradual rollout with feedback loops'
        })

        return risks

    def _create_monitoring_plan(self, success_metrics: Dict) -> Dict[str, Any]:
        """Create monitoring plan for tracking progress"""

        return {
            'monitoring_framework': {
                'daily': [
                    'Compliance violations check',
                    'Movement efficiency tracking',
                    'Critical issue identification'
                ],
                'weekly': [
                    'Chaos score calculation',
                    'KPI dashboard review',
                    'Progress against milestones'
                ],
                'monthly': [
                    'ROI validation',
                    'Comprehensive performance review',
                    'Strategy adjustment meeting'
                ]
            },
            'reporting_structure': {
                'operational_dashboard': {
                    'audience': 'Warehouse team',
                    'frequency': 'Real-time',
                    'metrics': ['Picking efficiency', 'Current violations', 'Queue status']
                },
                'management_report': {
                    'audience': 'Management team',
                    'frequency': 'Weekly',
                    'metrics': ['KPI performance', 'Cost savings', 'Issues resolved']
                },
                'executive_summary': {
                    'audience': 'C-suite',
                    'frequency': 'Monthly',
                    'metrics': ['ROI achievement', 'Strategic progress', 'Risk status']
                }
            },
            'alert_thresholds': {
                'chaos_score': {'warning': 10, 'critical': 15},
                'compliance_score': {'warning': 85, 'critical': 80},
                'efficiency': {'warning': 75, 'critical': 70}
            },
            'review_schedule': [
                {'week': 1, 'review': 'Initial progress check'},
                {'week': 2, 'review': 'Quick wins validation'},
                {'week': 4, 'review': 'Month 1 comprehensive review'},
                {'week': 12, 'review': 'Quarter 1 strategic review'}
            ]
        }

    def _calculate_optimization_score(
        self,
        chaos_analysis: Dict,
        compliance_report: Dict,
        movement_analysis: Dict
    ) -> float:
        """Calculate overall optimization score"""

        # Get individual scores
        chaos_score = chaos_analysis.get('efficiency_score', 0)
        compliance_score = compliance_report.get('compliance_scores', {}).get('overall', 0)

        movement_efficiency = movement_analysis.get('efficiency_metrics', {}).get('overall_efficiency', '0%')
        if isinstance(movement_efficiency, str):
            movement_score = float(movement_efficiency.rstrip('%'))
        else:
            movement_score = movement_efficiency

        # Weighted average
        optimization_score = (
            chaos_score * 0.3 +
            compliance_score * 0.4 +
            movement_score * 0.3
        )

        return round(optimization_score, 1)

    def _get_priority_score(self, priority: str) -> int:
        """Get numeric score for priority level"""
        priority_map = {
            'Critical': 4,
            'High': 3,
            'Medium': 2,
            'Low': 1,
            'Low-Medium': 1.5
        }
        return priority_map.get(priority, 0)

    def _parse_currency(self, currency_str: str) -> float:
        """Parse currency string to float"""
        if not currency_str:
            return 0

        # Remove currency symbols and commas
        cleaned = currency_str.replace('$', '').replace(',', '').strip()

        try:
            return float(cleaned)
        except:
            return 0

    def _parse_hours(self, hours_str: str) -> float:
        """Parse hours string to float"""
        if not hours_str:
            return 0

        # Extract numeric value
        import re
        numbers = re.findall(r'[\d.]+', hours_str)

        if numbers:
            try:
                return float(numbers[0])
            except:
                return 0
        return 0

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response if JSON parsing fails"""
        result = {
            "EXECUTIVE_SUMMARY": {},
            "IMMEDIATE_ACTIONS": [],
            "SHORT_TERM_PLAN": {},
            "LONG_TERM_STRATEGY": {},
            "SUCCESS_METRICS": {},
            "RESOURCE_REQUIREMENTS": {}
        }

        lines = text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if 'EXECUTIVE' in line.upper():
                current_section = 'EXECUTIVE_SUMMARY'
            elif 'IMMEDIATE' in line.upper():
                current_section = 'IMMEDIATE_ACTIONS'
            elif 'SHORT' in line.upper():
                current_section = 'SHORT_TERM_PLAN'
            elif 'LONG' in line.upper():
                current_section = 'LONG_TERM_STRATEGY'
            elif 'SUCCESS' in line.upper() or 'METRIC' in line.upper():
                current_section = 'SUCCESS_METRICS'
            elif 'RESOURCE' in line.upper():
                current_section = 'RESOURCE_REQUIREMENTS'
            elif line and current_section:
                if current_section == 'IMMEDIATE_ACTIONS':
                    if line.startswith(('-', '*', '•', '1', '2', '3')):
                        result['IMMEDIATE_ACTIONS'].append(line.lstrip('-*•0123456789. '))

        return result