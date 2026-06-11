from __future__ import annotations

from pathlib import Path

from tools.check_supply_chain import (
    collect_issues,
    validate_requirements,
    validate_workflow_text,
)


def test_current_repo_passes_supply_chain_guard():
    assert collect_issues(Path(".")) == []


def test_workflow_rejects_unpinned_action_reference():
    workflow = """
name: bad
jobs:
  test:
    steps:
      - uses: actions/checkout@v6
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("not pinned to a full commit SHA" in issue for issue in issues)


def test_workflow_requires_version_comment_for_sha_pinned_actions():
    workflow = """
name: bad
jobs:
  test:
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("missing inline version comment" in issue for issue in issues)


def test_workflow_rejects_ad_hoc_audit_tool_installs():
    workflow = """
name: bad
jobs:
  test:
    steps:
      - run: python -m pip install pip-audit
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("install audit tooling from requirements-dev.txt" in issue for issue in issues)


def test_requirements_requires_manifested_pip_audit():
    issues = validate_requirements("pytest>=9.0.3,<10\n")

    assert any("pip-audit" in issue for issue in issues)
