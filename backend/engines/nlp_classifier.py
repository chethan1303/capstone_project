"""NLP classifier for offline prompt-injection experiments."""

from typing import Sequence, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


BENIGN_LABEL = "benign"
INJECTION_LABEL = "prompt_injection"


class PromptInjectionClassifier:
    """TF-IDF word n-grams with a balanced logistic-regression classifier."""

    def __init__(self, random_state: int = 42) -> None:
        self._pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(1, 2),
                        strip_accents="unicode",
                        sublinear_tf=True,
                    ),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=random_state,
                    ),
                ),
            ]
        )
        self._fitted = False

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> "PromptInjectionClassifier":
        """Fit on labeled text and require both supported classes."""
        if not texts or len(texts) != len(labels):
            raise ValueError("texts and labels must be non-empty and have equal lengths")
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("training texts must be non-empty strings")
        if set(labels) != {BENIGN_LABEL, INJECTION_LABEL}:
            raise ValueError("training data must contain benign and prompt_injection labels")

        self._pipeline.fit(texts, labels)
        self._fitted = True
        return self

    def predict(self, text: str) -> Tuple[str, float]:
        """Return the predicted label and injection probability."""
        if not self._fitted:
            raise RuntimeError("classifier must be fitted before prediction")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        probabilities = self._pipeline.predict_proba([text])[0]
        classes = self._pipeline.named_steps["classifier"].classes_
        injection_index = list(classes).index(INJECTION_LABEL)
        probability = float(probabilities[injection_index])
        label = INJECTION_LABEL if probability >= 0.5 else BENIGN_LABEL
        return label, probability
