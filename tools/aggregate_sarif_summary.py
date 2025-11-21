#!/usr/bin/env python3
"""
Aggregate SARIF findings from multiple tools into a compact summary.
Used for GitHub PR comments.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def count_sarif_levels(sarif_path: Path) -> Tuple[int, int, int]:
    """Returns (errors, warnings, notes) from a SARIF file."""
    if not sarif_path.exists():
        return (0, 0, 0)
    
    try:
        data = json.loads(sarif_path.read_text(encoding="utf-8"))
    except Exception:
        return (0, 0, 0)
    
    levels: Dict[str, int] = {"error": 0, "warning": 0, "note": 0}
    for run in data.get("runs", []):
        for res in run.get("results", []):
            lvl = res.get("level", "note")
            levels[lvl] = levels.get(lvl, 0) + 1
    
    return levels["error"], levels["warning"], levels["note"]


def get_top_issues(sarif_path: Path, limit: int = 3) -> List[str]:
    """Extract top N issues from SARIF for display."""
    if not sarif_path.exists():
        return []
    
    try:
        data = json.loads(sarif_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    
    issues = []
    for run in data.get("runs", []):
        for res in run.get("results", []):
            msg = res.get("message", {}).get("text", "Unknown issue")
            lvl = res.get("level", "note")
            if lvl in ("error", "warning"):
                issues.append(f"  - [{lvl.upper()}] {msg[:80]}")
            if len(issues) >= limit:
                break
        if len(issues) >= limit:
            break
    
    return issues


def main() -> None:
    root = Path(".")
    
    # Find SARIF files
    pip_sarif = root / "pip_audit.sarif"
    npm_sarif = root / "npm_audit.sarif"
    bandit_sarif = root / "bandit_report.sarif"
    
    # Count findings
    pip_counts = count_sarif_levels(pip_sarif)
    npm_counts = count_sarif_levels(npm_sarif)
    bandit_counts = count_sarif_levels(bandit_sarif)
    
    total_errors = pip_counts[0] + npm_counts[0] + bandit_counts[0]
    total_warnings = pip_counts[1] + npm_counts[1] + bandit_counts[1]
    total_notes = pip_counts[2] + npm_counts[2] + bandit_counts[2]
    
    # Build summary
    lines = [
        "## 🔒 Security Scan Summary",
        "",
        f"**Total**: {total_errors} errors, {total_warnings} warnings, {total_notes} notes",
        "",
        "| Tool | Errors | Warnings | Notes |",
        "|------|--------|----------|-------|",
        f"| pip-audit | {pip_counts[0]} | {pip_counts[1]} | {pip_counts[2]} |",
        f"| npm audit | {npm_counts[0]} | {npm_counts[1]} | {npm_counts[2]} |",
        f"| Bandit | {bandit_counts[0]} | {bandit_counts[1]} | {bandit_counts[2]} |",
        "",
    ]
    
    # Add top issues if any critical findings
    if total_errors > 0 or total_warnings > 0:
        lines.append("### 🔴 Top Issues")
        lines.append("")
        
        if pip_counts[0] + pip_counts[1] > 0:
            lines.append("**pip-audit:**")
            lines.extend(get_top_issues(pip_sarif))
            lines.append("")
        
        if npm_counts[0] + npm_counts[1] > 0:
            lines.append("**npm audit:**")
            lines.extend(get_top_issues(npm_sarif))
            lines.append("")
        
        if bandit_counts[0] + bandit_counts[1] > 0:
            lines.append("**Bandit:**")
            lines.extend(get_top_issues(bandit_sarif))
            lines.append("")
    else:
        lines.append("✅ **No critical issues found**")
        lines.append("")
    
    lines.append("*Full details in artifacts: `security-dashboard`, `sarif-bundle`*")
    
    print("\n".join(lines))


if __name__ == "__main__":
    main()
