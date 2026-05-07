from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
from pathlib import Path
from app.routers import recipes, recommendations
from app.utils.recommend import RecipeRecommender
from app.ingestion import get_document_processor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vegvibe.main")

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
    description="Vegan Recipe Recommendation Engine with High-Fidelity Document Ingestion",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the recommender
logger.info(f"Loading recipes from: {RECIPES_CSV}")
if os.path.exists(RECIPES_CSV):
    try:
        recommender = RecipeRecommender(RECIPES_CSV)
        recipes.set_recommender(recommender)
        recommendations.set_recommender(recommender)
        logger.info("✅ Recommender initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing recommender: {e}")
else:
    logger.warning(f"⚠️ CSV file not found at {RECIPES_CSV}")

# Initialize document processor for high-fidelity PDF parsing
try:
    doc_processor = get_document_processor(chunk_size=1024, chunk_overlap=128)
    logger.info("✅ Document processor initialized (Docling)")
except Exception as e:
    logger.warning(f"⚠️ Document processor initialization failed: {e}")
    doc_processor = None

# Include routers
app.include_router(recipes.router)
app.include_router(recommendations.router)

# Mount static files (React app)
frontend_dist = os.path.join(
    Path(__file__).parent.parent.parent, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
    logger.info(f"✅ Mounted frontend from {frontend_dist}")


@app.get("/api-info", tags=["root"])
async def read_root():
    """Root endpoint."""
    return {
        "message": "🥬 Welcome to Veg Vibe API v2.0",
        "docs": "/docs",
        "version": "2.0.0",
        "features": [
            "Recipe recommendation with verification",
            "High-fidelity PDF document parsing (Docling)",
            "Table-aware chunking",
            "Source attribution",
        ]
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "recommender": "ready" if recommender else "unavailable",
            "doc_processor": "ready" if doc_processor else "unavailable",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
