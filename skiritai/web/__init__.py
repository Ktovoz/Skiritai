"""Skiritai web module — optional FastAPI-based REST + WebSocket server.

Requires: pip install skiritai[web]
"""
try:
    import fastapi  # noqa: F401
except ImportError:
    raise ImportError(
        "Skiritai web module requires FastAPI. "
        "Install with: pip install skiritai[web]"
    )
