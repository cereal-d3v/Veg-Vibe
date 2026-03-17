import React from 'react';
import { FiHeart, FiMessageCircle, FiClock } from 'react-icons/fi';
import '../styles/RecipeCard.css';

export const RecipeCard = ({ recipe, onFavorite, isFavorite }) => {
  return (
    <div className="recipe-card">
      <div className="recipe-header">
        <h3>{recipe.title}</h3>
        <button
          className={`favorite-btn ${isFavorite ? 'favorited' : ''}`}
          onClick={() => onFavorite && onFavorite(recipe.id)}
          title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          <FiHeart fill={isFavorite ? 'currentColor' : 'none'} />
        </button>
      </div>

      <div className="recipe-meta">
        {recipe.prep_time && (
          <span className="meta-item">
            <FiClock size={16} /> Prep: {recipe.prep_time}m
          </span>
        )}
        {recipe.cook_time && (
          <span className="meta-item">
            <FiClock size={16} /> Cook: {recipe.cook_time}m
          </span>
        )}
        {recipe.difficulty && (
          <span className={`difficulty difficulty-${recipe.difficulty.toLowerCase()}`}>
            {recipe.difficulty}
          </span>
        )}
      </div>

      <div className="recipe-nutrition">
        {recipe.calories && <p>🔥 {recipe.calories} kcal</p>}
        {recipe.protein && <p>💪 {recipe.protein}g protein</p>}
      </div>

      <div className="recipe-ingredients">
        <strong>Ingredients:</strong>
        <p className="truncated">{recipe.ingredients}</p>
      </div>

      <div className="recipe-rating">
        <span className="rating">⭐ {recipe.rating.toFixed(1)}</span>
        <span className="reviews">
          <FiMessageCircle size={14} /> {recipe.reviews_count} reviews
        </span>
      </div>
    </div>
  );
};

export default RecipeCard;
