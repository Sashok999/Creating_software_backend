import os
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score

MODEL_PATH = Path("model.pkl")
ENCODERS_PATH = Path("encoders.pkl")
DATA_PATH = Path("training_data.csv")

CITIES = ["Москва", "Санкт-Петербург", "Казань", "Сочи", "Екатеринбург", "Новосибирск", "Краснодар", "Нижний Новгород"]
PROPERTY_TYPES = ["apartment", "house", "studio", "room", "villa"]
AMENITIES_POOL = ["wifi", "parking", "kitchen", "pool", "gym", "ac", "balcony", "washer", "tv", "pets"]


def _build_features(df: pd.DataFrame, city_enc: LabelEncoder, type_enc: LabelEncoder) -> np.ndarray:
    city_col = city_enc.transform(df["city"].fillna("Москва"))
    type_col = type_enc.transform(df["property_type"].fillna("apartment"))
    price_range = (df["max_price"] - df["min_price"]).fillna(0).values
    rooms = df["rooms"].fillna(0).values
    guests = df["guests"].fillna(1).values
    nights = (
        pd.to_datetime(df["check_out"], errors="coerce") -
        pd.to_datetime(df["check_in"], errors="coerce")
    ).dt.days.fillna(1).values

    amenity_matrix = np.zeros((len(df), len(AMENITIES_POOL)))
    for i, row in enumerate(df["amenities"]):
        try:
            items = json.loads(row) if isinstance(row, str) else (row or [])
        except Exception:
            items = []
        for item in items:
            if item in AMENITIES_POOL:
                amenity_matrix[i, AMENITIES_POOL.index(item)] = 1

    return np.column_stack([city_col, type_col, price_range, rooms, guests, nights, amenity_matrix])


def train_model(data_path: str = str(DATA_PATH)) -> dict:
    df = pd.read_csv(data_path)

    city_enc = LabelEncoder().fit(CITIES)
    type_enc = LabelEncoder().fit(PROPERTY_TYPES)

    df["city"] = df["city"].where(df["city"].isin(CITIES), CITIES[0])
    df["property_type"] = df["property_type"].where(df["property_type"].isin(PROPERTY_TYPES), PROPERTY_TYPES[0])

    X = _build_features(df, city_enc, type_enc)
    y = df["booked"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
    }
#22
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    with open(ENCODERS_PATH, "wb") as f:
        pickle.dump({"city": city_enc, "type": type_enc}, f)

    return metrics


def load_model():
    if not MODEL_PATH.exists() or not ENCODERS_PATH.exists():
        raise FileNotFoundError("Модель не найдена. Запустите /ai/train сначала.")
    with open(MODEL_PATH, "rb") as f:
        clf = pickle.load(f)
    with open(ENCODERS_PATH, "rb") as f:
        encoders = pickle.load(f)
    return clf, encoders


def get_recommendations(
    city: str,
    property_type: str,
    min_price: float,
    max_price: float,
    rooms: int,
    amenities: list[str],
    check_in: str,
    check_out: str,
    guests: int,
    top_n: int = 5,
) -> list[dict]:
    clf, encoders = load_model()
    city_enc: LabelEncoder = encoders["city"]
    type_enc: LabelEncoder = encoders["type"]

    city = city if city in CITIES else CITIES[0]
    property_type = property_type if property_type in PROPERTY_TYPES else PROPERTY_TYPES[0]

    candidates = []
    for prop_id in range(1, 501):
        row = {
            "city": city,
            "property_type": property_type,
            "min_price": min_price,
            "max_price": max_price,
            "rooms": rooms,
            "guests": guests,
            "amenities": json.dumps(amenities, ensure_ascii=False),
            "check_in": check_in,
            "check_out": check_out,
        }
        df_row = pd.DataFrame([row])
        X = _build_features(df_row, city_enc, type_enc)
        prob = clf.predict_proba(X)[0][1]
        candidates.append({"property_id": prop_id, "score": round(float(prob), 4)})

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]
