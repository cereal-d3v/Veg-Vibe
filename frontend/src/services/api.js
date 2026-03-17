import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const recipeService = {
  // Search recipes
  searchRecipes: (query, limit = 10) =>
    apiClient.get('/api/recipes/search', { params: { q: query, limit } }),

  // Get recipe by ID
  getRecipe: (id) =>
    apiClient.get(`/api/recipes/${id}`),

  // Get recommendations
  getRecommendations: (ingredients, options = {}) =>
    apiClient.post('/api/recommendations', {
      ingredients,
      num_recommendations: options.numRecommendations || 5,
      difficulty_filter: options.difficulty,
      dietary_filters: options.dietary,
    }),

  // Get recommendations with GET (alternative)
  getRecommendationsGet: (ingredients, options = {}) =>
    apiClient.get('/api/recommendations', {
      params: {
        ingredients,
        num_recommendations: options.numRecommendations || 5,
        difficulty: options.difficulty,
        dietary: options.dietary,
      },
    }),

  // Health check
  healthCheck: () =>
    apiClient.get('/health'),
};

export default apiClient;
