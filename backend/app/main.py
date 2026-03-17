from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from app.routers import recipes, recommendations
from app.utils.recommend import RecipeRecommender

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
    description="Vegan Recipe Recommendation Engine",
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

# Initialize the recommender
print(f"Loading recipes from: {RECIPES_CSV}")
if os.path.exists(RECIPES_CSV):
    try:
        recommender = RecipeRecommender(RECIPES_CSV)
        recipes.set_recommender(recommender)
        recommendations.set_recommender(recommender)
        print("✅ Recommender initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing recommender: {e}")
else:
    print(f"⚠️ CSV file not found at {RECIPES_CSV}")

# Include routers
app.include_router(recipes.router)
app.include_router(recommendations.router)

# Mount static files (React app)
frontend_dist = os.path.join(
    Path(__file__).parent.parent.parent, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
    print(f"✅ Mounted frontend from {frontend_dist}")


git clone https://huggingface.co/spaces/YOUR_USERNAME/veg-vibe
cd veg-vibe@app.get("/api-info", tags=["root"])
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
