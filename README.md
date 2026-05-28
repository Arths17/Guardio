# Guardio — Backend

<!-- cspell:ignore Guardio guardio devkey GUARDIO venv uvicorn wscat Cytoscape pytest -->

[![CI](https://github.com/Arths17/Guardio/actions/workflows/ci.yml/badge.svg)](https://github.com/Arths17/Guardio/actions/workflows/ci.yml)

Guardio is a FastAPI-based prototype backend that simulates network traffic,
attacks and IDS/defense behavior for demos, education and local experimentation.
It provides a WebSocket event stream for a visualization frontend, REST
controls to operate the simulator, and an experimental ML model integration
for tabular cyber-classification workloads.

**Quick Links**
- **API entrypoint:** [backend/main.py](backend/main.py)
- **Simulator:** [backend/simulation.py](backend/simulation.py)
- **Model training:** [model/train_cyber.py](model/train_cyber.py)
- **Tests:** [tests/](tests/)

**Local Quickstart**

- Create and activate a Python 3.11 virtual environment (recommended for
  PyTorch compatibility):

```bash
python3.11 -m venv .venv-py311
source .venv-py311/bin/activate
pip install -r requirements.txt
```

- Run the server (development):

```bash
uvicorn backend.main:app --reload --port 8000
```

- Example control requests (use header `X-API-Key: devkey`):

```bash
# start simulation
curl -X POST -H "X-API-Key: devkey" http://127.0.0.1:8000/start

# block a host
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: devkey" \
  -d '{"host":"host-1"}' http://127.0.0.1:8000/defense/firewall/block

# connect to websocket (wscat example)
wscat -c ws://127.0.0.1:8000/ws?api_key=devkey
```

**Train the tabular cyber model**

The repository includes a small PyTorch MLP trainer for tabular datasets at
[model/train_cyber.py](model/train_cyber.py). Example usage:

```bash
# activate .venv-py311 first
python model/train_cyber.py --data data/cyber.csv --epochs 10 --out models
```

This writes the following artifacts to the `models/` directory:
- `cyber_model.pt` — PyTorch model state_dict
- `preprocessor.joblib` — preprocessing (imputer/scaler/encoders)
- `label_encoder.joblib` — label encoder
- `feature_schema.json` — feature schema used for preprocessing

**Model management & inference (API)**

The FastAPI app exposes endpoints to list, upload, select, and delete models
under `/ai/phishing/models` and to score URLs/features at `/ai/phishing/score`.
Uploads are accepted as a base64-encoded ZIP (use the upload endpoint or
create a model directory manually under `models/`). See [backend/main.py](backend/main.py)
and [backend/ai_model.py](backend/ai_model.py) for implementation details.

**Run tests**

Run the test suite inside the `python3.11` venv:

```bash
source .venv-py311/bin/activate
pytest -q
```

Current test status in this workspace: `37 passed, 3 warnings` (local run).

**Compatibility notes**

- PyTorch wheels are sensitive to Python and numpy versions — we recommend
  using the supplied `.venv-py311` (Python 3.11) when working with `torch`.
- On macOS, `xgboost` may require `libomp` from Homebrew (`brew install libomp`) and
  setting `DYLD_LIBRARY_PATH` when running locally.
- If you see warnings like "StandardScaler was fitted with feature names",
  ensure you pass a `pandas.DataFrame` with the expected column names to the
  scaler (the repo's code follows a schema-driven transform to avoid this).

**Development tips**

- Use `GUARDIO_API_KEY` to change the API key in non-development setups.
- Inspect `models/` for trained artifacts and `data/` for sample datasets.
- To add a model in CI scripts, create `models/<name>/` with the expected
  artifacts (`preprocessor.joblib`, `label_encoder.joblib`, `feature_schema.json`, and a model file) and call the upload/select endpoints.

**Contributing & next steps**

- Improve feature extraction for URL-based models (WHOIS, page content,
  favicon checks), add persistent model-selection state, and expand CI to
  cover GPU/CPU inference paths if needed.

If you'd like, I can also add a short `docs/README_MODEL.md` with sample
inference scripts and a small packaging helper to produce uploadable zip files.
