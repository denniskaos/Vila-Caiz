"""Core package for the Vila-Caiz football club management application."""

from importlib import resources


def _load_version() -> str:
    try:
        return resources.files(__name__).joinpath("VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:  # pragma: no cover - fallback for editable installs
        return "0.0.0"


__version__ = _load_version()

__all__ = [
    "models",
    "storage",
    "services",
    "__version__",
]
