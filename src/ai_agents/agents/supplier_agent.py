"""Supplier Optimization Agent for PO Generation"""

import json
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

from ..config import get_config
from ..state import POGenerationState, AgentReasoning, update_progress, add_reasoning
from ..logger import supplier_logger as logger


class SupplierAgent:
    """Agent responsible for optimizing supplier selection and allocation"""

    def __init__(self):
        self.config = get_config()
        self.llm = ChatOpenAI(
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            openai_api_key=self.config.openai_api_key,
            timeout=self.config.request_timeout,
        )

    def __call__(self, state: POGenerationState) -> POGenerationState:
        """Process state and optimize supplier allocations"""

        logger.info(
            f"Starting supplier optimization for {len(state.get('adjusted_quantities', {}))} items"
        )

        # Update progress
        state = update_progress(state, "supplier_agent", "Evaluating suppliers", 10)

        supplier_allocations = {}
        reasoning_points = []

        # Score all suppliers
        supplier_scores = self._score_suppliers(state["suppliers"])

        for med_id, adjusted in state["adjusted_quantities"].items():
            med = next((m for m in state["medications"] if m["med_id"] == med_id), None)
            if not med:
                continue

            # Get supplier options for this medication
            supplier_options = self._get_supplier_options(
                med, state["suppliers"], supplier_scores
            )

            # Use LLM to analyze supplier selection
            llm_recommendation = self._analyze_suppliers_with_llm(
                med, adjusted["adjusted_quantity"], supplier_options
            )

            # Optimize allocation
            allocation = self._optimize_allocation(
                med, adjusted["adjusted_quantity"], supplier_options, llm_recommendation
            )

            supplier_allocations[med_id] = allocation

            # Build detailed supplier reasoning
            quantity_needed = adjusted["adjusted_quantity"]
            strategy = allocation.get("strategy", "single")
            total_cost = allocation.get("total_cost", 0)
            avg_lead_time = allocation.get("avg_lead_time", 0)

            med_reasoning = []
            med_reasoning.append(f"Quantity needed: {quantity_needed:.0f} units")

            # Show top supplier options considered
            if len(supplier_options) > 1:
                top_3 = supplier_options[:3]
                options_desc = []
                for opt in top_3:
                    score_desc = f"score {opt['score']:.2f}"
                    lead_desc = f"{opt['lead_time']}d lead"
                    price_desc = f"${opt['price_per_unit']:.2f}/unit"
                    options_desc.append(
                        f"{opt['supplier_name']} ({score_desc}, {lead_desc}, {price_desc})"
                    )
                med_reasoning.append(
                    f"Top suppliers evaluated: {'; '.join(options_desc)}"
                )

            # Strategy reasoning
            if strategy == "split":
                med_reasoning.append("Strategy: Split order for risk mitigation")
                for alloc in allocation["allocations"]:
                    supplier_name = alloc["supplier_name"]
                    qty = alloc["quantity"]
                    percent = (
                        int((qty / quantity_needed) * 100) if quantity_needed > 0 else 0
                    )
                    price = alloc["unit_price"]
                    lead_time = alloc["lead_time"]
                    subtotal = alloc["subtotal"]
                    med_reasoning.append(
                        f"  → {supplier_name}: {qty:.0f} units ({percent}%) @ ${price:.2f}/unit, "
                        f"{lead_time}d lead time, subtotal ${subtotal:.2f}"
                    )
            else:
                alloc = (
                    allocation["allocations"][0] if allocation["allocations"] else {}
                )
                supplier_name = alloc.get("supplier_name", "Unknown")
                price = alloc.get("unit_price", 0)
                lead_time = alloc.get("lead_time", 0)

                # Get supplier selection reason
                if supplier_options:
                    best_supplier = supplier_options[0]
                    if best_supplier.get("is_primary"):
                        reason = "primary supplier"
                    elif best_supplier["score"] > 0.8:
                        reason = "highest reliability score"
                    elif best_supplier["lead_time"] <= 3:
                        reason = "shortest lead time"
                    else:
                        reason = "best overall score"

                    med_reasoning.append(f"Strategy: Single supplier ({reason})")

                med_reasoning.append(
                    f"Selected: {supplier_name} @ ${price:.2f}/unit, "
                    f"{lead_time}d lead time, total ${total_cost:.2f}"
                )

            # LLM recommendation insight
            llm_reasoning = llm_recommendation.get("reasoning", "")
            if llm_reasoning and "LLM failed" not in llm_reasoning:
                med_reasoning.append(f"AI recommendation: {llm_reasoning}")

            # Summary metrics
            med_reasoning.append(f"Average lead time: {avg_lead_time:.1f} days")

            # Add to overall reasoning with medication name prefix
            reasoning_points.extend(
                [f"{med['name']}: {reason}" for reason in med_reasoning]
            )

        # Update state
        state["supplier_allocations"] = supplier_allocations

        # Add reasoning
        reasoning = AgentReasoning(
            agent_name="supplier_agent",
            timestamp=datetime.utcnow().isoformat(),
            input_summary=f"Optimizing suppliers for {len(state['adjusted_quantities'])} medications",
            decision_points=reasoning_points,
            output_summary=f"Created allocations for {len(supplier_allocations)} medications",
            confidence=0.88,
        )
        state = add_reasoning(state, "supplier_agent", reasoning)

        # Update progress
        state = update_progress(
            state,
            "supplier_agent",
            "Supplier optimization complete",
            100,
            f"Optimized suppliers for {len(supplier_allocations)} medications",
        )

        return state

    def _score_suppliers(self, suppliers: List[Dict[str, Any]]) -> Dict[int, float]:
        """Score suppliers based on multiple criteria"""

        scores = {}
        weights = self.config.supplier_scoring_weights

        for supplier in suppliers:
            supplier_id = supplier.get("supplier_id")
            score = 0.0

            # Lead time score (lower is better)
            lead_time = supplier.get("avg_lead_time", 7)
            lead_time_score = max(0, 1 - (lead_time / self.config.max_lead_time_days))
            score += lead_time_score * weights.get("lead_time", 0.3)

            # Status score
            status = supplier.get("status", "Unknown")
            status_score = (
                1.0 if status == "OK" else (0.5 if status == "Shortage" else 0.0)
            )
            score += status_score * weights.get("status", 0.3)

            # Price score (placeholder - would need actual price comparison)
            # For now, assume all suppliers have similar pricing
            price_score = 0.7
            score += price_score * weights.get("price", 0.4)

            scores[supplier_id] = score

        return scores

    def _get_supplier_options(
        self,
        med: Dict[str, Any],
        suppliers: List[Dict[str, Any]],
        supplier_scores: Dict[int, float],
    ) -> List[Dict[str, Any]]:
        """Get viable supplier options for a medication"""

        options = []

        # Primary supplier (from medication data)
        primary_supplier_id = med.get("supplier_id")

        for supplier in suppliers:
            supplier_id = supplier.get("supplier_id")

            # Check if supplier meets minimum requirements
            if supplier_scores.get(supplier_id, 0) < self.config.min_supplier_score:
                continue

            if supplier.get("avg_lead_time", 999) > self.config.max_lead_time_days:
                continue

            # Get price (use base price for now)
            price = med.get("price", {}).get("price_per_unit", 100)

            # Add price variation for different suppliers (simulation)
            if supplier_id != primary_supplier_id:
                price *= 1.05  # 5% higher for non-primary suppliers

            options.append(
                {
                    "supplier_id": supplier_id,
                    "supplier_name": supplier.get("name"),
                    "score": supplier_scores.get(supplier_id, 0),
                    "lead_time": supplier.get("avg_lead_time", 7),
                    "status": supplier.get("status", "Unknown"),
                    "price_per_unit": price,
                    "is_primary": supplier_id == primary_supplier_id,
                }
            )

        # Sort by score (highest first)
        options.sort(key=lambda x: x["score"], reverse=True)

        return options

    def _analyze_suppliers_with_llm(
        self,
        med: Dict[str, Any],
        quantity: float,
        supplier_options: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use LLM to analyze supplier selection"""

        # Prepare supplier summary
        supplier_summary = []
        for opt in supplier_options[:5]:  # Top 5 options
            supplier_summary.append(
                {
                    "name": opt["supplier_name"],
                    "score": round(opt["score"], 2),
                    "lead_time": opt["lead_time"],
                    "status": opt["status"],
                    "price": opt["price_per_unit"],
                }
            )

        prompt = f"""Analyze supplier selection for medication procurement:

Medication: {med["name"]}
Quantity Needed: {quantity:.0f} units
Category: {med.get("category", "Unknown")}

Top Supplier Options:
{json.dumps(supplier_summary, indent=2)}

Consider:
1. Risk mitigation (single vs multiple suppliers)
2. Lead time urgency
3. Cost optimization
4. Supplier reliability

Recommend supplier strategy in JSON:
{{
    "strategy": "single" or "split",
    "preferred_suppliers": [1-3 supplier names],
    "split_ratios": [percentages if split],
    "reasoning": "brief explanation"
}}"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            recommendation = json.loads(response.content)

            return {
                "strategy": recommendation.get("strategy", "single"),
                "preferred_suppliers": recommendation.get("preferred_suppliers", []),
                "split_ratios": recommendation.get("split_ratios", [100]),
                "reasoning": recommendation.get("reasoning", ""),
            }
        except Exception as e:
            # Fallback strategy
            return {
                "strategy": "single",
                "preferred_suppliers": [supplier_options[0]["supplier_name"]]
                if supplier_options
                else [],
                "split_ratios": [100],
                "reasoning": f"Using highest-scored supplier (LLM failed: {str(e)})",
            }

    def _optimize_allocation(
        self,
        med: Dict[str, Any],
        quantity: float,
        supplier_options: List[Dict[str, Any]],
        llm_recommendation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize final supplier allocation"""

        allocations = []
        total_allocated = 0

        # Determine allocation strategy
        use_splitting = (
            self.config.enable_order_splitting
            and llm_recommendation.get("strategy") == "split"
            and len(supplier_options) >= 2
            and quantity >= 100  # Only split larger orders
        )

        if use_splitting:
            # Split order among multiple suppliers
            preferred = llm_recommendation.get("preferred_suppliers", [])
            split_ratios = llm_recommendation.get("split_ratios", [])

            # Match preferred suppliers to options
            selected_suppliers = []
            for pref_name in preferred[: self.config.max_suppliers_per_order]:
                for opt in supplier_options:
                    if opt["supplier_name"] == pref_name:
                        selected_suppliers.append(opt)
                        break

            # If no matches, use top suppliers
            if not selected_suppliers:
                selected_suppliers = supplier_options[: min(2, len(supplier_options))]

            # Allocate quantities
            for i, supplier in enumerate(selected_suppliers):
                if i < len(split_ratios):
                    ratio = split_ratios[i] / 100
                else:
                    ratio = 1.0 / len(selected_suppliers)

                alloc_quantity = round(quantity * ratio)

                # Ensure minimum order quantity
                pack_size = med.get("pack_size", 1)
                alloc_quantity = max(alloc_quantity, pack_size * 2)

                # Round to pack size
                alloc_quantity = round(alloc_quantity / pack_size) * pack_size

                allocations.append(
                    {
                        "supplier_id": supplier["supplier_id"],
                        "supplier_name": supplier["supplier_name"],
                        "quantity": alloc_quantity,
                        "unit_price": supplier["price_per_unit"],
                        "lead_time": supplier["lead_time"],
                        "subtotal": alloc_quantity * supplier["price_per_unit"],
                    }
                )

                total_allocated += alloc_quantity

            # Adjust last allocation to match total quantity
            if allocations and total_allocated != quantity:
                difference = quantity - total_allocated
                allocations[-1]["quantity"] += difference
                allocations[-1]["subtotal"] = (
                    allocations[-1]["quantity"] * allocations[-1]["unit_price"]
                )

        else:
            # Single supplier allocation
            best_supplier = supplier_options[0] if supplier_options else None

            if best_supplier:
                allocations.append(
                    {
                        "supplier_id": best_supplier["supplier_id"],
                        "supplier_name": best_supplier["supplier_name"],
                        "quantity": quantity,
                        "unit_price": best_supplier["price_per_unit"],
                        "lead_time": best_supplier["lead_time"],
                        "subtotal": quantity * best_supplier["price_per_unit"],
                    }
                )

        # Calculate totals
        total_cost = sum(a["subtotal"] for a in allocations)
        avg_lead_time = (
            sum(a["lead_time"] * a["quantity"] for a in allocations) / quantity
            if quantity > 0
            else 0
        )

        # Build reasoning
        reasoning_parts = []
        if use_splitting:
            reasoning_parts.append(
                f"Split order among {len(allocations)} suppliers for risk mitigation"
            )
        else:
            reasoning_parts.append("Single supplier allocation for simplicity")

        reasoning_parts.append(llm_recommendation.get("reasoning", ""))

        for alloc in allocations:
            reasoning_parts.append(
                f"{alloc['supplier_name']}: {alloc['quantity']} units @ ${alloc['unit_price']:.2f}"
            )

        return {
            "med_id": med["med_id"],
            "allocations": allocations,
            "total_cost": total_cost,
            "avg_lead_time": avg_lead_time,
            "strategy": "split" if use_splitting else "single",
            "reasoning": " | ".join(reasoning_parts),
            "confidence": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _get_supplier_name(
        self, suppliers: List[Dict[str, Any]], supplier_id: int
    ) -> str:
        """Get supplier name by ID"""
        for supplier in suppliers:
            if supplier.get("supplier_id") == supplier_id:
                return supplier.get("name", f"Supplier {supplier_id}")
        return f"Supplier {supplier_id}"
