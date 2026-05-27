from ._bridge import load_source

_module = load_source(__name__, "ai_client.py")
globals().update(_module.__dict__)
