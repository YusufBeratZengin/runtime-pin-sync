"""`scripts/sir_tarama.sh` davranış testleri — kapının kendisi test edilir.

Neden ayrı bir test: bu betik `check.sh`in ve pre-commit kancasının ilk
adımıdır. Betik "temiz" dediğinde sonucun gerçekten TARANDIĞINA güvenmek
gerekir. Bu testler grep'in üç çıkış durumunu (eşleşme / eşleşme yok / hata)
ayrı ayrı sabitler; betik geçici bir depo kopyası üzerinde çalıştırılır, böylece
proje ağacına test verisi yazılmaz.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
BETIK = KOK / "scripts" / "sir_tarama.sh"

# Açıkça UYDURMA değerler (gerçek anahtar değil): "XXXX…".
SAHTE_AWS = "AKIA" + "X" * 16
SAHTE_ANAHTAR_SATIRI = f"aws_access_key_id = {SAHTE_AWS}\n"

TAM_HATA_SHIMI = """#!/usr/bin/env bash
echo "grep: sahte okuma hatası" >&2
exit 2
"""

KISMI_HATA_SHIMI = """#!/usr/bin/env bash
case "$*" in
  *AKIA*) echo "./ayar.txt:1:aws_access_key_id = (kaldırıldı)"; exit 0 ;;
esac
echo "grep: sahte okuma hatası" >&2
exit 2
"""


def _bash() -> str:
    yol = shutil.which("bash")
    if yol is None:
        pytest.skip("bash bulunamadı (Windows'ta Git-Bash gerekir)")
    return yol


def _depo(tmp_path: Path) -> Path:
    """Betiği geçici bir depo köküne kopyalar (betik ../ kökünü tarar)."""
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    hedef = tmp_path / "scripts" / "sir_tarama.sh"
    hedef.write_bytes(BETIK.read_bytes())
    return hedef


def _kos(depo: Path, ek_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    ortam = dict(os.environ)
    if ek_path is not None:
        ortam["PATH"] = f"{ek_path}{os.pathsep}{ortam.get('PATH', '')}"
    return subprocess.run(
        [_bash(), str(depo / "scripts" / "sir_tarama.sh")],
        cwd=str(depo),
        env=ortam,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _shim(dizin: Path, govde: str) -> None:
    """`grep` yerine geçen sahte komut: grep'in çıkış kodunu taklit eder."""
    dizin.mkdir(parents=True, exist_ok=True)
    yol = dizin / "grep"
    yol.write_bytes(govde.encode("utf-8"))   # bayt yazımı: LF korunur (Windows)
    yol.chmod(0o755)


def test_temiz_agac_sifir_doner(tmp_path):
    _depo(tmp_path)
    (tmp_path / "paket.json").write_text('{"engines": {"node": "20"}}\n', encoding="utf-8")
    sonuc = _kos(tmp_path)
    assert sonuc.returncode == 0, sonuc.stderr
    assert "temiz" in sonuc.stdout


def test_bulgu_bir_doner_ve_satiri_listeler(tmp_path):
    _depo(tmp_path)
    (tmp_path / "ayar.txt").write_text(SAHTE_ANAHTAR_SATIRI, encoding="utf-8")
    sonuc = _kos(tmp_path)
    assert sonuc.returncode == 1
    assert "ayar.txt" in sonuc.stdout
    assert "temiz" not in sonuc.stdout


def test_grep_hatasi_temiz_sayilmaz(tmp_path):
    """Zorunlu bulgu regresyonu: grep >=2 ile dönerse tarama EKSİKtir.

    Düzeltmeden önce (`... || true`) betik hata çıktısını yutuyor, "temiz"
    basıyor ve çıkış 0 veriyordu; yani okunamayan dosya/dizin sessizce
    taranmamış sayılıyordu.
    """
    _depo(tmp_path)
    _shim(tmp_path / "bin", TAM_HATA_SHIMI)
    sonuc = _kos(tmp_path, ek_path=tmp_path / "bin")
    assert sonuc.returncode == 2, (sonuc.stdout, sonuc.stderr)
    assert "temiz" not in sonuc.stdout
    assert "HATA" in sonuc.stderr


def test_grep_hatasi_bulgu_varsa_bulgu_kazanir(tmp_path):
    """Kısmi hata: bir desen eşleşir, diğerleri okuma hatası verir.

    Bulgu kaybolmaz (çıkış 1) ama eksik tarama uyarısı da basılır.
    """
    _depo(tmp_path)
    (tmp_path / "ayar.txt").write_text(SAHTE_ANAHTAR_SATIRI, encoding="utf-8")
    _shim(tmp_path / "bin", KISMI_HATA_SHIMI)
    sonuc = _kos(tmp_path, ek_path=tmp_path / "bin")
    assert sonuc.returncode == 1
    assert "ayar.txt" in sonuc.stdout
    assert "UYARI" in sonuc.stderr


def test_ayni_agac_shim_yokken_temiz_shim_varken_hata(tmp_path):
    """Kontrol testi: fark gerçekten grep çıkış kodundan geliyor."""
    _depo(tmp_path)
    (tmp_path / "paket.json").write_text("{}\n", encoding="utf-8")
    assert _kos(tmp_path).returncode == 0
    _shim(tmp_path / "bin", TAM_HATA_SHIMI)
    assert _kos(tmp_path, ek_path=tmp_path / "bin").returncode == 2
