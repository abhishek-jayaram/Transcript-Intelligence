
"""This pipeline that reads labeled text data → trains a TF-IDF + Logistic Regression classifier → and 
 honestly evaluates how well it generalizes using cross-validation, without any data leakage"""

import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

df = pd.read_csv(r"C:\Users\Abhishek\OneDrive\Documents\AIML Projects\Transcript Intelligence\Data\LLM_labeling_sheet.csv")

# Clean labels
df["manual_label"] = df["manual_label"].astype(str).str.strip()

# Build combined text
for col in ["title", "summary", "topics", "action_items"]:
    if col not in df.columns:
        df[col] = ""

df["combined_text"] = (
    df["title"].fillna("") + " " +
    df["summary"].fillna("") + " " +
    df["topics"].fillna("") + " " +
    df["action_items"].fillna("")
)

X = df["combined_text"]
y = df["manual_label"]

model = Pipeline([
    ("tfidf", TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english"
    )),
    ("clf", LogisticRegression(
        max_iter=2000,
        class_weight="balanced"
    ))
])

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

preds = cross_val_predict(model, X, y, cv=cv)

print(classification_report(y, preds, digits=4))
print(confusion_matrix(y, preds))




