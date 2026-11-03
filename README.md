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
$ runtime-pin-sync .
ÇALIŞMA ZAMANI  KAYNAK                    TÜR              SABİTLEME  DURUM
--------------  ------------------------  ---------------  ---------  --------
node            .github/workflows/ci.yml  ci-adim          20         referans
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

(Real output from `ornek-depolar/uyumsuz` in this repo. The CLI speaks Turkish
by design; glossary: `uyumlu` = consistent, `ÇELİŞKİ` = conflict, `referans` =
reference source, `dinamik, atlandı` = dynamic expression, skipped,
`okunamadı` = could not parse. English flag aliases: `--source`, `--variable`.)

Fix it from a single source of truth:

```console
$ runtime-pin-sync sync --kaynak .tool-versions --dry-run
.python-version:1  '3.9' → '3.12.1' (değiştirilecek)
Dockerfile:2  '22' → '20.11.0' (değiştirilecek)
$ runtime-pin-sync sync --kaynak .tool-versions     # real rewrite, only the target lines
$ runtime-pin-sync . && echo clean
SONUÇ: tüm sabitlemeler uyumlu ✓
clean
```

## What it reads

| Runtime | Sources |
| --- | --- |
| Node | `.nvmrc`, `.node-version`, `package.json` → `engines.node`, `.tool-versions`, `mise.toml`, Dockerfile `FROM node:…`, devcontainer `image`/`features`, `actions/setup-node` + matrix |
| Python | `.python-version`, `pyproject.toml` → `requires-python`, `.tool-versions`, `mise.toml`, Dockerfile `FROM python:…`, devcontainer, `actions/setup-python` + matrix |
| Go | `go.mod` (`go`, `toolchain`), `.go-version`, Dockerfile `FROM golang:…`, `actions/setup-go` + matrix |
| Rust | `rust-toolchain`, `rust-toolchain.toml`, Dockerfile `FROM rust:…`, `dtolnay/rust-toolchain` |
| Java | `.java-version`, `pom.xml` (`maven.compiler.release` etc.), Dockerfile `FROM eclipse-temurin:…` etc., `actions/setup-java` + matrix |

## Conflict semantics (the important part)

Every pin becomes a **set of versions**; two pins conflict only when their
sets are disjoint:

- `engines.node: ">=18"` vs `.nvmrc: 20` → **fine** (ranges don't fight pins).
- `requires-python: ">=3.10"` vs `.python-version: 3.9` → **conflict**.
- `.nvmrc: 20` vs `FROM node:22` → **conflict** (two concrete majors).
- `3.12` vs `3.12.*` vs `3.12.1` — prefix semantics: `3.12` covers `3.12.1`,
  but a fully specified version is a point: `20.1.0` does **not** intersect
  `>20.1.0` (it excludes itself from that range).
- CI **matrix** (`[20, 22]`) is a test grid: it is compared as the *union* of
  its entries, so a pin equal to any grid member never conflicts.
- Supported spec syntax: plain/prefix (`20`, `20.x`), ranges (`>= > <= < ==`),
  `||` unions, comma/AND lists (`>=3.10,<4.0`), semver `^`/`~`, PEP 440 `~=`.
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
  repository are never touched — the boundary also guards **reads** (a
  symlinked version file or `*-version-file: ../..` target is refused before
  its content can leak into any report); files are read/written byte-wise so
  CRLF and mixed line endings survive untouched outside the target line;
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
- YAML: GitHub Actions files need only a small subset (maps, block/flow
  sequences, scalars); a ~170-line parser (`miniyaml.py`) covers it and
  refuses everything else with an "okunamadı" note — no PyYAML needed.
- JSON/JSONC: stdlib `json` plus a comment/trailing-comma tolerant wrapper
  for `devcontainer.json`.

A dev tool that runs in every CI job should install in one second and never
supply-chain-surprise you.

## Limitations (honest list)

- CLI messages are Turkish (flags have English aliases); a `--lang en`
  output mode is planned (see issues).
- CI workflow files use our minimal YAML subset; exotic YAML raises an
  "okunamadı" warning instead of a false report.
- Package/dependency versions are out of scope (that's `renovate` /
  `syncpack`); so are compiler/ABI drift and tool installation.
- Node `lts/<codename>` resolves via a built-in, manually kept table
  (gallium→16, hydrogen→18, iron→20, jod→22, krypton→24, per the official
  nodejs/Release schedule); unknown aliases are skipped, never guessed.
  The moving alias `lts/*` is treated as *dynamic* — the table's newest entry
  is not presented as a current fact.
- Prerelease suffixes (`1.85.0-rc1`) and `!=` exclusion ranges are reported
  as "okunamadı" rather than mis-compared.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
bash scripts/check.sh    # ruff + mypy --strict + pytest --cov-fail-under=85
```

## License

MIT © 2026 Yusuf Berat Zengin
