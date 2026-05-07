"""
Multi-source data fetcher integrating USDA FoodData Central and Open Food Facts APIs.

This service provides grounding for nutritional claims and vegan ingredient verification.
It acts as the "Source of Truth" for nutrient data and ingredient validation.

API Documentation:
- USDA FoodData Central: https://fdc.nal.usda.gov/api-guide
  * Provides authoritative nutritional data
  * Requires API_KEY environment variable
  * Free tier available at https://fdc.nal.usda.gov/

- Open Food Facts: https://world.openfoodfacts.org/data
  * Verifies if branded products are plant-based
  * Open API, no key required (but rate-limited)
  * Community-maintained vegan product database

- PETA Animal-Derived Ingredients Reference:
  * Used as hard-coded filter for ingredient verification
  * Source: https://www.peta.org/living/food/animal-derived-ingredients/
"""

import logging
import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger("vegvibe.data_fetcher")


# PETA-aligned animal-derived ingredients that should NEVER appear in vegan recipes
ANIMAL_DERIVED_INGREDIENTS = {
    # Dairy & Lactose
    "milk", "dairy", "cheese", "whey", "casein", "lactose", "butter", "ghee", "cream",
    "yogurt", "sour cream", "buttermilk", "kefir", "ricotta", "mozzarella", "feta",
    "parmesan", "cheddar", "brie", "camembert", "gouda", "halloumi",
    
    # Eggs & Egg Products
    "egg", "eggs", "albumin", "mayonnaise", "meringue", "lecithin",
    
    # Meat & Poultry
    "meat", "beef", "pork", "lamb", "chicken", "turkey", "duck", "fish", "seafood",
    "shrimp", "prawn", "crab", "lobster", "oyster", "clam", "mussel", "anchovy",
    "bacon", "ham", "sausage", "hotdog", "pepperoni", "salami", "prosciutto",
    "bone broth", "stock", "bouillon", "gelatin", "collagen",
    
    # Honey & Bee Products
    "honey", "propolis", "royal jelly", "beeswax", "bee pollen",
    
    # Other Animal Products
    "lard", "tallow", "lanolin", "carmine", "cochineal", "shellac", "isinglass",
    "pepsin", "rennet", "animal fat", "animal oil",
}

# Common vegan substitutes (safe to use)
VEGAN_SAFE_KEYWORDS = {
    "tofu", "tempeh", "seitan", "legume", "lentil", "chickpea", "bean", "pea",
    "nut", "seed", "grain", "vegetable", "fruit", "mushroom", "alga", "kelp",
    "tahini", "peanut butter", "coconut milk", "almond milk", "oat milk",
    "hemp milk", "rice milk", "soy milk", "plant-based", "vegan", "vegetable oil",
}


class USDADataFetcher:
    """Fetches nutritional data from USDA FoodData Central API."""
    
    BASE_URL = "https://fdc.nal.usda.gov/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize USDA data fetcher.
        
        Args:
            api_key: USDA API key (defaults to environment variable USDA_API_KEY)
        """
        self.api_key = api_key or os.getenv("USDA_API_KEY", "DEMO_KEY")
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def search_food(self, query: str, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        Search for foods in USDA FoodData Central.
        
        Args:
            query: Food name or ingredient to search
            page_size: Number of results to return
        
        Returns:
            List of food records with nutritional data
        """
        if query in self._cache:
            return self._cache[query]
        
        try:
            endpoint = f"{self.BASE_URL}/foods/search"
            params = {
                "query": query,
                "pageSize": page_size,
                "api_key": self.api_key,
            }
            
            response = requests.get(endpoint, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            foods = data.get("foods", [])
            
            self._cache[query] = foods
            logger.info(f"✅ USDA search succeeded for '{query}': {len(foods)} results")
            return foods
            
        except requests.RequestException as e:
            logger.error(f"❌ USDA API error for '{query}': {e}")
            return []
    
    def get_nutrient_values(
        self,
        food_name: str,
        nutrients: List[str] = None
    ) -> Dict[str, float]:
        """
        Extract specific nutrient values for a food.
        
        Args:
            food_name: Name of the food ingredient
            nutrients: List of nutrient names (e.g., ["Protein", "Carbohydrates"])
        
        Returns:
            Dictionary mapping nutrient names to values (per 100g)
        """
        if nutrients is None:
            nutrients = ["Protein", "Energy", "Carbohydrates", "Total lipid (fat)"]
        
        foods = self.search_food(food_name, page_size=1)
        if not foods:
            return {}
        
        food = foods[0]
        nutrients_data: Dict[str, float] = {}
        
        for nutrient in food.get("foodNutrients", []):
            nutrient_name = nutrient.get("nutrientName", "")
            if any(n.lower() in nutrient_name.lower() for n in nutrients):
                value = nutrient.get("value")
                if value is not None:
                    nutrients_data[nutrient_name] = float(value)
        
        return nutrients_data


class OpenFoodFactsFetcher:
    """Verifies if branded products are vegan using Open Food Facts API."""
    
    BASE_URL = "https://world.openfoodfacts.org/api/v2"
    
    def __init__(self):
        """Initialize Open Food Facts fetcher (no API key required)."""
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def search_product(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for a product in Open Food Facts.
        
        Args:
            product_name: Name of the branded product
        
        Returns:
            Product data including vegan status, or None if not found
        """
        if product_name in self._cache:
            return self._cache[product_name]
        
        try:
            endpoint = f"{self.BASE_URL}/search"
            params = {
                "q": product_name,
                "pageSize": 1,
            }
            
            response = requests.get(endpoint, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            products = data.get("products", [])
            
            if products:
                product = products[0]
                self._cache[product_name] = product
                logger.info(f"✅ Open Food Facts found: '{product_name}'")
                return product
            
            logger.info(f"⚠️ Open Food Facts: '{product_name}' not found")
            return None
            
        except requests.RequestException as e:
            logger.error(f"❌ Open Food Facts API error for '{product_name}': {e}")
            return None
    
    def is_product_vegan(self, product_name: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if a branded product is vegan.
        
        Args:
            product_name: Name of the product
        
        Returns:
            Tuple of (is_vegan: bool, reason: Optional[str])
        """
        product = self.search_product(product_name)
        if not product:
            return False, "Product not found in Open Food Facts"
        
        # Check official vegan label
        labels = product.get("labels", "") or ""
        if "vegan" in labels.lower():
            return True, f"Marked as vegan in Open Food Facts"
        
        # Check if product is explicitly marked as not vegan
        if "vegetarian" in labels.lower() and "vegan" not in labels.lower():
            return False, "Marked as vegetarian but not vegan"
        
        # Fallback: Check ingredients list for animal products
        ingredients = product.get("ingredients_text", "") or ""
        animal_found = [ing for ing in ANIMAL_DERIVED_INGREDIENTS 
                       if ing in ingredients.lower()]
        
        if animal_found:
            return False, f"Contains animal-derived ingredients: {', '.join(animal_found[:3])}"
        
        return True, "No animal-derived ingredients detected"


class VeganIngredientVerifier:
    """
    Verifies if an ingredient is vegan using PETA guidelines and
    external data sources.
    """
    
    def __init__(self, usda_fetcher: USDADataFetcher, off_fetcher: OpenFoodFactsFetcher):
        """Initialize with external API fetchers."""
        self.usda = usda_fetcher
        self.off = off_fetcher
        self._verification_cache: Dict[str, bool] = {}
    
    def is_ingredient_vegan(self, ingredient: str) -> Tuple[bool, List[str]]:
        """
        Verify if an ingredient is vegan.
        
        Args:
            ingredient: Ingredient name to verify
        
        Returns:
            Tuple of (is_vegan: bool, evidence: List[str])
        """
        ingredient_normalized = ingredient.lower().strip()
        
        if ingredient_normalized in self._verification_cache:
            is_vegan = self._verification_cache[ingredient_normalized]
            evidence = [
                f"Cached: '{ingredient}' is {'✓ vegan' if is_vegan else '✗ NOT vegan'}"
            ]
            return is_vegan, evidence
        
        evidence: List[str] = []
        
        # Hard-coded check against PETA animal-derived ingredients list
        for animal_ingredient in ANIMAL_DERIVED_INGREDIENTS:
            if animal_ingredient in ingredient_normalized:
                evidence.append(
                    f"❌ PETA animal-derived list: '{ingredient}' contains "
                    f"'{animal_ingredient}'"
                )
                self._verification_cache[ingredient_normalized] = False
                return False, evidence
        
        # Check against known vegan-safe keywords
        for vegan_keyword in VEGAN_SAFE_KEYWORDS:
            if vegan_keyword in ingredient_normalized:
                evidence.append(
                    f"✓ Recognized vegan ingredient: '{ingredient}' "
                    f"(keyword: {vegan_keyword})"
                )
                self._verification_cache[ingredient_normalized] = True
                return True, evidence
        
        # Fallback: Query USDA for unknown ingredients (try for plant-based markers)
        usda_results = self.usda.search_food(ingredient, page_size=1)
        if usda_results:
            food_category = usda_results[0].get("foodCategory", "").lower()
            if any(marker in food_category for marker in 
                   ["plant", "vegetable", "fruit", "grain", "legume", "nut", "seed"]):
                evidence.append(f"✓ USDA food category indicates plant-based: {food_category}")
                self._verification_cache[ingredient_normalized] = True
                return True, evidence
        
        # Try Open Food Facts for branded ingredients
        is_vegan_product, reason = self.off.is_product_vegan(ingredient)
        if is_vegan_product:
            evidence.append(f"✓ Open Food Facts verification: {reason}")
            self._verification_cache[ingredient_normalized] = True
            return True, evidence
        
        # Unknown ingredient: be conservative
        evidence.append(f"⚠️ Unknown ingredient: '{ingredient}' - manual review recommended")
        self._verification_cache[ingredient_normalized] = False
        return False, evidence
    
    def verify_recipe_ingredients(
        self,
        ingredients_list: List[str]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify all ingredients in a recipe.
        
        Args:
            ingredients_list: List of ingredient names
        
        Returns:
            Tuple of (all_vegan: bool, verification_report: Dict)
        """
        report = {
            "total_ingredients": len(ingredients_list),
            "verified_vegan": [],
            "animal_derived": [],
            "unknown": [],
            "confidence_score": 1.0,
        }
        
        for ingredient in ingredients_list:
            is_vegan, evidence = self.is_ingredient_vegan(ingredient)
            
            if is_vegan:
                report["verified_vegan"].append({
                    "ingredient": ingredient,
                    "evidence": evidence,
                })
            else:
                if any("animal-derived" in e for e in evidence):
                    report["animal_derived"].append({
                        "ingredient": ingredient,
                        "evidence": evidence,
                    })
                else:
                    report["unknown"].append({
                        "ingredient": ingredient,
                        "evidence": evidence,
                    })
        
        # Calculate confidence score
        verified_count = len(report["verified_vegan"])
        animal_count = len(report["animal_derived"])
        total = len(ingredients_list)
        
        if animal_count > 0:
            report["confidence_score"] = 0.0
        elif total > 0:
            report["confidence_score"] = verified_count / total
        
        all_vegan = animal_count == 0
        return all_vegan, report


# Singleton instances
_usda_fetcher: Optional[USDADataFetcher] = None
_off_fetcher: Optional[OpenFoodFactsFetcher] = None
_verifier: Optional[VeganIngredientVerifier] = None


def get_usda_fetcher() -> USDADataFetcher:
    """Get or create USDA fetcher singleton."""
    global _usda_fetcher
    if _usda_fetcher is None:
        _usda_fetcher = USDADataFetcher()
    return _usda_fetcher


def get_off_fetcher() -> OpenFoodFactsFetcher:
    """Get or create Open Food Facts fetcher singleton."""
    global _off_fetcher
    if _off_fetcher is None:
        _off_fetcher = OpenFoodFactsFetcher()
    return _off_fetcher


def get_verifier() -> VeganIngredientVerifier:
    """Get or create ingredient verifier singleton."""
    global _verifier
    if _verifier is None:
        _verifier = VeganIngredientVerifier(get_usda_fetcher(), get_off_fetcher())
    return _verifier
