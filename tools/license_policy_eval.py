#!/usr/bin/env python3
"""Evaluate disallowed licenses in collected license JSON files.
Outputs:
  license_bad_python.txt
  license_bad_node.txt
"""
import json, os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
DISALLOWED = {d.strip() for d in (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DISALLOWED_LICENSES','')).replace(',', ' ').split() if d.strip()}
py_out = ROOT / 'license_bad_python.txt'
node_out = ROOT / 'license_bad_node.txt'
py_file = ROOT / 'python' / 'python_licenses.json'
node_file = ROOT / 'node' / 'node_licenses.json'
py_bad = set()
if py_file.exists():
    try:
        data = json.loads(py_file.read_text(encoding='utf-8'))
        for pkg in data:
            lic = (pkg.get('license') or '').strip()
            if any(dl in lic for dl in DISALLOWED):
                py_bad.add(lic)
    except Exception:
        pass
node_bad = set()
if node_file.exists():
    try:
        data = json.loads(node_file.read_text(encoding='utf-8'))
        for k,v in data.items():
            if isinstance(v, dict):
                lic = (v.get('licenses') or '').strip()
                if any(dl in lic for dl in DISALLOWED):
                    node_bad.add(lic)
    except Exception:
        pass
py_out.write_text(','.join(sorted(py_bad)), encoding='utf-8')
node_out.write_text(','.join(sorted(node_bad)), encoding='utf-8')
print(f"Python disallowed: {','.join(sorted(py_bad)) or 'NONE'}")
print(f"Node disallowed: {','.join(sorted(node_bad)) or 'NONE'}")
