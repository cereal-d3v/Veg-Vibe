import gradio as gr
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

data = pd.read_csv("vegan_recipes.csv")


def clean(text):
    text = re.sub(r'\d+', '', str(text))
    text = re.sub(r'[^\w\s]', '', text).lower()
    return ' '.join(w for w in text.split() if w not in {"the", "and", "with", "of", "in"})


data["cleaned"] = data["ingredients"].apply(clean)
tfidf = TfidfVectorizer()
tfidf_matrix = tfidf.fit_transform(data["cleaned"])
cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
indices = pd.Series(data.index, index=data["title"]).drop_duplicates()


def recommend(ingredients):
    input_vec = tfidf.transform([clean(ingredients)])
    sim_scores = linear_kernel(input_vec, tfidf_matrix).flatten()
    top_indices = sim_scores.argsort()[-3:][::-1]
    recs = data.iloc[top_indices][["title", "ingredients"]]
    return recs.to_string(index=False)


gr.Interface(fn=recommend, inputs="text", outputs="text").launch()
