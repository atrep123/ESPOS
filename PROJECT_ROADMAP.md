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

---

 
## 17. Detailed Timeline (Quarterly View)

| Quarter | Focus | Key Deliverables | Exit Criteria |
|---------|-------|------------------|---------------|
| Q1 | Security Hardening | PR comment workflow, license policy, secret scan v2 | All high/critical issues auto-commented; no manual triage required |
| Q2 | CI/CD Maturity | Firmware build & test, coverage reporting, flaky test isolation | Coverage badge >85%, flaky test list generated weekly |
| Q3 | UX & Export Parity | Advanced animation editor, responsive rules, parity diff tests | Zero parity diff failures on weekly run |
| Q4 | Observability & Dashboards | Security/perf dashboard, dependency freshness automation | Dashboard updates per merge with <5 min latency |

 
## 18. Test Strategy Matrix

| Layer | Scope | Tools | Cadence | Gate Policy |
|-------|-------|------|---------|-------------|
| Unit (Python) | Functions & helpers | pytest | Per PR | Fail blocks merge |
| Unit (C Firmware) | Kernel/services modules | Unity/CMock (future) | Nightly + PR (critical paths) | Fail blocks merge |
| Integration (Simulator) | RPC, UI pipeline, export | pytest + live recording | Per PR | Export parity required |
| Web Frontend | Build & module linkage | npm + custom smoke script | Per PR | Warnings allowed, failures block |
| Security Scan | Dependencies & code | pip-audit, npm audit, bandit, CodeQL | Per PR + weekly schedule | High/Critical fail |
| Performance | FPS, memory snapshots | profiler scripts | Weekly | Trend regression >10% triggers warning |
| License/Secrets | Policy compliance | custom scripts | Per PR | Violation blocks merge |

 
## 19. Performance Budgets

| Metric | Target | Warning Threshold | Hard Fail |
|--------|--------|------------------|-----------|
| Avg Simulator FPS | ≥ 60 | < 55 | < 50 |
| Frame Time StdDev (ms) | < 4.0 | 4–6 | > 6 |
| Memory (sim process MB) | < 400 | 400–450 | > 450 |
| Firmware Image Size (KB) | < 512 | 512–560 | > 560 |
| Python Test Duration (matrix avg min) | < 6 | 6–8 | > 8 |

 
## 20. Security Maturity Levels

| Level | Description | Actions Required |
|-------|-------------|------------------|
| 1 (Baseline) | Manual triage, basic scans | Complete initial workflows (Done) |
| 2 (Automated) | Auto comments & issue creation | Expand secret/license coverage (In progress) |
| 3 (Preventive) | Pre-commit + supply chain alerts | Add dependency freshness + SBOM diff gating |
| 4 (Adaptive) | Trend analysis & auto remediation suggestions | Integrate advisory summarizer + patch PR drafts |
| 5 (Predictive) | ML anomaly detection & proactive pinning | Future research; not scheduled yet |

 
## 21. Roles & Ownership (Lightweight)

| Area | Primary | Backup | Notes |
|------|---------|--------|-------|
| CI/CD Workflows | Automation Maintainer | Security Engineer | Ensure YAML consistency & caching |
| Security Scripts | Security Engineer | Tooling Maintainer | Regex, severity thresholds |
| UI Designer & Export | UI Lead | Simulator Maintainer | Parity & usability |
| Firmware Kernel | Firmware Lead | QA Engineer | Stability & resource usage |
| Documentation | Tech Writer | Any Contributor | Review quarterly |
| Dashboard & Reporting | Data Maintainer | Security Engineer | Merge metrics sources |

 
## 22. Dependency Freshness Plan

| Ecosystem | Method | Frequency | Report |
|-----------|--------|----------|--------|
| Python | pip list + version compare | Weekly | `reports/deps_python.json` |
| Node | npm outdated | Weekly | `reports/deps_node.json` |
| Firmware (ESP-IDF) | Manifest diff | Monthly | `reports/deps_firmware.json` |
| Rust (Tauri) | cargo audit / outdated | Monthly | `reports/deps_rust.json` |

 
## 23. SBOM & Supply Chain Enhancements

- Add SBOM diff script comparing previous release vs current build.
- Flag newly introduced high-risk licenses and transitive dependencies.
- Planned artifact bundling: `sbom-unified.json`, `sbom-diff.json` per release.

 
## 24. Contribution Triage Flow

1. New PR opened → auto workflows run (tests, lint, security, SBOM).
2. Bot comment consolidates findings (single message).
3. If failures: contributor fixes; label `needs-fix` auto-applied.
4. Maintainer review after green status checks.
5. Merge + dashboard update job triggers.

 
## 25. Backlog Prioritization Scoring

| Item | Value (1–5) | Effort (1–5) | Score (V/E) | Notes |
|------|-------------|--------------|-------------|-------|
| Firmware build workflow | 5 | 3 | 1.67 | Unlocks integration gates |
| Dashboard generator | 4 | 2 | 2.00 | High visibility |
| Dependency freshness | 3 | 2 | 1.50 | Prevent drift |
| Advanced animation editor | 4 | 4 | 1.00 | UX feature depth |
| SBOM diff gating | 4 | 3 | 1.33 | Supply chain hygiene |
| Pre-commit hooks expansion | 3 | 1 | 3.00 | Quick win |

 
## 26. Future Research & Innovation

- ML-based anomaly detection on simulator performance traces.
- WASM export of UI components for in-browser simulation.
- Automated vulnerability patch suggestion bot (draft PRs).
- Incremental binary diffing for firmware size optimization.
- Live collaborative editing conflict resolution strategies.

## 27. Decommission / Sunset Criteria
- Any script unused for 3 consecutive months & no references in workflows.
- License whitelist entry obsolete (no deps referencing) → remove.
- Deprecated export formats replaced by stable alternatives.

## 28. Review & Update Mechanism
- Monthly mini-review: update backlog scores.
- Quarterly major review: revise phases & success criteria.
- Automatic reminder issue created if roadmap untouched > 90 days.

## 29. Glossary (Quick Reference)
| Term | Definition |
|------|------------|
| Parity | Identical visual/logical output across export targets |
| SBOM | Software Bill of Materials, dependency inventory |
| SARIF | Static Analysis Results Interchange Format |
| FPS Variance | Percentage deviation from median frame rate |
| Flaky Test | Test with intermittent pass/fail behavior |

## 30. Immediate Next Actions Snapshot
1. Merge PR comment logic to main.
2. Integrate npm SARIF into workflow artifacts + comment aggregation.
3. Implement coverage reporting & badge.
4. Draft SECURITY.md (include disclosure policy).
5. Prepare firmware build workflow skeleton.
6. Add SBOM diff script placeholder.
7. Extend secret scan patterns and add whitelisting config.
8. Begin dashboard generator prototype.

---
*Extended roadmap version adds timeline, maturity model, metrics depth, prioritization scoring, and actionable next steps.*
