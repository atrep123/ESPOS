# Pre-Commit Hook Setup (Optional)

Basic markdown linting and smoke verification before commits.

## Quick Enable

```powershell
git config core.hooksPath .githooks
```

## What It Does

The `.githooks/pre-commit` hook runs:
1. `python tools/md_lint_basic.py` - checks fenced code blocks have language
2. `powershell tools/ci_smoke.ps1 -NoSimRoundtrip` - fast smoke (skips simulator)

## Disable Temporarily

```powershell
git commit --no-verify
```

## Disable Permanently

```powershell
git config --unset core.hooksPath
```

## Manual Lint/Smoke

Run individually without hook:

```powershell
# Markdown lint
python tools/md_lint_basic.py

# Full smoke (with simulator roundtrip)
powershell -NoProfile -ExecutionPolicy Bypass -File tools/ci_smoke.ps1

# Fast smoke (skip simulator)
powershell -NoProfile -ExecutionPolicy Bypass -File tools/ci_smoke.ps1 -NoSimRoundtrip
```

## VS Code Tasks

- **CI: Smoke** - full verification with RPC/UART
- **Docs: Basic Markdown Lint** - check fence languages (if added to tasks.json)
- **Simulator: Profile Metrics** - metrics export + HTML report

Run via: Ctrl+Shift+P → "Tasks: Run Task"

## Notes

- Lint script (`md_lint_basic.py`) flags:
  - Fenced code blocks without language (````\`\`\`` vs ````\`\`\`python`)
  - Bold text used as heading (`**Title**` instead of `### Title`)
- Older docs may have many warnings; focus on new/edited files.
- Hook is bash-style; works in Git Bash or WSL on Windows.

---
Enable when desired; not required for normal workflow.
