# 🥬 Veg Vibe - Web Application Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    VEGAN RECIPE RECOMMENDER                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐
│   React + Vite Frontend      │
│   ├─ App.jsx                 │
│   ├─ Components              │
│   │  ├─ RecipeCard.jsx       │
│   │  ├─ SearchAndFilter.jsx  │
│   │  ├─ RecipeRecommender    │
│   │  └─ Favorites.jsx        │
│   ├─ Services                │
│   │  └─ api.js              │
│   └─ Styles                  │
│      └─ CSS Modules          │
│                              │
│  http://localhost:5173       │
└──────────────┬───────────────┘
               │ (REST API)
               │
        ┌──────▼──────┐
        │   Axios     │
        │ API Client  │
        └──────┬──────┘
               │
               │
┌──────────────▼──────────────────┐
│   FastAPI Backend                │
│   ├─ app.main:app               │
│   ├─ Routers                     │
│   │  ├─ /api/recipes             │
│   │  ├─ /api/recommendations     │
│   │  └─ /health                  │
│   ├─ Models                      │
│   │  └─ recipe.py               │
│   └─ Utils                       │
│      └─ recommend.py            │
│                                  │
│  http://localhost:8000           │
│  📖 Docs: /docs                  │
└──────────────┬───────────────────┘
               │
       ┌───────▼────────┐
       │  ML Engine     │
       ├─ TF-IDF        │
       ├─ Cosine        │
       │  Similarity    │
       └───────┬────────┘
               │
       ┌───────▼─────────┐
       │ Recipe Data     │
       ├─ CSV file      │
       ├─ Ingredients   │
       ├─ Nutrition     │
       ├─ Difficulty    │
       └─ Dietary tags  │
```

## API Endpoints

### ROOT

- `GET /` - Welcome message
- `GET /health` - Health check

### RECIPES

- `GET /api/recipes/search?q=tomato&limit=10` - Search recipes
- `GET /api/recipes/{recipe_id}` - Get recipe details

### RECOMMENDATIONS

- `POST /api/recommendations` - Get recipe recommendations
- `GET /api/recommendations?ingredients=tomato&num_recommendations=5` - GET endpoint

## Data Model

```
Recipe {
  id: int
  title: string
  ingredients: string
  difficulty: string (Easy|Medium|Hard)
  prep_time: int (minutes)
  cook_time: int (minutes)
  servings: int
  calories: float
  protein: float (g)
  carbs: float (g)
  fat: float (g)
  dietary_tags: list[string]
  rating: float (0-5)
  reviews_count: int
}
```

## Features (Phase 1)

### ✅ Core Features

- [x] Ingredient-based recipe search using TF-IDF
- [x] Recipe search and filtering
- [x] Difficulty level filtering
- [x] Dietary restriction filtering
- [x] Nutritional information display
- [x] Favorites system (localStorage)
- [x] Responsive UI (desktop/mobile)
- [x] REST API with automatic documentation

### 🔄 Features (Phase 2 - Future)

- [ ] User authentication
- [ ] Database integration (SQLite/PostgreSQL)
- [ ] User ratings and reviews
- [ ] Recipe ratings persistence
- [ ] Chat interface for conversational recommendations
- [ ] Image uploads for recipes
- [ ] Meal planning
- [ ] Shopping list generator

## Technology Stack

### Frontend

- React 18 (UI library)
- Vite (build tool)
- Axios (HTTP client)
- CSS3 (styling)
- React Icons (icon library)

### Backend

- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- scikit-learn (ML)
- NLTK (text processing)
- Pandas (data manipulation)

### Infrastructure

- Docker (containerization)
- Docker Compose (orchestration)
- Vite (dev server)
- HuggingFace Spaces (deployment)

## Development Workflow

### Local Development

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Docker Development

```bash
docker-compose up
```

### Production Build

```bash
# Frontend
cd frontend && npm run build

# Backend (using Gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## File Structure

```
Veg-Vibe/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 (Main FastAPI app)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── recipe.py            (Data models)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── recipes.py           (Recipe endpoints)
│   │   │   └── recommendations.py   (Recommendation endpoints)
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── recommend.py         (ML logic)
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RecipeCard.jsx
│   │   │   ├── SearchAndFilter.jsx
│   │   │   ├── RecipeRecommender.jsx
│   │   │   └── Favorites.jsx
│   │   ├── services/
│   │   │   └── api.js               (API client)
│   │   ├── styles/
│   │   │   ├── index.css
│   │   │   ├── App.css
│   │   │   ├── RecipeCard.css
│   │   │   ├── SearchAndFilter.css
│   │   │   ├── RecipeRecommender.css
│   │   │   └── Favorites.css
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
│
├── HuggingFaceSpaces/
│   ├── app.py                       (Gradio app)
│   ├── requirements.txt
│   └── vegan_recipes.csv
│
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── setup.sh                         (Setup script)
├── start-dev.sh                     (Development startup)
├── APP_README.md                    (App documentation)
├── vegan_recipes.csv
├── .gitignore
└── README.md
```

## Deployment

### HuggingFace Spaces

- Push code to Space repository
- Automatically builds and deploys
- Uses `HuggingFaceSpaces/app.py` as entry point

### Docker

```bash
docker-compose up -d
```

## Next Steps

1. **Data Enhancement**
   - Enrich recipe data with more nutritional information
   - Add recipe images
   - Add difficulty ratings

2. **Features**
   - User authentication
   - Save favorites to database
   - User ratings and reviews
   - Meal planning
   - Shopping list generation

3. **Performance**
   - Cache recommendations
   - Paginate search results
   - Add search indexing
   - Implement monitoring

4. **Testing**
   - Add unit tests for API endpoints
   - Add integration tests
   - Add frontend component tests
   - E2E testing with Cypress

---

For more details, see [APP_README.md](./APP_README.md)
