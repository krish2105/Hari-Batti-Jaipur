# Security policy

HariBatti is **read-only**: no part of it can send a command to a traffic signal, a signal controller or a
police system. Please help us keep it safe.

## Reporting a vulnerability

Report privately through GitHub: **Security → Report a vulnerability**
(https://github.com/krish2105/Hari-Batti-Jaipur/security/advisories/new). Please do not open a public issue.
We reply within 5 working days and aim to fix critical issues within 30 days. See
[docs/legal/responsible-disclosure.md](docs/legal/responsible-disclosure.md) for scope and safe-harbour terms.

## What we do

- OWASP ASVS Level 1 controls on the API and dashboard (auth rate limits, short sessions, role checks on every
  write route, security headers, input validation, a least-privilege database role for the AI copilot).
- Every push: `pnpm audit`, `pip-audit`, a gitleaks secret scan and a CycloneDX SBOM (`.github/workflows/security.yml`);
  Dependabot proposes updates weekly.
- Personal data: minimum collected, retention enforced by a daily job, export and erasure on request (DPDP Act 2023).
