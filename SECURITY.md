# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | ✅ |
| < 0.1 | ❌ |

## Scope

`runtime-pin-sync` is an offline, read-mostly static analyzer:

- It opens files inside the repository you point it at and rewrites lines
  only during explicit `sync` (never with `--dry-run`).
- It performs **no network access** and has **zero runtime dependencies**.
- It does not execute any code, container or build tool you point it at.

Threat model highlights we already defend against:

- **Path handling:** `sync` only rewrites files the scanner parsed, at the
  recorded line, when the version token appears exactly once with numeric
  boundaries; ambiguous matches go to the manual-edit list instead of being
  written.
- **Malicious repo files:** malformed YAML/TOML/JSON is caught per file and
  reported as `okunamadı`; a crafted file cannot crash the scan or cause
  writes (writers require a parsed, conflict-flagged pin with line anchor).
- **No secrets:** the tool never reads environment variables for
  credentials and prints only version strings and file paths.

## Reporting a vulnerability

Email the maintainer privately via the GitHub "Report a vulnerability" form
on the repository's Security tab (private vulnerability reporting). Include
a minimal reproduction with fake data. We aim to acknowledge within 5 days
and will credit reporters unless anonymity is requested.

## Dependency policy

Runtime dependency count: 0. Dev dependencies (`pytest`, `pytest-cov`,
`ruff`, `mypy` via the `.[dev]` extra) are intentionally **not** version
pinned in `pyproject.toml`; CI installs their latest releases and Dependabot
monitors the GitHub Actions. Pinning dev deps is a planned improvement, not a
current guarantee.
