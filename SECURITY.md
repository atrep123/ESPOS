# Security Policy

This repo is a lightweight embedded UI toolkit + designer. Security is handled in a simple, contributor-friendly way.

## Reporting

- Vulnerabilities: please open a private GitHub Security Advisory (preferred). If you cannot, open an issue with minimal details and ask for a private channel.
- Supported versions: `main` only (no backport policy yet).
- Scope: issues in the firmware runtime, exporter, or designer that can lead to memory corruption, unintended writes, or unsafe behavior.

## Hardening summary

### Firmware (C)

- **Integer overflow protection** — all render arithmetic (`int64_t` intermediaries), `SET_VALUE` clamped to `INT32_MIN..INT32_MAX`, chart `data_count` bounds-checked against buffer size.
- **Buffer safety** — `snprintf` everywhere (never `sprintf`), all string ops bounded by `sizeof(dest)`, widget text overrides use fixed `UI_TEXT_OVERRIDE_LEN`.
- **RPC frame validation** — frame length checked before access, NUL-terminated, mutex-guarded shared state, desync recovery on malformed frames.
- **Binding/store thread safety** — `xSemaphoreTake`/`Give` guards on binding registry and NVS store; no bare globals for shared mutable state.
- **Widget type dispatch** — `widget->type < UIW__COUNT` validated before function-pointer dispatch; out-of-range types logged and skipped.
- **Meta constraint parsing** — `precision` clamped to `[0..6]`, `scale` rejects non-positive, string fields truncated to buffer size.
- **Compiler flags** — `-Wall -Wextra -Wshadow` on all source; `-Werror` on native tests. Zero warnings policy.

### Codegen (Python → C)

- **String escaping** — all user-supplied text (widget labels, constraint strings) passed through C string escaping before emission into generated `.c` files; prevents injection of arbitrary C code via design JSON.
- **Preset whitelist** — only known preset names are accepted by the codegen pipeline; arbitrary identifiers are rejected.
- **Deterministic output** — stable widget ordering, write-only-on-change; prevents spurious diffs.

### Designer / Python tooling

- **Input validation** — design JSON validated against schema (`schemas/ui_design.schema.json`) before export; `validate_design.py` checks field types, ranges, and cross-references.
- **Path handling** — no `eval`/`exec` on user input; file paths sanitized through `pathlib`.
- **Dependency pinning** — `requirements.txt` pins exact versions; `ruff` lint rules include `S` (flake8-bandit) for security anti-patterns.
