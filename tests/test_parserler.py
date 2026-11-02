"""miniyaml ve minitoml: desteklenen alt küme + hata yolları."""

import pytest

from runtime_pin_sync import minitoml
from runtime_pin_sync.miniyaml import MiniYamlError, ayristir


def test_ic_ic_eşleme_ve_dizi():
    veri = ayristir("""
name: akis
on:
  push:
    branches:
      - main
      - develop
jobs:
  test:
    runs-on: ubuntu-latest
""")
    assert veri["name"] == "akis"
    assert veri["on"]["push"]["branches"] == ["main", "develop"]
    assert veri["jobs"]["test"]["runs-on"] == "ubuntu-latest"


def test_acik_dizi_ve_tırnaklar():
    veri = ayristir("""
m:
  node-version: [20, 22, 'lts/hydrogen']
  bos: []
""")
    assert veri["m"]["node-version"] == ["20", "22", "lts/hydrogen"]
    assert veri["m"]["bos"] == []


def test_adim_listesi_eşlemelerle():
    veri = ayristir("""
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-node@v4
    with:
      node-version: 20
""")
    assert veri["steps"][0]["uses"] == "actions/checkout@v4"
    assert veri["steps"][1]["with"]["node-version"] == "20"


def test_yorum_ve_blok_metin():
    veri = ayristir("""
a: 1  # yorum
b: |
  satir1
  satir2
c: "# renk değil metin"
""")
    assert veri["a"] == "1"
    assert veri["b"] == "satir1 satir2"
    assert veri["c"] == "# renk değil metin"


def test_null_ve_boolean_normalizasyonu():
    veri = ayristir("a: null\nb: true\nc: no\n")
    assert veri["a"] == ""
    assert veri["b"] == "true"
    assert veri["c"] == "false"


def test_bos_ve_belge_işaretleri():
    assert ayristir("---\n...\n") is None
    assert ayristir("") is None


def test_bozuk_yaml_hata_fırlatır():
    with pytest.raises(MiniYamlError):
        ayristir("duz metin satiri\n")
    with pytest.raises(MiniYamlError):
        ayristir("a: 1\n  b: 2\n")     # anormal girinti
    with pytest.raises(MiniYamlError):
        ayristir("\ta: 1\n")            # sekme girintisi


# --- minitoml --------------------------------------------------------------

def test_mini_toml_temel():
    veri = minitoml.mini_ayristir("""
# yorum
[tools]
node = "20.11.0"
python = ["3.11", "3.12"]
[tablo.İçi]
x = 5
b = true
""")
    assert veri["tools"]["node"] == "20.11.0"
    assert veri["tools"]["python"] == ["3.11", "3.12"]
    assert veri["tablo"]["İçi"]["x"] == 5
    assert veri["tablo"]["İçi"]["b"] is True


def test_mini_toml_bozuk():
    with pytest.raises(ValueError):
        minitoml.mini_ayristir("burada eşleme yok\n")
    with pytest.raises(ValueError):
        minitoml.mini_ayristir("[a[[b]]]\nx = 1\n")


def test_mini_toml_oku_üzerinden_tomllib_veya_yedek():
    veri = minitoml.oku(b'[toolchain]\nchannel = "1.84.0"\n')
    assert veri["toolchain"]["channel"] == "1.84.0"


def test_mini_toml_çakışan_anahtar():
    with pytest.raises(ValueError):
        minitoml.mini_ayristir('a = "metin"\n[a.b]\nx = 1\n')


def test_mini_toml_tırnak_içi_yorum():
    veri = minitoml.mini_ayristir('a = "#x" # gerçek yorum\n')
    assert veri["a"] == "#x"


def test_mini_toml_çok_satırlı_dizi():
    veri = minitoml.mini_ayristir(
        'keywords = [\n  "bir", "iki",   # yorum\n  "üç",\n]\nsonraki = 1\n')
    assert veri["keywords"] == ["bir", "iki", "üç"]
    assert veri["sonraki"] == 1


def test_mini_toml_kendi_pyproject_310_yedeğinde():
    # Yedek ayrıştırıcı projemizin KENDİ pyproject.toml'unu (çok satırlı
    # keywords + [[dizi.tablo]]) reddetmemeli: requires-python kaybolmamalı.
    from pathlib import Path
    metin = (Path(__file__).resolve().parent.parent
             / "pyproject.toml").read_text(encoding="utf-8")
    veri = minitoml.mini_ayristir(metin)
    assert veri["project"]["requires-python"] == ">=3.10"
    assert "devtools" in veri["project"]["keywords"]
    assert veri["project"]["authors"][0]["name"]


def test_pyproject_310_yedeği_bulucuya_kadar_ulaşır(monkeypatch):
    from runtime_pin_sync import minitoml
    from runtime_pin_sync.bulucular import python
    monkeypatch.setattr(minitoml, "_tomllib", None)  # 3.10 yolu: mini yedek
    içerik = ('[project]\nname = "x"\nkeywords = [\n  "a",\n  "b",\n]\n'
              'requires-python = ">=3.10"\n')
    (p,) = python.pyproject("pyproject.toml", içerik)
    assert p.ham == ">=3.10" and p.kullanilabilir
