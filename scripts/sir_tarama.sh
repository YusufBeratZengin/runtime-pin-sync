#!/usr/bin/env bash
# Sır taraması: ağaçta BİLİNEN sağlayıcı anahtarı biçimlerini arar.
# Genel amaçlı entropi tarayıcısı değildir; kapsam aşağıdaki desenlerdir ve
# bu sınır dürüstçe dar tutulmuştur. Yalnız grep kullanır (ek bağımlılık yok).
# Bulgu varsa çıkış kodu 1 — check.sh ve pre-commit bu kapıdan geçer.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

DESENLER=(
  'AKIA[0-9A-Z]{16}'                      # AWS access key id
  'ASIA[0-9A-Z]{16}'                      # AWS geçici access key id
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'    # özel anahtar bloğu
  'gh[pousr]_[A-Za-z0-9]{20,}'            # GitHub token'ları
  'github_pat_[A-Za-z0-9_]{20,}'          # GitHub fine-grained PAT
  'xox[abprs]-[A-Za-z0-9-]{10,}'          # Slack token
  'sk-[A-Za-z0-9]{24,}'                   # OpenAI biçimli anahtar
  'AIza[0-9A-Za-z_-]{35}'                 # Google API anahtarı
)

# Yerel çalışma notları (HAT-*) ve üretilen çıktılar taranmaz.
HARIC=(
  --binary-files=without-match
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.venv-wheel
  --exclude-dir=dist --exclude-dir=build --exclude-dir=__pycache__
  --exclude-dir=.pytest_cache --exclude-dir=.mypy_cache --exclude-dir=.ruff_cache
  --exclude=HAT-NOTLAR.md --exclude=HAT-META.json --exclude=HAT-HAZIR
)

bulundu=0
for desen in "${DESENLER[@]}"; do
  while IFS= read -r satir; do
    echo "[sır taraması] $satir"
    bulundu=1
  done < <(grep -rInE "${HARIC[@]}" -- "$desen" . || true)
done

if [ "$bulundu" -ne 0 ]; then
  echo "[sır taraması] BAŞARISIZ: bulunan satırlar incelenmeli (anahtar değilse desen daraltılmalı)" >&2
  exit 1
fi
echo "[sır taraması] temiz"
