"""Backward-compatible module alias for `python -m pipeline.validate_cmd`."""
from .validate_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
