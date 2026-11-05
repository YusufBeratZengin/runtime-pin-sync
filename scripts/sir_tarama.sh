#!/usr/bin/env bash
# Sır taraması: ağaçta BİLİNEN sağlayıcı anahtarı biçimlerini arar.
# Genel amaçlı entropi tarayıcısı değildir; kapsam aşağıdaki desenlerdir ve
# bu sınır dürüstçe dar tutulmuştur. Yalnız grep kullanır (ek bağımlılık yok).
#
# Çıkış kodları (check.sh ve pre-commit bu kapıdan geçer):
#   0 = temiz             her desen tarandı, eşleşme yok
#   1 = bulgu var         eşleşen satırlar yukarıda listelendi
#   2 = tarama YAPILAMADI grep yok ya da grep hata verdi (izin, G/Ç, desen)
#
# 2 ile 1'in ayrılması önemlidir: "eşleşme yok" (grep çıkışı 1) temiz sonuçtur,
# grep'in hata çıkışı (>=2) ise taramanın EKSİK olduğunu gösterir. Eksik tarama
# hiçbir zaman "temiz" diye sunulmaz; kapı başarısız olur.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

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

if ! command -v grep >/dev/null 2>&1; then
  echo "[sır taraması] HATA: grep bulunamadı; tarama yapılamadı" >&2
  echo "[sır taraması] BAŞARISIZ: sonuç 'temiz' sayılamaz." >&2
  exit 2
fi

bulundu=0
hata=0
for desen in "${DESENLER[@]}"; do
  # grep çıkışı: 0 = eşleşme, 1 = eşleşme yok, >=2 = gerçek hata.
  cikti="$(grep -rInE "${HARIC[@]}" -- "$desen" .)"
  durum=$?
  case "$durum" in
    0)
      while IFS= read -r satir; do
        [ -n "$satir" ] || continue
        echo "[sır taraması] $satir"
        bulundu=1
      done <<< "$cikti"
      ;;
    1)
      : # bu desen için eşleşme yok — normal durum
      ;;
    *)
      echo "[sır taraması] HATA: grep taraması başarısız (çıkış $durum, desen: $desen)." >&2
      echo "[sır taraması] Tarama eksik olabilir; sonuç 'temiz' sayılmaz." >&2
      hata=1
      ;;
  esac
done

if [ "$bulundu" -ne 0 ]; then
  echo "[sır taraması] BAŞARISIZ: bulunan satırlar incelenmeli (anahtar değilse desen daraltılmalı)" >&2
  [ "$hata" -eq 0 ] || echo "[sır taraması] UYARI: tarama sırasında hata da oluştu; liste eksik olabilir." >&2
  exit 1
fi
if [ "$hata" -ne 0 ]; then
  echo "[sır taraması] BAŞARISIZ: tarama tamamlanamadı, sonuç güvenilir değil." >&2
  exit 2
fi
echo "[sır taraması] temiz"
