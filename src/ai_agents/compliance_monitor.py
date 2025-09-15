"""
Compliance Monitor Agent
Monitors FIFO compliance, temperature zones, and regulatory requirements
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
import json
from datetime import datetime, timedelta
from dateutil import parser


class ComplianceMonitor:
    """Monitors warehouse compliance with FIFO, temperature, and regulatory requirements"""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the compliance monitor with LLM"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )
        logger.info("ComplianceMonitor initialized")

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze compliance issues in warehouse operations

        Args:
            state: Contains fifo_violations, temperature_data, batch_info, regulatory_requirements

        Returns:
            Compliance analysis with violations, risks, and corrective actions
        """
        try:
            fifo_violations = state.get("fifo_violations", [])
            temperature_data = state.get("temperature_data", {})
            batch_info = state.get("batch_info", [])
            zone_violations = state.get("zone_violations", [])
            regulatory_requirements = state.get("regulatory_requirements", {})

            system_prompt = """You are a warehouse compliance expert specializing in pharmaceutical storage.
            Your role is to ensure FIFO compliance, proper temperature control, and regulatory adherence.

            Focus areas:
            1. FIFO COMPLIANCE: Identify and prevent expiry risks
            2. TEMPERATURE CONTROL: Ensure proper storage conditions
            3. ZONE INTEGRITY: Verify items are in correct zones
            4. REGULATORY COMPLIANCE: Meet FDA, GMP, and other requirements
            5. RISK ASSESSMENT: Identify potential compliance failures

            Provide specific violations with severity levels and immediate corrective actions.
            """

            analysis_prompt = f"""
            Analyze the following compliance data:

            FIFO VIOLATIONS:
            - Total Violations: {len(fifo_violations)}
            - Items Near Expiry (30 days): {self._count_near_expiry(batch_info, 30)}
            - Items Near Expiry (7 days): {self._count_near_expiry(batch_info, 7)}
            - Blocked Older Stock: {len([v for v in fifo_violations if v.get('type') == 'blocked'])}

            TEMPERATURE VIOLATIONS:
            - Out of Range Items: {temperature_data.get('violations_count', 0)}
            - Critical Violations: {temperature_data.get('critical_count', 0)}
            - Affected Medications: {json.dumps(temperature_data.get('affected_items', [])[:5], indent=2)}

            ZONE VIOLATIONS:
            - Items in Wrong Zone: {len(zone_violations)}
            - Controlled Substances Misplaced: {len([z for z in zone_violations if z.get('controlled', False)])}
            - Temperature Sensitive Misplaced: {len([z for z in zone_violations if z.get('temp_sensitive', False)])}

            BATCH DETAILS:
            {json.dumps([self._format_batch_info(b) for b in batch_info[:10]], indent=2)}

            Provide comprehensive compliance analysis including:
            1. CRITICAL_VIOLATIONS: Immediate action required items
            2. EXPIRY_RISK_ASSESSMENT: Items at risk with days remaining
            3. TEMPERATURE_COMPLIANCE: Zone integrity and monitoring gaps
            4. CORRECTIVE_ACTIONS: Specific steps to resolve violations
            5. PREVENTIVE_MEASURES: Process improvements to prevent future issues

            Format as JSON with clear priorities and timelines.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            try:
                compliance_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                compliance_analysis = self._parse_text_response(response.content)

            # Generate detailed compliance report
            compliance_report = self._generate_compliance_report(
                fifo_violations,
                temperature_data,
                batch_info,
                zone_violations
            )

            # Calculate compliance scores
            compliance_scores = self._calculate_compliance_scores(
                fifo_violations,
                temperature_data,
                zone_violations
            )

            # Generate action plan
            action_plan = self._generate_action_plan(
                compliance_report,
                compliance_scores
            )

            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "compliance_scores": compliance_scores,
                "critical_violations": compliance_analysis.get("CRITICAL_VIOLATIONS", []),
                "expiry_risk_assessment": self._assess_expiry_risks(batch_info),
                "temperature_compliance": compliance_analysis.get("TEMPERATURE_COMPLIANCE", {}),
                "zone_compliance": self._analyze_zone_compliance(zone_violations),
                "corrective_actions": action_plan['immediate_actions'],
                "preventive_measures": action_plan['preventive_measures'],
                "compliance_report": compliance_report,
                "regulatory_gaps": self._identify_regulatory_gaps(
                    compliance_scores,
                    regulatory_requirements
                ),
                "audit_readiness": self._assess_audit_readiness(compliance_scores),
                "risk_matrix": self._generate_risk_matrix(
                    fifo_violations,
                    temperature_data,
                    zone_violations
                )
            }

        except Exception as e:
            logger.error(f"Error in compliance monitoring: {str(e)}")
            return {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat(),
                "compliance_scores": {},
                "critical_violations": [],
                "expiry_risk_assessment": {},
                "temperature_compliance": {},
                "zone_compliance": {},
                "corrective_actions": [],
                "preventive_measures": [],
                "compliance_report": {},
                "regulatory_gaps": [],
                "audit_readiness": {},
                "risk_matrix": {}
            }

    def _count_near_expiry(self, batch_info: List[Dict], days: int) -> int:
        """Count items near expiry within specified days"""
        count = 0
        cutoff_date = datetime.now() + timedelta(days=days)

        for batch in batch_info:
            try:
                expiry_date = batch.get('expiry_date')
                if expiry_date:
                    if isinstance(expiry_date, str):
                        expiry_date = parser.parse(expiry_date)
                    elif not isinstance(expiry_date, datetime):
                        continue

                    if expiry_date <= cutoff_date:
                        count += 1
            except:
                continue

        return count

    def _format_batch_info(self, batch: Dict) -> Dict:
        """Format batch information for analysis"""
        expiry_date = batch.get('expiry_date')
        days_until_expiry = None

        if expiry_date:
            try:
                if isinstance(expiry_date, str):
                    expiry_date = parser.parse(expiry_date)
                days_until_expiry = (expiry_date - datetime.now()).days
            except:
                pass

        return {
            'batch_id': batch.get('batch_id'),
            'lot_number': batch.get('lot_number'),
            'medication': batch.get('medication_name'),
            'quantity': batch.get('quantity'),
            'days_until_expiry': days_until_expiry,
            'location': batch.get('location')
        }

    def _generate_compliance_report(
        self,
        fifo_violations: List[Dict],
        temperature_data: Dict,
        batch_info: List[Dict],
        zone_violations: List[Dict]
    ) -> Dict[str, Any]:
        """Generate detailed compliance report"""

        # FIFO compliance analysis
        fifo_compliance = {
            'total_violations': len(fifo_violations),
            'severity_breakdown': {
                'critical': len([v for v in fifo_violations if v.get('severity') == 'critical']),
                'high': len([v for v in fifo_violations if v.get('severity') == 'high']),
                'medium': len([v for v in fifo_violations if v.get('severity') == 'medium']),
                'low': len([v for v in fifo_violations if v.get('severity') == 'low'])
            },
            'expired_items': self._count_near_expiry(batch_info, 0),
            'expiring_7_days': self._count_near_expiry(batch_info, 7),
            'expiring_30_days': self._count_near_expiry(batch_info, 30),
            'blocked_stock_value': sum(v.get('value', 0) for v in fifo_violations)
        }

        # Temperature compliance
        temp_compliance = {
            'monitored_zones': temperature_data.get('monitored_zones', 0),
            'violations_last_24h': temperature_data.get('violations_count', 0),
            'critical_excursions': temperature_data.get('critical_count', 0),
            'average_deviation': temperature_data.get('avg_deviation', 0),
            'affected_value': temperature_data.get('affected_value', 0)
        }

        # Zone compliance
        zone_compliance = {
            'total_violations': len(zone_violations),
            'controlled_substance_violations': len([z for z in zone_violations if z.get('controlled')]),
            'temperature_zone_violations': len([z for z in zone_violations if z.get('temp_sensitive')]),
            'quarantine_violations': len([z for z in zone_violations if z.get('quarantine')])
        }

        return {
            'fifo_compliance': fifo_compliance,
            'temperature_compliance': temp_compliance,
            'zone_compliance': zone_compliance,
            'report_date': datetime.now().isoformat(),
            'overall_status': self._determine_overall_status(
                fifo_compliance,
                temp_compliance,
                zone_compliance
            )
        }

    def _calculate_compliance_scores(
        self,
        fifo_violations: List[Dict],
        temperature_data: Dict,
        zone_violations: List[Dict]
    ) -> Dict[str, float]:
        """Calculate compliance scores for different areas"""

        # FIFO score (100 - violations * penalty)
        fifo_score = max(0, 100 - len(fifo_violations) * 5)

        # Temperature score
        temp_violations = temperature_data.get('violations_count', 0)
        temp_score = max(0, 100 - temp_violations * 10)

        # Zone score
        zone_score = max(0, 100 - len(zone_violations) * 3)

        # Overall compliance score (weighted average)
        overall_score = (fifo_score * 0.4 + temp_score * 0.4 + zone_score * 0.2)

        return {
            'overall': round(overall_score, 1),
            'fifo': round(fifo_score, 1),
            'temperature': round(temp_score, 1),
            'zone': round(zone_score, 1),
            'status': 'Compliant' if overall_score >= 80 else 'At Risk' if overall_score >= 60 else 'Non-Compliant'
        }

    def _assess_expiry_risks(self, batch_info: List[Dict]) -> Dict[str, Any]:
        """Assess expiry risks in detail"""
        risk_categories = {
            'expired': [],
            'critical_7_days': [],
            'high_30_days': [],
            'medium_60_days': [],
            'low_90_days': []
        }

        for batch in batch_info:
            days_until_expiry = None
            expiry_date = batch.get('expiry_date')

            if expiry_date:
                try:
                    if isinstance(expiry_date, str):
                        expiry_date = parser.parse(expiry_date)
                    days_until_expiry = (expiry_date - datetime.now()).days

                    batch_summary = {
                        'batch_id': batch.get('batch_id'),
                        'medication': batch.get('medication_name'),
                        'lot_number': batch.get('lot_number'),
                        'quantity': batch.get('quantity'),
                        'value': batch.get('value', 0),
                        'days_remaining': days_until_expiry,
                        'location': batch.get('location')
                    }

                    if days_until_expiry < 0:
                        risk_categories['expired'].append(batch_summary)
                    elif days_until_expiry <= 7:
                        risk_categories['critical_7_days'].append(batch_summary)
                    elif days_until_expiry <= 30:
                        risk_categories['high_30_days'].append(batch_summary)
                    elif days_until_expiry <= 60:
                        risk_categories['medium_60_days'].append(batch_summary)
                    elif days_until_expiry <= 90:
                        risk_categories['low_90_days'].append(batch_summary)
                except:
                    continue

        # Calculate total value at risk
        total_value_at_risk = sum(
            sum(item.get('value', 0) for item in items)
            for items in [risk_categories['expired'], risk_categories['critical_7_days']]
        )

        return {
            'risk_categories': risk_categories,
            'total_at_risk': len(risk_categories['expired']) + len(risk_categories['critical_7_days']),
            'value_at_risk': total_value_at_risk,
            'immediate_action_required': len(risk_categories['expired']) + len(risk_categories['critical_7_days']),
            'monitoring_required': len(risk_categories['high_30_days']) + len(risk_categories['medium_60_days'])
        }

    def _analyze_zone_compliance(self, zone_violations: List[Dict]) -> Dict[str, Any]:
        """Analyze zone compliance violations"""
        violation_types = {
            'temperature': [],
            'controlled': [],
            'quarantine': [],
            'hazardous': []
        }

        for violation in zone_violations:
            if violation.get('temp_sensitive'):
                violation_types['temperature'].append(violation)
            if violation.get('controlled'):
                violation_types['controlled'].append(violation)
            if violation.get('quarantine'):
                violation_types['quarantine'].append(violation)
            if violation.get('hazardous'):
                violation_types['hazardous'].append(violation)

        return {
            'violation_summary': {
                'temperature_violations': len(violation_types['temperature']),
                'controlled_violations': len(violation_types['controlled']),
                'quarantine_violations': len(violation_types['quarantine']),
                'hazardous_violations': len(violation_types['hazardous'])
            },
            'critical_violations': violation_types['controlled'] + violation_types['hazardous'],
            'remediation_priority': self._prioritize_zone_remediation(violation_types)
        }

    def _generate_action_plan(
        self,
        compliance_report: Dict,
        compliance_scores: Dict
    ) -> Dict[str, Any]:
        """Generate action plan based on compliance issues"""
        immediate_actions = []
        preventive_measures = []

        # Check FIFO compliance
        if compliance_scores['fifo'] < 80:
            immediate_actions.append({
                'action': 'Reorganize inventory for FIFO compliance',
                'priority': 'High',
                'timeline': '24 hours',
                'resources': '2 operators',
                'impact': f"Prevent expiry of {compliance_report['fifo_compliance']['expiring_7_days']} items"
            })

        # Check temperature compliance
        if compliance_scores['temperature'] < 90:
            immediate_actions.append({
                'action': 'Calibrate temperature monitoring systems',
                'priority': 'Critical',
                'timeline': '4 hours',
                'resources': 'Maintenance team',
                'impact': 'Ensure product integrity'
            })

        # Check zone compliance
        if compliance_scores['zone'] < 85:
            immediate_actions.append({
                'action': 'Relocate misplaced items to correct zones',
                'priority': 'High',
                'timeline': '8 hours',
                'resources': '1 operator, zone map',
                'impact': 'Ensure regulatory compliance'
            })

        # Add preventive measures
        preventive_measures = [
            {
                'measure': 'Implement daily FIFO audits',
                'frequency': 'Daily',
                'responsible': 'Warehouse supervisor',
                'expected_improvement': '25% reduction in violations'
            },
            {
                'measure': 'Install zone access controls',
                'frequency': 'One-time',
                'responsible': 'IT/Security',
                'expected_improvement': 'Eliminate unauthorized zone access'
            },
            {
                'measure': 'Automate expiry alerts',
                'frequency': 'Continuous',
                'responsible': 'IT team',
                'expected_improvement': '90% reduction in expired items'
            }
        ]

        return {
            'immediate_actions': immediate_actions,
            'preventive_measures': preventive_measures
        }

    def _identify_regulatory_gaps(
        self,
        compliance_scores: Dict,
        regulatory_requirements: Dict
    ) -> List[Dict[str, Any]]:
        """Identify gaps in regulatory compliance"""
        gaps = []

        if compliance_scores['overall'] < 80:
            gaps.append({
                'regulation': 'FDA 21 CFR Part 211',
                'requirement': 'Current Good Manufacturing Practice',
                'gap': 'Overall compliance below acceptable threshold',
                'remediation': 'Implement comprehensive compliance program'
            })

        if compliance_scores['temperature'] < 85:
            gaps.append({
                'regulation': 'USP <1079>',
                'requirement': 'Good Storage and Distribution Practices',
                'gap': 'Temperature excursions exceed limits',
                'remediation': 'Upgrade temperature monitoring and control systems'
            })

        if compliance_scores['fifo'] < 75:
            gaps.append({
                'regulation': 'FDA Guidance',
                'requirement': 'First-In-First-Out inventory management',
                'gap': 'FIFO violations present expiry risk',
                'remediation': 'Implement automated FIFO tracking system'
            })

        return gaps

    def _assess_audit_readiness(self, compliance_scores: Dict) -> Dict[str, Any]:
        """Assess readiness for regulatory audit"""
        overall_score = compliance_scores['overall']

        readiness_level = (
            'Audit Ready' if overall_score >= 90 else
            'Minor Issues' if overall_score >= 80 else
            'Major Gaps' if overall_score >= 60 else
            'Critical Risk'
        )

        return {
            'readiness_level': readiness_level,
            'score': overall_score,
            'estimated_prep_time': (
                '0 days' if overall_score >= 90 else
                '1-3 days' if overall_score >= 80 else
                '1-2 weeks' if overall_score >= 60 else
                '2-4 weeks'
            ),
            'key_risks': self._identify_audit_risks(compliance_scores),
            'documentation_status': 'Complete' if overall_score >= 85 else 'Gaps Present'
        }

    def _generate_risk_matrix(
        self,
        fifo_violations: List[Dict],
        temperature_data: Dict,
        zone_violations: List[Dict]
    ) -> Dict[str, Any]:
        """Generate risk matrix for compliance issues"""
        risks = []

        # FIFO risks
        if len(fifo_violations) > 0:
            risks.append({
                'category': 'FIFO Compliance',
                'probability': 'High' if len(fifo_violations) > 10 else 'Medium',
                'impact': 'High',
                'risk_level': 'Critical' if len(fifo_violations) > 10 else 'High',
                'mitigation': 'Immediate inventory reorganization'
            })

        # Temperature risks
        if temperature_data.get('violations_count', 0) > 0:
            risks.append({
                'category': 'Temperature Control',
                'probability': 'Medium',
                'impact': 'Critical',
                'risk_level': 'High',
                'mitigation': 'Enhanced monitoring and control systems'
            })

        # Zone risks
        if len(zone_violations) > 0:
            risks.append({
                'category': 'Zone Integrity',
                'probability': 'Low' if len(zone_violations) < 5 else 'Medium',
                'impact': 'High',
                'risk_level': 'Medium' if len(zone_violations) < 5 else 'High',
                'mitigation': 'Access controls and staff training'
            })

        return {
            'risk_items': risks,
            'highest_risk': max(risks, key=lambda x: x['risk_level']) if risks else None,
            'total_risks': len(risks)
        }

    def _determine_overall_status(
        self,
        fifo_compliance: Dict,
        temp_compliance: Dict,
        zone_compliance: Dict
    ) -> str:
        """Determine overall compliance status"""
        critical_issues = (
            fifo_compliance['expired_items'] > 0 or
            temp_compliance['critical_excursions'] > 0 or
            zone_compliance['controlled_substance_violations'] > 0
        )

        if critical_issues:
            return 'Critical - Immediate Action Required'

        high_issues = (
            fifo_compliance['expiring_7_days'] > 5 or
            temp_compliance['violations_last_24h'] > 10 or
            zone_compliance['total_violations'] > 15
        )

        if high_issues:
            return 'At Risk - Action Required'

        return 'Compliant - Minor Issues'

    def _prioritize_zone_remediation(self, violation_types: Dict) -> List[str]:
        """Prioritize zone remediation actions"""
        priorities = []

        if violation_types['controlled']:
            priorities.append('1. Relocate controlled substances immediately')
        if violation_types['hazardous']:
            priorities.append('2. Secure hazardous materials')
        if violation_types['temperature']:
            priorities.append('3. Move temperature-sensitive items')
        if violation_types['quarantine']:
            priorities.append('4. Isolate quarantine items')

        return priorities

    def _identify_audit_risks(self, compliance_scores: Dict) -> List[str]:
        """Identify key risks for audit"""
        risks = []

        if compliance_scores['fifo'] < 80:
            risks.append('FIFO compliance documentation')
        if compliance_scores['temperature'] < 85:
            risks.append('Temperature monitoring records')
        if compliance_scores['zone'] < 80:
            risks.append('Zone access controls')

        return risks

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response if JSON parsing fails"""
        result = {
            "CRITICAL_VIOLATIONS": [],
            "EXPIRY_RISK_ASSESSMENT": {},
            "TEMPERATURE_COMPLIANCE": {},
            "CORRECTIVE_ACTIONS": [],
            "PREVENTIVE_MEASURES": []
        }

        lines = text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if 'CRITICAL' in line.upper():
                current_section = 'CRITICAL_VIOLATIONS'
            elif 'EXPIRY' in line.upper():
                current_section = 'EXPIRY_RISK_ASSESSMENT'
            elif 'TEMPERATURE' in line.upper():
                current_section = 'TEMPERATURE_COMPLIANCE'
            elif 'CORRECTIVE' in line.upper():
                current_section = 'CORRECTIVE_ACTIONS'
            elif 'PREVENTIVE' in line.upper():
                current_section = 'PREVENTIVE_MEASURES'
            elif line and current_section:
                if current_section in ['CRITICAL_VIOLATIONS', 'CORRECTIVE_ACTIONS', 'PREVENTIVE_MEASURES']:
                    if line.startswith(('-', '*', '•', '1', '2', '3')):
                        result[current_section].append(line.lstrip('-*•0123456789. '))

        return result