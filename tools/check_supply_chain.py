from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

USE_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>[^\s#]+)(?P<rest>.*)$")
FULL_SHA_RE = re.compile(r"@[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"#\s*v\d+(?:\.\d+){0,2}\b")
PIP_INSTALL_RE = re.compile(r"\b(?:python\s+-m\s+)?pip\s+install\b(?P<args>[^\n#]*)", re.IGNORECASE)
AUDIT_TOOL_INSTALL_RE = re.compile(
    r"\b(?:python\s+-m\s+)?pip\s+install\b(?![^\n]*\s-r\b)[^\n#]*"
    r"(?:^|[\s\"'])(pip-audit|bandit|safety|cyclonedx-bom|pip-licenses)"
    r"(?:[<>=\s\"']|$)",
    re.IGNORECASE,
)
PIP_AUDIT_REQUIREMENT_RE = re.compile(r"^\s*pip-audit\b", re.MULTILINE)
DEPENDABOT_UPDATE_RE = re.compile(r"^\s*-\s+package-ecosystem:\s*(?P<ecosystem>.+?)\s*$")
WRITE_PERMISSION_RE = re.compile(r"^\s*[a-z-]+:\s*write\s*(?:#.*)?$", re.IGNORECASE)
JOB_HEADER_RE = re.compile(r"^  (?P<job>[A-Za-z0-9_-]+):\s*(?:#.*)?$")
RUNS_ON_RE = re.compile(r"^    runs-on:\s*.+$")
JOB_TIMEOUT_RE = re.compile(r"^    timeout-minutes:\s*(?P<value>\S+)\s*(?:#.*)?$")
STEP_NAME_RE = re.compile(r"^\s*-\s+name:\s*(?P<name>.+?)\s*(?:#.*)?$")
CONTINUE_ON_ERROR_TRUE_RE = re.compile(
    r"^\s*continue-on-error:\s*true\s*(?:#.*)?$",
    re.IGNORECASE,
)
IGNORED_FAILURE_RE = re.compile(r"\|\|\s*true(?:\s*(?:#.*)?)?$")
SECURITY_STEP_NAME_RE = re.compile(r"\bsecurity audit\b|\bsupply-chain guard\b", re.IGNORECASE)
SECRET_REFERENCE_RE = re.compile(r"\${{\s*secrets\.", re.IGNORECASE)
CHECKOUT_ACTION_RE = re.compile(r"^actions/checkout@[0-9a-f]{40}$", re.IGNORECASE)
PERSIST_CREDENTIALS_FALSE_RE = re.compile(
    r"^\s*persist-credentials:\s*false\s*(?:#.*)?$",
    re.IGNORECASE,
)
DOWNLOAD_EXECUTE_RE = re.compile(
    r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sh|bash)\b"
    r"|\b(?:irm|iwr|invoke-restmethod|invoke-webrequest)\b[^\n|]*\|\s*(?:iex|invoke-expression)\b",
    re.IGNORECASE,
)
PULL_REQUEST_TARGET_RE = re.compile(r"\bpull_request_target\b")
WORKFLOW_RUN_RE = re.compile(r"\bworkflow_run\b")
PIP_REQUIREMENT_OPTIONS = {"-r", "--requirement"}
PIP_OPTIONS_WITH_VALUE = PIP_REQUIREMENT_OPTIONS | {
    "-c",
    "-C",
    "--abi",
    "--cache-dir",
    "--cert",
    "--client-cert",
    "--config-settings",
    "--constraint",
    "--extra-index-url",
    "--find-links",
    "--implementation",
    "--index-url",
    "--platform",
    "--prefix",
    "--python-version",
    "--root",
    "--src",
    "--target",
    "--trusted-host",
    "--upgrade-strategy",
}


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


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _step_indent_for_uses(lines: list[str], uses_index: int) -> int:
    uses_line = lines[uses_index]
    uses_indent = _leading_spaces(uses_line)
    if uses_line.lstrip().startswith("- "):
        return uses_indent

    for previous in reversed(lines[:uses_index]):
        previous_indent = _leading_spaces(previous)
        if previous_indent < uses_indent and previous.lstrip().startswith("- "):
            return previous_indent
    return max(0, uses_indent - 2)


def _step_block_after_uses(lines: list[str], uses_index: int) -> list[str]:
    step_indent = _step_indent_for_uses(lines, uses_index)
    block: list[str] = []
    for line in lines[uses_index + 1 :]:
        if line.strip() and _leading_spaces(line) <= step_indent:
            break
        block.append(line)
    return block


def _job_blocks(lines: list[str]) -> list[tuple[int, str, list[str]]]:
    blocks: list[tuple[int, str, list[str]]] = []
    in_jobs = False
    current_start = 0
    current_name = ""
    current_block: list[str] = []

    for line_no, line in enumerate(lines, start=1):
        if re.match(r"^jobs:\s*(?:#.*)?$", line):
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith((" ", "\t")):
            break
        if not in_jobs:
            continue

        job_match = JOB_HEADER_RE.match(line)
        if job_match:
            if current_name:
                blocks.append((current_start, current_name, current_block))
            current_start = line_no
            current_name = job_match.group("job")
            current_block = [line]
        elif current_name:
            current_block.append(line)

    if current_name:
        blocks.append((current_start, current_name, current_block))
    return blocks


def _validate_job_timeouts(path: Path, lines: list[str]) -> list[str]:
    issues: list[str] = []
    for line_no, job_name, block in _job_blocks(lines):
        if not any(RUNS_ON_RE.match(line) for line in block):
            continue

        timeout_values = [
            timeout_match.group("value")
            for line in block
            if (timeout_match := JOB_TIMEOUT_RE.match(line))
        ]
        if not timeout_values:
            issues.append(f"{path}:{line_no}: job {job_name!r} must set timeout-minutes")
            continue

        timeout_value = _clean_yaml_scalar(timeout_values[-1])
        if not timeout_value.isdecimal() or int(timeout_value) <= 0:
            issues.append(
                f"{path}:{line_no}: job {job_name!r} timeout-minutes must be a positive integer"
            )
    return issues


def _validate_security_steps(path: Path, lines: list[str]) -> list[str]:
    issues: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        step_match = STEP_NAME_RE.match(line)
        if not step_match:
            continue

        step_name = _clean_yaml_scalar(step_match.group("name"))
        if not SECURITY_STEP_NAME_RE.search(step_name):
            continue

        block = _step_block_after_uses(lines, line_no - 1)
        if any(CONTINUE_ON_ERROR_TRUE_RE.match(block_line) for block_line in block):
            issues.append(
                f"{path}:{line_no}: security step {step_name!r} must not use continue-on-error"
            )
        if any(IGNORED_FAILURE_RE.search(block_line) for block_line in block):
            issues.append(f"{path}:{line_no}: security step {step_name!r} must not use || true")
    return issues


def _direct_pip_install_package(line: str) -> str | None:
    install_match = PIP_INSTALL_RE.search(line.split("#", 1)[0])
    if not install_match:
        return None

    try:
        tokens = shlex.split(install_match.group("args"))
    except ValueError:
        return "<unparseable>"

    package_tokens: list[str] = []
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token in PIP_OPTIONS_WITH_VALUE:
            skip_next = True
            continue
        if token.startswith("--requirement=") or token.startswith("--constraint="):
            continue
        if token.startswith(("-r", "-c", "-C")) and token not in {"-r", "-c", "-C"}:
            continue
        if token.startswith("-"):
            continue
        package_tokens.append(token)

    for package in package_tokens:
        normalized = package.strip("\"'").lower()
        if not re.match(r"^pip(?:$|[<>=!~\[])", normalized):
            return package
    return None


def validate_workflow_text(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    if not _has_top_level_contents_read_permission(text):
        issues.append(f"{path}: workflow must declare top-level permissions: contents: read")

    lines = text.splitlines()
    issues.extend(_validate_job_timeouts(path, lines))
    issues.extend(_validate_security_steps(path, lines))

    for line_no, line in enumerate(lines, start=1):
        if WRITE_PERMISSION_RE.match(line):
            issues.append(f"{path}:{line_no}: workflow must not grant write permission")
        if DOWNLOAD_EXECUTE_RE.search(line):
            issues.append(
                f"{path}:{line_no}: workflow must not pipe downloaded scripts directly to a shell"
            )
        if PULL_REQUEST_TARGET_RE.search(line.split("#", 1)[0]):
            issues.append(f"{path}:{line_no}: workflow must not use pull_request_target")
        if WORKFLOW_RUN_RE.search(line.split("#", 1)[0]):
            issues.append(f"{path}:{line_no}: workflow must not use workflow_run")
        if SECRET_REFERENCE_RE.search(line):
            issues.append(f"{path}:{line_no}: workflow must not reference secrets")

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

            if CHECKOUT_ACTION_RE.match(ref) and not any(
                PERSIST_CREDENTIALS_FALSE_RE.match(block_line)
                for block_line in _step_block_after_uses(lines, line_no - 1)
            ):
                issues.append(
                    f"{path}:{line_no}: actions/checkout must set persist-credentials: false"
                )

        install_match = AUDIT_TOOL_INSTALL_RE.search(line)
        if install_match:
            tool = install_match.group(1)
            issues.append(
                f"{path}:{line_no}: install audit tooling from requirements-dev.txt, not ad hoc ({tool})"
            )
        direct_package = _direct_pip_install_package(line)
        if direct_package is not None:
            issues.append(
                f"{path}:{line_no}: install dependencies from a dependency manifest, "
                f"not ad hoc ({direct_package})"
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
