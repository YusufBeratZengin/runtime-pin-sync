"""Depo taraması uçtan uca testler."""

from pathlib import Path

import pytest

from conftest import yaz
from runtime_pin_sync import tara

PROJE_KOK = Path(__file__).resolve().parent.parent


def test_örnek_uyumsuz_depo_kabul1():
    pimler = tara(PROJE_KOK / "ornek-depolar/uyumsuz")
    kaynaklar = {p.dosya for p in pimler if p.calisma_zamani == "node"}
    # kabul ölçütü 1: üç kaynak görünürlüğü (nvmrc, engines, Dockerfile, CI)
    assert {".nvmrc", "package.json", "Dockerfile",
            ".github/workflows/ci.yml"} <= kaynaklar


def test_örnek_tutarli_çelişkisiz():
    from runtime_pin_sync import celiski
    assert celiski(tara(PROJE_KOK / "ornek-depolar/tutarli")) == []


def test_örnek_bozuk_hata_vermez_kabul4():
    pimler = tara(PROJE_KOK / "ornek-depolar/bozuk")
    assert any(p.durum == "okunamadı" for p in pimler)     # bozuk JSON uyarısı
    assert any(p.durum == "dinamik, atlandı" for p in pimler)
    assert not any(p.kullanilabilir and p.calisma_zamani == "node"
                   and p.ham == "20" and p.tur == "engines" for p in pimler)


def test_node_modules_atlanır(tmp_path):
    yaz(tmp_path, "node_modules/paket/.nvmrc", "12")
    yaz(tmp_path, ".nvmrc", "20")
    pimler = tara(tmp_path)
    assert [p.dosya for p in pimler] == [".nvmrc"]


def test_gizli_dizinler_atlanır(tmp_path):
    yaz(tmp_path, ".git/hooks/.python-version", "2.7")
    yaz(tmp_path, ".venv/py/.python-version", "3.2")
    assert tara(tmp_path) == []


def test_bilinmeyen_uzantılar_yoksayar(tmp_path):
    yaz(tmp_path, "README.md", "node 20 yazar")
    yaz(tmp_path, "not.txt", "python 3.8")
    assert tara(tmp_path) == []


def test_klasör_olmayan_yol(tmp_path):
    with pytest.raises(ValueError):
        tara(tmp_path / "yok-boyle-bir-klasör")
    with pytest.raises(ValueError):
        tara(__file__)  # dosya, klasör değil


def test_bilinen_adlı_dizin_atlanır(tmp_path):
    yaz(tmp_path, "build/Dockerfile", "FROM node:99")
    yaz(tmp_path, "Dockerfile", "FROM node:20")
    pimler = tara(tmp_path)
    assert [p.dosya for p in pimler] == ["Dockerfile"]


def test_dockerfile_varyantları(tmp_path):
    yaz(tmp_path, "docker/Dockerfile.dev", "FROM golang:1.23")
    yaz(tmp_path, "eski.dockerfile", "FROM rust:1.80")
    pimler = tara(tmp_path)
    assert sorted(p.ham for p in pimler) == ["1.23", "1.80"]


def test_tekrarlar_tekilleştirilir(tmp_path):
    # aynı ham değer, aynı dosya/tür: tek sabitleme — ama KONUMLAR KAYBOLMAZ
    yaz(tmp_path, ".tool-versions", "node 20\nnodejs 20\n")
    pimler = [p for p in tara(tmp_path) if p.calisma_zamani == "node"]
    assert len(pimler) == 1
    assert pimler[0].satir == 1
    assert pimler[0].tüm_satırlar == (1, 2)


def test_iki_from_satırı_konum_kaybetmez(tmp_path):
    yaz(tmp_path, "Dockerfile", "FROM node:22 AS a\nRUN x\nFROM node:22 AS b\n")
    (p,) = [p for p in tara(tmp_path) if p.calisma_zamani == "node"]
    assert p.ham == "22"
    assert p.tüm_satırlar == (1, 3)


def test_okuma_hatasi_uyariya_döner(tmp_path, monkeypatch):
    yaz(tmp_path, "Dockerfile", "FROM node:20\n")
    yaz(tmp_path, ".nvmrc", "20\n")
    gerçek = Path.read_text

    def patlayan_read_text(self, *a, **k):
        if self.name == ".nvmrc":
            raise OSError("sahte okuma hatası")
        return gerçek(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", patlayan_read_text)
    pimler = tara(tmp_path)
    uyarili = [p for p in pimler if p.durum == "okunamadı"]
    assert [p.dosya for p in uyarili] == [".nvmrc"]
    assert "sahte okuma hatası" in uyarili[0].uyari


def test_kaynak_kontrol():
    from runtime_pin_sync.tara import kaynak_kontrol
    pimler = tara(PROJE_KOK / "ornek-depolar/uyumsuz")
    assert kaynak_kontrol(pimler, ".tool-versions")
    assert not kaynak_kontrol(pimler, "olmayan")


def test_kaynak_kontrol_boş_ya_da_çözülemeyen_dosyayı_reddeder(tmp_path):
    # Dosya YOLU bulunmak yetmez; kaynak KULLANILABİLİR bir sürüm üretmeli.
    # Boş .nvmrc uyarılı bir Sabitleme üretir — kaynak sayılmamalı.
    from runtime_pin_sync.tara import kaynak_kontrol

    yaz(tmp_path, ".nvmrc", "")
    pimler = tara(tmp_path)
    assert pimler and pimler[0].uyari and not pimler[0].kullanilabilir
    assert not kaynak_kontrol(pimler, ".nvmrc")

    yaz(tmp_path, ".python-version", "sürüm-yok")
    pimler = tara(tmp_path)
    assert not any(p.kullanilabilir for p in pimler if p.dosya == ".python-version")
    assert not kaynak_kontrol(pimler, ".python-version")
