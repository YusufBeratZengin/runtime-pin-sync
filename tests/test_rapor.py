"""Rapor üretimi: tablo ve JSON sözlüğü."""

from runtime_pin_sync.bulucular import pin
from runtime_pin_sync.karsilastir import celiski
from runtime_pin_sync.rapor import json_sözlüğü, tablo, uyari_cevir
from runtime_pin_sync.sabitleme import Sabitleme


def test_tablo_boş_depo():
    assert "bulunamadı" in tablo([], [])


def test_tablo_uyumlu():
    pimler = [pin("node", ".nvmrc", "nvmrc", "20"),
              pin("node", "Dockerfile", "dockerfile", "20")]
    out = tablo(pimler, [])
    assert "uyumlu ✓" in out
    assert ".nvmrc" in out and "20" in out


def test_tablo_çelişkili_özet_satırı():
    pimler = [pin("node", ".nvmrc", "nvmrc", "20"),
              pin("node", "Dockerfile", "dockerfile", "22"),
              Sabitleme("python", "x.json", "engines", "",
                        uyari="okunamadı: örnek"),
              Sabitleme("python", "ci.yml", "ci", "${{ }}", dinamik=True)]
    celiskiler = celiski(pimler)
    out = tablo(pimler, celiskiler)
    assert "ÇELİŞKİ: Dockerfile" in out
    assert "NOTLAR" in out and "okunamadı: örnek" in out
    assert "dinamik ifade" in out


def test_tablo_kaynak_referans_gösterir():
    pimler = [pin("node", ".nvmrc", "nvmrc", "20"),
              pin("node", "Dockerfile", "dockerfile", "22")]
    out = tablo(pimler, celiski(pimler, kaynak=".nvmrc"), kaynak=".nvmrc")
    assert "referans" in out
    assert "ÇELİŞKİ" in out


def test_json_sözlüğü_alanları():
    pimler = [pin("node", ".nvmrc", "nvmrc", "20"),
              Sabitleme("node", "ci.yml", "ci-adim", "${{ m.x }}", dinamik=True),
              Sabitleme("node", "b.json", "engines", "", uyari="okunamadı: x")]
    d = json_sözlüğü(pimler, celiski(pimler))
    assert len(d["sabitlemeler"]) == 3
    assert d["uyarilar"] == ["okunamadı: x"]
    assert d["dinamikler"][0]["dosya"] == "ci.yml"
    durumlar = {s["dosya"]: s["durum"] for s in d["sabitlemeler"]}
    assert durumlar["ci.yml"] == "dinamik, atlandı"
    assert durumlar["b.json"] == "okunamadı"


def test_tablo_ingilizce_ve_uyari_cevir():
    pimler = [
        pin("node", ".nvmrc", "nvmrc", "20"),
        pin("node", "Dockerfile", "dockerfile", "22"),
        Sabitleme("python", "ci.yml", "ci", "${{ }}", dinamik=True),
        Sabitleme("python", "empty.txt", "toolchain", "", uyari="okunamadı: boş dosya"),
    ]
    celiskiler = celiski(pimler)
    out = tablo(pimler, celiskiler, lang="en")
    assert "RUNTIME" in out and "STATUS" in out
    assert "CONFLICT: Dockerfile" in out
    assert "RESULT: 1 runtime has conflicts." in out
    assert "NOTES:" in out
    assert "dynamic expression: not compared" in out
    assert "could not read: empty file" in out


def test_tablo_ingilizce_bos():
    assert "No version sources found" in tablo([], [], lang="en")


def test_json_sozlugu_ingilizce():
    pimler = [
        pin("node", ".nvmrc", "nvmrc", "20"),
        Sabitleme("node", "b.json", "engines", "", uyari="okunamadı: boş belirteç"),
    ]
    d = json_sözlüğü(pimler, [], lang="en")
    assert d["sabitlemeler"][0]["durum"] == "consistent"
    assert d["sabitlemeler"][1]["durum"] == "could not read"
    assert d["sabitlemeler"][1]["uyari"] == "could not read: empty token"
    assert d["uyarilar"] == ["could not read: empty token"]


def test_uyari_cevir_fonksiyonu():
    assert uyari_cevir("okunamadı: boş dosya", "en") == "could not read: empty file"
    assert uyari_cevir("okunamadı: desteklenmeyen YAML", "en") == "could not read: unsupported YAML"
    assert uyari_cevir("okunamadı: boş dosya", "tr") == "okunamadı: boş dosya"
    assert uyari_cevir(None, "en") == ""

