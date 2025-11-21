#!/usr/bin/env python3
"""
Generate a simple Markdown dashboard summarizing security artifacts.
Outputs:
- reports/security_dashboard.md with a consistent table-driven summary
- optional plain-text summary file for PR comments
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def summarize_json_count(path: Optional[Path]) -> int:
    if not path or not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(data.get("results", data))
    return 0


def count_sarif(path: Optional[Path]) -> Optional[Tuple[int, int, int]]:
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    levels: Dict[str, int] = {"error": 0, "warning": 0, "note": 0}
    for run in data.get("runs", []):
        for res in run.get("results", []):
            lvl = res.get("level", "note")
            levels[lvl] = levels.get(lvl, 0) + 1
    return levels["error"], levels["warning"], levels["note"]


def count_safety(path: Optional[Path]) -> Optional[int]:
    if not path or not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    return sum(1 for line in lines if "Vulnerability ID" in line or "affected" in line.lower())


def count_components(path: Optional[Path]) -> Optional[int]:
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict):
        if "components" in data and isinstance(data["components"], list):
            return len(data["components"])
        if "bom" in data and isinstance(data["bom"], dict) and isinstance(data["bom"].get("components"), list):
            return len(data["bom"]["components"])
    return None


def format_sarif_row(name: str, counts: Optional[Tuple[int, int, int]]) -> str:
    if counts is None:
        return f"| {name} | n/a | n/a | n/a |"
    err, warn, note = counts
    return f"| {name} | {err} | {warn} | {note} |"


def build_dashboard(out_path: Path, summary_path: Optional[Path] = None) -> str:
    root = Path(".")
    py_vulns = first_existing([root / "python_vulns.json", root / "python" / "python_vulns.json"])
    npm_vulns = first_existing([root / "npm_vulns.json", root / "node" / "npm_vulns.json"])
    npm_sarif = first_existing([root / "npm_audit.sarif", root / "node" / "npm_audit.sarif"])
    pip_sarif = first_existing([root / "pip_audit.sarif", root / "python" / "pip_audit.sarif"])
    bandit_sarif = first_existing([root / "bandit_report.sarif", root / "python" / "bandit_report.sarif"])
    bandit_report = first_existing([root / "bandit_report.json", root / "python" / "bandit_report.json"])
    python_license_bad = first_existing([root / "license_bad_python.txt", root / "python" / "license_bad_python.txt"])
    node_license_bad = first_existing([root / "license_bad_node.txt", root / "node" / "license_bad_node.txt"])
    safety_report = first_existing([root / "safety_report.txt", root / "python" / "safety_report.txt"])
    sbom_python = first_existing([root / "sbom-python.json", root / "python" / "sbom-python.json"])
    sbom_node = first_existing([root / "sbom-node.json", root / "node" / "sbom-node.json"])
    sbom_unified = root / "sbom-unified.json"
    codeql_sarif = next((p for p in root.glob("**/*codeql*.sarif")), None)

    dashboard = ["# Security Dashboard", ""]
    dashboard.append("## SARIF Findings (errors/warnings/notes)")
    dashboard.append("| Tool | Errors | Warnings | Notes |")
    dashboard.append("| --- | --- | --- | --- |")
    dashboard.append(format_sarif_row("pip-audit", count_sarif(pip_sarif)))
    dashboard.append(format_sarif_row("npm audit", count_sarif(npm_sarif)))
    dashboard.append(format_sarif_row("Bandit", count_sarif(bandit_sarif)))
    dashboard.append(format_sarif_row("CodeQL", count_sarif(codeql_sarif)))
    dashboard.append("")

    dashboard.append("## Safety & Licenses")
    safety_count = count_safety(safety_report)
    dashboard.append(f"- Safety findings: {safety_count if safety_count is not None else 'n/a'} (report present: {bool(safety_report)})")
    dashboard.append(f"- Disallowed Python licenses: {python_license_bad.read_text().strip() if python_license_bad else 'NONE'}")
    dashboard.append(f"- Disallowed Node licenses: {node_license_bad.read_text().strip() if node_license_bad else 'NONE'}")
    dashboard.append("")

    dashboard.append("## SBOM Components")
    py_components = count_components(sbom_python)
    node_components = count_components(sbom_node)
    unified_components = count_components(sbom_unified) if sbom_unified.exists() else None
    delta = None
    if unified_components is not None and py_components is not None and node_components is not None:
        delta = unified_components - (py_components + node_components)
    dashboard.append(f"- Python SBOM components: {py_components if py_components is not None else 'n/a'}")
    dashboard.append(f"- Node SBOM components: {node_components if node_components is not None else 'n/a'}")
    dashboard.append(f"- Unified SBOM components: {unified_components if unified_components is not None else 'n/a'}"
                     + ("" if delta is None else f" (delta vs sum: {delta})"))
    dashboard.append("")

    dashboard.append("## Artifact Presence")
    dashboard.append(f"- Python vulnerabilities JSON present: {bool(py_vulns)}")
    dashboard.append(f"- Node npm audit JSON present: {bool(npm_vulns)}")
    dashboard.append(f"- npm audit SARIF present: {bool(npm_sarif)}")
    dashboard.append(f"- Bandit findings (JSON count): {summarize_json_count(bandit_report)}")
    dashboard.append(f"- CodeQL SARIF present: {bool(codeql_sarif)}")
    dashboard.append(f"- Safety report present: {bool(safety_report)}")
    dashboard.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(dashboard), encoding="utf-8")
    logging.info("Security dashboard written to %s", out_path)

    def fmt(counts: Optional[Tuple[int, int, int]]) -> str:
        return "n/a" if counts is None else f"{counts[0]}/{counts[1]}/{counts[2]}"

    summary_lines = [
        "### Security Audit Summary",
        f"- pip-audit (err/warn/note): {fmt(count_sarif(pip_sarif))}",
        f"- npm audit (err/warn/note): {fmt(count_sarif(npm_sarif))}",
        f"- Bandit (err/warn/note): {fmt(count_sarif(bandit_sarif))}",
        f"- CodeQL (err/warn/note): {fmt(count_sarif(codeql_sarif))}",
        f"- Safety findings: {safety_count if safety_count is not None else 'n/a'}",
        f"- SBOM components (py/node/unified): {(py_components, node_components, unified_components)}"
          + ("" if delta is None else f" (delta {delta:+d})"),
        f"- Disallowed licenses (py/node): "
        f"{python_license_bad.read_text().strip() if python_license_bad else 'NONE'} / "
        f"{node_license_bad.read_text().strip() if node_license_bad else 'NONE'}",
        "Artifacts: reports/security_dashboard.md, sarif-bundle (pip_audit, npm_audit, bandit), sbom-unified.json",
    ]
    summary = "\n".join(summary_lines)
    if summary_path:
        summary_path.write_text(summary, encoding="utf-8")
        logging.info("Summary written to %s", summary_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate security dashboard and summary.")
    parser.add_argument("--dashboard", type=Path, default=Path("reports/security_dashboard.md"))
    parser.add_argument("--summary-file", type=Path, help="Optional path to write a short summary (for PR comments).")
    args = parser.parse_args()
    build_dashboard(args.dashboard, args.summary_file)


if __name__ == "__main__":
    main()
