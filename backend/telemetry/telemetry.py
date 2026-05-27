from src.backend.telemetry.telemetry import *from .._bridge import load_source

_module = load_source(__name__, "telemetry/telemetry.py")
globals().update(_module.__dict__)
