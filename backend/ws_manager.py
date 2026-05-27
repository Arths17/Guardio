from ._bridge import load_source

_module = load_source(__name__, "ws_manager.py")
globals().update(_module.__dict__)
