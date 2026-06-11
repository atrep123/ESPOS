from __future__ import annotations

import argparse
import re
from pathlib import Path

USE_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>[^\s#]+)(?P<rest>.*)$")
FULL_SHA_RE = re.compile(r"@[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"#\s*v\d+(?:\.\d+){0,2}\b")
AUDIT_TOOL_INSTALL_RE = re.compile(
    r"\b(?:python\s+-m\s+)?pip\s+install\b(?![^\n]*\s-r\b)[^\n#]*"
    r"(?:^|[\s\"'])(pip-audit|bandit|safety|cyclonedx-bom|pip-licenses)"
    r"(?:[<>=\s\"']|$)",
    re.IGNORECASE,
)
PIP_AUDIT_REQUIREMENT_RE = re.compile(r"^\s*pip-audit\b", re.MULTILINE)
DEPENDABOT_UPDATE_RE = re.compile(r"^\s*-\s+package-ecosystem:\s*(?P<ecosystem>.+?)\s*$")
WRITE_PERMISSION_RE = re.compile(r"^\s*[a-z-]+:\s*write\s*(?:#.*)?$", re.IGNORECASE)


def _has_top_level_contents_read_permission(text: str) -> bool:
    in_permissions = False
    for line in text.splitlines():
        if re.match(r"^permissions:\s*(?:#.*)?$", line):
            in_permissions = True
            continue
        if not in_permissions:
            continue
        if line and not line.startswith((" ", "\t")):
            return False
        if re.match(r"^\s+contents:\s*read\s*(?:#.*)?$", line):
            return True
    return False


def validate_workflow_text(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    if not _has_top_level_contents_read_permission(text):
        issues.append(f"{path}: workflow must declare top-level permissions: contents: read")

    for line_no, line in enumerate(text.splitlines(), start=1):
        if WRITE_PERMISSION_RE.match(line):
            issues.append(f"{path}:{line_no}: workflow must not grant write permission")

        uses_match = USE_RE.match(line)
        if uses_match:
            ref = uses_match.group("ref")
            if ref.startswith("./"):
                continue
            if not FULL_SHA_RE.search(ref):
                issues.append(
                    f"{path}:{line_no}: action reference {ref!r} is not pinned to a full commit SHA"
                )
            elif not VERSION_COMMENT_RE.search(uses_match.group("rest")):
                issues.append(
                    f"{path}:{line_no}: action reference {ref!r} is missing inline version comment"
                )

        install_match = AUDIT_TOOL_INSTALL_RE.search(line)
        if install_match:
            tool = install_match.group(1)
            issues.append(
                f"{path}:{line_no}: install audit tooling from requirements-dev.txt, not ad hoc ({tool})"
            )
    return issues


def validate_requirements(text: str) -> list[str]:
    if PIP_AUDIT_REQUIREMENT_RE.search(text):
        return []
    return ["requirements-dev.txt: pip-audit must be declared in the dev dependency manifest"]


def _clean_yaml_scalar(value: str) -> str:
    return value.strip().strip("\"'")


def _dependabot_update_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current_ecosystem: str | None = None
    for line in text.splitlines():
        update_match = DEPENDABOT_UPDATE_RE.match(line)
        if update_match:
            current_ecosystem = _clean_yaml_scalar(update_match.group("ecosystem"))
            blocks[current_ecosystem] = [line]
        elif current_ecosystem is not None:
            blocks[current_ecosystem].append(line)
    return {ecosystem: "\n".join(lines) for ecosystem, lines in blocks.items()}


def _has_yaml_value(text: str, key: str, value: str) -> bool:
    return bool(
        re.search(
            rf"(?m)^\s*(?:-\s*)?{re.escape(key)}:\s*[\"']?{re.escape(value)}[\"']?\s*$",
            text,
        )
    )


def _validate_dependabot_update(
    path: Path,
    ecosystem: str,
    block: str | None,
    *,
    expected_time: str,
    expected_limit: str,
    expected_prefix: str,
) -> list[str]:
    if block is None:
        return [f"{path}: missing {ecosystem} Dependabot update block"]

    checks = [
        ("directory", "/"),
        ("interval", "weekly"),
        ("day", "monday"),
        ("time", expected_time),
        ("timezone", "Europe/Prague"),
        ("open-pull-requests-limit", expected_limit),
        ("prefix", expected_prefix),
        ("include", "scope"),
    ]
    issues = [
        f"{path}: {ecosystem} schedule/metadata must include {key}: {value}"
        for key, value in checks
        if not _has_yaml_value(block, key, value)
    ]
    if ecosystem == "pip" and not _has_yaml_value(block, "dependency-type", "direct"):
        issues.append(f"{path}: pip updates must be limited to direct dependencies")
    if ecosystem == "github-actions" and not re.search(
        r"(?ms)^\s*groups:\s*$.*^\s*github-actions:\s*$.*^\s*-\s*[\"']?\*[\"']?\s*$",
        block,
    ):
        issues.append(f"{path}: github-actions updates must define groups.github-actions")
    return issues


def validate_dependabot_text(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    if not _has_yaml_value(text, "version", "2"):
        issues.append(f"{path}: Dependabot config must use version: 2")

    blocks = _dependabot_update_blocks(text)
    issues.extend(
        _validate_dependabot_update(
            path,
            "pip",
            blocks.get("pip"),
            expected_time="06:00",
            expected_limit="5",
            expected_prefix="deps",
        )
    )
    issues.extend(
        _validate_dependabot_update(
            path,
            "github-actions",
            blocks.get("github-actions"),
            expected_time="06:30",
            expected_limit="3",
            expected_prefix="ci",
        )
    )
    return issues


def collect_issues(root: Path) -> list[str]:
    issues: list[str] = []
    workflows_dir = root / ".github" / "workflows"
    for pattern in ("*.yml", "*.yaml"):
        for workflow in sorted(workflows_dir.glob(pattern)):
            issues.extend(validate_workflow_text(workflow, workflow.read_text(encoding="utf-8")))

    requirements_dev = root / "requirements-dev.txt"
    if requirements_dev.exists():
        issues.extend(validate_requirements(requirements_dev.read_text(encoding="utf-8")))
    else:
        issues.append("requirements-dev.txt: missing dev dependency manifest")

    dependabot = root / ".github" / "dependabot.yml"
    if dependabot.exists():
        issues.extend(validate_dependabot_text(dependabot, dependabot.read_text(encoding="utf-8")))
    else:
        issues.append(".github/dependabot.yml: missing Dependabot configuration")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check CI supply-chain guardrails.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root to scan.")
    args = parser.parse_args(argv)

    issues = collect_issues(args.root)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print("[OK] supply-chain guardrails")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
