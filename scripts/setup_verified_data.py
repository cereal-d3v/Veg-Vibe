#!/usr/bin/env python3
"""
Bootstrap script to set up verified vegan recipe dataset.

This script:
1. Downloads the datahiveai/recipes-with-nutrition dataset from Hugging Face
2. Filters for strictly vegan recipes using PETA-aligned ingredient logic
3. Exports to CSV for use in the Veg Vibe backend

Usage:
    python scripts/setup_verified_data.py [--output-path <path>]

Example:
    python scripts/setup_verified_data.py --output-path backend/vegan_recipes_verified.csv
"""

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.data_fetcher import (
    ANIMAL_DERIVED_INGREDIENTS,
    get_verifier,
    VeganIngredientVerifier,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def install_datasets():
    """Ensure datasets library is available."""
    try:
        import datasets
        logger.info(f"✓ datasets library version {datasets.__version__}")
    except ImportError:
        logger.warning(
            "⚠️  'datasets' library not found. Installing from PyPI...\n"
            "   Run: pip install datasets\n"
            "   Or: pip install -r backend/requirements.txt"
        )
        raise


def load_recipe_dataset(dataset_name: str = "datahiveai/recipes-with-nutrition"):
    """
    Load recipe dataset from Hugging Face.
    
    Args:
        dataset_name: Name of the dataset to load
    
    Returns:
        Dataset object with recipe data
    """
    try:
        from datasets import load_dataset
        
        logger.info(f"📥 Loading dataset '{dataset_name}' from Hugging Face...")
        dataset = load_dataset(dataset_name)
        
        logger.info(
            f"✓ Dataset loaded successfully\n"
            f"   Total recipes: {len(dataset.get('train', dataset))}"
        )
        return dataset
        
    except Exception as e:
        logger.error(f"❌ Failed to load dataset: {e}")
        raise


def normalize_ingredients(ingredients_raw: Optional[str]) -> List[str]:
    """
    Normalize ingredient list from dataset format.
    
    Args:
        ingredients_raw: Raw ingredient string or JSON from dataset
    
    Returns:
        List of normalized ingredient names
    """
    if not ingredients_raw:
        return []
    
    try:
        # Try parsing as JSON list
        if isinstance(ingredients_raw, str):
            if ingredients_raw.startswith("["):
                ingredients = json.loads(ingredients_raw)
                return [str(ing).lower().strip() for ing in ingredients]
            else:
                # Try comma-separated
                return [ing.lower().strip() for ing in ingredients_raw.split(",")]
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fallback: treat as single ingredient
    return [str(ingredients_raw).lower().strip()]


def is_recipe_vegan(
    ingredients: List[str],
    verifier: VeganIngredientVerifier,
) -> tuple[bool, str]:
    """
    Check if a recipe is vegan based on ingredients.
    
    Args:
        ingredients: List of ingredient names
        verifier: VeganIngredientVerifier instance
    
    Returns:
        Tuple of (is_vegan: bool, reason: str)
    """
    if not ingredients:
        return False, "No ingredients found"
    
    # Quick check for obvious animal products
    for ingredient in ingredients:
        ing_lower = ingredient.lower()
        for animal_ingredient in ANIMAL_DERIVED_INGREDIENTS:
            if animal_ingredient in ing_lower:
                return False, f"Contains {animal_ingredient}"
    
    # Use verifier for unknown ingredients
    all_vegan, report = verifier.verify_recipe_ingredients(ingredients)
    
    if report["confidence_score"] >= 0.7:
        return all_vegan, f"Confidence: {report['confidence_score']:.0%}"
    else:
        unknown_count = len(report["unknown"])
        return False, f"Too many unverified ingredients ({unknown_count})"


def filter_vegan_recipes(
    dataset,
    output_csv: str,
    verifier: VeganIngredientVerifier,
    max_recipes: Optional[int] = None,
) -> Dict[str, int]:
    """
    Filter dataset for vegan recipes and export to CSV.
    
    Args:
        dataset: Hugging Face dataset object
        output_csv: Path to output CSV file
        verifier: VeganIngredientVerifier instance
        max_recipes: Maximum recipes to process (for testing)
    
    Returns:
        Statistics dict
    """
    stats = {
        "total_recipes": 0,
        "vegan_recipes": 0,
        "non_vegan_recipes": 0,
        "unverifiable_recipes": 0,
        "exported_recipes": 0,
    }
    
    # Use train split or first available split
    split_data = dataset.get("train", dataset)
    if isinstance(split_data, dict):
        split_data = list(split_data.values())[0]
    
    logger.info(f"📊 Processing recipes...")
    
    vegan_recipes: List[Dict] = []
    
    for idx, record in enumerate(split_data):
        stats["total_recipes"] += 1
        
        # Limit processing for testing
        if max_recipes and idx >= max_recipes:
            logger.info(f"   (reached max_recipes limit of {max_recipes})")
            break
        
        # Log progress every 100 recipes
        if (idx + 1) % 100 == 0:
            logger.info(f"   Processed {idx + 1} recipes...")
        
        # Extract recipe data
        title = record.get("title") or record.get("name", "Unknown")
        ingredients_raw = record.get("ingredients") or record.get("ingredient_names", "")
        
        # Parse ingredients
        ingredients = normalize_ingredients(ingredients_raw)
        
        # Verify if vegan
        is_vegan, reason = is_recipe_vegan(ingredients, verifier)
        
        if is_vegan:
            stats["vegan_recipes"] += 1
            
            # Extract nutritional info
            vegan_recipes.append({
                "title": title,
                "ingredients": json.dumps(ingredients),
                "prep_time": record.get("prep_time", ""),
                "cook_time": record.get("cook_time", ""),
                "servings": record.get("servings", ""),
                "calories": record.get("calories", ""),
                "protein": record.get("protein", ""),
                "carbs": record.get("carbs", ""),
                "fat": record.get("fat", ""),
                "difficulty": record.get("difficulty", "Medium"),
                "dietary_tags": "vegan",
                "source": "HuggingFace/recipes-with-nutrition",
            })
        else:
            if "unknown" in reason.lower():
                stats["unverifiable_recipes"] += 1
            else:
                stats["non_vegan_recipes"] += 1
    
    # Export to CSV
    logger.info(f"\n💾 Exporting {len(vegan_recipes)} vegan recipes to {output_csv}...")
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        if vegan_recipes:
            fieldnames = vegan_recipes[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vegan_recipes)
            stats["exported_recipes"] = len(vegan_recipes)
            logger.info(f"✓ Exported {len(vegan_recipes)} recipes")
        else:
            logger.warning("⚠️  No vegan recipes found to export")
    
    return stats


def print_statistics(stats: Dict[str, int]):
    """Print formatted statistics."""
    logger.info("\n" + "=" * 70)
    logger.info("📈 DATASET PROCESSING STATISTICS")
    logger.info("=" * 70)
    logger.info(f"Total recipes processed:        {stats['total_recipes']}")
    logger.info(f"Verified vegan recipes:         {stats['vegan_recipes']}")
    logger.info(f"Non-vegan recipes rejected:     {stats['non_vegan_recipes']}")
    logger.info(f"Unverifiable recipes:           {stats['unverifiable_recipes']}")
    logger.info(f"Recipes exported to CSV:        {stats['exported_recipes']}")
    
    if stats["total_recipes"] > 0:
        vegan_pct = (stats["vegan_recipes"] / stats["total_recipes"]) * 100
        logger.info(f"Vegan percentage:               {vegan_pct:.1f}%")
    logger.info("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap Veg Vibe with verified vegan recipe dataset"
    )
    parser.add_argument(
        "--output-path",
        default="backend/vegan_recipes_verified.csv",
        help="Path to output CSV file",
    )
    parser.add_argument(
        "--dataset",
        default="datahiveai/recipes-with-nutrition",
        help="Hugging Face dataset identifier",
    )
    parser.add_argument(
        "--max-recipes",
        type=int,
        default=None,
        help="Maximum recipes to process (for testing)",
    )
    
    args = parser.parse_args()
    
    try:
        # Check dependencies
        logger.info("🔍 Checking dependencies...")
        install_datasets()
        
        # Load dataset
        logger.info(f"\n📥 Loading dataset...")
        dataset = load_recipe_dataset(args.dataset)
        
        # Initialize verifier
        logger.info(f"\n🔧 Initializing verifier...")
        verifier = get_verifier()
        
        # Filter and export
        logger.info(f"\n⚙️  Filtering for vegan recipes...")
        stats = filter_vegan_recipes(
            dataset=dataset,
            output_csv=args.output_path,
            verifier=verifier,
            max_recipes=args.max_recipes,
        )
        
        # Print results
        print_statistics(stats)
        
        logger.info(f"✅ Setup complete!")
        logger.info(f"   Output file: {args.output_path}")
        logger.info(f"   Ready to use in backend: cp {args.output_path} backend/vegan_recipes.csv")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Error during setup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
