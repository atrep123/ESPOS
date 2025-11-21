#!/usr/bin/env python3
"""Evaluate disallowed licenses in collected license JSON files.
Outputs:
  license_bad_python.txt
  license_bad_node.txt
"""
import json
import logging
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def evaluate(disallowed: set[str], root: pathlib.Path = ROOT) -> tuple[set[str], set[str]]:
    py_file = root / 'python' / 'python_licenses.json'
    node_file = root / 'node' / 'node_licenses.json'
    py_bad: set[str] = set()
    node_bad: set[str] = set()

    if py_file.exists():
        try:
            data = json.loads(py_file.read_text(encoding='utf-8'))
            for pkg in data:
                lic = (pkg.get('license') or '').strip()
                if any(dl in lic for dl in disallowed):
                    py_bad.add(lic)
        except Exception as exc:
            logging.warning("Failed to parse %s: %s", py_file, exc)

    if node_file.exists():
        try:
            data = json.loads(node_file.read_text(encoding='utf-8'))
            for _pkg, meta in data.items():
                if isinstance(meta, dict):
                    lic = (meta.get('licenses') or '').strip()
                    if any(dl in lic for dl in disallowed):
                        node_bad.add(lic)
        except Exception as exc:
            logging.warning("Failed to parse %s: %s", node_file, exc)

    return py_bad, node_bad


if __name__ == '__main__':
    disallowed_arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DISALLOWED_LICENSES','')
    DISALLOWED = {d.strip() for d in disallowed_arg.replace(',', ' ').split() if d.strip()}
    py_bad, node_bad = evaluate(DISALLOWED)

    py_out = ROOT / 'license_bad_python.txt'
    node_out = ROOT / 'license_bad_node.txt'
    py_out.write_text(','.join(sorted(py_bad)), encoding='utf-8')
    node_out.write_text(','.join(sorted(node_bad)), encoding='utf-8')
    logging.info("Python disallowed: %s", ','.join(sorted(py_bad)) or 'NONE')
    logging.info("Node disallowed: %s", ','.join(sorted(node_bad)) or 'NONE')
