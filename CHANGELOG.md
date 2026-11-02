# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed (independent review round)
- Conflict engine now reports pairwise contradictions (union-find components);
  a hub pin (`20`, `>=18`) can no longer hide that `20.11.0` conflicts with
  `20.12.0` or that `20` conflicts with `<20`.
- Fully specified versions compare as exact points: `20.1.0` no longer
  "intersects" `>20.1.0`; short tokens (`20`, `3.12`) stay prefix ranges.
- `sync` targets the parsed field's exact position: `package.json`
  `dependencies.node` can no longer be rewritten instead of `engines.node`;
  CI input lookup matches `^\s*<key>:` lines, not prose like
  `name: node-version 22 installation`.
- `sync` refuses symlinked targets and paths resolving outside the repo;
  files are read/written byte-wise so CRLF and mixed line endings survive.
- `sync` writes only when outlier AND reference tokens are plain fixed
  versions: `^22` outliers and `>=22`/matrix (`22, 24`) references go to the
  manual list instead of being written into `.nvmrc`-style files.
- Deduplication keeps all line occurrences (two `FROM node:22` stages both
  rewrite); after writing, the repo is rescanned and surviving conflicts
  exit 1 instead of reporting success.
- Node LTS table corrected (hydrogen→18, gallium→16 added; source:
  nodejs/Release schedule.json); moving alias `lts/*` is dynamic, not the
  table's newest entry.
- go.mod `go` directive modeled as a minimum requirement: `go 1.22` +
  `toolchain go1.23.1` is valid, not a conflict.
- `dtolnay/rust-toolchain@1.85.0` without `with.toolchain` reads the `uses`
  ref; existing custom `*-version-file` targets are read for content.
- Rust prereleases (`1.85.0-rc1`) are no longer coerced to `1.85.0`; they are
  reported (with a warning) and excluded from comparison. Target triples
  still reduce to the version.
- 3.10 TOML fallback parses multiline arrays, inline tables and
  `[[array.table]]` — the project's own `pyproject.toml` no longer breaks it.
- LICENSE/README/pyproject copyright name is "Yusuf Berat Zengin";
  SECURITY.md no longer claims dev dependencies are pinned; skipped
  directories are pruned before descent (`os.walk`); CI negative-example step
  asserts exit code exactly 1.

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
