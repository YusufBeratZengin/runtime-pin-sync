# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- `--lang en` English message mode
- `--sdkmanrc` and Ruby `.ruby-version` finders
- GitHub Action wrapper (`action.yml`) + pre-commit hook id
- EOL (end-of-life) warnings fed by an explicit data source
- Monorepo per-package expectation file (`.pins.toml`)
- MCP tool `check_runtime_pins` (JSON only, never writes)

## [0.1.0] - 2026-11-03

### Added
- Scanners for Node (`.nvmrc`, `.node-version`, `package.json` engines),
  Python (`.python-version`, `pyproject.toml` requires-python), Go (`go.mod`,
  `.go-version`), Rust (`rust-toolchain[.toml]`), Java (`.java-version`,
  `pom.xml`)
- Multi-runtime files: `.tool-versions` (asdf) and `mise.toml`
- Dockerfile reader: multi-stage `FROM`, stage aliases, `ARG`-parameterized
  tags (resolved when a default exists, marked dynamic otherwise)
- devcontainer.json reader (`image` + `features`, JSONC tolerant)
- GitHub Actions reader: `actions/setup-node|python|go|java`,
  `dtolnay/rust-toolchain`, `*-version` / `*-version-file` inputs,
  `strategy.matrix` grids compared as a union; `${{ … }}` expressions are
  skipped dynamically or resolved via `--degisken AD=DEGER`
- Set-based conflict engine: ranges vs pins (`>=3.10` vs `3.9` conflicts,
  `3.12` vs `>=3.10` does not), prefix semantics (`20` covers `20.11.0`),
  semver `^`/`~`, PEP 440 `~=`, `||` unions, comma AND-lists
- `--kaynak` single-source mode and `sync` with conservative, line-anchored
  rewrites; `--dry-run` provably touches no bytes; unsafe rewrites listed as
  manual edits instead of applied
- CLI (`runtime-pin-sync`, exit 0/1/2), `--json` machine output, table report
- Zero runtime dependencies: stdlib `tomllib` with 3.10 fallback parser,
  built-in minimal YAML subset parser, JSONC-tolerant devcontainer reader
- Node LTS alias table (hydrogen→16 … krypton→24); unknown aliases skipped,
  never guessed
- 149 tests, 93% coverage, ruff + strict mypy, Linux/Windows/macOS CI
