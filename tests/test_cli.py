"""CLI sözleşmesi: çıkış kodları, --json, sync, --degisken, --kaynak."""

import json
import os
from pathlib import Path

import pytest

from conftest import yaz
from runtime_pin_sync.cli import main

PROJE = str(Path(__file__).resolve().parent.parent / "ornek-depolar")


def test_check_çelişkide_bir(tmp_path, capsys):
    assert main([f"{PROJE}/uyumsuz"]) == 1
    out = capsys.readouterr().out
    assert "ÇELİŞKİ" in out


def test_check_uyumlu_sıfır(tmp_path, capsys):
    assert main([f"{PROJE}/tutarli"]) == 0
    assert "uyumlu" in capsys.readouterr().out


def test_check_bozuk_sıfır_uyarılı(tmp_path, capsys):
    assert main([f"{PROJE}/bozuk"]) == 0
    out = capsys.readouterr().out
    assert "okunamadı" in out and "dinamik" in out


def test_json_çıktı_geçerli(tmp_path, capsys):
    assert main([f"{PROJE}/uyumsuz", "--kaynak", ".tool-versions", "--json"]) == 1
    d = json.loads(capsys.readouterr().out)
    assert {c["calisma_zamani"] for c in d["celiskiler"]} == {"node", "python"}
    assert all(k in d for k in ("sabitlemeler", "celiskiler", "uyarilar", "dinamikler"))
    assert any(s["durum"] == "referans" for s in d["sabitlemeler"])


def test_kaynak_çelişki_listesini_değiştirir(tmp_path, capsys):
    # .nvmrc=20 kaynaksa Dockerfile 22 hatalıdır; tam tersi de geçerlidir
    assert main([f"{PROJE}/uyumsuz", "--kaynak", ".nvmrc"]) == 1
    out = capsys.readouterr().out
    assert "referans" in out


def test_kaynak_yoksa_iki(tmp_path, capsys):
    assert main([f"{PROJE}/uyumsuz", "--kaynak", "yok.txt"]) == 2
    assert "kaynak bulunamadı" in capsys.readouterr().err


def test_path_yoksa_iki(tmp_path):
    assert main(["/yok/böyle/bir/depoda/yok"]) == 2


def test_sync_kaynaksız_iki(tmp_path, capsys):
    assert main(["sync", f"{PROJE}/tutarli"]) == 2
    assert "--kaynak" in capsys.readouterr().err


def test_sync_dry_run_dosyaya_dokunmaz(tmp_path, capsys):
    depo = tmp_path / "depo"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, ".nvmrc", "22\n")
    assert main(["sync", str(depo), "--kaynak", ".tool-versions",
                 "--dry-run"]) == 0
    assert (depo / ".nvmrc").read_text(encoding="utf-8") == "22\n"
    assert "değiştirilecek" in capsys.readouterr().out


def test_sync_gerçek_yazar_tekrar_temiz(tmp_path, capsys):
    depo = tmp_path / "depo2"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, ".nvmrc", "22\n")
    assert main(["sync", str(depo), "--kaynak", ".tool-versions"]) == 0
    assert (depo / ".nvmrc").read_text(encoding="utf-8") == "20.11.0\n"
    assert main(["check", str(depo)]) == 0


def test_sync_json(tmp_path, capsys):
    depo = tmp_path / "depo3"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, ".nvmrc", "22\n")
    assert main(["sync", str(depo), "--kaynak", ".tool-versions",
                 "--dry-run", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["kuru_calis"] is True
    assert d["degisiklikler"][0]["eski"] == "22"


def test_sync_elle_olsa_bir(tmp_path, capsys):
    depo = tmp_path / "depo4"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, "package.json", '{"engines": {"node": ">=22"}}\n')
    assert main(["sync", str(depo), "--kaynak", ".tool-versions"]) == 1
    assert "ELLE DÜZELTİLMELİ" in capsys.readouterr().out


def test_sync_uyumlu_depoda_boş_geçer(tmp_path, capsys):
    assert main(["sync", f"{PROJE}/tutarli", "--kaynak", ".nvmrc"]) == 0
    assert "her şey zaten kaynakla uyumlu" in capsys.readouterr().out


def test_degisken_bozuk_biçim_iki(tmp_path, capsys):
    assert main([f"{PROJE}/tutarli", "--degisken", "sadecead"]) == 2
    assert "AD=DEĞER" in capsys.readouterr().err


def test_degisken_ci_ifadesini_çözer(tmp_path, capsys):
    depo = tmp_path / "depo5"
    yaz(depo, ".github/workflows/ci.yml",
        "jobs:\n  t:\n    steps:\n      - uses: actions/setup-node@v4\n"
        "        with:\n          node-version: ${{ inputs.node }}\n")
    assert main([str(depo)]) == 0
    assert "dinamik" in capsys.readouterr().out
    assert main([str(depo), "--degisken", "node=20"]) == 0
    assert "dinamik" not in capsys.readouterr().out


def test_version_bayrağı(capsys):
    try:
        main(["--version"])
        raised = False
    except SystemExit as e:
        raised = e.code == 0
    assert raised
    assert "0.1.0" in capsys.readouterr().out


def test_ingilizce_bayraklar(tmp_path, capsys):
    assert main([f"{PROJE}/uyumsuz", "--source", ".tool-versions"]) == 1


def test_cli_ingilizce_tablo_ve_ozet(capsys):
    assert main([f"{PROJE}/uyumsuz", "--lang", "en"]) == 1
    out = capsys.readouterr().out
    assert "RUNTIME" in out and "SOURCE" in out and "STATUS" in out
    assert "CONFLICT: Dockerfile" in out
    assert "RESULT: 2 runtimes have conflicts." in out


def test_cli_ingilizce_uyumlu(capsys):
    assert main([f"{PROJE}/tutarli", "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "RESULT: all pins are consistent ✓" in out


def test_cli_ingilizce_hatalar(capsys):
    # kaynak yok hatası
    assert main([f"{PROJE}/uyumsuz", "--lang", "en", "--source", "nonexistent.txt"]) == 2
    err = capsys.readouterr().err
    assert "error: source not found or yields no versions: nonexistent.txt" in err

    # sync için kaynak eksik hatası
    assert main(["sync", f"{PROJE}/tutarli", "--lang", "en"]) == 2
    err = capsys.readouterr().err
    assert "error: sync requires --source (single source of truth file)" in err

    # bozuk değişken hatası
    assert main([f"{PROJE}/tutarli", "--lang", "en", "--variable", "invalid_var"]) == 2
    err = capsys.readouterr().err
    assert "error: --variable must be in 'NAME=VALUE' format: 'invalid_var'" in err


def test_cli_ingilizce_sync_kuru_calis(tmp_path, capsys):
    depo = tmp_path / "depo_en"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, ".nvmrc", "22\n")
    assert main(["sync", str(depo), "--source", ".tool-versions", "--dry-run", "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "(to be changed)" in out


def test_cli_ingilizce_sync_elle_duzeltme(tmp_path, capsys):
    depo = tmp_path / "depo_en_elle"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, "package.json", '{"engines": {"node": ">=22"}}\n')
    assert main(["sync", str(depo), "--source", ".tool-versions", "--lang", "en"]) == 1
    out = capsys.readouterr().out
    assert "MUST BE FIXED MANUALLY:" in out


def test_cli_ingilizce_sync_zaten_uyumlu(capsys):
    assert main(["sync", f"{PROJE}/tutarli", "--source", ".nvmrc", "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "nothing to sync - all pins already match the source." in out


def test_cli_ingilizce_bozuk_depo_notlari(capsys):
    assert main([f"{PROJE}/bozuk", "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "NOTES:" in out
    assert "could not read" in out or "dynamic expression" in out


def test_cli_lang_ortam_degiskeni(monkeypatch, capsys):
    monkeypatch.setenv("RUNTIME_PIN_SYNC_LANG", "en")
    assert main([f"{PROJE}/tutarli"]) == 0
    out = capsys.readouterr().out
    assert "RESULT: all pins are consistent ✓" in out


def test_temiz_ortamda_pytest_src_bulur():
    import os
    import subprocess
    import sys
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    # PYTHONPATH olmaksızın pytest'in pyproject.toml pythonpath=["src"] ile çalıştığını doğrula
    cmd = [sys.executable, "-m", "pytest", "tests/test_bulucular.py", "-q"]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert res.returncode == 0, f"pytest başarısız: {res.stderr}\n{res.stdout}"


def test_boş_kaynak_kullanılabilir_sürüm_istiyor(tmp_path, capsys):
    depo = tmp_path / "depo_bos_kaynak"
    yaz(depo, ".nvmrc", "")
    yaz(depo, "Dockerfile", "FROM node:22\n")

    assert main([str(depo), "--kaynak", ".nvmrc"]) == 2
    assert "sürüm üretmiyor" in capsys.readouterr().err

    assert main(["sync", str(depo), "--kaynak", ".nvmrc"]) == 2
    assert capsys.readouterr().err  # sync de aynı hatayla durur

    assert main([str(depo), "--kaynak", ".nvmrc", "--lang", "en"]) == 2
    assert "yields no versions" in capsys.readouterr().err


def test_cli_ingilizce_sync_gerekceleri_tamamen_ingilizce(tmp_path, capsys):
    depo = tmp_path / "depo_en_gerekce"
    yaz(depo, ".tool-versions", "node 20.11.0\n")
    yaz(depo, "Dockerfile", "ARG TAG=22-slim\nFROM node:${TAG}\n")
    yaz(depo, "package.json", '{"engines": {"node": ">=22"}}\n')
    assert main(["sync", str(depo), "--source", ".tool-versions",
                 "--dry-run", "--lang", "en"]) == 1
    out = capsys.readouterr().out
    assert "standalone" in out                  # şablonlu FROM gerekçesi
    assert "is a range/matrix" in out          # aralık hedef gerekçesi
    for tr in ("satırda", "dosya okunamadı", "aralık/ızgara", "uygulanamadı",
               "sabit sürüm"):
        assert tr not in out, f"İngilizce çıktıda Türkçe gerekçe: {tr}"


def test_cli_ingilizce_uyarilar_tamamen_ingilizce(tmp_path, capsys):
    depo = tmp_path / "depo_en_uyari"
    yaz(depo, ".nvmrc", "")
    yaz(depo, ".python-version", "surum-yok")
    yaz(depo, "Dockerfile", "FROM node:22-sucuk\n")
    yaz(depo, ".github/workflows/ci.yml", "jobs:\n\tbuild: x\n")
    assert main([str(depo), "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "could not read" in out
    assert "unsupported YAML" in out
    for tr in ("okunamadı", "boş dosya", "çözümlenemedi", "desteklenmeyen",
               "sekme", "sonek"):
        assert tr not in out, f"İngilizce çıktıda Türkçe uyarı: {tr}"


def test_tarama_eksikse_sıfır_dönmez(tmp_path, monkeypatch, capsys):
    """Okunamayan dizin "temiz sonuç" gibi görünmemeli: check ve sync exit 2."""
    depo = tmp_path / "eksik_tarama"
    yaz(depo, ".nvmrc", "20")
    (depo / "kilitli").mkdir()
    gerçek_walk = os.walk

    def walk(kok, *a, **k):
        onerror = k["onerror"]
        for yürütülen, dizinler, dosyalar in gerçek_walk(kok):
            dizinler[:] = [d for d in dizinler if d != "kilitli"]
            if Path(yürütülen) == depo:
                onerror(PermissionError(13, "Permission denied",
                                        str(depo / "kilitli")))
            yield yürütülen, dizinler, dosyalar

    monkeypatch.setattr(os, "walk", walk)
    assert main([str(depo)]) == 2
    assert "tarama eksik" in capsys.readouterr().err
    assert main(["sync", str(depo), "--kaynak", ".nvmrc", "--dry-run"]) == 2
    assert "tarama eksik" in capsys.readouterr().err
    assert main([str(depo), "--lang", "en"]) == 2
    assert "scan incomplete" in capsys.readouterr().err


# --- yardım metni de seçilen dili izler --------------------------------------

def _yardim(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 0
    return capsys.readouterr().out


def test_yardim_varsayilan_turkce(monkeypatch, capsys):
    monkeypatch.delenv("RUNTIME_PIN_SYNC_LANG", raising=False)
    out = _yardim(["--help"], capsys)
    assert out.startswith("kullanım: runtime-pin-sync")
    assert "depo kökü (varsayılan: .)" in out
    assert "bu yardımı göster ve çık" in out
    assert "program sürümünü göster ve çık" in out
    assert "makine okuyabilir JSON çıktı" in out
    assert "\nkonumsal argümanlar:" in out and "\nseçenekler:" in out
    assert "repository root" not in out
    assert "usage:" not in out and "positional arguments" not in out


def test_yardim_lang_bayragi_ile_ingilizce(monkeypatch, capsys):
    monkeypatch.delenv("RUNTIME_PIN_SYNC_LANG", raising=False)
    out = _yardim(["--lang", "en", "--help"], capsys)
    assert "repository root (default: .)" in out
    assert "machine-readable JSON output" in out
    assert "show this help message and exit" in out
    assert "depo kökü" not in out


def test_yardim_lang_esittir_bicimi(monkeypatch, capsys):
    monkeypatch.delenv("RUNTIME_PIN_SYNC_LANG", raising=False)
    out = _yardim(["--lang=en", "-h"], capsys)
    assert "single source of truth file (e.g. .tool-versions)" in out


def test_yardim_ortam_degiskenini_izler(monkeypatch, capsys):
    monkeypatch.setenv("RUNTIME_PIN_SYNC_LANG", "en")
    out = _yardim(["--help"], capsys)
    assert "language of the output and of this help" in out
    assert "çıktının ve bu yardımın dili" not in out


def test_sync_yardimi_dry_run_metnini_dile_gore_basar(monkeypatch, capsys):
    monkeypatch.delenv("RUNTIME_PIN_SYNC_LANG", raising=False)
    tr = _yardim(["sync", "--help"], capsys)
    assert "--dry-run" in tr and "dosyaları değiştirmeden göster" in tr
    en = _yardim(["sync", "--lang", "en", "--help"], capsys)
    assert "show changes without modifying files" in en
    assert "dosyaları değiştirmeden" not in en
