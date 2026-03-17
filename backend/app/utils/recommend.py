import pandas as pd
import re
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from typing import List, Tuple, Optional

# Download stopwords on module load
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))


def clean_text(text: str) -> str:
    """Clean and normalize text for TF-IDF vectorization."""
    text = re.sub(r'\d+', '', str(text))
    text = re.sub(r'[^\w\s]', '', text).lower()
    return ' '.join(word for word in text.split() if word not in STOP_WORDS)


class RecipeRecommender:
    def __init__(self, csv_path: str):
        """Initialize the recommender with recipe data."""
        self.df = pd.read_csv(csv_path)
        self.df.fillna('', inplace=True)

        # Prepare data
        self.df['cleaned'] = self.df['ingredients'].apply(clean_text)

        # Build TF-IDF vectorizer
        self.tfidf = TfidfVectorizer(max_features=1000, stop_words='english')
        self.tfidf_matrix = self.tfidf.fit_transform(self.df['cleaned'])

        # Precompute cosine similarity matrix
        self.cosine_sim = linear_kernel(self.tfidf_matrix, self.tfidf_matrix)

    def get_recommendations(
        self,
        ingredients: str,
        num_recommendations: int = 5,
        difficulty_filter: Optional[str] = None,
        dietary_filters: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, List[float]]:
        """
        Get recipe recommendations based on ingredients.

        Args:
            ingredients: Input ingredient string
            num_recommendations: Number of recommendations to return
            difficulty_filter: Filter by difficulty (Easy/Medium/Hard)
            dietary_filters: List of dietary tags to filter by

        Returns:
            Tuple of (recipes dataframe, similarity scores)
        """
        # Clean and vectorize input
        cleaned_input = clean_text(ingredients)
        input_vec = self.tfidf.transform([cleaned_input])
        sim_scores = linear_kernel(input_vec, self.tfidf_matrix).flatten()

        # Get top indices (skip the first one as it's the input itself)
        top_indices = sim_scores.argsort()[::-1][:num_recommendations * 2]

        # Apply filters
        recommendations = self.df.iloc[top_indices].copy()
        recommendations['similarity_score'] = sim_scores[top_indices]

        if difficulty_filter:
            recommendations = recommendations[
                recommendations.get('difficulty', '').str.lower(
                ) == difficulty_filter.lower()
            ]

        if dietary_filters:
            for tag in dietary_filters:
                recommendations = recommendations[
                    recommendations.get('dietary_tags', '').str.contains(
                        tag, case=False, na=False)
                ]

        # Return top N after filtering
        recommendations = recommendations.head(num_recommendations)

        return recommendations, recommendations['similarity_score'].tolist()

    def search_recipes(self, query: str, limit: int = 10) -> pd.DataFrame:
        """Search recipes by title or ingredients."""
        results = self.df[
            (self.df['title'].str.contains(query, case=False, na=False)) |
            (self.df['ingredients'].str.contains(query, case=False, na=False))
        ].head(limit)

        return results

    def get_recipe_by_id(self, recipe_id: int) -> Optional[dict]:
        """Get recipe details by ID."""
        recipe = self.df[self.df.index == recipe_id]
        if recipe.empty:
            return None
        return recipe.iloc[0].to_dict()
