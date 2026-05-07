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


class ToolCall(BaseModel):
    tool: str
    arguments: dict


class AgenticQueryRequest(BaseModel):
    question: str
    max_results: int = 5


class ReliabilityReport(BaseModel):
    grounded: bool
    hallucinated_ingredients: List[str]
    checked_ingredient_mentions: List[str]


class VerificationStatus(BaseModel):
    """Result of recipe verification against external sources."""
    recipe_id: int
    recipe_title: str
    status: str  # verified_vegan, contains_animal_derived, contains_unknown, verification_failed
    confidence: float
    is_safe: bool


class VerificationStats(BaseModel):
    """Statistics about verification attempts."""
    total_verifications: int
    failed_verifications: int
    success_rate: str


class AgenticQueryResponse(BaseModel):
    answer: str
    citations: List[int]
    retrieved_count: int
    verified_vegan_count: int = 0
    tool_call: ToolCall
    reliability: ReliabilityReport
    verification_results: Optional[List[VerificationStatus]] = None
    verification_stats: Optional[VerificationStats] = None
