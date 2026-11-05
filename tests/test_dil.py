"""Dil sözleşmesi: uyarılar ÜRETİLDİKLERİ yerde çevrilir.

Regresyon: uyarı metinleri bir zamanlar yalnız Türkçe üretilip rapor
katmanında substring değiştirmeyle "çevriliyordu". Eşleme tablosunda
karşılığı olmayan bir cümle (ör. version-file sınır reddi) ``--lang en``
çıktısında Türkçe kalıyordu. Bu dosya sözleşmeyi iki düzeyde sabitler:
bulucu API'si ve CLI çıktısı.
"""

from __future__ import annotations

import json

from conftest import yaz
from runtime_pin_sync.bulucular import node
from runtime_pin_sync.ci import is_aksi
from runtime_pin_sync.cli import main
from runtime_pin_sync.docker import dockerfile, etiket_sınıflandır
from runtime_pin_sync.tara import tara

NL = "\n"
TAB = "	"
TURKCE = set("çğıİöşüÇĞÖŞÜ")
YALNIZ_YORUM = "# yalnız yorum" + NL
AKIS = (
    "jobs:" + NL
    + "  t:" + NL
    + "    runs-on: ubuntu-latest" + NL
    + "    steps:" + NL
    + "      - uses: actions/setup-node@v4" + NL
    + "        with:" + NL
    + "          node-version-file: ../disarida.txt" + NL
)


def _turkce(metin: str) -> list[str]:
    return sorted(TURKCE & set(metin))


def test_bos_package_json_uyarisi_dile_gore() -> None:
    tr = node.package_json("package.json", "")[0]
    en = node.package_json("package.json", "", lang="en")[0]
    assert tr.uyari is not None and tr.uyari.startswith("okunamadı: geçersiz JSON")
    assert en.uyari is not None
    assert en.uyari.startswith("could not read: invalid JSON")
    assert _turkce(en.uyari) == []


def test_tara_dili_buluculara_gecirir(tmp_path) -> None:
    yaz(tmp_path, ".nvmrc", YALNIZ_YORUM)
    (pim,) = tara(tmp_path, lang="en")
    assert pim.uyari == "could not read: empty file"


def test_ci_version_file_depo_disi_uyarisi_ingilizce(tmp_path) -> None:
    (pim,) = is_aksi(".github/workflows/ci.yml", AKIS,
                     depo_koku=str(tmp_path), lang="en")
    assert pim.uyari is not None
    assert pim.uyari.startswith("could not read: version-file")
    assert "depo" not in pim.uyari
    assert _turkce(pim.uyari) == []
    # aynı uyarı Türkçe modda Türkçe kalır (varsayılan dil korunur)
    (tr,) = is_aksi(".github/workflows/ci.yml", AKIS, depo_koku=str(tmp_path))
    assert tr.uyari is not None
    assert tr.uyari.startswith("okunamadı: version-file")


def test_docker_etiket_uyarisi_ingilizce() -> None:
    _, _, uyari = etiket_sınıflandır("22-zzz", lang="en")
    assert uyari == "could not read: unsupported tag suffix (22-zzz)"
    _, _, tr = etiket_sınıflandır("22-zzz")
    assert tr is not None and tr.startswith("okunamadı:")


def test_docker_etiketsiz_yer_tutucu_cevrilir() -> None:
    (pim,) = dockerfile("Dockerfile", "FROM node" + NL, lang="en")
    assert pim.ham == "(untagged)"
    (tr,) = dockerfile("Dockerfile", "FROM node" + NL)
    assert tr.ham == "(etiketsiz)"


def test_cli_ingilizce_ciktida_turkce_karakter_kalmaz(tmp_path, capsys) -> None:
    """Bozuk dosyaların TAMAMI: tek bir çevrilmemiş cümle testi düşürür."""
    yaz(tmp_path, "package.json", "{bozuk")
    yaz(tmp_path, ".nvmrc", YALNIZ_YORUM)
    yaz(tmp_path, "Dockerfile", "FROM node:22-zzz" + NL)
    yaz(tmp_path, ".github/workflows/ci.yml",
        "jobs:" + NL + "  t:" + NL + TAB + "steps: []" + NL)

    main([str(tmp_path), "--lang", "en"])
    en = capsys.readouterr().out
    assert "could not read" in en
    assert _turkce(en) == [], en

    main([str(tmp_path), "--lang", "tr"])
    tr = capsys.readouterr().out
    assert "okunamadı" in tr
    assert "could not read" not in tr


def test_json_uyarilari_da_dile_uyar(tmp_path, capsys) -> None:
    yaz(tmp_path, ".nvmrc", YALNIZ_YORUM)
    main([str(tmp_path), "--json", "--lang", "en"])
    veri = json.loads(capsys.readouterr().out)
    assert veri["uyarilar"] == ["could not read: empty file"]
