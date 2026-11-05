"""Sentiment model that learns to rate news the way you do.

Until you've rated enough articles it falls back to VADER, a generic
rule-based sentiment scorer. Once you have, it trains a logistic regression
on TF-IDF word features plus the VADER score, so it starts from a sensible
prior and then learns which words *you* see as good or bad news.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

MIN_RATINGS = 10        # ratings needed (with both labels) before training
MIN_PER_CLASS = 3

_vader = SentimentIntensityAnalyzer()


def article_text(article):
    return f"{article['title']}. {article.get('summary') or ''}".strip()


def vader_score(text):
    """Generic sentiment in [-1, 1]."""
    return _vader.polarity_scores(text)["compound"]


def _vader_features(texts):
    return np.array([[vader_score(t)] for t in texts])


def _build_pipeline():
    features = FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)),
        ("vader", FunctionTransformer(_vader_features)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])


class Rater:
    def __init__(self):
        self.pipeline = None
        self.n_trained = 0
        self.cv_accuracy = None      # personal model, cross-validated
        self.vader_accuracy = None   # generic VADER on the same ratings

    @property
    def is_personal(self):
        return self.pipeline is not None

    def fit(self, articles):
        """Train on articles that have a user_label."""
        rated = [a for a in articles if a.get("user_label") is not None]
        texts = [article_text(a) for a in rated]
        labels = np.array([a["user_label"] for a in rated])

        self.n_trained = len(rated)
        self.pipeline = self.cv_accuracy = self.vader_accuracy = None
        if not rated:
            return self

        self.vader_accuracy = float(np.mean(
            [(vader_score(t) >= 0) == bool(y) for t, y in zip(texts, labels)]
        ))

        minority = min(np.sum(labels == 1), np.sum(labels == 0))
        if len(rated) < MIN_RATINGS or minority < MIN_PER_CLASS:
            return self

        if minority >= 2:
            folds = StratifiedKFold(n_splits=min(5, minority), shuffle=True, random_state=0)
            self.cv_accuracy = float(np.mean(
                cross_val_score(_build_pipeline(), texts, labels, cv=folds)
            ))

        self.pipeline = _build_pipeline().fit(texts, labels)
        return self

    def predict_proba(self, articles):
        """Probability each article is positive news (in your eyes, once trained)."""
        if not articles:
            return np.array([])
        texts = [article_text(a) for a in articles]
        if self.pipeline is not None:
            return self.pipeline.predict_proba(texts)[:, 1]
        return np.array([(vader_score(t) + 1) / 2 for t in texts])

    def top_words(self, n=15):
        """Words/phrases that push the personal model most towards positive / negative."""
        if self.pipeline is None:
            return [], []
        tfidf = self.pipeline.named_steps["features"].transformer_list[0][1]
        names = tfidf.get_feature_names_out()
        coefs = self.pipeline.named_steps["clf"].coef_[0][: len(names)]
        order = np.argsort(coefs)
        positive = [(names[i], coefs[i]) for i in order[::-1][:n] if coefs[i] > 0]
        negative = [(names[i], coefs[i]) for i in order[:n] if coefs[i] < 0]
        return positive, negative
