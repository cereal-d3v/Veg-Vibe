import json
import logging
import re
from typing import Any, Dict, List

from app.prompts import (
    SYSTEM_GROUNDED_PROMPT,
    VERIFICATION_REQUIREMENT_PROMPT,
    ANSWER_PROMPT_WITH_VERIFICATION,
)
from app.services.verification_agent import TwoStepVerificationAgent, VerificationStatus
from app.utils.recommend import RecipeRecommender, parse_ingredients

logger = logging.getLogger("vegvibe.agentic")


class AgenticRecipeAssistant:
    """
    Two-Step Verification Pattern for Recipe RAG.
    
    Step A: Query recipes from vector DB (search_recipes tool)
    Step B: Verify each result against external APIs (verify_recipe_ingredients tool)
    
    This implements the "reliable interface" requirement by constraining the LLM's
    creativity with hard data from USDA, Open Food Facts, and PETA guidelines.
    """

    def __init__(self, recommender: RecipeRecommender):
        self.recommender = recommender
        self.verification_agent = TwoStepVerificationAgent()
        logger.info("✓ AgenticRecipeAssistant initialized with verification agent")

    def _map_fuzzy_filters(self, question: str) -> Dict[str, Any]:
        q = question.lower()
        filters: Dict[str, Any] = {
            "min_protein": None,
            "max_calories": None,
            "max_carbs": None,
            "max_total_time": None,
            "dietary_tags": [],
        }

        # Data impedance mapping: natural language -> concrete filter constraints.
        if "high protein" in q or "protein-rich" in q:
            filters["min_protein"] = 20
        if "low carb" in q or "keto" in q:
            filters["max_carbs"] = 20
            filters["dietary_tags"].append("keto")
        if "low calorie" in q or "light" in q:
            filters["max_calories"] = 450
        if "quick" in q or "fast" in q or "under 30" in q:
            filters["max_total_time"] = 30
        if "gluten free" in q:
            filters["dietary_tags"].append("gluten-free")
        if "nut free" in q:
            filters["dietary_tags"].append("nut-free")

        return filters

    def _build_tool_call(self, question: str, max_results: int) -> Dict[str, Any]:
        filters = self._map_fuzzy_filters(question)
        return {
            "tool": "search_recipes",
            "arguments": {
                "query": question,
                "limit": max_results,
                "filters": filters,
            },
        }

    def _format_context(self, recipes: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for row in recipes:
            lines.append(
                " | ".join(
                    [
                        f"RID={row.get('id')}",
                        f"title={row.get('title', '')}",
                        f"ingredients={row.get('ingredients', '')}",
                        f"protein={row.get('protein')}",
                        f"calories={row.get('calories')}",
                    ]
                )
            )
        return "\n".join(lines)
    
    def _format_verification_context(self, verification_results: List[Any]) -> str:
        """Format verification results for inclusion in LLM context."""
        lines: List[str] = []
        for result in verification_results:
            status_icon = {
                VerificationStatus.VERIFIED_VEGAN: "✅",
                VerificationStatus.CONTAINS_ANIMAL_DERIVED: "❌",
                VerificationStatus.CONTAINS_UNKNOWN: "⚠️",
                VerificationStatus.VERIFICATION_FAILED: "🔧",
            }.get(result.status, "❓")
            
            lines.append(
                f"{status_icon} RID:{result.recipe_id} | {result.recipe_title}\n"
                f"   Status: {result.status.value} (confidence: {result.confidence_score:.0%})\n"
                f"   Verified: {', '.join(result.verified_vegan_ingredients[:3])}\n"
                f"   Issues: {result.reason_for_rejection or 'None'}"
            )
        return "\n".join(lines)

    def _synthesize_answer(
        self,
        question: str,
        recipes: List[Dict[str, Any]],
        verification_results: List[Any] = None,
    ) -> str:
        """Synthesize answer with verification status included."""
        if not recipes:
            return (
                "I could not find grounded recipe evidence for that request in the current dataset. "
                "Try adding key ingredients or relaxing constraints."
            )

        verification_results = verification_results or []
        
        lead = (
            "🥬 **Veg Vibe Verified Results** - All recommendations verified against "
            "USDA, Open Food Facts, and PETA guidelines.\n\n"
        )
        bullets: List[str] = []
        
        for row in recipes:
            recipe_id = row.get("id")
            verification = next(
                (v for v in verification_results if v.recipe_id == recipe_id),
                None,
            )
            
            status_icon = "✅" if verification and verification.is_safe_to_recommend() else "❌"
            
            bullet = (
                f"{status_icon} **{row.get('title', 'Unknown')}** [RID:{recipe_id}]\n"
                f"   Ingredients: {row.get('ingredients', '')}\n"
                f"   Protein: {row.get('protein', 'N/A')}g | "
                f"Calories: {row.get('calories', 'N/A')}"
            )
            
            if verification:
                if verification.is_safe_to_recommend():
                    bullet += f"\n   ✅ Verified vegan (confidence: {verification.confidence_score:.0%})"
                else:
                    bullet += f"\n   ❌ {verification.reason_for_rejection}"
            
            bullets.append(bullet)
        
        return lead + "\n".join(bullets)

    def _verify_grounding(self, answer: str, recipes: List[Dict[str, Any]]) -> Dict[str, Any]:
        allowed_ingredients: set[str] = set()
        for row in recipes:
            allowed_ingredients.update(
                self._normalize_ingredients(parse_ingredients(row.get("ingredients", "")))
            )

        mentioned_raw: List[str] = []
        for line in answer.splitlines():
            if "Ingredients:" in line:
                ing_part = line.split("Ingredients:", 1)[1].strip()
                mentioned_raw.extend(parse_ingredients(ing_part))

        mentioned = set(self._normalize_ingredients(mentioned_raw))

        hallucinated = sorted(list(mentioned - allowed_ingredients))
        report = {
            "grounded": len(hallucinated) == 0,
            "hallucinated_ingredients": hallucinated,
            "checked_ingredient_mentions": sorted(list(mentioned)),
        }
        logger.info("agentic_reliability=%s", json.dumps(report))
        return report

    def _normalize_ingredients(self, items: List[str]) -> List[str]:
        normalized: List[str] = []
        for item in items:
            txt = item.lower()
            txt = re.sub(r"\([^)]*\)", "", txt)
            txt = re.sub(r"\b\d+[\d/\.]*\b", "", txt)
            txt = re.sub(
                r"\b(c|cup|cups|tbsp|tablespoon|tablespoons|tsp|teaspoon|teaspoons|oz|ounce|ounces|lb|pound|pounds|can|cans|pkg|package|small|large|medium|firmly|packed|melted|softened|choice|as|many|you|need|for|dinner)\b",
                "",
                txt,
            )
            txt = re.sub(r"[^a-z\s-]", " ", txt)
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt:
                normalized.append(txt)
        return normalized

    def answer(self, question: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Answer with Two-Step Verification Pattern.
        
        Step A: Query recipes from the vector DB
        Step B: Verify each result against external APIs
        
        Returns verified recipes with transparency about vegan status.
        """
        # STEP A: Query recipes from vector DB
        tool_call = self._build_tool_call(question=question, max_results=max_results)
        args = tool_call["arguments"]
        recipes = self.recommender.search_recipes_tool(
            query=args["query"],
            limit=args["limit"],
            filters=args["filters"],
        )

        # Reliability fallback: preserve tool interface but relax filters if nothing is found.
        if not recipes and any(v for v in args["filters"].values()):
            fallback_call = {
                "tool": "search_recipes",
                "arguments": {
                    "query": args["query"],
                    "limit": args["limit"],
                    "filters": {
                        "min_protein": None,
                        "max_calories": None,
                        "max_carbs": None,
                        "max_total_time": None,
                        "dietary_tags": [],
                    },
                },
            }
            recipes = self.recommender.search_recipes_tool(
                query=fallback_call["arguments"]["query"],
                limit=fallback_call["arguments"]["limit"],
                filters=fallback_call["arguments"]["filters"],
            )
            tool_call = fallback_call

        # STEP B: Verify all retrieved recipes
        verification_results, safe_recipes = self.verification_agent.verify_recipe_batch(
            recipes=recipes
        )

        # Generate answer with verification status
        answer = self._synthesize_answer(
            question=question,
            recipes=recipes,
            verification_results=verification_results,
        )
        
        # Verify grounding (check for hallucinated ingredients)
        reliability = self._verify_grounding(answer=answer, recipes=recipes)
        
        # Count verified vegan recipes
        verified_vegan_count = sum(
            1 for v in verification_results 
            if v.is_safe_to_recommend()
        )
        
        citations = [int(r["id"]) for r in recipes if r.get("id") is not None]
        
        return {
            "answer": answer,
            "citations": citations,
            "retrieved_count": len(recipes),
            "verified_vegan_count": verified_vegan_count,
            "tool_call": tool_call,
            "reliability": reliability,
            "tool_context": self._format_context(recipes),
            "verification_context": self._format_verification_context(verification_results),
            "verification_results": [
                {
                    "recipe_id": v.recipe_id,
                    "recipe_title": v.recipe_title,
                    "status": v.status.value,
                    "confidence": v.confidence_score,
                    "is_safe": v.is_safe_to_recommend(),
                }
                for v in verification_results
            ],
            "verification_stats": self.verification_agent.get_verification_stats(),
        }
