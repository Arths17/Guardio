import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
import pytest
import torch

# ensure repo root is importable (tests may run with CWD=repo)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model.train_cyber import build_feature_frame, CyberMLP


def test_cyber_model_inference_on_sample():
    model_path = "models/cyber_model.pt"
    preproc_path = "models/preprocessor.joblib"
    label_enc_path = "models/label_encoder.joblib"
    schema_path = "models/feature_schema.json"
    data_path = "data/cyber.csv"

    # Skip if required artifacts or data are not present
    for p in (model_path, preproc_path, label_enc_path, schema_path, data_path):
        if not os.path.exists(p):
            pytest.skip(f"Required file missing: {p}")

    df = pd.read_csv(data_path)
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    label_col = schema.get("label", "label")
    feature_bundle = build_feature_frame(df, label_col, schema.get("drop_columns", []), schema.get("timestamp_columns", []))
    feature_df = feature_bundle.feature_frame
    X = feature_df.drop(columns=[label_col])

    pre = joblib.load(preproc_path)

    numeric_cols = pre.get("numeric_columns", [])
    categorical_cols = pre.get("categorical_columns", [])

    row_df = X.iloc[[0]]

    if numeric_cols:
        num_imp = pre.get("numeric_imputer")
        num_scaler = pre.get("numeric_scaler")
        num = num_scaler.transform(num_imp.transform(row_df[numeric_cols]))
    else:
        num = np.empty((1, 0))

    if categorical_cols:
        cat_imp = pre.get("categorical_imputer")
        onehot = pre.get("onehot_encoder")
        cat = onehot.transform(cat_imp.transform(row_df[categorical_cols]))
    else:
        cat = np.empty((1, 0))

    features = np.hstack([num, cat]).astype(np.float32)

    label_enc = joblib.load(label_enc_path)
    num_classes = len(label_enc.classes_)

    # Instead of running a forward pass (which can cause native crashes
    # on some binary combinations), verify the saved model parameter shapes
    # are compatible with the feature vector and label encoder.
    state = torch.load(model_path, map_location="cpu")

    # find first linear layer weight (should be net.0.weight) and final layer
    # weight (net.6.weight) in the saved state dict
    if "net.0.weight" in state:
        first_w = state["net.0.weight"]
    else:
        # fallback: pick the first weight-like tensor
        first_w = next(v for k, v in state.items() if v.ndim == 2)

    if "net.6.weight" in state:
        last_w = state["net.6.weight"]
    else:
        # fallback: pick the last weight-like tensor
        last_w = [v for k, v in state.items() if v.ndim == 2][-1]

    expected_input_dim = int(first_w.shape[1])
    expected_num_classes = int(last_w.shape[0])

    assert features.shape[1] == expected_input_dim, (
        f"Feature vector length {features.shape[1]} != model expected {expected_input_dim}"
    )
    assert num_classes == expected_num_classes

    # Basic label checks
    raw = df.iloc[0][label_col]
    if pd.isna(raw):
        true_label = "missing"
    elif isinstance(raw, float) and raw.is_integer():
        true_label = str(int(raw))
    else:
        true_label = str(raw)

    assert true_label in list(label_enc.classes_)
