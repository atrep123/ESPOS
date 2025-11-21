#!/usr/bin/env python3
"""Merge Python and Node SBOM CycloneDX JSON files into a unified document.
Produces sbom-unified.json with top-level keys: python, node.
"""
from pathlib import Path
import json
import logging

ROOT = Path(__file__).resolve().parent.parent
PY_SBOM = ROOT / 'sbom-python.json'
NODE_SBOM = ROOT / 'sbom-node.json'
OUT = ROOT / 'sbom-unified.json'

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def load(path: Path):
    if not path.exists():
        logging.warning("SBOM file missing: %s", path)
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        logging.error("Failed to read %s: %s", path, e)
        return None

py_data = load(PY_SBOM) or {}
node_data = load(NODE_SBOM) or {}

combined = {
    'schema': 'cyclonedx-unified-v1',
    'python': py_data,
    'node': node_data,
    'generated_by': 'unify_sbom.py',
}

OUT.write_text(json.dumps(combined, indent=2), encoding='utf-8')
logging.info("Unified SBOM written: %s", OUT)
