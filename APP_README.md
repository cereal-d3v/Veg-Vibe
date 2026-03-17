# 🥬 Veg Vibe - Vegan Recipe Recommender

A modern web application that recommends vegan recipes based on ingredients you have. Built with React + Vite frontend and FastAPI backend.

## 🌟 Features

- 🔍 **Smart Recipe Search** - Search by ingredients or recipe names
- 🎯 **Personalized Recommendations** - Get recipe suggestions based on available ingredients using TF-IDF vectorization
- 🏷️ **Advanced Filtering** - Filter by:
  - Difficulty level (Easy, Medium, Hard)
  - Dietary restrictions (Gluten-free, Nut-free, Soy-free, Keto-friendly)
  - Nutritional information (Calories, Protein, Carbs, Fat)
- ❤️ **Favorites System** - Save your favorite recipes (stored locally)
- ⭐ **Community Ratings** - View recipe ratings and reviews
- 📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
- 🌐 **REST API** - Complete API documentation at `/docs`

## 🏗️ Project Structure

```
Veg-Vibe/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── main.py         # Main FastAPI application
│   │   ├── models/         # Pydantic data models
│   │   ├── routers/        # API endpoints
│   │   └── utils/          # Recommendation engine
│   └── requirements.txt
│
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API service client
│   │   ├── styles/         # CSS stylesheets
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── HuggingFaceSpaces/      # Original Gradio app
├── vegan_recipes.csv       # Recipe dataset
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory**

   ```bash
   cd backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

- 📖 API Docs: `http://localhost:8000/docs`
- 🔄 ReDoc: `http://localhost:8000/redoc`

### Frontend Setup

1. **Navigate to frontend directory**

   ```bash
   cd frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Create environment file**

   ```bash
   cp .env.example .env
   ```

4. **Run development server**
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:5173`

## 📚 API Endpoints

### Recipes

- `GET /api/recipes/search?q=tomato&limit=10` - Search recipes
- `GET /api/recipes/{recipe_id}` - Get recipe details

### Recommendations

- `POST /api/recommendations` - Get recipe recommendations
  ```json
  {
    "ingredients": "tomato, basil, olive oil",
    "num_recommendations": 5,
    "difficulty_filter": "Easy",
    "dietary_filters": ["gluten-free"]
  }
  ```

### Health

- `GET /health` - API health check

## 🛠️ Development

### Adding New Features

1. **Backend**: Add new routers in `backend/app/routers/`
2. **Frontend**: Add new components in `frontend/src/components/`
3. **Models**: Update data models in `backend/app/models/`

### Building for Production

**Frontend:**

```bash
cd frontend
npm run build
```

**Backend:**
Use a production ASGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 🌍 Deployment

### HuggingFace Spaces

1. **Create new Space** on HuggingFace
2. **Push to Space repository**
3. **Add `app.py` from `HuggingFaceSpaces/` directory**
4. **Configure environment variables**

### Vercel (Frontend) + Railway/Heroku (Backend)

- Frontend: Deploy to Vercel with `npm run build`
- Backend: Deploy to Heroku/Railway with Procfile

## 📊 Data

- Recipe data: `vegan_recipes.csv`
- Includes: Title, Ingredients, Difficulty, Nutrition info, Dietary tags

### Data Format

```csv
title,ingredients,difficulty,prep_time,cook_time,servings,calories,protein,carbs,fat,dietary_tags,rating,reviews_count
```

## 🤝 Contributing

Feel free to open issues and pull requests!

## 📝 License

See LICENSE file for details.

## 🙏 Acknowledgments

- Recipe dataset from various vegan recipe sources
- Built with [React](https://react.dev) + [Vite](https://vitejs.dev) + [FastAPI](https://fastapi.tiangolo.com)

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

Made with 💚 for vegans everywhere! 🌱
