from fastapi import APIRouter, Query
from typing import Optional, List
from ..models.recipe import Recipe, RecommendationRequest, RecommendationResponse
from ..utils.recommend import RecipeRecommender

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

# This will be initialized in main app
recommender: Optional[RecipeRecommender] = None


def set_recommender(rec: RecipeRecommender):
    """Set the recommender instance."""
    global recommender
    recommender = rec


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get recipe recommendations based on ingredients."""
    if not recommender:
        return RecommendationResponse(recommendations=[], similarity_scores=[])

    results, scores = recommender.get_recommendations(
        ingredients=request.ingredients,
        num_recommendations=request.num_recommendations,
        difficulty_filter=request.difficulty_filter,
        dietary_filters=request.dietary_filters
    )

    recipes = []
    for idx, (_, row) in enumerate(results.iterrows()):
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

    return RecommendationResponse(
        recommendations=recipes,
        similarity_scores=scores
    )


@router.get("", response_model=RecommendationResponse)
async def get_recommendations_get(
    ingredients: str = Query(..., description="Available ingredients"),
    num_recommendations: int = Query(5, ge=1, le=20),
    difficulty: Optional[str] = Query(None),
    dietary: Optional[List[str]] = Query(None)
):
    """Get recipe recommendations (GET endpoint)."""
    if not recommender:
        return RecommendationResponse(recommendations=[], similarity_scores=[])

    results, scores = recommender.get_recommendations(
        ingredients=ingredients,
        num_recommendations=num_recommendations,
        difficulty_filter=difficulty,
        dietary_filters=dietary
    )

    recipes = []
    for _, row in results.iterrows():
        recipe = Recipe(
            id=int(row.name),
            title=row.get('title', ''),
            ingredients=row.get('ingredients', ''),
            difficulty=row.get('difficulty', 'Medium'),
        )
        recipes.append(recipe)

    return RecommendationResponse(
        recommendations=recipes,
        similarity_scores=scores
    )
