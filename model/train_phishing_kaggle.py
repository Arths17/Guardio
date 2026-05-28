import argparse
import json
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_curve
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


def prepare_dataframe(path: Path, target_col: str = "Result"):
	if path.suffix.lower() == ".parquet":
		df = pd.read_parquet(path)
	else:
		df = pd.read_csv(path)

	if "index" in df.columns:
		df = df.drop(columns=["index"])
	if target_col not in df.columns:
		raise SystemExit(f"Target column '{target_col}' not found. Available columns: {list(df.columns)}")

	X = df.drop(columns=[target_col])
	Y = df[target_col].astype(int)
	unique_values = set(Y.dropna().unique().tolist())
	if unique_values <= {-1, 1}:
		Y = Y.map({-1: 0, 1: 1}).astype(int)
	elif unique_values <= {0, 1}:
		Y = Y.astype(int)
	else:
		raise SystemExit(f"Unsupported label values: {sorted(unique_values)}")
	return X, Y


def train_and_compare_models(train_X, train_y, test_X, test_y):
	models = {
		"LogisticRegression": LogisticRegression(max_iter=1000),
		"KNeighborsClassifier": KNeighborsClassifier(n_neighbors=4),
		"XGBClassifier": XGBClassifier(objective="binary:logistic", eval_metric="auc"),
	}

	results = []
	for name, model in models.items():
		model.fit(train_X, train_y)
		pred = model.predict(test_X)
		prob = model.predict_proba(test_X)[:, 1]
		acc = accuracy_score(test_y, pred)
		fpr, tpr, _ = roc_curve(test_y, prob, pos_label=1)
		print(f"[{name}] accuracy={acc:.4f}")
		print(classification_report(test_y, pred))
		print(confusion_matrix(test_y, pred))
		results.append((name, acc, fpr, tpr, model))

	return results


def main():
	warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn.linear_model._logistic")
	warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.linear_model._logistic")

	parser = argparse.ArgumentParser(description="Train models on the Kaggle phishing URL dataset used by cybersecurity.ipynb.")
	parser.add_argument("--data", type=str, default="data/kaggle/book_my_show/dataset.csv")
	parser.add_argument("--target", type=str, default="Result")
	parser.add_argument("--drop-columns", type=str, default="index")
	parser.add_argument("--test-size", type=float, default=0.3)
	parser.add_argument("--random-state", type=int, default=9)
	parser.add_argument("--out", type=str, default="models/phishing_kaggle")
	args = parser.parse_args()

	data_path = Path(args.data)
	if not data_path.exists():
		raise SystemExit(
			f"Data file not found: {data_path}. Download the Kaggle dataset and point --data at dataset.csv."
		)

	X, y = prepare_dataframe(data_path, args.target)
	drop_columns = [col.strip() for col in args.drop_columns.split(",") if col.strip()]
	for column in drop_columns:
		if column in X.columns:
			X = X.drop(columns=[column])

	X_train, X_test, y_train, y_test = train_test_split(
		X,
		y,
		test_size=args.test_size,
		random_state=args.random_state,
		stratify=y,
	)

	scaler = StandardScaler()
	X_train = scaler.fit_transform(X_train)
	X_test = scaler.transform(X_test)

	out_dir = Path(args.out)
	out_dir.mkdir(parents=True, exist_ok=True)
	joblib.dump(scaler, out_dir / "scaler.joblib")
	with open(out_dir / "schema.json", "w", encoding="utf-8") as handle:
		json.dump(
			{
				"target": args.target,
				"drop_columns": drop_columns,
				"features": list(X.columns),
			},
			handle,
			indent=2,
		)

	results = train_and_compare_models(X_train, y_train.values.ravel(), X_test, y_test.values.ravel())
	best_name, best_acc, best_fpr, best_tpr, best_model = max(results, key=lambda item: item[1])
	print(f"Best model: {best_name} with accuracy {best_acc:.4f}")

	if best_name == "XGBClassifier":
		joblib.dump(best_model, out_dir / "best_model.joblib")
	else:
		joblib.dump(best_model, out_dir / f"{best_name}.joblib")

	xgb_cv = XGBClassifier(n_estimators=100, objective="binary:logistic", eval_metric="auc")
	scores = cross_val_score(xgb_cv, X_train, y_train.values.ravel(), cv=10, scoring="accuracy")
	print(f"XGB 10-fold mean={scores.mean():.4f}, std={scores.std():.4f}")

	grid = GridSearchCV(
		estimator=LogisticRegression(max_iter=1000),
		param_grid=[
			{"solver": ["liblinear"], "C": [0.01, 0.1, 1, 10, 100], "penalty": ["l1", "l2"]},
			{"solver": ["newton-cg"], "C": [0.01, 0.1, 1, 10, 100], "penalty": ["l2"]},
		],
		cv=StratifiedKFold(4),
		n_jobs=-1,
		verbose=1,
		scoring="accuracy",
	)
	grid.fit(X_train, y_train.values.ravel())
	print(f"Grid best score={grid.best_score_:.4f}")
	print(f"Grid best params={grid.best_params_}")
	joblib.dump(grid.best_estimator_, out_dir / "logreg_best.joblib")


if __name__ == "__main__":
	main()