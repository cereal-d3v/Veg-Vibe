import React, { useState } from 'react';
import { FiArrowRight } from 'react-icons/fi';
import RecipeCard from './RecipeCard';
import { recipeService } from '../services/api';
import '../styles/RecipeRecommender.css';

export const RecipeRecommender = ({ favorites, onAddFavorite }) => {
  const [ingredients, setIngredients] = useState('');
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const handleRecommend = async (e) => {
    e.preventDefault();
    if (!ingredients.trim()) {
      setError('Please enter some ingredients');
      return;
    }

    setLoading(true);
    setError(null);
    setSubmitted(true);

    try {
      const response = await recipeService.getRecommendations(ingredients, {
        numRecommendations: 6,
      });
      setRecommendations(response.data?.recommendations || []);
    } catch (err) {
      setError('Failed to get recommendations. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="recommender-section">
      <div className="recommender-hero">
        <h2>🍽️ What Can You Cook Today?</h2>
        <p>Tell us what ingredients you have, and we'll suggest delicious vegan recipes!</p>
      </div>

      <form onSubmit={handleRecommend} className="recommender-form">
        <div className="input-group">
          <input
            type="text"
            value={ingredients}
            onChange={(e) => setIngredients(e.target.value)}
            placeholder="e.g., tomato, basil, olive oil, garlic..."
            className="recommender-input"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="recommend-btn"
          >
            {loading ? 'Finding Recipes...' : 'Get Recommendations'}
            <FiArrowRight size={18} />
          </button>
        </div>
      </form>

      {error && <div className="error-message">{error}</div>}

      {submitted && recommendations.length === 0 && !loading && !error && (
        <div className="no-results">
          <p>🤔 No recipes found with those ingredients. Try different ones!</p>
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="recommendations-container">
          <h3>Recommended Recipes ({recommendations.length})</h3>
          <div className="recipes-grid">
            {recommendations.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                isFavorite={favorites.includes(recipe.id)}
                onFavorite={onAddFavorite}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RecipeRecommender;
