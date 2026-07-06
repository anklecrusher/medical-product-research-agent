"""Small JSON persistence helpers for workflow intermediate artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


def write_model_json(path: Path | str, items: BaseModel | Iterable[BaseModel]) -> Path:
    """Write one model or a list of models as UTF-8 JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(items, BaseModel):
        payload = items.model_dump(mode="json")
    else:
        payload = [item.model_dump(mode="json") for item in items]
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
