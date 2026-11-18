"""Train the triage model.   Usage:  python models/train_triage.py
Reads data/emergency_data.csv (columns: text,category,severity[,base_id]).
If base_id exists, test sentences are ones the model never saw in any form (more honest score)."""
import os, joblib, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.metrics import classification_report, confusion_matrix

HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(HERE, "..", "data", "emergency_data.csv")).dropna(subset=["text", "category", "severity"])
df["text"] = df["text"].astype(str).str.lower().str.strip()
print(f"Loaded {len(df)} rows\n", df["category"].value_counts().to_string(), "\n")

def make():
    # word features capture keywords ("fire", "accident"); char features survive typos/Hinglish spelling
    feats = make_union(TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True),
                       TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True))
    return make_pipeline(feats, LogisticRegression(max_iter=3000, C=10))

if "base_id" in df.columns and df["base_id"].notna().all():
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=1).split(df, groups=df["base_id"]))
    train, test = df.iloc[tr], df.iloc[te]
else:
    train, test = train_test_split(df, test_size=0.25, random_state=1, stratify=df["category"])

for target in ("category", "severity"):
    m = make().fit(train["text"], train[target])
    pred = m.predict(test["text"])
    print(f"=== {target.upper()} ===")
    print(classification_report(test[target], pred, zero_division=0))
    labels = sorted(df[target].unique())
    cm = confusion_matrix(test[target], pred, labels=labels)
    print("Confusion matrix (rows=true, cols=pred):", labels); print(cm, "\n")
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 4)); ax.imshow(cm, cmap="Reds")
        ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
        for i in range(len(labels)):
            for j in range(len(labels)): ax.text(j, i, cm[i, j], ha="center", va="center")
        ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(f"{target} confusion matrix")
        fig.tight_layout(); fig.savefig(os.path.join(HERE, f"confusion_{target}.png"), dpi=150); plt.close(fig)
    except Exception as e:
        print("(skipped plot:", e, ")")

# Final model: retrain on ALL data
final = {t: make().fit(df["text"], df[t]) for t in ("category", "severity")}
joblib.dump(final, os.path.join(HERE, "triage_model.joblib"))
print("Saved models/triage_model.joblib")
