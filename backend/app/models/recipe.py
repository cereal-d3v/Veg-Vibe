from pydantic import BaseModel
from typing import Optional, List


class Recipe(BaseModel):
    id: int
    title: str
    ingredients: str
    difficulty: Optional[str] = "Medium"
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    servings: Optional[int] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    dietary_tags: Optional[List[str]] = []
    rating: float = 0.0
    reviews_count: int = 0


class RecipeResponse(BaseModel):
    recipes: List[Recipe]
    total_count: int


class RecommendationRequest(BaseModel):
    ingredients: str
    num_recommendations: int = 3
    difficulty_filter: Optional[str] = None
    dietary_filters: Optional[List[str]] = None


class RecommendationResponse(BaseModel):
    recommendations: List[Recipe]
    similarity_scores: List[float]


class FavoriteRequest(BaseModel):
    recipe_id: int
    user_id: str


class RatingRequest(BaseModel):
    recipe_id: int
    user_id: str
    rating: float
    review: Optional[str] = None
