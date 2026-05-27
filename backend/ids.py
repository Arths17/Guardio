from ._bridge import load_source

_module = load_source(__name__, "ids.py")
globals().update(_module.__dict__)
