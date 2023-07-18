#Building the search engine
import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
filtered_restaurant_df = pd.read_csv('C:/Users/omben/Desktop/Projects/Restaurant-Recommender-System/main/restaurants.csv')

vectorizer = TfidfVectorizer(ngram_range=(1,2))
corpus = filtered_restaurant_df['name']+' '+filtered_restaurant_df['cuisine']
tfidf = vectorizer.fit_transform(corpus)

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

#restaurants search engine
def search(name):
  name = name
  query_vec = vectorizer.transform([name])
  similarity = cosine_similarity(query_vec, tfidf).flatten()
  indices = np.argpartition(similarity, -5)[-5:]
  results = filtered_restaurant_df.iloc[indices][::-1]
  return results

# dump of the search engine
with open('search.pkl', 'wb') as file:
    pickle.dump(search, file)

