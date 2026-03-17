from fastapi import APIRouter, Query
from typing import Optional, List
from ..models.recipe import Recipe, RecipeResponse
from ..utils.recommend import RecipeRecommender

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# This will be initialized in main app
recommender: Optional[RecipeRecommender] = None


def set_recommender(rec: RecipeRecommender):
    """Set the recommender instance."""
    global recommender
    recommender = rec


@router.get("/search", response_model=RecipeResponse)
async def search_recipes(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100)
):
    """Search recipes by title or ingredients."""
    if not recommender:
        return RecipeResponse(recipes=[], total_count=0)

    results = recommender.search_recipes(q, limit=limit)
    recipes = []
    for _, row in results.iterrows():
        recipe = Recipe(
            id=int(row.name),
            title=row.get('title', ''),
            ingredients=row.get('ingredients', ''),
            difficulty=row.get('difficulty', 'Medium'),
            prep_time=int(row.get('prep_time', 0)) if row.get(
                'prep_time') else None,
            cook_time=int(row.get('cook_time', 0)) if row.get(
                'cook_time') else None,
            servings=int(row.get('servings', 0)) if row.get(
                'servings') else None,
            calories=float(row.get('calories', 0)) if row.get(
                'calories') else None,
            protein=float(row.get('protein', 0)) if row.get(
                'protein') else None,
            carbs=float(row.get('carbs', 0)) if row.get('carbs') else None,
            fat=float(row.get('fat', 0)) if row.get('fat') else None,
        )
        recipes.append(recipe)

    return RecipeResponse(recipes=recipes, total_count=len(recipes))


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    """Get recipe details by ID."""
    if not recommender:
        return Recipe(id=0, title="Not found", ingredients="")

    recipe_dict = recommender.get_recipe_by_id(recipe_id)
    if not recipe_dict:
        return Recipe(id=0, title="Not found", ingredients="")

    return Recipe(
        id=recipe_id,
        title=recipe_dict.get('title', ''),
        ingredients=recipe_dict.get('ingredients', ''),
        difficulty=recipe_dict.get('difficulty', 'Medium'),
    )
