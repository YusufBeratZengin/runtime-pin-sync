# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `scripts/kisitlar-dev.txt`: exact pins for the gate tools (pytest,
  pytest-cov, ruff, mypy, build). CI and `scripts/check.sh` install with
  `-c`, so reproducible runs no longer depend on which version pip picked;
  `tests/test_bagimlilik_kisitlari.py` keeps the locks inside the
  `pyproject.toml` `[dev]` ranges.
- `.sdkmanrc` (SDKMAN!) finder: the `java=` line is read as a Java source.
  `java=17.0.2+8` keeps its build metadata, a distribution suffix
  (`java=21.0.1-tem`) is not part of the version and survives a `sync`
  rewrite; `latest`/unknown values are dynamic, empty values unreadable.
- `--lang {tr,en}` CLI option and `RUNTIME_PIN_SYNC_LANG` environment variable support for full English output across tables, conflict reports, sync operations, and error/warning paths.
- Documented supported YAML subset in `miniyaml.py` with behavioral examples and explicit architectural comparison with PyYAML / ruamel.yaml in README (EN and TR).
- CI `paket` job builds sdist + wheel (`python -m build`) and installs **only the
  wheel** into a clean venv with `--no-index --find-links` (proves the
  zero-runtime-dependency claim), then runs `pip check`, `--version` and both
  example repos through the installed console script; `build` is part of the
  `[dev]` extra and the wheel-only check is documented in README,
  README.tr and CONTRIBUTING.

### Fixed
- `--lang en` could leave Turkish fragments in warnings: warning texts were
  written in Turkish and "translated" in the report layer by a substring
  replacement table, so any sentence missing from that table leaked through
  (e.g. `version-file '../x' points outside repository ya da dosya bağlantısı
  (rededildi)`), and every finder-level warning (empty `.nvmrc`, invalid
  `package.json`, bad TOML) was Turkish regardless of `--lang`. Warnings are
  now produced in the selected language at their source: `lang` is threaded
  through `tara()`, all finders, `docker`, `ci.is_aksi()` and the bundled
  `miniyaml`/`minitoml` parsers; `uyari_cevir()` and its replacement table are
  gone. Regression tests live in `tests/test_dil.py`, which also fails if a
  single Turkish character appears in an English report.
- The `version-file` boundary refusal message had a typo (`rededildi`); the
  catalogue entry now says `reddedildi`, and the English text no longer mixes
  two languages.
- `scripts/sir_tarama.sh` no longer treats a failed `grep` as "no match".
  Exit codes are now `0` clean, `1` finding, `2` scan could not complete
  (missing `grep`, permission or IO error); `2` fails the gate, so an
  unreadable file or directory can never be reported as a clean scan.
  Regression tests in `tests/test_sir_tarama.py` run the script against a
  temporary repo copy with a stubbed `grep`.
- Fixed clean-clone pytest collection failures (`ModuleNotFoundError: No module named 'runtime_pin_sync'`) by adding `pythonpath = ["src"]` to `[tool.pytest.ini_options]` in `pyproject.toml` and defining `export PYTHONPATH="src"` in `scripts/check.sh`.
- Pinned developmental dependency version bounds in `pyproject.toml` (`[project.optional-dependencies] dev`) for reproducible test and CI execution.
- Directory read errors during a scan are no longer swallowed by `os.walk`:
  the unreadable path is named in a warning and `check`/`sync` exit with code
  2 (`scan incomplete`) instead of presenting a partial scan as a clean pass.
- The English `TYPE` column no longer leaks Turkish-only internal ids
  (`ci-adim` -> `ci-step`, `ci-matrix`, `ci-file`, `ci-action`, `file`,
  `directory`); JSON `tur` keeps the stable id.
- README (EN/TR): the "zero supply-chain risk" claim was narrowed to what the
  code actually guarantees — no third-party YAML parser on the *runtime*
  dependency path. Building uses `hatchling` and tests/lint use the `[dev]`
  extra, as the README now says explicitly.

### Fixed (independent review round 2)
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

### Fixed (independent review round 3)
- `*-version-file` targets are read only inside the repo: `..` components,
  absolute paths and symlinked targets are rejected *before* reading, so
  outside content can never reach a warning; the scanner applies the same
  boundary (a symlink pointing outside the repo yields a refused-read
  warning and contributes no pins).
- CI input positions are derived from the job/step/`with` block: a matrix
  line (`node-version: [22, 24]`) can no longer become the position of a
  step's `node-version: 22` (sync used to rewrite the matrix and leave the
  step stale); repeated steps each bind to their own real line and all
  occurrences are written.
- `package.json` `engines.node` position binds to the ROOT `engines` key
  (brace-depth aware): `custom.engines.node` can no longer be the write
  target; ambiguity yields no position instead of a guess.
- `mise.toml` line positions bind to the `[tools]` section and the exact
  key: `[env] node = "22"` is no longer rewritten when the pin lives in
  `[tools]`; inline tables stay position-less (manual).
- A line that collided into the manual list stays disqualified: a third
  target on the same line can no longer re-enter the automatic plan
  (`python = ["3.9", "3.10", "3.11"]` now lists all three as manual).
- Multi-valued sources never auto-write their first member: with
  `node = ["22", "24"]` in the source file, the reference becomes the
  union (`22, 24`), which `sync` treats as non-fixed → manual list,
  matching the README's grid/list promise.
- Version comparison dialects split: PEP 440 keeps `==3.12.*` a wildcard
  prefix (matches `3.12.1`) and narrow `>`/`<=`; npm/semver (node, rust)
  follows node-semver x-ranges (`>20` == `>=21.0.0`, `<=20` == `<21.0.0`).
- Docker tags: prereleases (`node:22-rc1`) are no longer coerced to the
  stable `22` — reported with a warning and excluded from comparison;
  known distro suffixes (`3.12-slim-bookworm`, `17-jre`) keep the version;
  unknown suffixes warn and are excluded. Registry ports
  (`registry.example:5000/node:22`) split correctly in Dockerfile and
  devcontainer readers, so the pin is no longer silently dropped.
- `.tool-versions` multi-version lines (`python 3.12.1 3.11.8`, asdf
  installs both) model the UNION, not just the first entry — no more
  false conflicts against `.python-version=3.11.8`.

### Fixed (independent review round 4)
- `sync` writes are now atomic: the rewritten content goes to a sibling temp
  file, is flushed and `fsync`ed, then swapped in with `os.replace`. A failed
  or interrupted write leaves the target byte-for-byte unchanged, removes the
  temp file and keeps the original file mode (regression tests: forced
  `os.replace` failure + mode preservation; previously `write_bytes` truncated
  the target in place).
- README (EN/TR) now states the real symlink contract instead of claiming every
  symlinked version file is refused: a version file whose symlink resolves
  **outside** the repo is refused before reading (no content reaches a report),
  while a symlink that stays **inside** the repo is repo content — read for
  comparison, never written through, so it always lands in the manual list.
  A regression test pins both halves.
- The 0.1.0 coverage/test figures were stale (93% / 149); they now match the
  measured gate output.

### Fixed (independent review: unusable sources, mise unions, English reasons)
- `--kaynak` / `--source` now requires the source file to yield at least one
  *usable* version. An empty, unreadable or unparseable file (`.nvmrc` with no
  token, `.python-version: not-a-version`) used to pass the check and let
  `check`/`sync` exit 0 with nothing compared; both now exit 2 with
  "source ... yields no versions".
- `mise.toml` version lists (`node = ["22", "24"]`) are modeled as ONE union
  pin in default checks too, exactly like `.tool-versions` multi-value lines.
  Previously each member became a separate pin, so the comparator could report
  `24` as conflicting with a reference of `22` even though both are installed.
  A list with any dynamic/unknown member is skipped as a whole; a list is
  never auto-rewritten and never contributes a single member as reference.
- `sync` and scan reasons/errors are produced from a TR/EN message catalogue
  (`dil.py`) instead of post-hoc string patching, so `--lang en` no longer
  leaves Turkish reasons such as "satırda tek ve bağımsız değil" or
  "dosya okunamadı". The warning translation table now covers version-token,
  Docker tag-suffix, prerelease and YAML indentation messages as well.
- README (EN/TR) narrowed the English claim to the human-readable surface and
  states that JSON keys stay stable; examples now show the directory they run
  in. Added a documented boundary section for the Go (`go` = minimum,
  `toolchain` = exact) and Java (`pom.xml` first single-line literal element,
  no parent validation, no profiles) readers.

### Changed / Fixed (independent review round 5)
- `--help` is now localized like the rest of the CLI: `--lang en` (or
  `RUNTIME_PIN_SYNC_LANG=en`) prints the English description, option help and
  argparse skeleton labels, while the default Turkish help says `kullanım:`,
  `konumsal argümanlar:` and `seçenekler:`. The language is resolved before
  `parse_args`, so `--help` itself follows the requested language; wrapped
  usage lines keep their alignment.
- Unsupported version syntax is no longer guessed. Ruby's pessimistic `~>`
  operator used to be parsed with semver `~` semantics (wrong above two
  components: Ruby `~>1.2` means `>=1.2,<2.0`), and `~=3` — invalid in
  PEP 440, which requires two components — used to be read as `>=3,<4`.
  Both are now unresolvable and reported as skipped, like `!=`, `===`, npm
  hyphen ranges, pre-release suffixes and `lts/*` aliases. Regression tests
  pin every case (`tests/test_versiyon_referans.py`).
- Added a reference suite for the version comparator: PEP 440 examples
  (compatible release, wildcards, zero-padded equality, exclusive `>`/`<`)
  and node-semver examples (caret/tilde/X-ranges, `>1.2` == `>=1.3.0`),
  plus a test fixing the documented dialect difference (`>20`).
- `ci.py` docstring no longer claims that the bundled YAML parser reduces CI
  install time to zero (the workflow upgrades pip and installs `[dev]`
  dependencies); the claim now states the actual guarantee: no third-party
  YAML parser on the runtime dependency path.
- `scripts/check.sh` (and therefore the pre-commit hook) now runs
  `scripts/sir_tarama.sh` first: a grep-only scan for known provider key
  shapes (AWS, GitHub, Slack, Google, OpenAI-style `sk-`, private-key
  blocks). Its scope is deliberately narrow and documented in the script —
  it is not an entropy scanner.

### Planned
- Ruby `.ruby-version` finder
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
- Node LTS alias table (gallium→16, hydrogen→18, iron→20, jod→22,
  krypton→24); unknown aliases skipped, never guessed
- 218 tests, 92.32% coverage (Windows/py3.11 gate run), ruff + strict mypy,
  Linux/Windows/macOS CI
