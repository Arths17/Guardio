import base64
import io
import json
import os
import shutil
import zipfile
import sys

# ensure repo root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from backend.main import app

client = TestClient(app)
DEVKEY = {"X-API-Key": "devkey"}


def make_minimal_model_dir(path):
    os.makedirs(path, exist_ok=True)
    # scaler
    scaler = StandardScaler()
    scaler.fit([[0.0], [1.0]])
    joblib.dump(scaler, os.path.join(path, "scaler.joblib"))
    # dummy model
    X = [[0.0], [1.0]]
    y = [0, 1]
    m = LogisticRegression().fit(X, y)
    joblib.dump(m, os.path.join(path, "model.joblib"))
    # schema
    schema = {"target": "Result", "features": ["f1"]}
    with open(os.path.join(path, "schema.json"), "w", encoding="utf-8") as f:
        json.dump(schema, f)


@pytest.mark.order(1)
def test_list_and_current():
    r = client.get("/ai/phishing/models")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data


@pytest.mark.order(2)
def test_upload_select_metadata_delete():
    tmp = "models/test_upload_model"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    # create minimal model dir to zip
    src = "tmp_model_src"
    if os.path.exists(src):
        shutil.rmtree(src)
    make_minimal_model_dir(src)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as z:
        for root, dirs, files in os.walk(src):
            for f in files:
                z.write(os.path.join(root, f), arcname=os.path.join(os.path.relpath(root, src), f))
    b64 = base64.b64encode(mem.getvalue()).decode("ascii")
    # upload
    r = client.post(
        "/ai/phishing/models/upload",
        json={"model_name": "test_upload_model", "zip_base64": b64},
        headers=DEVKEY,
    )
    assert r.status_code == 200
    assert r.json().get("uploaded") == "test_upload_model"
    # metadata
    r2 = client.get("/ai/phishing/models/test_upload_model")
    assert r2.status_code == 200
    md = r2.json()
    assert md["model"] == "test_upload_model"
    assert "schema.json" in md["files"]
    # select
    r3 = client.post("/ai/phishing/models/select", json={"model": "test_upload_model"}, headers=DEVKEY)
    assert r3.status_code == 200
    # delete
    r4 = client.delete("/ai/phishing/models/test_upload_model", headers=DEVKEY)
    assert r4.status_code == 200
    assert r4.json().get("deleted") == "test_upload_model"
    # cleanup
    if os.path.exists(src):
        shutil.rmtree(src)


def test_feature_extraction_endpoint():
    r = client.get('/ai/phishing/features', params={'url': 'http://example.com'})
    assert r.status_code == 200
    data = r.json()
    assert 'features' in data
    assert isinstance(data['features'], dict)
