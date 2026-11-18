"""AI triage: text -> (category, severity, confidence) + safety rules.
Model = TF-IDF on character n-grams (handles typos + Hinglish) + Logistic Regression."""
import os, joblib

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "triage_model.joblib")
LOW_CONFIDENCE = 0.50

_model = None
def _load():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception as e:      # e.g. different scikit-learn version -> just retrain
            print("Could not load model (", e, "). Run: python models/train_triage.py")
    return _model

# Safety rules: if any of these appear, severity is forced to HIGH (fail toward caution).
HIGH_RISK = ["not breathing", "unconscious", "unresponsive", "not responding", "collapsed", "fainted", "behosh",
             "heavy bleeding", "bleeding heavily", "bahut khoon", "seizure", "chest pain", "trapped", "weapon",
             "gun", "knife", "flames", "aag", "explosion", "drowning", "stalk", "saans", "cant breathe",
             "can't breathe", "cannot breathe", "assault", "rape", "earthquake", "bhukamp", "flood",
             "suicide", "kill myself", "end my life", "marna chahta", "marna chahti"]

# Keyword hints: a unique match overrides the model; several matches only help when the model is unsure.
KEYWORD_CATEGORY = {"fire": ["fire", "aag", "smoke", "dhuan", "burning"],
                    "medical": ["faint", "breath", "bleed", "pain", "fever", "seizure", "behosh", "bukhar", "ulti"],
                    "accident": ["accident", "collid", "hit by", "fell", "gir gaya"],
                    "security": ["follow", "harass", "stalk", "threat", "weapon", "stolen", "chori", "ragging"],
                    "natural_disaster": ["earthquake", "flood", "storm", "cyclone", "bhukamp", "aandhi", "lightning"]}

# Extra first-aid topics (checked in this order; first match wins). Used for medical/accident.
SUBTOPIC_KEYWORDS = [
    ("mental_health", ["suicide", "kill myself", "end my life", "marna chahta", "marna chahti", "self harm", "hurt myself"]),
    ("unresponsive", ["not breathing", "unconscious", "unresponsive", "not responding", "collapsed", "faint", "behosh"]),
    ("choking", ["choking", "choke", "something stuck in throat"]),
    ("breathing_difficulty", ["asthma", "saans", "cant breathe", "can't breathe", "cannot breathe", "breathless"]),
    ("seizure", ["seizure", "fits", "convulsion"]),
    ("allergic_reaction", ["allergic", "allergy", "face is swelling", "anaphyla"]),
    ("chest_pain", ["chest pain", "heart attack", "seene me dard"]),
    ("bleeding", ["bleeding", "blood", "khoon"]),
    ("burn", ["burn", "scald", "jal gaya", "jalne"]),
]

def _norm(t):
    return " ".join(t.lower().replace("\u2019", "'").split())

def detect_subtopic(text):
    t = _norm(text)
    for name, kws in SUBTOPIC_KEYWORDS:
        if any(k in t for k in kws):
            return name
    return None

def predict(text):
    t = _norm(text)
    m = _load()
    probs = {}
    if m:
        cat_p = m["category"].predict_proba([t])[0]
        probs = {str(c): float(p) for c, p in zip(m["category"].classes_, cat_p)}
        category = max(probs, key=probs.get)
        conf = probs[category]
        severity = str(m["severity"].predict([t])[0])
    else:
        category, severity, conf = "unknown", "medium", 0.0
    # Hybrid rule: a clear keyword match for exactly ONE category overrides the model
    # (measured: 53% -> 66% on sentences the model had never seen).
    hits = [c for c, kws in KEYWORD_CATEGORY.items() if any(k in t for k in kws)]
    if len(hits) == 1:
        category = hits[0]
    elif hits and conf < LOW_CONFIDENCE:
        category = max(hits, key=lambda c: probs.get(c, 0))
    elif conf < LOW_CONFIDENCE:
        category = "unknown"
    matched = [k for k in HIGH_RISK if k in t]
    if matched:
        severity = "high"
    sub = detect_subtopic(t) if category in ("medical", "accident", "unknown") else None
    if sub == "mental_health":
        category, severity = "medical", "high"
    return {"category": category, "severity": severity, "confidence": round(conf, 3),
            "rules_triggered": matched, "subtopic": sub}
