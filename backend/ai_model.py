from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import json
import pandas as pd
import threading


class ModelManager:
    def __init__(self, models_root: Path = Path("models")):
        self.models_root = Path(models_root)
        self.lock = threading.RLock()
        self._available = self._scan_models()
        self._current_name = next(iter(self._available), None)
        self._artifacts = None

    def _scan_models(self) -> Dict[str, Path]:
        res = {}
        if not self.models_root.exists():
            return res
        for p in self.models_root.iterdir():
            if p.is_dir():
                # require scaler.joblib and schema.json
                if (p / "scaler.joblib").exists() and (p / "schema.json").exists():
                    res[p.name] = p
        return res

    def list_models(self) -> List[str]:
        with self.lock:
            self._available = self._scan_models()
            return list(self._available.keys())

    def current_model(self) -> str | None:
        with self.lock:
            return self._current_name

    def load(self, name: str | None = None):
        with self.lock:
            if name is None:
                name = self._current_name
            if name is None:
                raise FileNotFoundError("No model available to load")
            if name not in self._scan_models():
                raise FileNotFoundError(f"Model '{name}' not found under {self.models_root}")
            base = self.models_root / name
            scaler = joblib.load(base / "scaler.joblib")
            # model file may be 'best_model.joblib' or '<name>.joblib' or 'model.joblib'
            model_path = None
            for cand in ("best_model.joblib", "model.joblib", f"{name}.joblib", "logreg_best.joblib"):
                if (base / cand).exists():
                    model_path = base / cand
                    break
            if model_path is None:
                # fallback: first .joblib in dir
                for f in base.iterdir():
                    if f.suffix == ".joblib":
                        model_path = f
                        break
            if model_path is None:
                raise FileNotFoundError("No model file found for %s" % name)
            model = joblib.load(model_path)
            schema = json.loads((base / "schema.json").read_text(encoding="utf-8"))
            self._current_name = name
            self._artifacts = {"base": base, "scaler": scaler, "model": model, "schema": schema}

    def select(self, name: str):
        self.load(name)

    def predict_from_features(self, features: Dict[str, float]) -> Tuple[int, float, List[str], List[str]]:
        with self.lock:
            if not self._artifacts:
                self.load(self._current_name)
            scaler = self._artifacts["scaler"]
            model = self._artifacts["model"]
            meta = self._artifacts["schema"]
            expected = meta.get("features", [])
            missing = [c for c in expected if c not in features]
            extra = [c for c in features.keys() if c not in expected]
            fv = [float(features.get(c, 0.0)) for c in expected]
            # build a DataFrame with expected column names so StandardScaler
            # and downstream estimators preserve feature-name semantics
            df = pd.DataFrame([fv], columns=expected)
            Xs = scaler.transform(df)
            prob = float(model.predict_proba(Xs)[0, 1])
            pred = int(prob >= 0.5)
            return pred, prob, missing, extra

    def predict_from_url_heuristic(self, url: str) -> Tuple[int, float, List[str], List[str]]:
        return self.predict_from_features(self.extract_features_from_url(url))

    def extract_features_from_url(self, url: str, fetch_page: bool = False) -> Dict[str, float]:
        """Deterministically extract feature values from a URL to match model schema.

        If `fetch_page` is True, the extractor may attempt to fetch the page to compute
        additional signals; defaults to False to avoid network calls during tests.
        """
        from urllib.parse import urlparse
        import socket

        parsed = urlparse(url)

        # ensure schema is loaded
        try:
            if not self._artifacts:
                self.load(self._current_name)
        except Exception:
            pass
        features = {}
        if self._artifacts:
            expected = self._artifacts["schema"].get("features", [])
        else:
            expected = [
                "having_IPhaving_IP_Address",
                "URLURL_Length",
                "Shortining_Service",
            ]

        for feat in expected:
            features[feat] = 0

        netloc = parsed.netloc or ""
        hostname = netloc.split(":")[0]

        # IP address in hostname
        try:
            socket.inet_aton(hostname)
            features["having_IPhaving_IP_Address"] = 1
        except Exception:
            features["having_IPhaving_IP_Address"] = 0

        features["URLURL_Length"] = len(url)
        shorteners = ["bit.ly", "tinyurl", "t.co", "goo.gl", "ow.ly", "bitly.com"]
        features["Shortining_Service"] = 1 if any(s in url for s in shorteners) else 0
        features["having_At_Symbol"] = 1 if "@" in url else 0
        proto_idx = url.find("//")
        features["double_slash_redirecting"] = 1 if url.find("//", proto_idx + 2) != -1 else 0
        features["Prefix_Suffix"] = 1 if "-" in hostname else 0
        features["having_Sub_Domain"] = 1 if hostname.count(".") > 1 else 0
        features["SSLfinal_State"] = 1 if parsed.scheme == "https" else 0
        features["port"] = 1 if (":" in netloc and not netloc.endswith(":80") and not netloc.endswith(":443")) else 0
        features["HTTPS_token"] = 1 if "https" in hostname.lower() or "https" in parsed.path.lower() else 0

        # DNS record existence
        try:
            socket.gethostbyname(hostname)
            features["DNSRecord"] = 1
        except Exception:
            features["DNSRecord"] = 0

        # If fetch_page is requested, attempt to get a few signals (timeouts applied by caller if needed)
        if fetch_page:
            try:
                import requests

                resp = requests.get(url, timeout=3)
                html = resp.text
                # simple heuristics
                features["Favicon"] = 1 if "favicon" in html.lower() else features.get("Favicon", 0)
                features["Links_in_tags"] = html.count("<a ")
            except Exception:
                pass

        return features


# module-level manager
_MANAGER = ModelManager()


def list_models() -> List[str]:
    return _MANAGER.list_models()


def select_model(name: str):
    return _MANAGER.select(name)


def current_model() -> str | None:
    return _MANAGER.current_model()


def predict_from_features(features: Dict[str, float]):
    return _MANAGER.predict_from_features(features)


def predict_from_url_heuristic(url: str):
    return _MANAGER.predict_from_url_heuristic(url)

