# runtime-pin-sync

**Find and fix runtime version drift across `.nvmrc`, `.python-version`,
`.tool-versions`, `mise.toml`, `package.json` engines, `pyproject.toml`
`requires-python`, Dockerfile `FROM`, devcontainer, and CI `setup-*`/matrix —
without forcing anyone to switch tool managers.**

"Bende çalışıyor, CI'da patlıyor" ("works on my machine, breaks in CI") most
often means one thing: the same runtime version is pinned in six places and
someone only updated three. `runtime-pin-sync` reads every pin you already
have, compares them as **version sets** (a range like `>=18` never fights a
concrete `20`; `20` and `22` do), and can rewrite the outliers from one
authoritative source file.

[README in Turkish / Türkçesi](README.tr.md) ·
[Changelog](CHANGELOG.md) ·
[Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md)

## Install

```bash
pip install runtime-pin-sync
```

Python ≥ 3.10. **Zero runtime dependencies** (see
[Why zero dependencies?](#why-zero-dependencies)).

## 30-second example

```console
$ cd ornek-depolar/uyumsuz
$ runtime-pin-sync .
ÇALIŞMA ZAMANI  KAYNAK                    TÜR              SABİTLEME  DURUM
--------------  ------------------------  ---------------  ---------  --------
node            .github/workflows/ci.yml  ci-adım          20         referans
node            .nvmrc                    nvmrc            20         uyumlu
node            .tool-versions            tool-versions    20.11.0    uyumlu
node            Dockerfile                dockerfile       22         ÇELİŞKİ
node            package.json              engines          >=18       uyumlu
python          .python-version           python-version   3.9        ÇELİŞKİ
python          .tool-versions            tool-versions    3.12.1     referans
python          Dockerfile                dockerfile       3.12       uyumlu
python          pyproject.toml            requires-python  >=3.10     uyumlu

node: ci.yml=20 | .nvmrc=20 | .tool-versions=20.11.0 | Dockerfile=22 | package.json=>=18 → ÇELİŞKİ: Dockerfile
python: .python-version=3.9 | .tool-versions=3.12.1 | Dockerfile=3.12 | pyproject.toml=>=3.10 → ÇELİŞKİ: .python-version
SONUÇ: 2 çalışma zamanında çelişki bulundu.
$ echo $?
1
```

(Real output from `ornek-depolar/uyumsuz` in this repo, run from that directory;
every command below is shown with the directory it runs in. The CLI speaks
Turkish by default; the human-readable output — tables, conflict summaries,
sync plans and reasons, errors and warnings — is available in English via
`--lang en` or `RUNTIME_PIN_SYNC_LANG=en`. JSON field names stay stable
(Turkish) in both modes. English flag aliases: `--source`, `--variable`.)

Run in English:

```console
$ cd ornek-depolar/uyumsuz
$ runtime-pin-sync . --lang en
RUNTIME  SOURCE                    TYPE             PIN      STATUS
-------  ------------------------  ---------------  -------  ----------
node     .github/workflows/ci.yml  ci-step          20       reference
node     .nvmrc                    nvmrc            20       consistent
node     .tool-versions            tool-versions    20.11.0  consistent
node     Dockerfile                dockerfile       22       CONFLICT
node     package.json              engines          >=18     consistent
python   .python-version           python-version   3.9      CONFLICT
python   .tool-versions            tool-versions    3.12.1   reference
python   Dockerfile                dockerfile       3.12     consistent
python   pyproject.toml            requires-python  >=3.10   consistent

node: ci.yml=20 | .nvmrc=20 | .tool-versions=20.11.0 | Dockerfile=22 | package.json=>=18 → CONFLICT: Dockerfile
python: .python-version=3.9 | .tool-versions=3.12.1 | Dockerfile=3.12 | pyproject.toml=>=3.10 → CONFLICT: .python-version
RESULT: 2 runtimes have conflicts.
```

Fix it from a single source of truth (supports `--lang en` and Turkish):

```console
$ cd ornek-depolar/uyumsuz
$ runtime-pin-sync sync --source .tool-versions --dry-run --lang en
.python-version:1  '3.9' → '3.12.1' (to be changed)
Dockerfile:2  '22' → '20.11.0' (to be changed)
$ runtime-pin-sync sync --source .tool-versions
$ runtime-pin-sync . --lang en && echo clean
RESULT: all pins are consistent ✓
clean
```

## What it reads

| Runtime | Sources |
| --- | --- |
| Node | `.nvmrc`, `.node-version`, `package.json` → `engines.node`, `.tool-versions`, `mise.toml`, Dockerfile `FROM node:…`, devcontainer `image`/`features`, `actions/setup-node` + matrix |
| Python | `.python-version`, `pyproject.toml` → `requires-python`, `.tool-versions`, `mise.toml`, Dockerfile `FROM python:…`, devcontainer, `actions/setup-python` + matrix |
| Go | `go.mod` (`go`, `toolchain`), `.go-version`, Dockerfile `FROM golang:…`, `actions/setup-go` + matrix |
| Rust | `rust-toolchain`, `rust-toolchain.toml`, Dockerfile `FROM rust:…`, `dtolnay/rust-toolchain` |
| Java | `.java-version`, `.sdkmanrc` (`java=…`), `pom.xml` (`maven.compiler.release` etc.), Dockerfile `FROM eclipse-temurin:…` etc., `actions/setup-java` + matrix |

### Parser boundaries: Go and Java

Both readers are deliberately line-oriented; knowing where they stop prevents
false confidence.

**Go** — `go.mod` and `.go-version`:

```text
go 1.22               → >=1.22    (a minimum requirement, NOT a pin)
toolchain go1.23.1    → 1.23.1    (the exact toolchain; valid next to go 1.22)
```

`go 1.22` and `toolchain go1.23.1` therefore do not conflict: the first says
"at least 1.22", the second selects 1.23.1. `.go-version` is read as one exact
token. Supported: one `go`/`toolchain` directive per line, at any indentation,
`toolchain` with or without the `go` prefix. Not read: `toolchain default`,
multi-line directives, `GOTOOLCHAIN` from the environment, or versions hidden
inside comments/`replace` blocks.

**Java** — `pom.xml` and `.java-version`:

```xml
<properties>
  <maven.compiler.release>21</maven.compiler.release>
  <java.version>21</java.version>
</properties>
```

Every key from `maven.compiler.release`, `maven.compiler.source`,
`java.version`, `release` (in that order) is read, but only its FIRST
single-line literal element — the parent element is not validated, so a
`<release>` inside plugin configuration is matched too. `${...}` values are
reported as dynamic and skipped. Not read: multi-line or namespace-prefixed
elements; XML entities are not decoded (such values are reported as
unparseable). Values that differ per Maven profile, `toolchains.xml` and
`.mvn/jvm.config` are out of scope. `.java-version` is one exact token.

`.sdkmanrc` (SDKMAN!) is read as `key=value` lines; only the `java` key is a
Java source, other tools (`maven`, `gradle`) are ignored. `java=17.0.2+8`
keeps its build metadata; a distribution suffix (`java=21.0.1-tem`) is not
part of the version and is preserved when `sync` rewrites the line. `latest` or
any unrecognised value is reported as dynamic, an empty value as unreadable.

## Conflict semantics (the important part)

Every pin becomes a **set of versions**; two pins conflict only when their
sets are disjoint:

- `engines.node: ">=18"` vs `.nvmrc: 20` → **fine** (ranges don't fight pins).
- `requires-python: ">=3.10"` vs `.python-version: 3.9` → **conflict**.
- `.nvmrc: 20` vs `FROM node:22` → **conflict** (two concrete majors).
- `3.12` vs `3.12.*` vs `3.12.1` — prefix semantics: `3.12` covers `3.12.1`,
  but a fully specified version is a point: `20.1.0` does **not** intersect
  `>20.1.0` (it excludes itself from that range).
- CI **matrix** (`[20, 22]`), `mise.toml` lists (`node = ["22", "24"]`) and
  multi-value `.tool-versions` lines (`python 3.12.1 3.11.8`) are unions of
  installed versions, not separate conflicting pins: a pin equal to any member
  never conflicts, and no single member is promoted to "the" reference.
- Supported spec syntax: plain/prefix (`20`, `20.x`), ranges (`>= > <= < ==`),
  `||` unions, comma/AND lists (`>=3.10,<4.0`), semver `^`/`~`, PEP 440 `~=`.
- Unsupported spec syntax is never guessed: `!=`, `===`, npm hyphen ranges
  (`1.2.3 - 1.4.0`), pre-release suffixes (`1.2.3-beta.1`), Ruby's `~>`
  operator and Node aliases (`lts/iron`) are reported as unresolvable
  (skipped), never reinterpreted as a different range. `~=` needs at least
  two components (PEP 440), so `~=3` is unresolvable rather than silently
  read as `>=3,<4`.
- **Nothing dynamic is an error.** `${{ matrix.x }}`, unresolvable Dockerfile
  `ARG` tags, and unknown `lts/…` aliases are reported as *skipped*, not as
  failures. Supply values with `--degisken node=20` when you want them checked.

## Single source & `sync`

`--kaynak FILE` (alias `--source`) picks the authoritative file; `sync`
rewrites the others:

```bash
runtime-pin-sync sync --kaynak .tool-versions --dry-run   # plan, touch nothing
runtime-pin-sync sync --kaynak .tool-versions             # rewrite outliers
```

`sync` is deliberately conservative:

- only single-token, line-anchored replacements happen automatically, and
  only when BOTH the outlier and the reference value are plain fixed versions
  (no `>=`, `^`, `~`, `||`, no matrix lists); a range/grid reference disables
  automatic writes entirely;
- ranges (`>=18`), test grids, template expressions (`ARG TAG`-style tags) and
  any line where a replacement would be ambiguous are listed under
  **ELLE DÜZELTİLMELİ** (needs manual edit) — never rewritten;
- write targets are audited: symlinked files and paths resolving outside the
  repository are never written. Reads are guarded as well — a version file
  whose symlink resolves **outside** the repo (or a `*-version-file: ../..`
  target) is refused before its content can reach any report. A file symlink
  that stays **inside** the repo is repo content: it is read for comparison,
  but never written through, so it always ends up in the manual list; files
  are read/written byte-wise so CRLF and mixed line endings survive untouched
  outside the target line;
- writes are atomic: the new content goes to a sibling temp file, is flushed
  and `fsync`ed, then swapped in with `os.replace`. An interrupted or failed
  write leaves the original file byte-for-byte intact and no temp litter
  behind; the original file mode is preserved;
- when a pinned value occurs on several lines, ALL occurrences are rewritten;
  after writing, the repo is rescanned and any surviving conflict is reported
  (exit 1), never silently counted as success;
- `--dry-run` guarantees byte-identical files (verified by tests).

## Library API

```python
from runtime_pin_sync import tara, celiski   # aliases: scan, conflicts

pins = tara(".")          # list[Sabitleme]
for c in celiski(pins):   # list[Celiski]
    print(c.mesaj)        # "node: … → ÇELİŞKİ: Dockerfile"
```

## CI gate

```yaml
- uses: actions/setup-python@v5
- run: pipx run runtime-pin-sync . --json   # exit 1 on drift
```

## Why zero dependencies?

- TOML: stdlib `tomllib` (Python ≥ 3.11) with a small built-in fallback
  parser for Python 3.10 (`minitoml.py`).
- YAML: GitHub Actions files need only a focused subset; a self-contained
  ~170-line parser (`miniyaml.py`) covers it without external dependencies.
- JSON/JSONC: stdlib `json` plus a comment/trailing-comma tolerant wrapper
  for `devcontainer.json`.

A dev tool that runs in every CI job should install in one second and keep
its *runtime* free of third-party code: `pip install runtime-pin-sync` pulls no
packages. (Packaging uses `hatchling`; tests, lint and typing use the `[dev]`
extra — none of that reaches a user's runtime.)

### Supported YAML subset and comparison with PyYAML / ruamel.yaml

Our built-in YAML parser (`src/runtime_pin_sync/miniyaml.py`) intentionally implements the subset required by CI workflow files (`.github/workflows/*.yml`):

- **Supported syntax**:
  - Mappings: key-value pairs (`name: build`, `with:`) and nested indented maps.
  - Block lists (`- uses: actions/setup-node@v4`, `- run: ...`).
  - Flow lists (`node-version: [20, 22]`, `[3.10, 3.12]`).
  - Scalars: unquoted strings and numbers, single-quoted (`'20'`) and double-quoted (`"3.12"`) values.
  - Multi-line block text: literal (`|`, `|-`) and folded (`>`, `>-`).
  - Comments: `# ...` at line start or inline.

- **Deliberately excluded syntax**:
  - Anchors and aliases (`&anchor`, `*alias`)
  - Merge keys (`<<: *defaults`)
  - Custom data tags (`!!str`, `!custom`)
  - Complex / multi-line keys (`? [key]`)
  - Tab characters for indentation (rejected with a clear error to avoid ambiguous indentation)

- **Behavior on exotic YAML**:
  When encountering unsupported YAML features or syntax errors, `runtime-pin-sync` issues a clear warning (`could not read: unsupported YAML (...)` / `okunamadı: desteklenmeyen YAML (...)`) and continues evaluating the rest of the repository without crashing.

- **Why not PyYAML or ruamel.yaml?**:
  - *No compilation / C-extension requirements:* Works immediately across Linux, macOS, and Windows on any Python 3.10+ installation.
  - *No third-party YAML parser at runtime:* PyYAML/ruamel.yaml leave every
    user's dependency graph, so their advisories and upgrade churn do not
    reach you. This is **not** a claim that the project has no dependencies at
    all: building needs `hatchling`, and tests/lint need the `[dev]` extra.
  - *Predictable error boundaries:* Workflow parsing errors degrade gracefully into localized warnings instead of throwing unhandled exceptions.

## Limitations (honest list)

- CLI output defaults to Turkish; `--lang en` (or `RUNTIME_PIN_SYNC_LANG=en`)
  translates the human-readable surface: status tables, conflict summaries,
  sync change lists and *all* manual-edit reasons, error messages, scan
  warnings and parser warnings — and `--help` itself (description, options and
  argparse's `usage:`/section labels). Warnings are produced in the selected
  language **where they are created** (finders, the Dockerfile/CI readers and
  the bundled YAML/TOML parsers), not post-translated by string replacement.
  The only remaining display substitution is the fixed `→ ÇELİŞKİ:` marker on
  conflict lines (`→ CONFLICT:` in English), not a sentence table.
  A sentence missing from the message catalogue therefore cannot leak Turkish
  into English output; `tests/test_dil.py` fails if a single Turkish character
  shows up in an English report. One honest exception: on Python 3.11+ an
  invalid TOML file is diagnosed by stdlib `tomllib`, whose own text is quoted
  verbatim (English) inside the otherwise localized warning. JSON keys are not
  translated (they are a stable API). The table's `TYPE` column is a translated
  label (`ci-adim` → `ci-step`, `dosya` → `file`); the JSON `tur` field always
  keeps the stable id.
- A directory that cannot be read is never skipped silently: the scan stops
  with exit code 2 (`scan incomplete — unreadable director(y/ies): …`) instead
  of presenting a partial scan as a clean result.
- CI workflow files use our minimal YAML subset; exotic YAML raises an
  informative warning instead of a false report or crash.
- Package/dependency versions are out of scope (that's `renovate` /
  `syncpack`); so are compiler/ABI drift and tool installation.
- Node `lts/<codename>` resolves via a built-in, manually kept table
  (gallium→16, hydrogen→18, iron→20, jod→22, krypton→24, per the official
  nodejs/Release schedule); unknown aliases are skipped, never guessed.
  The moving alias `lts/*` is treated as *dynamic* — the table's newest entry
  is not presented as a current fact.
- Prerelease suffixes (`1.85.0-rc1`) and `!=` exclusion ranges are reported
  as warnings rather than mis-compared.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
bash scripts/check.sh    # secret scan + ruff + mypy --strict + pytest --cov-fail-under=85

# packaging check (same idea as CI's `paket` job: wheel only, no PyPI)
python -m build --outdir dist
python -m venv .venv-wheel && .venv-wheel/bin/pip install --no-index \
    --find-links dist runtime-pin-sync
```

## License

MIT © 2026 Yusuf Berat Zengin
