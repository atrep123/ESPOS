# Native Policy Blocker Triage

- Generated: 2026-03-09T19:56:03.9754770+01:00
- History: C:\Users\atrep\Desktop\ESPOS\ESPOS\reports\native_policy_probe_history.jsonl
- Runs: 21
- Top: 5
- Score formula: 2 * PolicyHits + TransientHits

## Top Suites For Allow-List Priority

| Rank | Suite | Score | PolicyHits | PolicyRunRate% | TransientHits | TransientRunRate% |
|---:|---|---:|---:|---:|---:|---:|
| 1 | test_msgbus | 8 | 4 | 19 | 0 | 0 |
| 2 | test_seesaw | 4 | 2 | 9.5 | 0 | 0 |
| 3 | test_store | 4 | 2 | 9.5 | 0 | 0 |
| 4 | test_ui_cmd | 4 | 2 | 9.5 | 0 | 0 |
| 5 | test_ui_components | 2 | 1 | 4.8 | 0 | 0 |

## Recommended Next Action

1. Prioritize allow-list requests for the top-ranked suites above.
2. Re-run scripts/burnin_native_policy.ps1 -Rounds 10 -DelaySeconds 2 after policy changes.
3. Compare triage reports before/after to verify rate reduction.
