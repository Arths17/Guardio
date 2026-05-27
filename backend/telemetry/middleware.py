from .._bridge import load_source

_module = load_source(__name__, "telemetry/middleware.py")
globals().update(_module.__dict__)

