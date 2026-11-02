#!/usr/bin/env bash
# Tek kapı: lint + tip kontrolü + testler + kapsama eşiği.
# Kullanım: bash scripts/check.sh   (proje kökünden)
# Düz Linux/macOS/Windows(Git-Bash) + python3 ile çalışır; ek araç gerekmez.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
elif [ -x .venv/Scripts/python ]; then        # Windows sanal ortamı
  PY=.venv/Scripts/python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then  # Windows'ta python3 olmayabilir
  PY=python
else
  echo "[check] python3/python bulunamadı"; exit 127
fi

ensure() {  # $1 = import adı, $2 = pip paketi
  if ! "$PY" -c "import $1" >/dev/null 2>&1; then
    echo "[check] $2 kuruluyor (geliştirme bağımlılığı)..."
    "$PY" -m pip install -q "$2"
  fi
}
ensure pytest pytest
ensure pytest_cov pytest-cov
ensure ruff ruff
ensure mypy mypy

echo "== lint (ruff) =="
"$PY" -m ruff check src tests scripts
echo "== tip (mypy) =="
"$PY" -m mypy src
echo "== testler (pytest, kapsama >=85) =="
"$PY" -m pytest -q --cov=runtime_pin_sync --cov-report=term-missing --cov-fail-under=85
echo "check.sh: TÜMÜ YEŞİL ✔"
