# Coverage policy — why the gate is 80%, not "97%"

## TL;DR

The CI coverage gate was lowered from `--cov-fail-under=97` to `80`, and
coverage was scoped (via `[tool.coverage]` in `pyproject.toml`) to the real
product packages. The old 97% was **not** a measure of behavioral
verification — it was a number manufactured to clear the gate, and the
mechanism used to manufacture it was also the root cause of a test-suite
memory blow-up. This document records the decision and its rationale so the
number is not silently raised back to a vanity figure.

## What "97%" actually measured (the audit findings)

The test/CI audit (`4_tests_ci.md`, HIGH-1) established:

- **19 files named `test_coverage_push*.py`, 14,388 LOC ≈ 23% of the entire
  61,577-LOC test corpus**, exist purely to chase line numbers, not to verify
  behavior.
- The dominant pattern is monkeypatching an internal to raise and then
  asserting nothing — i.e. proving that an `except Exception: pass` clause
  passes. These assert *no* behavior.
- **Self-admitted dead-code tests** (15 occurrences across 6 files): the test
  docstring states the targeted branch is unreachable, then exercises a
  *different* path while still booking the coverage line (e.g.
  `test_coverage_push19.py` `test_bounds_division_by_zero`,
  `test_fit_text_snap_up_zero`, `test_wide_help_overlay_draws`).
- **61 occurrences of `assert isinstance(x, …)` as the sole assertion** across
  30 files; many `draw_*` paths are exercised with zero assertions.
- Coverage was collected with `--cov=.` (whole repo) and **no `[tool.coverage]`
  section anywhere** — no `source`, no `omit`. So the denominator included the
  legacy `ui_designer.py` shim and padded exception lines, and the numerator
  was inflated by assertion-free line-touching. The "97%" was an artifact of
  that setup, not a property of the product.

Conclusion: a 97% gate over an unscoped tree, sustained by ~23% padding, is
*test theater*. Keeping it would have required preserving the padding (and the
memory hazard below) forever.

## The 97% gate was also a safety hazard

`ci.yml` ran the suite with `pytest … -n auto --cov=. …`.

- `-n auto` (pytest-xdist) spawns **one worker process per logical CPU**. On
  the primary development host that is **32 workers**.
- With `--cov=.` and **no `[tool.coverage]` scoping**, every worker
  instrumented and retained line-data for the *entire working tree* —
  including `.venv` site-packages, `.pio`, `output/`, and the 2.7MB test
  corpus itself.
- 32 × (whole-tree coverage map + pygame + per-test app/Surface state) drove
  each `python.exe` to **100+GB committed memory** and destabilized the host.

So the padded-97% mechanism (`--cov=.`, unscoped, under `-n auto`) was *itself*
the bug. Lowering the gate is not a retreat from quality — it is removing the
incentive to keep the padding that made the suite both meaningless and unsafe.

## The honest replacement

1. **Scope coverage to product code.** `[tool.coverage.run].source` lists the
   real packages (`cyberpunk_designer`, `tools`, the top-level model/util
   modules). `omit` excludes `.venv`, `.pio`, `output`, `build`, `tests`,
   `generated`, `.claude`, and demo/visual scripts. The coverage data set is
   now a few thousand product lines, independent of host core count.
2. **Bound the workers.** CI uses `-n 2 --maxprocesses 2` instead of
   `-n auto`. Two workers × scoped coverage is bounded and predictable on any
   host, including 32-core dev machines.
3. **Set an honest floor: `fail_under = 80`.** With the padding no longer
   counted against an inflated whole-tree denominator, 80% is a value that
   *real behavioral tests* can sustain without isinstance-tautologies or
   dead-code booking. It was deliberately **lowered to a truthful, enforceable
   number — not raised, not faked.**

## Rules going forward

- **Do not raise the gate by adding assertion-free or dead-code tests.** If the
  number needs to go up, it goes up because real behavioral tests were added.
- **Do not revert to `--cov=.`** or remove the `[tool.coverage]` scoping — that
  re-introduces both the vanity denominator and the 100+GB memory hazard.
- **Do not run the suite with `-n auto`** on a high-core host. Use the bounded
  invocation. See `docs/test_safety.md` / the CI `Run tests` step.
- New padding files (`test_coverage_push*`-style) should be treated as
  candidates for deletion or rewrite into behavioral tests, not as coverage
  assets.
