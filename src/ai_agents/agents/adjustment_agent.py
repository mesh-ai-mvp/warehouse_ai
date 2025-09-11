"""Context-aware Adjustment Agent for PO Generation"""

import json
import re
from datetime import datetime
from typing import Any, Dict

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import get_config
from ..logger import adjustment_logger as logger
from ..state import AgentReasoning, POGenerationState, add_reasoning, update_progress


class AdjustmentAgent:
    """Agent responsible for adjusting quantities based on external factors"""

    def __init__(self):
        self.config = get_config()
        self.llm = ChatOpenAI(
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            openai_api_key=self.config.openai_api_key,
            timeout=self.config.request_timeout,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    def __call__(self, state: POGenerationState) -> POGenerationState:
        """Process state and adjust quantities based on context"""

        logger.info(
            f"Starting adjustment phase for {len(state.get('forecast_data', {}))} forecasts"
        )

        # Update progress
        state = update_progress(
            state, "adjustment_agent", "Analyzing market conditions (US)", 10
        )

        adjusted_quantities = {}
        reasoning_points = []

        # Get current date context for seasonal adjustments
        now_dt = datetime.now()
        current_month = now_dt.month
        month_name = now_dt.strftime("%B").lower()
        current_date_str = now_dt.strftime("%Y-%m-%d")
        current_year = now_dt.year

        for med_id, forecast in state["forecast_data"].items():
            med = next((m for m in state["medications"] if m["med_id"] == med_id), None)
            if not med:
                continue

            # Calculate adjustments
            adjustments = self._calculate_adjustments(
                med, forecast, current_month, month_name
            )

            # Use LLM for additional context analysis
            llm_adjustments = self._analyze_context_with_llm(
                med, forecast, adjustments, current_date_str, month_name, current_year
            )

            # Combine adjustments
            final_adjustment = self._combine_adjustments(
                forecast["forecast_quantity"], adjustments, llm_adjustments, med
            )

            adjusted_quantities[med_id] = final_adjustment

            # Build detailed reasoning for this adjustment
            original_qty = forecast["forecast_quantity"]
            adjusted_qty = final_adjustment["adjusted_quantity"]
            adjustment_factors = final_adjustment.get("adjustment_factors", {})
            llm_insight = final_adjustment.get("llm_insight", "")

            med_reasoning = []
            med_reasoning.append(f"Original forecast: {original_qty:.0f} units")

            # Show each adjustment factor
            applied_adjustments = []
            for factor_name, factor_value in adjustment_factors.items():
                if factor_value != 1.0:
                    percent_change = int((factor_value - 1) * 100)
                    direction = "+" if percent_change > 0 else ""

                    factor_description = {
                        "seasonal": f"Seasonal ({month_name})",
                        "flu_season": "Flu season boost",
                        "holiday": "Holiday reduction",
                        "summer": "Summer adjustment",
                        "category_stability": "Category stability",
                        "event": "External events",
                    }.get(factor_name, factor_name.replace("_", " ").title())

                    applied_adjustments.append(
                        f"{factor_description}: {direction}{percent_change}%"
                    )

            if applied_adjustments:
                med_reasoning.extend(applied_adjustments)
            else:
                med_reasoning.append("No contextual adjustments applied")

            # Include LLM insights if significant
            if (
                llm_insight
                and llm_insight != "LLM analysis failed"
                and "none" not in llm_insight.lower()
            ):
                med_reasoning.append(f"AI context analysis: {llm_insight}")

            # Show total adjustment
            total_factor = final_adjustment.get("total_adjustment_factor", 1.0)
            if total_factor != 1.0:
                total_percent = int((total_factor - 1) * 100)
                direction = "increased" if total_percent > 0 else "decreased"
                med_reasoning.append(
                    f"Total adjustment: {direction} by {abs(total_percent)}%"
                )

            med_reasoning.append(f"Final adjusted quantity: {adjusted_qty:.0f} units")

            # Add to overall reasoning with medication name prefix
            reasoning_points.extend(
                [f"{med['name']}: {reason}" for reason in med_reasoning]
            )

        # Update state
        state["adjusted_quantities"] = adjusted_quantities

        # Add reasoning
        reasoning = AgentReasoning(
            agent_name="adjustment_agent",
            timestamp=datetime.utcnow().isoformat(),
            input_summary=f"Adjusting forecasts for {len(state['forecast_data'])} medications",
            decision_points=reasoning_points,
            output_summary=f"Applied context adjustments to {len(adjusted_quantities)} medications",
            confidence=0.82,
        )
        state = add_reasoning(state, "adjustment_agent", reasoning)

        # Update progress
        state = update_progress(
            state,
            "adjustment_agent",
            "Adjustment complete",
            100,
            f"Adjusted quantities for {len(adjusted_quantities)} medications",
        )

        return state

    def _calculate_adjustments(
        self,
        med: Dict[str, Any],
        forecast: Dict[str, Any],
        current_month: int,
        month_name: str,
    ) -> Dict[str, float]:
        """Calculate adjustment factors based on rules"""

        adjustments = {}

        if not self.config.adjustment_factors_enabled:
            return {"base": 1.0}

        # Seasonal adjustment
        seasonal_factor = self.config.seasonal_adjustments.get(month_name, 1.0)
        adjustments["seasonal"] = seasonal_factor

        # Flu season adjustment for relevant medications
        if current_month in self.config.flu_season_months:
            category = med.get("category", "").lower()
            if any(
                term in category
                for term in ["cold", "flu", "respiratory", "antibiotic"]
            ):
                adjustments["flu_season"] = self.config.flu_season_multiplier

        # Holiday adjustment (December)
        if current_month == 12:
            adjustments["holiday"] = self.config.holiday_reduction

        # Summer adjustment (June-August)
        if current_month in [6, 7, 8]:
            category = med.get("category", "").lower()
            if "chronic" not in category:  # Don't reduce chronic medications
                adjustments["summer"] = self.config.summer_reduction

        # Category-specific adjustments
        category = med.get("category", "").lower()
        if "chronic" in category:
            # Chronic medications are more stable
            adjustments["category_stability"] = 1.0
        elif "intermittent" in category:
            # Intermittent medications have more variability
            adjustments["category_stability"] = 1.1
        elif "sporadic" in category:
            # Sporadic medications are unpredictable
            adjustments["category_stability"] = 1.2

        return adjustments

    def _parse_json_robust(self, content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        raise ValueError("Failed to parse JSON from model output")

    def _analyze_context_with_llm(
        self,
        med: Dict[str, Any],
        forecast: Dict[str, Any],
        rule_adjustments: Dict[str, float],
        current_date_iso: str,
        month_name: str,
        year: int,
    ) -> Dict[str, Any]:
        """Use LLM to analyze additional context"""

        schema_hint = (
            '{"event_adjustment": 1.0, "event_name": "event description", '
            '"confidence": 0.0, "reasoning": "brief explanation"}'
        )

        system_msg = SystemMessage(
            content=(
                "Return ONLY a JSON object exactly matching the requested schema. "
                "No prose, no code fences."
            )
        )

        prompt = f"""Analyze context for medication demand adjustment in the United States:

Medication: {med["name"]}
Category: {med.get("category", "Unknown")}
Forecasted Quantity: {forecast["forecast_quantity"]:.0f} units
Current Date: {current_date_iso} (Month: {month_name}, Year: {year})
Rule-based Adjustments: {json.dumps(rule_adjustments, indent=2)}

Consider US-specific external factors:
1. Current US events (flu season, school calendar, holidays) for the given month
2. Weather patterns relevant to US regions
3. US economic factors affecting purchasing
4. Supply chain disruptions affecting US distributors
5. Regulatory changes in the US healthcare system

Respond in JSON format only with this schema:
{schema_hint}
"""

        try:
            response = self.llm.invoke([system_msg, HumanMessage(content=prompt)])
            analysis = self._parse_json_robust(response.content)
            return {
                "event_adjustment": float(analysis.get("event_adjustment", 1.0)),
                "event_name": analysis.get("event_name", ""),
                "confidence": float(analysis.get("confidence", 0.5)),
                "reasoning": analysis.get("reasoning", ""),
            }
        except Exception as e:
            logger.warning(f"AdjustmentAgent JSON parse failed, retrying: {e}")

        # Retry once with stricter instruction
        retry_msg = SystemMessage(
            content="Return only a valid JSON object (no markdown). Follow the schema strictly."
        )
        try:
            response = self.llm.invoke(
                [system_msg, retry_msg, HumanMessage(content=prompt)]
            )
            analysis = self._parse_json_robust(response.content)
            return {
                "event_adjustment": float(analysis.get("event_adjustment", 1.0)),
                "event_name": analysis.get("event_name", ""),
                "confidence": float(analysis.get("confidence", 0.5)),
                "reasoning": analysis.get("reasoning", ""),
            }
        except Exception as e:
            # Fallback if LLM fails
            return {
                "event_adjustment": 1.0,
                "event_name": "none",
                "confidence": 0.0,
                "reasoning": f"LLM analysis failed: {str(e)}",
            }

    def _combine_adjustments(
        self,
        original_quantity: float,
        rule_adjustments: Dict[str, float],
        llm_adjustments: Dict[str, Any],
        med: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Combine all adjustments and apply to quantity"""

        # Calculate total adjustment factor
        total_factor = 1.0
        adjustment_breakdown = {}

        # Apply rule-based adjustments
        for name, factor in rule_adjustments.items():
            total_factor *= factor
            adjustment_breakdown[name] = factor

        # Apply LLM adjustment with confidence weighting
        llm_factor = llm_adjustments.get("event_adjustment", 1.0)
        llm_confidence = llm_adjustments.get("confidence", 0.0)

        # Weight LLM adjustment by confidence
        weighted_llm_factor = 1.0 + (llm_factor - 1.0) * llm_confidence
        total_factor *= weighted_llm_factor

        if llm_confidence > 0.3:  # Only include if confident enough
            adjustment_breakdown["event"] = weighted_llm_factor

        # Apply bounds to prevent extreme adjustments
        total_factor = max(0.5, min(2.0, total_factor))

        # Calculate adjusted quantity
        adjusted_quantity = original_quantity * total_factor

        # Round to pack size
        pack_size = med.get("pack_size", 1)
        adjusted_quantity = round(adjusted_quantity / pack_size) * pack_size

        # Ensure minimum order quantity
        min_order = pack_size * 2  # At least 2 packs
        adjusted_quantity = max(adjusted_quantity, min_order)

        # Check against max stock constraint
        max_stock = med.get("max_stock", float("inf"))
        current_stock = med.get("current_stock", 0)
        max_order = max(0, max_stock - current_stock)

        if max_stock < float("inf"):
            adjusted_quantity = min(adjusted_quantity, max_order)

        # Build reasoning
        reasoning_parts = []
        for name, factor in adjustment_breakdown.items():
            if factor != 1.0:
                direction = "increased" if factor > 1.0 else "decreased"
                percent = abs(int((factor - 1.0) * 100))
                reasoning_parts.append(f"{name}: {direction} by {percent}%")

        if llm_adjustments.get("event_name") and llm_confidence > 0.3:
            reasoning_parts.append(f"Event: {llm_adjustments['event_name']}")

        reasoning = (
            ". ".join(reasoning_parts) if reasoning_parts else "No adjustments needed"
        )

        return {
            "med_id": med["med_id"],
            "original_quantity": original_quantity,
            "adjusted_quantity": adjusted_quantity,
            "adjustment_factors": adjustment_breakdown,
            "total_adjustment_factor": total_factor,
            "reasoning": reasoning,
            "llm_insight": llm_adjustments.get("reasoning", ""),
            "confidence": 0.75 + llm_confidence * 0.25,
            "timestamp": datetime.utcnow().isoformat(),
        }
