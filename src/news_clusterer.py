from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

class NewsClusterer:
    def __init__(self, eps=0.3, min_samples=2):
        self.eps = eps
        self.min_samples = min_samples
        
    def cluster_similar_news(self, titles, summaries):
        combined_texts = [f"{t} {s}" for t, s in zip(titles, summaries)]
        
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(combined_texts)
        
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(tfidf_matrix)
        
        clusters = {}
        for idx, label in enumerate(clustering.labels_):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return clusters 