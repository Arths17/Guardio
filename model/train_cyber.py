import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from torch.utils.data import DataLoader, Dataset


DEFAULT_TIMESTAMP_COLUMNS = (
	"timestamp",
	"time",
	"datetime",
	"start_time",
	"end_time",
	"ts",
	"flow_start",
	"flow_end",
)


@dataclass
class FeatureBundle:
	feature_frame: pd.DataFrame
	numeric_columns: list[str]
	categorical_columns: list[str]
	timestamp_columns: list[str]


class CyberTabularDataset(Dataset):
	def __init__(self, features: np.ndarray, labels: np.ndarray):
		self.features = torch.from_numpy(features.astype(np.float32))
		self.labels = torch.from_numpy(labels.astype(np.int64))

	def __len__(self):
		return len(self.labels)

	def __getitem__(self, idx):
		return self.features[idx], self.labels[idx]


class CyberMLP(nn.Module):
	def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout: float = 0.2):
		super().__init__()
		self.net = nn.Sequential(
			nn.Linear(input_dim, hidden_dim),
			nn.BatchNorm1d(hidden_dim),
			nn.ReLU(inplace=True),
			nn.Dropout(dropout),
			nn.Linear(hidden_dim, hidden_dim // 2),
			nn.ReLU(inplace=True),
			nn.Dropout(dropout),
			nn.Linear(hidden_dim // 2, num_classes),
		)

	def forward(self, x):
		return self.net(x)


def parse_csv_args(value):
	if not value:
		return []
	return [item.strip() for item in value.split(",") if item.strip()]


def build_feature_frame(df: pd.DataFrame, label_column: str, drop_columns: list[str], timestamp_columns: list[str]) -> FeatureBundle:
	working = df.copy()
	for column in drop_columns:
		if column in working.columns and column != label_column:
			working = working.drop(columns=[column])

	actual_timestamp_columns = []
	for column in timestamp_columns:
		if column in working.columns and column != label_column:
			actual_timestamp_columns.append(column)

	for column in list(working.columns):
		if column == label_column or column in drop_columns:
			continue
		if column.lower() in DEFAULT_TIMESTAMP_COLUMNS and column not in actual_timestamp_columns:
			actual_timestamp_columns.append(column)

	for column in actual_timestamp_columns:
		parsed = pd.to_datetime(working[column], errors="coerce", utc=True)
		working[f"{column}_year"] = parsed.dt.year.fillna(0).astype(int)
		working[f"{column}_month"] = parsed.dt.month.fillna(0).astype(int)
		working[f"{column}_day"] = parsed.dt.day.fillna(0).astype(int)
		working[f"{column}_hour"] = parsed.dt.hour.fillna(0).astype(int)
		working[f"{column}_dayofweek"] = parsed.dt.dayofweek.fillna(0).astype(int)
		working = working.drop(columns=[column])

	numeric_columns = []
	categorical_columns = []
	for column in working.columns:
		if column == label_column:
			continue
		if pd.api.types.is_numeric_dtype(working[column]):
			numeric_columns.append(column)
		else:
			categorical_columns.append(column)

	for column in numeric_columns:
		working[column] = pd.to_numeric(working[column], errors="coerce")

	for column in categorical_columns:
		working[column] = working[column].astype("string").fillna("missing")

	return FeatureBundle(
		feature_frame=working,
		numeric_columns=numeric_columns,
		categorical_columns=categorical_columns,
		timestamp_columns=actual_timestamp_columns,
	)


def encode_features(train_df: pd.DataFrame, val_df: pd.DataFrame, numeric_columns: list[str], categorical_columns: list[str]):
	numeric_imputer = None
	numeric_scaler = None
	if numeric_columns:
		numeric_imputer = SimpleImputer(strategy="median")
		numeric_scaler = StandardScaler()
		train_numeric = numeric_scaler.fit_transform(numeric_imputer.fit_transform(train_df[numeric_columns]))
		val_numeric = numeric_scaler.transform(numeric_imputer.transform(val_df[numeric_columns]))
	else:
		train_numeric = np.empty((len(train_df), 0))
		val_numeric = np.empty((len(val_df), 0))

	if categorical_columns:
		categorical_imputer = SimpleImputer(strategy="most_frequent")
		train_categorical = categorical_imputer.fit_transform(train_df[categorical_columns])
		val_categorical = categorical_imputer.transform(val_df[categorical_columns])
		encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
		train_categorical = encoder.fit_transform(train_categorical)
		val_categorical = encoder.transform(val_categorical)
	else:
		categorical_imputer = None
		encoder = None
		train_categorical = np.empty((len(train_df), 0))
		val_categorical = np.empty((len(val_df), 0))

	train_features = np.hstack([train_numeric, train_categorical]).astype(np.float32)
	val_features = np.hstack([val_numeric, val_categorical]).astype(np.float32)
	return train_features, val_features, numeric_imputer, numeric_scaler, categorical_imputer, encoder


def train_epoch(model, device, loader, optimizer, criterion):
	model.train()
	total_loss = 0.0
	for features, labels in loader:
		features, labels = features.to(device), labels.to(device)
		optimizer.zero_grad()
		logits = model(features)
		loss = criterion(logits, labels)
		loss.backward()
		optimizer.step()
		total_loss += loss.item() * features.size(0)
	return total_loss / len(loader.dataset)


def evaluate(model, device, loader, criterion):
	model.eval()
	total_loss = 0.0
	correct = 0
	with torch.no_grad():
		for features, labels in loader:
			features, labels = features.to(device), labels.to(device)
			logits = model(features)
			loss = criterion(logits, labels)
			total_loss += loss.item() * features.size(0)
			predictions = logits.argmax(dim=1)
			correct += (predictions == labels).sum().item()
	return total_loss / len(loader.dataset), correct / len(loader.dataset)


def main():
	parser = argparse.ArgumentParser(description="Train a mixed-tabular cybersecurity model from a CSV or parquet file.")
	parser.add_argument("--data", type=str, default="data/cyber.csv")
	parser.add_argument("--label", type=str, default="label")
	parser.add_argument("--drop-columns", type=str, default="", help="Comma-separated columns to drop before training.")
	parser.add_argument("--timestamp-columns", type=str, default="", help="Comma-separated columns to parse as timestamps.")
	parser.add_argument("--test-size", type=float, default=0.2)
	parser.add_argument("--batch-size", type=int, default=64)
	parser.add_argument("--epochs", type=int, default=10)
	parser.add_argument("--lr", type=float, default=1e-3)
	parser.add_argument("--out", type=str, default="models")
	args = parser.parse_args()

	path = Path(args.data)
	if not path.exists():
		raise SystemExit(f"Data file not found: {path}")

	if path.suffix.lower() == ".parquet":
		df = pd.read_parquet(path)
	else:
		df = pd.read_csv(path)

	if args.label not in df.columns:
		raise SystemExit(f"Label column '{args.label}' not found. Available columns: {list(df.columns)}")

	drop_columns = parse_csv_args(args.drop_columns)
	timestamp_columns = parse_csv_args(args.timestamp_columns)
	feature_bundle = build_feature_frame(df, args.label, drop_columns, timestamp_columns)
	feature_df = feature_bundle.feature_frame

	label_encoder = LabelEncoder()
	y = label_encoder.fit_transform(df[args.label].astype(str).fillna("missing"))
	X = feature_df.drop(columns=[args.label])

	X_train_df, X_val_df, y_train, y_val = train_test_split(
		X,
		y,
		test_size=args.test_size,
		stratify=y,
		random_state=42,
	)

	train_features, val_features, numeric_imputer, numeric_scaler, categorical_imputer, onehot_encoder = encode_features(
		X_train_df,
		X_val_df,
		feature_bundle.numeric_columns,
		feature_bundle.categorical_columns,
	)

	out_dir = Path(args.out)
	out_dir.mkdir(parents=True, exist_ok=True)
	joblib.dump(
		{
			"numeric_imputer": numeric_imputer,
			"numeric_scaler": numeric_scaler,
			"categorical_imputer": categorical_imputer,
			"onehot_encoder": onehot_encoder,
			"numeric_columns": feature_bundle.numeric_columns,
			"categorical_columns": feature_bundle.categorical_columns,
			"timestamp_columns": feature_bundle.timestamp_columns,
		},
		out_dir / "preprocessor.joblib",
	)
	joblib.dump(label_encoder, out_dir / "label_encoder.joblib")
	with open(out_dir / "feature_schema.json", "w", encoding="utf-8") as handle:
		json.dump(
			{
				"label": args.label,
				"drop_columns": drop_columns,
				"timestamp_columns": feature_bundle.timestamp_columns,
				"numeric_columns": feature_bundle.numeric_columns,
				"categorical_columns": feature_bundle.categorical_columns,
			},
			handle,
			indent=2,
		)

	train_dataset = CyberTabularDataset(train_features, y_train)
	val_dataset = CyberTabularDataset(val_features, y_val)
	train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
	val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	model = CyberMLP(input_dim=train_features.shape[1], num_classes=len(label_encoder.classes_)).to(device)
	optimizer = optim.Adam(model.parameters(), lr=args.lr)
	criterion = nn.CrossEntropyLoss()

	for epoch in range(1, args.epochs + 1):
		train_loss = train_epoch(model, device, train_loader, optimizer, criterion)
		val_loss, val_acc = evaluate(model, device, val_loader, criterion)
		val_acc *= 100.0
		print(
			f"Epoch {epoch}\n"
			f"  Train loss: {train_loss:.4f}\n"
			f"  Val loss: {val_loss:.4f}\n"
			f"  Val acc: {val_acc:.2f}%"
		)

	torch.save(model.state_dict(), out_dir / "cyber_model.pt")
	print(f"Saved model to {out_dir / 'cyber_model.pt'}")
	print(f"Saved preprocessing artifacts to {out_dir / 'preprocessor.joblib'} and {out_dir / 'label_encoder.joblib'}")


if __name__ == "__main__":
	main()