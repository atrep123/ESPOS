# ESP32OS Project Roadmap

> Status: Draft (to be iterated collaboratively)  
> Scope: Firmware (ESP32), Python simulator & tooling, Web/UI designer, Security & CI/CD

## 1. Vision & High-Level Objectives
- Reliable cross-environment development (firmware + rich simulator + web designer).
- Strong supply‑chain & runtime security posture (dependency, license, secret, vulnerability management).
- Fast iteration with full automated validation (tests, lint, build, scan) on every PR.
- Modular UI/animation/theme system with export parity (C header, HTML preview, ASCII modes).
- Predictable release lifecycle (versioned artifacts, changelog, reproducible builds, SBOM).

## 2. Strategic Pillars
1. CI/CD & Quality Automation
2. Security & Compliance
3. Developer Experience & Documentation
4. UI/UX Tooling & Export Parity
5. Performance & Profiling
6. Firmware Stability & Integration
7. Observability & Reporting

## 3. Phase Breakdown
### Phase A – Foundation (Completed / Ongoing Polishing)
- Multi-OS test workflow (`.github/workflows/tests.yml`).
- Release packaging (`release.yml`).
- Security audits & CodeQL (`security-audit.yml`, `codeql.yml`).
- Markdown lint + ignore for external deps.
- Version baseline (1.0.0 in `pyproject.toml`).

### Phase B – Security Hardening (In Progress)
- PR comment summarizing high/critical findings.
- SARIF for Python (`pip_audit.sarif`, `bandit_report.sarif`).
- Node SARIF conversion (`tools/npm_audit_to_sarif.py`).
- Unified SBOM (`tools/unify_sbom.py`).
- License enforcement (`tools/license_policy_eval.py`).
- Secret scanning (`tools/secret_scan.py`).

### Phase C – Expansion
- Notifications (Slack/email) for critical issues.
- Changelog automation (release note generation).
- Firmware build + flash test workflow.
- Dependency freshness & stale check workflow.

### Phase D – UX & Designer Enhancements
- Advanced theme layering & responsive layout validation.
- Animation pipeline: timeline editing, export to C/Javascript.
- Visual diff & regression snapshots (HTML/PNG) per PR.

### Phase E – Observability & Dashboards
- Security & quality dashboard (aggregate SARIF + metrics).
- Performance trend report (frame rate, memory from simulator logs).
- License & dependency delta diff per release.

## 4. Workstreams & Concrete Tasks
| Pillar | Key Tasks | Outputs |
|--------|-----------|---------|
| CI/CD | Add coverage artifact, flaky test detector | Coverage XML, stability report |
| Security | Extend regex patterns; integrate npm SARIF into workflow comment | Updated PR comment, fewer manual reviews |
| Docs | Contributor guide, security policy section | Updated `README.md`, `CONTRIBUTING.md` |
| UI/UX | Parity tests for ASCII vs HTML export | Test suite expansions |
| Performance | Batch profiler runs nightly | Trend CSV & HTML graphs |
| Firmware | Add integration test harness (UART loopback) | Pass/fail gating before merge |
| Reporting | Auto-generated `SECURITY_DASHBOARD.md` | Single-glance status |

## 5. Metrics & KPIs
- Test pass rate & average duration per matrix.
- Mean time to remediate HIGH/CRITICAL findings.
- % of PRs with successful SBOM & SARIF artifacts.
- Simulator FPS variance (target < ±10%).
- Export parity failures (target zero).
- Dependency update lag (days since latest available version) median.

## 6. Tooling Inventory (Current)
- Python security: pip-audit, safety, bandit.
- Node security: npm audit → SARIF conversion.
- SBOM: CycloneDX (Python & Node) + unified aggregator.
- License: pip-licenses, license-checker + policy evaluator.
- Secrets: regex-based custom scanner.
- Static analysis: CodeQL (Python + JS).

## 7. Risk & Mitigation
| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (secret/license) | Noise / dev fatigue | Whitelists + tuning patterns |
| Large workflow runtimes | Slower PR velocity | Parallelize jobs, caching deps |
| Firmware test flakiness | Unreliable gating | Isolate hardware-dependent tests, retry logic |
| Export format drift | Broken parity | Golden files + diff tests |
| Untracked perf regressions | UX degradation | Scheduled profiler runs & thresholds |

## 8. Release & Versioning Policy
- Semantic versioning (MAJOR.MINOR.PATCH).
- Automated changelog generation from conventional commits.
- Release packaging: simulator binary (PyInstaller), firmware build artifacts, SBOM bundle, SARIF bundle.
- Tag-triggered `release.yml` with checksum generation.

## 9. Documentation Roadmap
- `SECURITY.md`: audit process, reporting channels.
- `CONTRIBUTING.md`: coding standards, test matrix, commit format.
- `ROADMAP` (this file) updated quarterly.
- `UI_DESIGNER_GUIDE.md`: workflow from design → export.

## 10. Governance & Workflow Rules
- All changes via PR with required checks: tests, lint, security-audit.
- Automatic PR comment if any high/critical or license violation; block merge.
- Issues auto-labeled `security` / `documentation` / `performance` by workflows where possible.

## 11. Backlog (Initial Sequencing)
1. Merge PR comment workflow changes.
2. Integrate npm SARIF artifact upload and comment aggregation.
3. Add coverage + build badge to README.
4. Implement license & secret patterns expansion.
5. Add firmware build job.
6. Create SECURITY.md & CONTRIBUTING.md.
7. Add changelog automation script.
8. Build security dashboard generator.
9. Add dependency freshness workflow.
10. Performance regression threshold gate.

## 12. Contribution Guidelines (Draft)
- Favor minimal, localized changes (no broad API rewrites).
- Include/extend tests for any new script or export path.
- Provide language spec in fenced code blocks (markdown lint compliance).
- Keep external dependencies bounded to existing toolchain.

## 13. Dashboard Concept
A generated `SECURITY_DASHBOARD.md` linking:
- Latest SARIF counts (errors/warnings/notes).
- SBOM summary (# deps, new vs previous release).
- License status (violations list or NONE).
- Secret scan summary.
- Bandit issue count vs threshold.

## 14. Performance Tracking
- Simulator logs parsed for FPS & frame drops.
- Nightly scheduled run producing `reports/perf_trend.csv`.
- Threshold gating: average FPS below target triggers warning label.

## 15. Maintenance Cadence
- Weekly: dependency + vulnerability scan (already scheduled).
- Monthly: license whitelist review.
- Quarterly: roadmap assessment & reprioritization.

## 16. Success Criteria (End of Next Quarter)
- All PRs receive automated consolidated security status comment.
- Zero unaddressed HIGH/CRITICAL vulns > 48h old.
- Firmware build workflow stable (<2% failure unrelated to code changes).
- Export parity tests green across ASCII/HTML/C code.
- Dashboard auto-updated on main after each merge.

---
*Generated as an initial strategic planning artifact. Update iteratively as milestones are delivered.*
