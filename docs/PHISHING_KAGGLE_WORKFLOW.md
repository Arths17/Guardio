# Kaggle phishing workflow

The downloaded notebook at `cybersecurity.ipynb` trains on the Kaggle dataset `cybersecurity-data` and expects a CSV named `dataset.csv` with a `Result` label column.

## What the notebook does

- Loads `/kaggle/input/cybersecurity-data/dataset.csv`
- Drops the `index` column
- Trains `LogisticRegression`, `KNeighborsClassifier`, and `XGBClassifier`
- Compares accuracy, confusion matrix, ROC curve, and cross-validation scores
- Saves the best XGBoost model with `pickle`

## Local runner

Use the repo script at `model/train_phishing_kaggle.py`.

```bash
source .venv-py311/bin/activate
brew install libomp
python -m pip install -r requirements.txt
python model/train_phishing_kaggle.py --data data/dataset.csv --out models/phishing_kaggle
```

The Kaggle dataset used here is downloaded to `data/kaggle/book_my_show/dataset.csv`.

## Expected data shape

- `Result`: target label
- `index`: optional column to drop
- Remaining columns: numeric URL features, usually 32 in the Kaggle notebook
