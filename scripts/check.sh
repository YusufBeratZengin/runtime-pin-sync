#!/usr/bin/env bash
# Tek kapı: sır taraması + lint + tip kontrolü + testler + kapsama eşiği.
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

# Geliştirme araçları: aralıklar pyproject.toml [dev]'de, tam sürümler
# scripts/kisitlar-dev.txt'te (tekrarlanabilirlik). Kilit dosyası yoksa
# aralıklarla kurulur; kapı yine çalışır.
KISIT=scripts/kisitlar-dev.txt
if [ -f "$KISIT" ]; then KISIT_ARG=(-c "$KISIT"); else KISIT_ARG=(); fi

ensure() {  # $1 = import adı, $2 = pip paketi
  if ! "$PY" -c "import $1" >/dev/null 2>&1; then
    echo "[check] $2 kuruluyor (geliştirme bağımlılığı)..."
    # bash 3.2 (macOS) + `set -u`: boş dizinin genişlemesi hata verir,
    # bu yüzden +"..." deyimi kullanılır.
    "$PY" -m pip install -q ${KISIT_ARG[@]+"${KISIT_ARG[@]}"} "$2"
  fi
}
ensure pytest "pytest>=8.0.0,<10.0.0"
ensure pytest_cov "pytest-cov>=5.0.0,<8.0.0"
ensure ruff "ruff>=0.8.0,<1.0.0"
ensure mypy "mypy>=1.10.0,<2.0.0"

# Temiz klonda src yolunu ortamda da garantiye al
export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"

echo "== sır taraması =="
bash scripts/sir_tarama.sh
echo "== lint (ruff) =="
"$PY" -m ruff check src tests scripts
echo "== tip (mypy) =="
"$PY" -m mypy src
echo "== testler (pytest, kapsama >=85) =="
"$PY" -m pytest -q --cov=runtime_pin_sync --cov-report=term-missing --cov-fail-under=85
echo "check.sh: TÜMÜ YEŞİL ✔"
