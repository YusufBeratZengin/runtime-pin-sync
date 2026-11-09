"""Tur 4 bağımsız inceleme regresyonları (K1, K2, Y1, Y2).

Bulgu tetikleyicileri ve mevcut davranışı koruyan kontroller. Güncel API'de
mise ızgarasının satırı rapor için korunur, otomatik yazma yine reddedilir.
"""

import pytest

from conftest import yaz
from runtime_pin_sync import celiski, senkronla, tara
from runtime_pin_sync.bulucular import araclar, python
from runtime_pin_sync.docker import (
    devcontainer,
    dockerfile,
    imaj_coz,
)

# --- K1: resmî devcontainer nesil önekli imaj etiketi --------------------------

def test_devcontainer_mcr_nesil_onekli_etiket_python_surumu_okunur(tmp_path):
    yaz(tmp_path, ".python-version", "3.12.1\n")
    yaz(tmp_path, "Dockerfile", "FROM python:3.12-slim\n")
    yaz(tmp_path, "devcontainer.json",
        '{"image": "mcr.microsoft.com/devcontainers/python:1-3.12-bookworm"}\n')

    (dc,) = devcontainer(
        "devcontainer.json",
        '{"image": "mcr.microsoft.com/devcontainers/python:1-3.12-bookworm"}')
    assert (dc.calisma_zamani, dc.ham) == ("python", "3.12")
    assert dc.kullanilabilir

    # JavaScript/Go resmî devcontainer imajları da nesil öneki taşır.
    assert imaj_coz("mcr.microsoft.com/devcontainers/javascript-node",
                    "1-20-bookworm") == ("node", "20")

    # nesil öneki YOKSA sürüm yine doğru okunur (eski etiket biçimi)
    assert imaj_coz("mcr.microsoft.com/devcontainers/python",
                    "3.12-bookworm") == ("python", "3.12")
    # Nesil kuralı başka bir registry'deki benzer yola yayılmamalı.
    assert imaj_coz(
        "registry.example/devcontainers/python", "1-3.12-bookworm"
    ) != ("python", "3.12")

    assert celiski(tara(tmp_path)) == []
    otomatik, elle = senkronla(tmp_path, ".python-version", True)
    assert (otomatik, elle) == ([], [])


# --- K2: mise.toml dizi değeri tek sürüm kümesi -------------------------------

def test_mise_dizi_tek_kume_ve_round_trip_korunur(tmp_path):
    yaz(tmp_path, ".nvmrc", "22\n")
    yaz(tmp_path, "mise.toml", '[tools]\nnode = ["22", "24"]\n')
    once = (tmp_path / "mise.toml").read_bytes()

    pimler = araclar.mise("mise.toml", '[tools]\nnode = ["22", "24"]\n')
    (p,) = pimler
    assert p.ham == "22, 24"          # TEK pim, iki pim değil
    assert p.kullanilabilir
    assert p.aralik is not None
    assert not p.aralik.sabit         # ızgara: tek üyeye indirgenemez
    assert p.satir == 2              # güncel API: rapor konumu korunur
    assert not p.yeniden_yazilabilir

    # 22 ızgaranın üyesi → çelişki yok
    assert celiski(tara(tmp_path)) == []

    # sync hiçbir şey yazmaz; dosya bayt bayt AYNI kalır
    otomatik, elle = senkronla(tmp_path, ".nvmrc", False)
    assert (otomatik, elle) == ([], [])
    assert (tmp_path / "mise.toml").read_bytes() == once


def test_mise_dizi_hicbir_uyeyle_kesisniyorsa_celiski_ve_yazilmaz(tmp_path):
    yaz(tmp_path, ".nvmrc", "20\n")
    yaz(tmp_path, "mise.toml", '[tools]\nnode = ["22", "24"]\n')
    once = (tmp_path / "mise.toml").read_bytes()

    (c,) = celiski(tara(tmp_path))
    assert c.calisma_zamani == "node"
    assert {c.referans_dosya} | {p.dosya for p in c.dislananlar} == \
        {".nvmrc", "mise.toml"}

    otomatik, elle = senkronla(tmp_path, ".nvmrc", False)
    assert otomatik == []             # ızgara sabit sürüme zorlanmaz
    assert elle and (tmp_path / "mise.toml").read_bytes() == once


def test_mise_tek_elemanli_dizi_normal_pim_kalir(tmp_path):
    yaz(tmp_path, ".nvmrc", "20\n")
    yaz(tmp_path, "mise.toml", '[tools]\nnode = ["22"]\n')
    (p,) = araclar.mise("mise.toml", '[tools]\nnode = ["22"]\n')
    assert p.ham == "22" and p.satir == 2
    (c,) = celiski(tara(tmp_path))
    assert c.referans_ham == "20" and c.dislananlar[0].satir == 2


# --- Y1: çok satırlı .python-version ------------------------------------------

def test_python_version_cok_satir_birlisim_ve_round_trip(tmp_path):
    yaz(tmp_path, ".python-version", "3.11.8\n3.12.1\n")
    yaz(tmp_path, ".tool-versions", "python 3.12.1\n")
    once = (tmp_path / ".python-version").read_bytes()

    pimler = python.surum_dosyasi(".python-version", "3.11.8\n3.12.1\n")
    (p,) = pimler
    assert p.ham == "3.11.8, 3.12.1"  # iki ayrı pim değil, tek birleşim
    assert p.kullanilabilir
    assert p.aralik is not None
    assert not p.aralik.sabit

    assert celiski(tara(tmp_path)) == []
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert (otomatik, elle) == ([], [])
    assert (tmp_path / ".python-version").read_bytes() == once


def test_python_version_cok_satir_cakisan_birlisim_yazilmaz(tmp_path):
    yaz(tmp_path, ".python-version", "3.11.8\n3.12.1\n")
    yaz(tmp_path, ".tool-versions", "python 3.10.4\n")
    once = (tmp_path / ".python-version").read_bytes()
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert otomatik == []
    assert elle
    assert (tmp_path / ".python-version").read_bytes() == once


@pytest.mark.parametrize("deger", ["system", "bozuk", "${{ env.PY }}"])
@pytest.mark.parametrize("lang", ["tr", "en"])
def test_python_version_cozulemeyen_uye_kismi_kume_uretmez(tmp_path, deger, lang):
    icerik = f"# pyenv\n3.12.1\n{deger}\n"
    yaz(tmp_path, ".python-version", icerik)
    yaz(tmp_path, ".tool-versions", "python 3.11.8\n")
    once = (tmp_path / ".python-version").read_bytes()
    (p,) = python.surum_dosyasi(".python-version", icerik, lang=lang)
    assert not p.kullanilabilir and p.aralik is None and p.satir is None
    assert p.uyari == (
        "could not read: unresolvable value in multiline version file" if lang == "en"
        else "okunamadı: çok satırlı dosyada çözülemeyen değer"
    )
    assert celiski(tara(tmp_path, lang=lang)) == []
    assert senkronla(tmp_path, ".tool-versions", False, lang=lang) == ([], [])
    assert (tmp_path / ".python-version").read_bytes() == once


# --- Y2: Alpine etiketleri ----------------------------------------------------

def test_alpine_versionlu_etiket_surumu_korur(tmp_path):
    yaz(tmp_path, ".python-version", "3.9\n")
    yaz(tmp_path, "Dockerfile", "FROM python:3.12-alpine3.19\n")

    (p,) = dockerfile("Dockerfile", "FROM python:3.12-alpine3.19\n")
    assert (p.calisma_zamani, p.ham) == ("python", "3.12")
    assert p.kullanilabilir and p.uyari is None

    # yaygın resmî Alpine etiketleri
    (n,) = dockerfile("Dockerfile", "FROM node:20-alpine3.19\n")
    assert (n.calisma_zamani, n.ham) == ("node", "20")
    (g,) = dockerfile("Dockerfile", "FROM golang:1.22-alpine3.19\n")
    assert (g.calisma_zamani, g.ham) == ("go", "1.22")
    (n_yama,) = dockerfile("Dockerfile", "FROM node:20.11.1-alpine3.19.1\n")
    assert (n_yama.calisma_zamani, n_yama.ham) == ("node", "20.11.1")
    assert n_yama.kullanilabilir
    # noktalı ön sürüm hâlâ karşılaştırma dışı (nokta ayraç değişikliği
    # yüzünden kararlı sürüme indirgenmemeli)
    (rc,) = dockerfile("Dockerfile", "FROM node:22.0.0-rc.1\n")
    assert rc.durum == "okunamadı"
    assert rc.uyari is not None and "ön sürüm" in rc.uyari

    # gerçek kayma artık sessizce kaçmaz
    (c,) = celiski(tara(tmp_path))
    assert c.calisma_zamani == "python"
    assert c.dislananlar[0].dosya == "Dockerfile"
