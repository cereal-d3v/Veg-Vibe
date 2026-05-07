from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from app.routers import recipes, recommendations
from app.models.recipe import AgenticQueryRequest, AgenticQueryResponse
from app.utils.recommend import RecipeRecommender
from app.utils.agentic_rag import AgenticRecipeAssistant
from app.services.data_fetcher import (
    get_usda_fetcher,
    get_off_fetcher,
    get_verifier,
)

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the CSV path (adjust as needed)
RECIPES_CSV = os.path.join(
    Path(__file__).parent.parent.parent,
    "vegan_recipes.csv"
)

# Check if the CSV exists in HuggingFaceSpaces folder too
if not os.path.exists(RECIPES_CSV):
    RECIPES_CSV = os.path.join(
        Path(__file__).parent.parent.parent,
        "HuggingFaceSpaces",
        "vegan_recipes.csv"
    )

# Initialize FastAPI app
app = FastAPI(
    title="🥬 Veg Vibe API",
    description="Vegan Recipe Recommendation Engine with Verified Data Sources",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data fetching services (USDA, Open Food Facts, verification)
logger.info("🔧 Initializing data fetching services...")
try:
    usda_fetcher = get_usda_fetcher()
    logger.info("   ✓ USDA FoodData Central fetcher ready")
except Exception as e:
    logger.warning(f"   ⚠️  USDA fetcher initialization failed: {e}")

try:
    off_fetcher = get_off_fetcher()
    logger.info("   ✓ Open Food Facts fetcher ready")
except Exception as e:
    logger.warning(f"   ⚠️  Open Food Facts fetcher initialization failed: {e}")

try:
    verifier = get_verifier()
    logger.info("   ✓ Ingredient verification agent ready")
except Exception as e:
    logger.warning(f"   ⚠️  Verifier initialization failed: {e}")

# Initialize the recommender
print(f"Loading recipes from: {RECIPES_CSV}")
if os.path.exists(RECIPES_CSV):
    try:
        recommender = RecipeRecommender(RECIPES_CSV)
        agentic_assistant = AgenticRecipeAssistant(recommender)
        recipes.set_recommender(recommender)
        recommendations.set_recommender(recommender)
        print("✅ Recommender initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing recommender: {e}")
else:
    print(f"⚠️ CSV file not found at {RECIPES_CSV}")
    agentic_assistant = None

# Include routers
app.include_router(recipes.router)
app.include_router(recommendations.router)

# Mount static files (React app)
frontend_dist = os.path.join(
    Path(__file__).parent.parent.parent, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
    print(f"✅ Mounted frontend from {frontend_dist}")


@app.get("/api-info", tags=["root"])
async def read_root():
    """Root endpoint."""
    return {
        "message": "🥬 Welcome to Veg Vibe API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/agent/query", response_model=AgenticQueryResponse, tags=["agentic"])
async def agentic_query(request: AgenticQueryRequest):
    """
    Tool-driven grounded query endpoint for Agentic RAG behavior.
    
    This endpoint implements the Two-Step Verification Pattern:
    - Step A: Search recipes using semantic similarity
    - Step B: Verify ingredients against USDA, Open Food Facts, and PETA guidelines
    
    Returns only recipes that pass external verification.
    """
    if not agentic_assistant:
        return AgenticQueryResponse(
            answer="Recommender is not available.",
            citations=[],
            retrieved_count=0,
            verified_vegan_count=0,
            tool_call={"tool": "search_recipes", "arguments": {}},
            reliability={
                "grounded": True,
                "hallucinated_ingredients": [],
                "checked_ingredient_mentions": [],
            },
        )

    result = agentic_assistant.answer(
        question=request.question,
        max_results=request.max_results,
    )
    
    return AgenticQueryResponse(
        answer=result["answer"],
        citations=result["citations"],
        retrieved_count=result["retrieved_count"],
        verified_vegan_count=result.get("verified_vegan_count", 0),
        tool_call=result["tool_call"],
        reliability=result["reliability"],
        verification_results=result.get("verification_results"),
        verification_stats=result.get("verification_stats"),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
