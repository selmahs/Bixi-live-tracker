"""
train_model.py
Entraîne un modèle de régression pour prédire la demande de vélos BIXI
(nombre de départs) par station et par heure, à partir des données
historiques de trajets publiées par BIXI (https://bixi.com/en/open-data/).

Traite le(s) CSV par blocs (chunks) pour supporter de gros fichiers
(plusieurs millions de lignes) sans tout charger en mémoire d'un coup,
et utilise LightGBM (gère les variables catégorielles à haute cardinalité
nativement, ~800+ stations, et entraîne en quelques secondes sur ~1M lignes).

Utilisation:
    1. Télécharger et dézipper les données de trajets d'une année sur
       https://bixi.com/en/open-data/ (fichiers .csv)
    2. Placer le(s) fichier(s) CSV dans un dossier data/ à la racine du projet
    3. Lancer: python train_model.py --data-dir data --output model.pkl
"""
import argparse
import glob
import os
import time

import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

CHUNK_SIZE = 500_000  # lignes lues à la fois ; ajuster si RAM limitée


def _detect_columns(columns) -> tuple[str, str, bool]:
    """
    Détecte le format du CSV BIXI et retourne (colonne_temps, colonne_station,
    est_epoch_ms). Gère :
      - 2025-2026 : STARTSTATIONNAME, STARTTIMEMS (epoch en millisecondes)
      - formats plus anciens : start_date/start_station_code,
        ou STARTTIMEMS/start_stn_code
    """
    if "STARTSTATIONNAME" in columns and "STARTTIMEMS" in columns:
        return "STARTTIMEMS", "STARTSTATIONNAME", True
    if "start_date" in columns and "start_station_code" in columns:
        return "start_date", "start_station_code", False
    if "STARTTIMEMS" in columns and "start_stn_code" in columns:
        return "STARTTIMEMS", "start_stn_code", False
    raise ValueError(f"Format de colonnes BIXI non reconnu : {list(columns)}")


def _process_chunk(chunk: pd.DataFrame, time_col: str, station_col: str, is_epoch_ms: bool) -> pd.DataFrame:
    """Agrège un bloc de lignes individuelles en comptes (station, heure, jour, mois)."""
    chunk = chunk.dropna(subset=[station_col, time_col])

    if is_epoch_ms:
        start_time = pd.to_datetime(chunk[time_col], unit="ms", errors="coerce")
    else:
        start_time = pd.to_datetime(chunk[time_col], errors="coerce")

    out = pd.DataFrame({
        "station_id": chunk[station_col].values,
        "hour": start_time.dt.hour,
        "day_of_week": start_time.dt.dayofweek,  # 0 = lundi
        "month": start_time.dt.month,
    })
    out = out.dropna()
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(int)

    return (
        out.groupby(["station_id", "hour", "day_of_week", "month", "is_weekend"])
        .size()
        .reset_index(name="num_departures")
    )


def build_hourly_demand(data_dir: str, chunksize: int = CHUNK_SIZE) -> pd.DataFrame:
    """
    Lit tous les CSV d'un dossier par blocs et construit la table agrégée
    de demande horaire, sans jamais charger un fichier entier en mémoire.
    """
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans {data_dir}")

    partial_counts: list[pd.DataFrame] = []
    total_rows = 0

    for path in csv_files:
        header_cols = pd.read_csv(path, nrows=0).columns
        time_col, station_col, is_epoch_ms = _detect_columns(header_cols)
        usecols = [time_col, station_col]

        print(f"Lecture de {os.path.basename(path)} par blocs de {chunksize:,} lignes...")
        for i, chunk in enumerate(pd.read_csv(path, usecols=usecols, chunksize=chunksize)):
            total_rows += len(chunk)
            partial_counts.append(_process_chunk(chunk, time_col, station_col, is_epoch_ms))
            if (i + 1) % 5 == 0:
                print(f"  {total_rows:,} lignes traitées...")

    print(f"Total : {total_rows:,} lignes lues.")

    combined = pd.concat(partial_counts, ignore_index=True)
    hourly = (
        combined.groupby(["station_id", "hour", "day_of_week", "month", "is_weekend"])["num_departures"]
        .sum()
        .reset_index()
    )
    print(f"Table agrégée : {len(hourly):,} lignes (station x heure x jour x mois).")
    return hourly


def train(hourly: pd.DataFrame):
    features = ["hour", "day_of_week", "month", "is_weekend", "station_id"]
    X = hourly[features].copy()
    # station_id en type "category" : LightGBM gère nativement les
    # catégories à haute cardinalité (~800+ stations), sans one-hot
    # encoding et sans limite de 255 catégories (contrairement à
    # HistGradientBoostingRegressor de scikit-learn).
    X["station_id"] = X["station_id"].astype("category")
    y = hourly["num_departures"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("Entraînement du modèle (LightGBM)...")
    start = time.time()

    model = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.1,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train, y_train, categorical_feature=["station_id"])

    elapsed = time.time() - start
    print(f"Entraînement terminé en {elapsed:.1f} secondes.")

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"MAE:  {mae:.2f} départs/heure")
    print(f"RMSE: {rmse:.2f} départs/heure")

    # On sauvegarde les catégories de station_id vues à l'entraînement,
    # pour pouvoir encoder correctement une nouvelle prédiction plus tard
    # (voir predict_addition.py).
    station_categories = X["station_id"].cat.categories.tolist()

    return model, features, station_categories


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="model.pkl")
    parser.add_argument("--chunksize", type=int, default=CHUNK_SIZE)
    args = parser.parse_args()

    hourly = build_hourly_demand(args.data_dir, args.chunksize)
    model, feature_columns, station_categories = train(hourly)

    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "station_categories": station_categories,
        },
        args.output,
    )
    print(f"Modèle sauvegardé dans {args.output}")


if __name__ == "__main__":
    main()