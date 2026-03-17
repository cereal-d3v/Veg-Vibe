import React, { useState } from 'react';
import { FiSearch, FiFilter } from 'react-icons/fi';
import '../styles/SearchAndFilter.css';

export const SearchBar = ({ onSearch, onFilter, isLoading }) => {
  const [searchInput, setSearchInput] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    difficulty: '',
    dietary: [],
  });

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      onSearch && onSearch(searchInput);
    }
  };

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters };
    if (key === 'dietary') {
      if (newFilters.dietary.includes(value)) {
        newFilters.dietary = newFilters.dietary.filter((item) => item !== value);
      } else {
        newFilters.dietary.push(value);
      }
    } else {
      newFilters[key] = value;
    }
    setFilters(newFilters);
    onFilter && onFilter(newFilters);
  };

  return (
    <div className="search-filter-container">
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="🥕 Enter ingredients or search recipes..."
            className="search-input"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="search-btn"
            title="Search"
          >
            <FiSearch size={20} />
          </button>
        </div>
      </form>

      <button
        className="filter-toggle"
        onClick={() => setShowFilters(!showFilters)}
        title="Toggle filters"
      >
        <FiFilter size={20} />
        Filters
      </button>

      {showFilters && (
        <div className="filters-panel">
          <div className="filter-group">
            <label>Difficulty:</label>
            <select
              value={filters.difficulty}
              onChange={(e) => handleFilterChange('difficulty', e.target.value)}
              className="filter-select"
            >
              <option value="">All Levels</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </div>

          <div className="filter-group">
            <label>Dietary Tags:</label>
            <div className="filter-checkboxes">
              {['gluten-free', 'nut-free', 'soy-free', 'keto-friendly'].map(
                (tag) => (
                  <label key={tag} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={filters.dietary.includes(tag)}
                      onChange={() => handleFilterChange('dietary', tag)}
                    />
                    {tag}
                  </label>
                )
              )}
            </div>
          </div>

          <button
            className="clear-filters-btn"
            onClick={() => {
              setFilters({ difficulty: '', dietary: [] });
              onFilter && onFilter({ difficulty: '', dietary: [] });
            }}
          >
            Clear Filters
          </button>
        </div>
      )}
    </div>
  );
};

export default SearchBar;
