"""
train_model_pytorch.py
Entraîne un réseau de neurones (MLP) en PyTorch pour prédire la demande
horaire de vélos BIXI par station, à comparer avec le modèle LightGBM de
train_model.py. Utilise un embedding pour représenter les stations
(variable catégorielle à haute cardinalité, ~800+ stations).

Utilisation:
    python train_model_pytorch.py --data-dir data --output model_pytorch.pt
"""
import argparse

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

from train_model import build_hourly_demand, CHUNK_SIZE


class DemandMLP(nn.Module):
    """MLP avec embedding de station + features numériques normalisées."""

    def __init__(self, num_stations: int, embedding_dim: int = 16, hidden_dim: int = 64):
        super().__init__()
        self.station_embedding = nn.Embedding(num_stations, embedding_dim)
        self.net = nn.Sequential(
            nn.Linear(embedding_dim + 4, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, station_idx: torch.Tensor, numeric_feats: torch.Tensor) -> torch.Tensor:
        emb = self.station_embedding(station_idx)
        x = torch.cat([emb, numeric_feats], dim=1)
        return self.net(x).squeeze(-1)


def prepare_tensors(hourly: pd.DataFrame, station_to_idx: dict):
    station_idx = hourly["station_id"].map(station_to_idx).values
    numeric = hourly[["hour", "day_of_week", "month", "is_weekend"]].copy()
    # Normalisation simple des features numériques dans [0, 1]
    numeric["hour"] = numeric["hour"] / 23.0
    numeric["day_of_week"] = numeric["day_of_week"] / 6.0
    numeric["month"] = numeric["month"] / 12.0
    y = hourly["num_departures"].values.astype(np.float32)

    return (
        torch.tensor(station_idx, dtype=torch.long),
        torch.tensor(numeric.values, dtype=torch.float32),
        torch.tensor(y, dtype=torch.float32),
    )


def train(hourly: pd.DataFrame, epochs: int = 15, batch_size: int = 4096, lr: float = 1e-3):
    # Même split que LightGBM (même random_state) pour une comparaison équitable
    train_df, test_df = train_test_split(hourly, test_size=0.2, random_state=42)

    stations = sorted(hourly["station_id"].unique())
    station_to_idx = {s: i for i, s in enumerate(stations)}

    station_train, num_train, y_train = prepare_tensors(train_df, station_to_idx)
    station_test, num_test, y_test = prepare_tensors(test_df, station_to_idx)

    train_loader = DataLoader(
        TensorDataset(station_train, num_train, y_train),
        batch_size=batch_size,
        shuffle=True,
    )

    model = DemandMLP(num_stations=len(stations))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    print("Entraînement du modèle PyTorch (MLP)...")
    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for station_batch, num_batch, y_batch in train_loader:
            optimizer.zero_grad()
            preds = model(station_batch, num_batch)
            loss = loss_fn(preds, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(y_batch)
        avg_loss = total_loss / len(train_df)
        print(f"  Époque {epoch + 1}/{epochs} — MSE entraînement: {avg_loss:.3f}")

    model.eval()
    with torch.no_grad():
        preds_test = model(station_test, num_test).numpy()

    mae = mean_absolute_error(y_test.numpy(), preds_test)
    rmse = np.sqrt(mean_squared_error(y_test.numpy(), preds_test))
    print(f"MAE (PyTorch MLP):  {mae:.2f} départs/heure")
    print(f"RMSE (PyTorch MLP): {rmse:.2f} départs/heure")

    return model, station_to_idx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="model_pytorch.pt")
    parser.add_argument("--chunksize", type=int, default=CHUNK_SIZE)
    parser.add_argument("--epochs", type=int, default=15)
    args = parser.parse_args()

    hourly = build_hourly_demand(args.data_dir, args.chunksize)
    model, station_to_idx = train(hourly, epochs=args.epochs)

    torch.save(
        {"model_state_dict": model.state_dict(), "station_to_idx": station_to_idx},
        args.output,
    )
    print(f"Modèle PyTorch sauvegardé dans {args.output}")


if __name__ == "__main__":
    main()
