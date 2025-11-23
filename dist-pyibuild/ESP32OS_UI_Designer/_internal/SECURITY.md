# Security Policy

## Security Audit Workflow

- Automated security audits run weekly (`.github/workflows/security-audit.yml`) or on demand via workflow_dispatch.
- Scans: pip-audit, Bandit, npm audit → SARIF, SBOM (CycloneDX), license policy evaluation, custom secret scan.
- PRs receive a comment summarizing SARIF counts and license policy status; dashboard artifact (`reports/security_dashboard.md`) is uploaded.
- Slack alerting is available when `SLACK_WEBHOOK_URL` is set; critical/high findings or policy violations trigger notifications.

## Reporting a Vulnerability

- Please open a private security report via GitHub Security Advisories or email the maintainers (see repository contact).
- Include reproduction steps, affected versions, and impact. A maintainer will acknowledge within 72 hours.

## License & Dependency Policy

- Disallowed licenses default to `GPL-3.0, AGPL-3.0, LGPL-3.0, SSPL, BUSL-1.1` (configurable in workflow).
- Dependency freshness checks run weekly (`.github/workflows/deps-outdated.yml`) for pip/npm.

## Secrets Handling

- Code is scanned for common secrets (AWS keys, OAuth/Google tokens, generic API keys, JWT Bearer tokens, private key headers).
- Add known test fixtures to `ALLOWED_FILES` in `tools/secret_scan.py` to avoid noise.
