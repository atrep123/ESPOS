# Integrations

This directory contains project-level integrations that are useful to ESPOS
but keep their own build, test, and firmware workflow.

## `m5-prop-lora/`

Vendored snapshot of `atrep123/m5-prop-lora`.

- Source commit: `29d19a5169e165926907e0adf57ba3fed6a2486b`
- Imported from: `https://github.com/atrep123/m5-prop-lora.git`
- Purpose: M5 Dial / DinMeter prop-control firmware, shared protocol code,
  UIFlow2 custom blocks, and offline deployment tooling.
- Vendored LVGL firmware sources are kept for the Dial build, but the upstream
  LVGL docs-only Python environment manifest is intentionally stripped from
  this snapshot. ESPOS does not build LVGL documentation, and keeping that old
  docs manifest creates misleading dependency security alerts unrelated to the
  firmware path.

Validate the integration from its own directory:

```powershell
cd integrations\m5-prop-lora
python tools\validate_uiflow_blocks.py
python -m pytest -q
```

The ESPOS root test suite intentionally treats this as an embedded project,
not as native ESPOS package code.
