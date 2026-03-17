import React, { useState, useEffect } from 'react';
import { FiX } from 'react-icons/fi';
import RecipeCard from './RecipeCard';
import '../styles/Favorites.css';

export const Favorites = ({ favorites, onRemoveFavorite, allRecipes }) => {
  const [favoriteRecipes, setFavoriteRecipes] = useState([]);

  useEffect(() => {
    const filtered = allRecipes.filter((recipe) => favorites.includes(recipe.id));
    setFavoriteRecipes(filtered);
  }, [favorites, allRecipes]);

  if (!favorites || favorites.length === 0) {
    return (
      <div className="favorites-empty">
        <p>💜 No favorite recipes yet. Add some to get started!</p>
      </div>
    );
  }

  return (
    <div className="favorites-section">
      <div className="favorites-header">
        <h3>❤️ My Favorites ({favorites.length})</h3>
        <button
          className="close-btn"
          onClick={() => {}}
          title="Close"
        >
          <FiX size={20} />
        </button>
      </div>

      <div className="favorites-grid">
        {favoriteRecipes.map((recipe) => (
          <RecipeCard
            key={recipe.id}
            recipe={recipe}
            isFavorite={true}
            onFavorite={() => onRemoveFavorite(recipe.id)}
          />
        ))}
      </div>
    </div>
  );
};

export default Favorites;
