"""CLI sözleşmesi: çıkış kodları, --json, sync, --degisken, --kaynak."""

import json
from pathlib import Path

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
