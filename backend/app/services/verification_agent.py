"""
Two-Step Verification Agent Pattern for Reliable Vegan Recipe Recommendations.

This module implements a verification pipeline that:
1. **Step A**: The RAG system queries the vector DB for recipes
2. **Step B**: Before returning results, the agent triggers a "Verification Tool" 
   that calls external APIs to ensure ingredients are truly vegan

The agent enforces reliability constraints and prevents hallucination about
dietary claims by grounding every recommendation in verified data sources.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.services.data_fetcher import (
    get_verifier,
    VeganIngredientVerifier,
    ANIMAL_DERIVED_INGREDIENTS,
)

logger = logging.getLogger("vegvibe.verification_agent")


class VerificationStatus(str, Enum):
    """Status of recipe verification."""
    VERIFIED_VEGAN = "verified_vegan"
    CONTAINS_ANIMAL_DERIVED = "contains_animal_derived"
    CONTAINS_UNKNOWN = "contains_unknown"
    VERIFICATION_FAILED = "verification_failed"


@dataclass
class VerificationResult:
    """Result of a single recipe verification."""
    recipe_id: int
    recipe_title: str
    status: VerificationStatus
    verified_vegan_ingredients: List[str]
    animal_derived_ingredients: List[str]
    unknown_ingredients: List[str]
    confidence_score: float
    evidence: List[str]
    reason_for_rejection: Optional[str] = None
    
    def is_safe_to_recommend(self) -> bool:
        """Check if recipe is safe to recommend."""
        return (
            self.status == VerificationStatus.VERIFIED_VEGAN
            and len(self.animal_derived_ingredients) == 0
        )


class TwoStepVerificationAgent:
    """
    Implements the Two-Step Verification Agent Pattern:
    
    Step A: Query recipes from RAG/vector DB
    Step B: Verify each result against USDA, Open Food Facts, and PETA guidelines
    
    This ensures that no recipe is recommended without external verification.
    """
    
    def __init__(self):
        """Initialize verification agent with external API clients."""
        self.verifier: VeganIngredientVerifier = get_verifier()
        self.verification_attempts = 0
        self.verification_failures = 0
    
    def verify_recipe_ingredients(
        self,
        recipe_id: int,
        recipe_title: str,
        ingredients_list: List[str],
    ) -> VerificationResult:
        """
        **Verification Tool**: Main verification function called in Step B.
        
        This is the core "tool use" that constrains the LLM's creativity with
        hard data from external sources.
        
        Args:
            recipe_id: ID of the recipe in the database
            recipe_title: Name of the recipe
            ingredients_list: List of ingredient names from the recipe
        
        Returns:
            VerificationResult with detailed findings
        """
        self.verification_attempts += 1
        
        try:
            # Verify all ingredients
            all_vegan, report = self.verifier.verify_recipe_ingredients(ingredients_list)
            
            # Categorize findings
            verified_vegan = [
                item["ingredient"] for item in report["verified_vegan"]
            ]
            animal_derived = [
                item["ingredient"] for item in report["animal_derived"]
            ]
            unknown = [
                item["ingredient"] for item in report["unknown"]
            ]
            
            # Determine overall status
            if animal_derived:
                status = VerificationStatus.CONTAINS_ANIMAL_DERIVED
                reason = (
                    f"Recipe contains animal-derived ingredients: "
                    f"{', '.join(animal_derived[:3])}"
                )
            elif unknown and len(unknown) / len(ingredients_list) > 0.3:
                # More than 30% unknown ingredients = insufficient confidence
                status = VerificationStatus.CONTAINS_UNKNOWN
                reason = (
                    f"Too many unverified ingredients ({len(unknown)}/{len(ingredients_list)}). "
                    f"Cannot guarantee vegan status."
                )
            else:
                status = VerificationStatus.VERIFIED_VEGAN
                reason = None
            
            # Build evidence trail for transparency
            evidence = []
            for item in report["verified_vegan"]:
                evidence.extend(item["evidence"])
            for item in report["animal_derived"]:
                evidence.extend(item["evidence"])
            for item in report["unknown"]:
                evidence.extend(item["evidence"])
            
            result = VerificationResult(
                recipe_id=recipe_id,
                recipe_title=recipe_title,
                status=status,
                verified_vegan_ingredients=verified_vegan,
                animal_derived_ingredients=animal_derived,
                unknown_ingredients=unknown,
                confidence_score=report["confidence_score"],
                evidence=evidence[:5],  # Keep top 5 evidence items
                reason_for_rejection=reason,
            )
            
            logger.info(
                f"✓ Verification complete for '{recipe_title}' (RID:{recipe_id}): "
                f"status={status.value}, confidence={report['confidence_score']:.2%}"
            )
            
            return result
            
        except Exception as e:
            self.verification_failures += 1
            logger.error(f"✗ Verification failed for recipe {recipe_id}: {e}")
            
            return VerificationResult(
                recipe_id=recipe_id,
                recipe_title=recipe_title,
                status=VerificationStatus.VERIFICATION_FAILED,
                verified_vegan_ingredients=[],
                animal_derived_ingredients=[],
                unknown_ingredients=ingredients_list,
                confidence_score=0.0,
                evidence=[f"Verification tool failed: {str(e)}"],
                reason_for_rejection="Verification service unavailable",
            )
    
    def verify_recipe_batch(
        self,
        recipes: List[Dict[str, Any]],
    ) -> Tuple[List[VerificationResult], List[Dict[str, Any]]]:
        """
        Verify a batch of recipes (Step B applied to multiple results).
        
        Args:
            recipes: List of recipe dictionaries with 'id', 'title', 'ingredients'
        
        Returns:
            Tuple of (verification_results, filtered_safe_recipes)
        """
        results: List[VerificationResult] = []
        safe_recipes: List[Dict[str, Any]] = []
        
        for recipe in recipes:
            recipe_id = recipe.get("id", -1)
            recipe_title = recipe.get("title", "Unknown")
            ingredients = recipe.get("ingredients", [])
            
            # Normalize ingredients to list if needed
            if isinstance(ingredients, str):
                ingredients = [ing.strip() for ing in ingredients.split(",")]
            
            # Run verification
            verification = self.verify_recipe_ingredients(
                recipe_id=recipe_id,
                recipe_title=recipe_title,
                ingredients_list=ingredients,
            )
            results.append(verification)
            
            # Only include verified recipes
            if verification.is_safe_to_recommend():
                recipe["_verification"] = verification
                safe_recipes.append(recipe)
        
        return results, safe_recipes
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Get statistics about verification attempts."""
        success_rate = (
            (self.verification_attempts - self.verification_failures)
            / max(self.verification_attempts, 1)
        ) * 100
        
        return {
            "total_verifications": self.verification_attempts,
            "failed_verifications": self.verification_failures,
            "success_rate": f"{success_rate:.1f}%",
        }
    
    def format_verification_for_user(self, result: VerificationResult) -> str:
        """
        Format verification result for user-facing feedback.
        
        Args:
            result: VerificationResult object
        
        Returns:
            Human-readable verification summary
        """
        if result.is_safe_to_recommend():
            summary = (
                f"✅ **Verified Vegan**: {result.recipe_title}\n"
                f"   Confidence: {result.confidence_score:.0%}\n"
                f"   Verified ingredients: {len(result.verified_vegan_ingredients)}/{len(result.verified_vegan_ingredients) + len(result.unknown_ingredients)}\n"
            )
        elif result.status == VerificationStatus.CONTAINS_ANIMAL_DERIVED:
            summary = (
                f"❌ **NOT VEGAN**: {result.recipe_title}\n"
                f"   Reason: {result.reason_for_rejection}\n"
                f"   Non-vegan ingredients: {', '.join(result.animal_derived_ingredients[:3])}\n"
            )
        elif result.status == VerificationStatus.CONTAINS_UNKNOWN:
            summary = (
                f"⚠️ **CANNOT VERIFY**: {result.recipe_title}\n"
                f"   Reason: {result.reason_for_rejection}\n"
                f"   Unknown ingredients: {', '.join(result.unknown_ingredients[:3])}\n"
            )
        else:
            summary = (
                f"🔧 **VERIFICATION ERROR**: {result.recipe_title}\n"
                f"   Reason: {result.reason_for_rejection}\n"
            )
        
        return summary
