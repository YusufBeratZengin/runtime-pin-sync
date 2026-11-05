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
  (secret scan + ruff + strict mypy + pytest ≥ 85% coverage); the repo's
  `.git/hooks/pre-commit` runs it before every commit.

## Setup

```bash
python3 -m venv .venv
# -c pins the gate tools to the versions this repo is verified with
.venv/bin/pip install -e ".[dev]" -c scripts/kisitlar-dev.txt
bash scripts/check.sh

# packaging: wheel-only clean install (no runtime deps, no PyPI)
python -m build --outdir dist
python -m venv .venv-wheel
.venv-wheel/bin/pip install --no-index --find-links dist runtime-pin-sync
```

### Two layers of dev pins

`pyproject.toml` `[dev]` carries bounded ranges (`>=x,<y`) — the floor every
contributor can install. `scripts/kisitlar-dev.txt` carries exact versions —
what CI and `scripts/check.sh` actually use, so a red gate means your code,
not a tool upgrade. Bump the lock deliberately, rerun the gate, commit.
`tests/test_bagimlilik_kisitlari.py` fails if a lock falls outside the
matching range or names a package that `[dev]` does not list.

### Secret scan exit codes

`scripts/sir_tarama.sh` (first step of the gate, also run by the pre-commit
hook) is a known-pattern scanner, not an entropy scanner. It exits `0` when
every pattern was scanned with no match, `1` on a finding, and `2` when the
scan could not complete (`grep` missing, permission/IO error). `2` fails the
gate: an incomplete scan is never reported as clean.

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
