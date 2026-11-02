# Contributing

Thanks for considering a contribution! Small, focused PRs are ideal.

## Ground rules

- **Zero runtime dependencies is a feature.** A PR that adds one must make
  the case in the issue first. Dev-only dependencies (`[dev]` extra) are fine.
- **Never guess versions.** Unknown spec syntax, unknown LTS aliases and
  dynamic `${{ }}` expressions must become `okunamadı` / `dinamik` notes,
  not invented values.
- Every accepted behavior needs a failing test first (bug) or a test written
  alongside (feature). The gate is `bash scripts/check.sh`
  (ruff + strict mypy + pytest ≥ 85% coverage).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
bash scripts/check.sh
```

## Layout

- `src/runtime_pin_sync/versiyon.py` — spec → version-set engine
  (range algebra; the most-tested module).
- `src/runtime_pin_sync/bulucular/` — one file per ecosystem; each finder
  is independent and must never raise, only return `Sabitleme`s.
- `src/runtime_pin_sync/docker.py` / `ci.py` — Dockerfile/devcontainer and
  GitHub Actions readers.
- `src/runtime_pin_sync/karsilastir.py` — reference selection + conflict
  detection; `yaz.py` — conservative rewriting; `rapor.py` — table/JSON.
- `ornek-depolar/` — obviously fake example repos used by tests and README.

## Adding a finder

1. New module under `bulucular/` returning `list[Sabitleme]` (never raises).
2. Register the filename in `tara.py::_dosya_işle`.
3. Unit tests + one entry in an `ornek-depo` + row in both READMEs' tables.

## Style

Turkish identifiers/messages are intentional (CLI copy, module names); doc
strings in Turkish or English both fine. 100-char lines, type hints required
in `src/` (strict mypy).

## Reporting bugs

Include: `runtime-pin-sync --version`, OS, a minimal fake repo reproducing
the drift, and both expected and actual output. Never include real internal
URLs or credentials — reduce fixtures to obviously fake data.
