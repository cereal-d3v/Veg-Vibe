import React, { useState, useEffect } from 'react';
import { FiMenu, FiX } from 'react-icons/fi';
import RecipeRecommender from './components/RecipeRecommender';
import SearchBar from './components/SearchAndFilter';
import Favorites from './components/Favorites';
import { recipeService } from './services/api';
import './styles/App.css';

function App() {
  const [favorites, setFavorites] = useState([]);
  const [showFavorites, setShowFavorites] = useState(false);
  const [allRecipes, setAllRecipes] = useState([]);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Load favorites from localStorage on mount
  useEffect(() => {
    const savedFavorites = localStorage.getItem('vegvibe_favorites');
    if (savedFavorites) {
      setFavorites(JSON.parse(savedFavorites));
    }

    // Check API health
    recipeService
      .healthCheck()
      .then(() => console.log('✅ API is healthy'))
      .catch((err) => console.warn('⚠️ API connection issue:', err));
  }, []);

  // Save favorites to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('vegvibe_favorites', JSON.stringify(favorites));
  }, [favorites]);

  const handleAddFavorite = (recipeId) => {
    if (favorites.includes(recipeId)) {
      setFavorites(favorites.filter((id) => id !== recipeId));
    } else {
      setFavorites([...favorites, recipeId]);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <h1>🥬 Veg Vibe</h1>
            <p className="tagline">Your Vegan Recipe Guide</p>
          </div>

          {/* Desktop Navigation */}
          <nav className="nav-desktop">
            <button
              className={`nav-link ${showFavorites ? 'active' : ''}`}
              onClick={() => setShowFavorites(!showFavorites)}
            >
              ❤️ Favorites ({favorites.length})
            </button>
          </nav>

          {/* Mobile Menu Toggle */}
          <button
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <FiX size={24} /> : <FiMenu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="nav-mobile">
            <button
              className={`nav-link ${showFavorites ? 'active' : ''}`}
              onClick={() => {
                setShowFavorites(!showFavorites);
                setMobileMenuOpen(false);
              }}
            >
              ❤️ Favorites ({favorites.length})
            </button>
          </nav>
        )}
      </header>

      {/* Main Content */}
      <main className="app-main">
        {/* Favorites Sidebar */}
        {showFavorites && (
          <aside className="favorites-sidebar">
            <Favorites
              favorites={favorites}
              onRemoveFavorite={handleAddFavorite}
              allRecipes={allRecipes}
            />
          </aside>
        )}

        {/* Main Content Area */}
        <div className={`main-content ${showFavorites ? 'with-sidebar' : ''}`}>
          <section className="hero-section">
            <div className="hero-content">
              <h2>Discover Your Next Favorite Vegan Recipe</h2>
              <p>
                Enter your available ingredients and get personalized recipe recommendations
              </p>
            </div>
          </section>

          {/* Search and Filter */}
          <section className="search-section">
            <SearchBar isLoading={false} />
          </section>

          {/* Recipe Recommender */}
          <section className="recommender-section">
            <RecipeRecommender
              favorites={favorites}
              onAddFavorite={handleAddFavorite}
            />
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p>🌱 Made with 💚 for vegans everywhere</p>
          <p className="footer-links">
            <a href="https://github.com/cereal-d3v/Veg-Vibe" target="_blank" rel="noopener noreferrer">
              GitHub
            </a>
            {' • '}
            <a href="#about">About</a>
            {' • '}
            <a href="#contact">Contact</a>
          </p>
          <p className="version">v1.0.0</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
