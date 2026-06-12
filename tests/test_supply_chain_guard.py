from __future__ import annotations

from pathlib import Path

from tools.check_supply_chain import (
    collect_issues,
    validate_dependabot_text,
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


def test_workflow_requires_checkout_persist_credentials_false():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("persist-credentials: false" in issue for issue in issues)


def test_workflow_rejects_checkout_persist_credentials_true():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
        with:
          persist-credentials: true
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("persist-credentials: false" in issue for issue in issues)


def test_workflow_accepts_checkout_persist_credentials_false():
    workflow = """
name: good
permissions:
  contents: read
jobs:
  test:
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
        with:
          persist-credentials: false
"""

    issues = validate_workflow_text(Path(".github/workflows/good.yml"), workflow)

    assert not any("persist-credentials" in issue for issue in issues)


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


def test_workflow_rejects_direct_pip_package_installs():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - run: python -m pip install platformio
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("dependency manifest" in issue for issue in issues)


def test_workflow_allows_manifested_pip_installs_and_pip_upgrade():
    workflow = """
name: good
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - run: python -m pip install --upgrade "pip>=26.1.2,<27"
      - run: python -m pip install -r requirements.txt -r requirements-dev.txt
"""

    issues = validate_workflow_text(Path(".github/workflows/good.yml"), workflow)

    assert not any("dependency manifest" in issue for issue in issues)


def test_workflow_requires_read_only_contents_permission():
    workflow = """
name: bad
jobs:
  test:
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("permissions: contents: read" in issue for issue in issues)


def test_workflow_requires_job_timeout_minutes():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("timeout-minutes" in issue for issue in issues)


def test_workflow_rejects_non_positive_job_timeout_minutes():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 0
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("timeout-minutes" in issue for issue in issues)


def test_workflow_step_timeout_does_not_satisfy_job_timeout():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: slow
        timeout-minutes: 5
        run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("job 'test' must set timeout-minutes" in issue for issue in issues)


def test_workflow_accepts_job_timeout_minutes():
    workflow = """
name: good
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/good.yml"), workflow)

    assert issues == []


def test_workflow_rejects_continue_on_error_security_step():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Dependency security audit
        continue-on-error: true
        run: python -m pip_audit -r requirements-dev.txt --strict
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("security step" in issue and "continue-on-error" in issue for issue in issues)


def test_workflow_rejects_ignored_security_step_failure():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Supply-chain guard
        run: python tools/check_supply_chain.py || true
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("security step" in issue and "|| true" in issue for issue in issues)


def test_workflow_allows_non_security_advisory_step():
    workflow = """
name: good
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Mypy (designer - advisory)
        continue-on-error: true
        run: python -m mypy ui_designer.py || true
"""

    issues = validate_workflow_text(Path(".github/workflows/good.yml"), workflow)

    assert issues == []


def test_workflow_rejects_secret_references():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env:
      API_TOKEN: ${{ secrets.PYPI_TOKEN }}
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("must not reference secrets" in issue for issue in issues)


def test_workflow_allows_non_secret_expressions():
    workflow = """
name: good
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      matrix:
        python-version: ["3.12"]
    steps:
      - run: echo "${{ matrix.python-version }}"
"""

    issues = validate_workflow_text(Path(".github/workflows/good.yml"), workflow)

    assert issues == []


def test_workflow_rejects_write_permissions():
    workflow = """
name: bad
permissions:
  contents: write
jobs:
  test:
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("write permission" in issue for issue in issues)


def test_workflow_rejects_curl_pipe_shell_installers():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    steps:
      - run: curl -fsSL https://example.invalid/install.sh | bash
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("downloaded scripts directly to a shell" in issue for issue in issues)


def test_workflow_rejects_powershell_download_execute_installers():
    workflow = """
name: bad
permissions:
  contents: read
jobs:
  test:
    steps:
      - run: irm https://example.invalid/install.ps1 | iex
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("downloaded scripts directly to a shell" in issue for issue in issues)


def test_workflow_rejects_pull_request_target_event():
    workflow = """
name: bad
on:
  pull_request_target:
permissions:
  contents: read
jobs:
  test:
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("pull_request_target" in issue for issue in issues)


def test_workflow_rejects_pull_request_target_inline_event():
    workflow = """
name: bad
on: [push, pull_request_target]
permissions:
  contents: read
jobs:
  test:
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("pull_request_target" in issue for issue in issues)


def test_workflow_rejects_workflow_run_event():
    workflow = """
name: bad
on:
  workflow_run:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("workflow_run" in issue for issue in issues)


def test_workflow_rejects_workflow_run_inline_event():
    workflow = """
name: bad
on: [push, workflow_run]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - run: echo ok
"""

    issues = validate_workflow_text(Path(".github/workflows/bad.yml"), workflow)

    assert any("workflow_run" in issue for issue in issues)


def test_requirements_requires_manifested_pip_audit():
    issues = validate_requirements("pytest>=9.0.3,<10\n")

    assert any("pip-audit" in issue for issue in issues)


def test_dependabot_requires_github_actions_group():
    dependabot = """
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:30"
      timezone: "Europe/Prague"
"""

    issues = validate_dependabot_text(Path(".github/dependabot.yml"), dependabot)

    assert any("groups.github-actions" in issue for issue in issues)


def test_dependabot_requires_pip_prague_schedule():
    dependabot = """
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "daily"
"""

    issues = validate_dependabot_text(Path(".github/dependabot.yml"), dependabot)

    assert any("pip schedule" in issue for issue in issues)
