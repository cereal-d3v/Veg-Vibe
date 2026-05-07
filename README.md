# Veg-Vibe 🥬

Veg-Vibe is a **Personalized Vegan Food Recommender System** powered by agentic AI with real-world data verification.

## 🎯 Key Features

- **Semantic Recipe Search**: TF-IDF vectorizer finds recipes by ingredients & preferences
- **Two-Step Verification**: Every recipe is verified against external APIs before recommendation
- **Multi-Source Grounding**: 
  - USDA FoodData Central (nutritional authority)
  - Open Food Facts (real-world product verification)
  - PETA animal-derived ingredients list (hard-coded standards)
- **Agentic Tool Use**: LLM constrained by verified data sources, not model weights
- **Transparent Evidence**: Every recommendation includes confidence scores and verification evidence
- **Production-Ready**: Retry logic, caching, error handling, and monitoring

## 📚 Documentation

### For Understanding the Architecture
- **[RELIABLE_SOURCES.md](./RELIABLE_SOURCES.md)** - Complete technical guide to the verification pipeline
  - Two-Step Verification Pattern (Step A: Search, Step B: Verify)
  - External data sources and their roles
  - System prompt enforcement
  - Bootstrap dataset setup
  - Debugging guide

### For Turing Grant Context
- **[TURING_APPLICATION.md](./TURING_APPLICATION.md)** - How Veg-Vibe demonstrates "complex data source" + "reliable interface" requirements
  - Maps architecture to Turing requirements
  - Shows agentic behavior with constraints
  - Explains 3-class hallucination prevention
  - Competitive advantage analysis

### For Developers
- **[APP_README.md](./APP_README.md)** - Application-level documentation
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture overview

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ (for frontend)
- USDA API key (free): https://fdc.nal.usda.gov/

### Backend Setup

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your USDA_API_KEY

# 3. (Optional) Bootstrap verified dataset
python ../scripts/setup_verified_data.py

# 4. Run server
python -m uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

### Test the Verification Pipeline

```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "high protein quick vegan recipes",
    "max_results": 5
  }'
```

Response includes:
- ✅ Verified recipes only
- 📊 Confidence scores
- 🔍 Verification evidence
- 📈 System statistics

## 🏗️ Architecture Overview

### Two-Step Verification Pattern

```
Step A: Query
User Question → [search_recipes tool] → Semantic Search → Initial Results

Step B: Verify
Initial Results → [verify_recipe_ingredients tool] → External APIs → Safe Results
                     ├─ USDA FoodData Central
                     ├─ Open Food Facts
                     └─ PETA Ingredients List

Filter & Return: Only recipes with status="verified_vegan" & confidence>0.7
```

### Key Components

**Backend** (`backend/`):
- FastAPI server with agentic RAG
- Data fetcher services (USDA, Open Food Facts, verification)
- Two-step verification agent with tool use
- Pydantic models for structured responses

**Frontend** (`frontend/`):
- React + Vite
- Recipe card components
- Search and filter UI
- Favorites management

**Services** (`backend/app/services/`):
- `data_fetcher.py`: External API integrations
- `verification_agent.py`: Two-step verification logic

**Scripts** (`scripts/`):
- `setup_verified_data.py`: Bootstrap HuggingFace dataset with PETA filtering

## 🔬 How It Prevents Hallucination

### Class 1: Ingredient Hallucination
```python
# Without verification: LLM says "honey is vegan"
# With verification: PETA hard-coded list → ❌ Rejected
```

### Class 2: Nutritional Hallucination
```python
# Without verification: LLM claims "50g protein"
# With verification: USDA data says "15g" → Corrected
```

### Class 3: Product Status Hallucination
```python
# Without verification: LLM says "plant-based meat is vegan"
# With verification: Open Food Facts checks ingredients → Verified or rejected
```

## 📊 API Response Example

```json
{
  "answer": "🥬 **Veg Vibe Verified Results**...",
  "verified_vegan_count": 5,
  "verification_results": [
    {
      "recipe_id": 12,
      "recipe_title": "Tofu Scramble",
      "status": "verified_vegan",
      "confidence": 0.95,
      "is_safe": true
    },
    {
      "recipe_id": 45,
      "recipe_title": "Honey Cookies",
      "status": "contains_animal_derived",
      "confidence": 0.0,
      "is_safe": false
    }
  ],
  "verification_stats": {
    "total_verifications": 10,
    "success_rate": "100.0%"
  }
}
```

## 🛠️ Configuration

### Environment Variables (`.env`)

```bash
# USDA API (get free key at https://fdc.nal.usda.gov/)
USDA_API_KEY=your_key_here

# Open Food Facts (no key needed)
# Uses public API at https://world.openfoodfacts.org/api

# Verification settings
ENABLE_VERIFICATION=true
MIN_VERIFICATION_CONFIDENCE=0.7
STRICT_VERIFICATION_MODE=false

# Logging
LOG_LEVEL=INFO
```

## 📦 Dependencies

**Backend**:
- `fastapi` - Web framework
- `pandas` - Data processing
- `scikit-learn` - TF-IDF vectorization
- `requests` - HTTP client
- `datasets` - HuggingFace datasets
- `tenacity` - Retry logic

**Frontend**:
- `react` - UI framework
- `vite` - Build tool
- `axios` - HTTP client

## 🧪 Testing

### Unit Tests (TODO)
```bash
pytest backend/tests/
```

### Integration Tests
```bash
# Test verification pipeline
python backend/scripts/test_verification.py

# Test USDA API
python backend/scripts/test_usda.py

# Test Open Food Facts API
python backend/scripts/test_off.py
```

## 📈 Monitoring

### Check System Health
```bash
# Verification statistics
curl http://localhost:8000/api/verification-stats

# Data fetcher status
curl http://localhost:8000/api/health
```

### Debug Logs
```bash
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload
```

## 🚢 Deployment

### Docker Deployment (Recommended)

```bash
# Build images
docker-compose build

# Start services
docker-compose up

# Access at http://localhost/
```

### HuggingFace Spaces

Deploy frontend + backend to HuggingFace Spaces:
- See `DEPLOY_HUGGINGFACE.md` for instructions
- **OR** use `Dockerfile.spaces` for direct deployment

## 📖 API Documentation

- **OpenAPI (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Recipe Search**:
- `GET /api/recipes` - Search recipes
- `GET /api/recipes/{id}` - Get recipe details

**Agentic Query** (with verification):
- `POST /api/agent/query` - Query with Two-Step Verification

**Recommendations**:
- `POST /api/recommendations` - Get recommendations

**Health**:
- `GET /health` - Health check
- `GET /api-info` - API info

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **USDA FoodData Central** - Nutritional data authority
- **Open Food Facts** - Community-maintained product database
- **PETA** - Animal-derived ingredients reference
- **HuggingFace** - Recipe dataset (datahiveai/recipes-with-nutrition)

## 📮 Contact

For questions or feedback, open an issue on GitHub or contact the development team.

---

**Last Updated**: May 2026  
**Version**: 1.0.0  
**Status**: ✅ Production-Ready
