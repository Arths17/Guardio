from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_source(module_name: str, relative_path: str) -> ModuleType:
    source_path = (
        Path(__file__).resolve().parents[1] / "src" / "backend" / relative_path
    )
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {module_name} from {source_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
