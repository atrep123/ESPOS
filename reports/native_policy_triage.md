# Native Policy Blocker Triage

- Generated: 2026-03-09T22:23:51.0974830+01:00
- History: C:\Users\atrep\Desktop\ESPOS\ESPOS\reports\native_policy_probe_history.jsonl
- Runs: 36
- Top: 1
- DeltaWindow: 0
- OnlyWorsening: False
- IncludeAllDeltaRows: False
- MinAbsDeltaScore: 0
- DeltaSortBy: abs-delta
- Score formula: 2 * PolicyHits + TransientHits

## Top Suites For Allow-List Priority

| Rank | Suite | Score | PolicyHits | PolicyRunRate% | TransientHits | TransientRunRate% |
|---:|---|---:|---:|---:|---:|---:|
| 1 | test_msgbus | 26 | 13 | 36.1 | 0 | 0 |

## Recommended Next Action

1. Prioritize allow-list requests for the top-ranked suites above.
2. Re-run scripts/burnin_native_policy.ps1 -Rounds 10 -DelaySeconds 2 after policy changes.
3. Compare triage reports before/after to verify rate reduction.
