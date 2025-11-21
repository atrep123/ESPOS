from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def load_config(path: Path, defaults: Dict[str, object]) -> Dict[str, object]:
    cfg = defaults.copy()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
    except Exception:
        # best effort; return defaults on error
        return cfg
    return cfg


def save_config(path: Path, cfg: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
