# Token Lint Usage

`tools/token_lint.py` enforces that UI code uses design tokens instead of hard‑coded hex colors.

## Basics

```bash
python tools/token_lint.py --paths ui_designer.py ui_designer_preview.py
```

- Returns exit code 1 when non‑token literals are found (use `--no-fail` for report-only).
- Scans only `.py` files by default; add `--ext` to include more (e.g., `.py .c .h`).

## Options

- `--allow-file path` – extra allowed hex values (one per line, with or without `#`).
- `--out path` – write the report to a file (stdout is always printed).
- `--top N` – limit number of shown literals.

## Inventory helper

`tools/token_inventory.py` reports the most common literals (including allowed tokens) to plan migrations. Options mirror `token_lint` (`--paths`, `--ext`, `--allow-file`, `--out`).

## CI scope

`token-lint` workflow runs on `.py`, `.c`, `.h` under `ui_*`, `tools`, and `src`. HTML/docs are currently excluded because they intentionally embed sample colors.

### If you want to lint HTML/docs

- Run locally with `--ext .html` and an allowlist, e.g.:
  ```bash
  python tools/token_lint.py --paths web docs --ext .html --allow-file web/token_allow.txt --no-fail
  ```
- Create/maintain `web/token_allow.txt` with intentional sample colors (one per line) to avoid false positives in documentation.

CI guard: `token-lint` workflow fails if `web/token_allow.txt` changes unless `ALLOW_TOKEN_ALLOWLIST_CHANGE=1` is set (to acknowledge intentional edits).
