"""Demand Forecasting Agent for PO Generation"""

import json
import re
import numpy as np
from typing import Dict, Any
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..config import get_config
from ..state import POGenerationState, AgentReasoning, update_progress, add_reasoning
from ..logger import forecast_logger as logger


class ForecastAgent:
    """Agent responsible for forecasting medication demand"""

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
        """Process state and generate forecasts"""

        logger.info(
            f"Starting forecast generation for {len(state['medications'])} medications"
        )

        # Update progress
        state = update_progress(
            state, "forecast_agent", "Analyzing consumption patterns", 10
        )

        forecast_data = {}
        reasoning_points = []

        for med in state["medications"]:
            med_id = med["med_id"]
            logger.debug(f"Processing forecast for medication {med_id}: {med['name']}")

            # Get consumption history
            history = state["consumption_history"].get(med_id, {})

            # Calculate base forecast using moving average
            base_forecast = self._calculate_base_forecast(
                history, med, state["current_stock"].get(med_id, 0)
            )

            # Optionally use LLM to provide qualitative insights only (no numeric adjustments here)
            llm_analysis = self._analyze_with_llm(med, history, base_forecast)

            # Combine using ONLY base statistical forecast (ignore any adjustment factors)
            final_forecast = self._combine_forecasts(base_forecast, llm_analysis, med)

            forecast_data[med_id] = final_forecast

            # Build detailed reasoning for this medication
            med_reasoning = []

            # Base forecast details
            if base_forecast.get("method") == "moving_average_with_trend":
                avg_consumption = base_forecast.get("avg_consumption", 0)
                trend_factor = base_forecast.get("trend_factor", 1.0)
                safety_multiplier = base_forecast.get("safety_multiplier", 1.0)
                base_qty = base_forecast.get("base_quantity", 0)

                trend_direction = (
                    "increasing"
                    if trend_factor > 1.05
                    else "decreasing"
                    if trend_factor < 0.95
                    else "stable"
                )
                safety_percent = int((safety_multiplier - 1) * 100)

                med_reasoning.append(
                    f"Base forecast: {avg_consumption:.1f} units/day average × {self.config.forecast_horizon_months * 30} days × {trend_factor:.2f} trend factor = {base_qty:.0f} units"
                )
                med_reasoning.append(
                    f"Consumption trend: {trend_direction} ({trend_factor:.2f}x)"
                )
                if safety_percent > 0:
                    med_reasoning.append(
                        f"Safety stock adjustment: +{safety_percent}% for demand variability"
                    )

            # LLM analysis details (qualitative only)
            llm_reasoning = llm_analysis.get("reasoning", "")
            if llm_reasoning:
                med_reasoning.append(f"AI analysis: {llm_reasoning}")

            # Final result (no LLM numeric adjustment here)
            final_qty = final_forecast.get("forecast_quantity", 0)
            pack_size = med.get("pack_size", 1)
            packs = int(final_qty / pack_size) if pack_size > 0 else 1

            med_reasoning.append(
                f"Final forecast: {final_qty:.0f} units ({packs} packs of {pack_size})"
            )

            # Add to overall reasoning
            reasoning_points.extend(
                [f"{med['name']}: {reason}" for reason in med_reasoning]
            )

            logger.debug(
                f"Completed forecast for {med['name']}: {final_forecast['forecast_quantity']} units"
            )

        # Update state with forecast data
        state["forecast_data"] = forecast_data
        logger.info("Forecast generation completed for all medications")

        # Add reasoning
        reasoning = AgentReasoning(
            agent_name="forecast_agent",
            timestamp=datetime.utcnow().isoformat(),
            input_summary=f"Analyzing {len(state['medications'])} medications",
            decision_points=reasoning_points,
            output_summary=f"Generated forecasts for {len(forecast_data)} medications",
            confidence=0.85,
        )
        state = add_reasoning(state, "forecast_agent", reasoning)

        # Update progress
        state = update_progress(
            state,
            "forecast_agent",
            "Forecast generation complete",
            100,
            f"Generated forecasts for {len(forecast_data)} medications",
        )

        return state

    def _calculate_base_forecast(
        self, history: Dict[str, Any], med: Dict[str, Any], current_stock: float
    ) -> Dict[str, Any]:
        """Calculate base forecast using statistical methods"""

        # Get historical data
        historical_data = history.get("historical_data", [])
        if not historical_data:
            # Fallback to simple calculation
            avg_daily = med.get("avg_daily_consumption", 10)
            forecast_quantity = avg_daily * 30 * self.config.forecast_horizon_months

            return {
                "base_quantity": forecast_quantity,
                "method": "simple_average",
                "confidence": 0.5,
            }

        # Extract consumption values
        consumptions = [
            d.get("consumption", 0)
            for d in historical_data[-self.config.forecast_lookback_days :]
        ]

        if not consumptions:
            avg_daily = med.get("avg_daily_consumption", 10)
            forecast_quantity = avg_daily * 30 * self.config.forecast_horizon_months

            return {
                "base_quantity": forecast_quantity,
                "method": "fallback",
                "confidence": 0.5,
            }

        # Calculate statistics
        avg_consumption = float(np.mean(consumptions))
        std_consumption = float(np.std(consumptions)) if len(consumptions) > 1 else 0.0

        # Calculate trend
        if len(consumptions) >= 7:
            recent_avg = float(np.mean(consumptions[-7:]))
            older_avg = float(np.mean(consumptions[:-7]))
            trend_factor = (recent_avg / older_avg) if older_avg > 0 else 1.0
        else:
            trend_factor = 1.0

        # Calculate forecast quantity
        days_in_period = 30 * self.config.forecast_horizon_months
        base_quantity = avg_consumption * days_in_period * trend_factor

        # Add safety stock based on variability
        safety_multiplier = 1 + (
            std_consumption / avg_consumption if avg_consumption > 0 else 0.1
        )
        forecast_quantity = base_quantity * min(
            safety_multiplier, 1.3
        )  # Cap at 30% extra

        # Consider reorder point and max stock
        reorder_point = med.get("reorder_point", 0)
        max_stock = med.get("max_stock", float("inf"))

        # Ensure we order enough to reach reorder point + safety
        min_quantity = max(
            0, reorder_point + med.get("safety_stock", 0) - current_stock
        )
        forecast_quantity = max(forecast_quantity, min_quantity)

        # Don't exceed max stock
        max_quantity = max(0, max_stock - current_stock)
        forecast_quantity = (
            min(forecast_quantity, max_quantity)
            if max_stock < float("inf")
            else forecast_quantity
        )

        return {
            "base_quantity": float(forecast_quantity),
            "method": "moving_average_with_trend",
            "avg_consumption": float(avg_consumption),
            "trend_factor": float(trend_factor),
            "safety_multiplier": float(safety_multiplier),
            "confidence": 0.75,
        }

    def _parse_json_robust(self, content: str) -> Dict[str, Any]:
        """Parse JSON from model output reliably by stripping fences and extracting the first object."""
        text = (content or "").strip()
        # Strip code fences if present
        if text.startswith("```"):
            # remove first fence
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            # remove trailing fence
            text = re.sub(r"```$", "", text).strip()
        # Try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # Find the first JSON object
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        raise ValueError("Failed to parse JSON from model output")

    def _analyze_with_llm(
        self,
        med: Dict[str, Any],
        history: Dict[str, Any],
        base_forecast: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use LLM to analyze patterns and provide insights (qualitative only)"""

        # Prepare context for LLM
        context = {
            "medication": med["name"],
            "category": med.get("category", "Unknown"),
            "current_stock": med.get("current_stock", 0),
            "avg_daily_consumption": base_forecast.get("avg_consumption", 0),
            "trend_factor": base_forecast.get("trend_factor", 1.0),
            "base_forecast_quantity": base_forecast.get("base_quantity", 0),
            "forecast_months": self.config.forecast_horizon_months,
        }

        schema_hint = (
            '{"is_reasonable": true/false, '
            '"key_factors": ["factor1", "factor2"], "reasoning": "brief explanation"}'
        )

        system_msg = SystemMessage(
            content=(
                "Return ONLY a JSON object exactly matching the requested schema. "
                "No prose, no code fences."
            )
        )

        prompt = f"""Analyze the medication demand forecast and provide qualitative insights (United States healthcare context):

Medication: {context["medication"]}
Category: {context["category"]}
Current Stock: {context["current_stock"]} units
Average Daily Consumption: {context["avg_daily_consumption"]:.1f} units
Trend Factor: {context["trend_factor"]:.2f}
Base Forecast for {context["forecast_months"]} months: {context["base_forecast_quantity"]:.0f} units

Do not suggest numeric adjustments. Provide qualitative factors only.
Respond in JSON format only with this schema:
{schema_hint}
"""

        # Try once with JSON mode and strict system instruction
        try:
            response = self.llm.invoke([system_msg, HumanMessage(content=prompt)])
            analysis = self._parse_json_robust(response.content)
            return {
                # No numeric factor returned here
                "key_factors": analysis.get("key_factors", []),
                "reasoning": analysis.get("reasoning", ""),
                "llm_confidence": 0.8,
            }
        except Exception as e:
            logger.warning(
                f"ForecastAgent JSON parse failed, retrying with stricter instruction: {e}"
            )

        # Retry once with even stricter instruction
        retry_prompt = (
            "You must return only a valid JSON object (no markdown). "
            "Follow the schema strictly."
        )
        try:
            response = self.llm.invoke(
                [
                    system_msg,
                    SystemMessage(content=retry_prompt),
                    HumanMessage(content=prompt),
                ]
            )
            analysis = self._parse_json_robust(response.content)
            return {
                "key_factors": analysis.get("key_factors", []),
                "reasoning": analysis.get("reasoning", ""),
                "llm_confidence": 0.8,
            }
        except Exception as e:
            # Fallback if LLM fails
            return {
                "key_factors": ["statistical_analysis_only"],
                "reasoning": f"LLM analysis failed, using statistical forecast only: {str(e)}",
                "llm_confidence": 0.0,
            }

    def _combine_forecasts(
        self,
        base_forecast: Dict[str, Any],
        llm_analysis: Dict[str, Any],
        med: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Combine base forecast with LLM insights (no numeric adjustment here)"""

        base_quantity = base_forecast.get("base_quantity", 0)

        # Final quantity equals base quantity (rounded to pack size)
        pack_size = med.get("pack_size", 1)
        final_quantity = round(base_quantity / pack_size) * pack_size

        # Confidence combines base and a small weight for LLM qualitative confidence
        base_confidence = base_forecast.get("confidence", 0.5)
        llm_confidence = llm_analysis.get("llm_confidence", 0.0)
        combined_confidence = base_confidence * 0.9 + llm_confidence * 0.1

        return {
            "med_id": int(med["med_id"]),
            "forecast_quantity": float(final_quantity),
            "forecast_months": int(self.config.forecast_horizon_months),
            "confidence_score": float(combined_confidence),
            "method_used": f"{base_forecast['method']}",
            "base_quantity": float(base_quantity),
            "adjustment_factor": 1.0,
            "key_factors": llm_analysis.get("key_factors", []),
            "reasoning": f"Base forecast: {base_quantity:.0f} units. {llm_analysis.get('reasoning', '')}",
            "timestamp": datetime.utcnow().isoformat(),
        }
