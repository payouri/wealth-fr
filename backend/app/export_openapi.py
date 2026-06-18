"""Write the FastAPI-emitted OpenAPI schema to the committed `openapi.json`.

`openapi.json` is the **cross-job interface** of the backend-canonical contract
(ADR 0005, issue #17): the Pydantic models in `models.py` are the single source of
truth, FastAPI emits them as OpenAPI here, and `frontend/src/api/types.ts` is
generated from this file by `openapi-typescript`. It lives at the **repo root** so
the pure-Node frontend CI job can read it without touching the Python toolchain.

Run via `python -m app.export_openapi` (from `backend/`, where `app` is importable),
or `pnpm gen:contract` from the repo root, which does this then regenerates the TS.
CI's `git diff --exit-code` on the committed `openapi.json` is what gates drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from .main import app

# Repo root is two levels up from this file (backend/app/export_openapi.py).
OUTPUT = Path(__file__).resolve().parents[2] / "openapi.json"


def main() -> None:
    schema = app.openapi()
    # Trailing newline + sorted keys keep the committed artifact stable and
    # diff-friendly so the CI freshness gate only fires on a real contract change.
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
