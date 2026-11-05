"""Sürüm aralığı motoru: PEP 440 ve semver REFERANS örnekleri.

Buradaki tablolar uydurma değil, iki belirtimin kendi örneklerinden türetilmiştir:

- PEP 440, "Version specifiers" (compatible release, wildcards, exclusive
  comparisons; sürümler sıfırla doldurulur: ``1.1 == 1.1.0``):
  https://packaging.python.org/en/latest/specifications/version-specifiers/
- node-semver README (caret/tilde/X-range tabloları ve ``>``/``<=`` için
  X-range davranışı): https://github.com/npm/node-semver#ranges

Amaç, özel karşılaştırıcının belgelenmiş sınırlarda sessizce YANLIŞ eşleşme
üretmediğini göstermek. Desteklenmeyen sözdizimi ``None`` (çözümlenemedi)
dönmelidir; tahmin edilmemelidir.
"""

import pytest

from runtime_pin_sync.versiyon import kümeler_kesisir, spek_ayristir


def kesisir(a, b, semver=False):
    x, y = spek_ayristir(a, semver), spek_ayristir(b, semver)
    if x is None or y is None:
        raise AssertionError(f"çözümlenemedi: {a!r} / {b!r}")
    return kümeler_kesisir(x, y)


# --- PEP 440 -----------------------------------------------------------------

PEP440_ORNEKLERI = [
    # ~=X.Y  ->  >=X.Y, ==X.*   (PEP 440 "compatible release")
    ("~=2.2", "2.2", True),
    ("~=2.2", "2.9", True),
    ("~=2.2", "3.0", False),
    # ~=X.Y.Z -> >=X.Y.Z, ==X.Y.*
    ("~=1.4.5", "1.4.5", True),
    ("~=1.4.5", "1.4.9", True),
    ("~=1.4.5", "1.5.0", False),
    # ==X.Y.* yıldızlı ön ektir
    ("==1.1.*", "1.1", True),
    ("==1.1.*", "1.1.5", True),
    ("==1.1.*", "1.2.0", False),
    # ==X.Y (yıldızsız) sıfırla doldurulur: 1.1 == 1.1.0, ama 1.2 DEĞİL
    ("==1.1", "1.1.0", True),
    ("==1.1", "1.2", False),
    # > dışlayıcı: ">1.7" 1.7'yi kapsamaz, 1.7.1'i kapsar
    ("<1.7", "1.7", False),
    (">1.7", "1.7.0", False),
    (">1.7", "1.7.1", True),
    ("<=1.7", "1.7.0", True),
    (">=3.10", "3.10.0", True),
    (">=3.10", "3.9.19", False),
    # VE listesi
    (">=3.10,<4.0", "3.13.0", True),
    (">=3.10,<4.0", "4.0.0", False),
]


@pytest.mark.parametrize("spek,surum,beklenen", PEP440_ORNEKLERI)
def test_pep440_referans_ornekleri(spek, surum, beklenen):
    assert kesisir(spek, surum) is beklenen


def test_kisa_belirtec_onek_oldugu_icin_pep_operatoruyle_kesisir():
    """Bilinçli sapma: ``1.7`` bu araçta 1.7.x ÖNEKİDİR (PEP 440'da 1.7.0).

    Ön ek semantiği ``20`` ile ``20.11.0`` uyumunu mümkün kılar; bu yüzden
    ``>1.7`` (1.7.0'ı dışlar) ile ``1.7`` (1.7.x) kesişir. Tam nokta için
    ``1.7.0`` yazılmalıdır — yukarıdaki referans tablosu bunu kullanır.
    """
    assert kesisir(">1.7", "1.7") is True
    assert kesisir(">1.7", "1.7.0") is False


# --- semver (node-semver) ----------------------------------------------------

SEMVER_ORNEKLERI = [
    # ^X.Y.Z -> >=X.Y.Z <(X+1).0.0
    ("^1.2.3", "1.9.9", True),
    ("^1.2.3", "2.0.0", False),
    # ^0.Y.Z -> >=0.Y.Z <0.(Y+1).0
    ("^0.2.3", "0.2.9", True),
    ("^0.2.3", "0.3.0", False),
    # ^0.0.Z -> >=0.0.Z <0.0.(Z+1)
    ("^0.0.3", "0.0.3", True),
    ("^0.0.3", "0.0.4", False),
    # ~X.Y.Z -> >=X.Y.Z <X.(Y+1).0 ; ~X.Y -> >=X.Y.0 <X.(Y+1).0
    ("~1.2.3", "1.2.9", True),
    ("~1.2.3", "1.3.0", False),
    ("~1.2", "1.2.5", True),
    ("~1.2", "1.3.0", False),
    # X-range
    ("1.2.x", "1.2.5", True),
    ("1.2.x", "1.3.0", False),
    # node-semver X-range: ">1.2" == ">=1.3.0", "<=1.2" == "<1.3.0"
    (">1.2", "1.2.9", False),
    (">1.2", "1.3.0", True),
    ("<=1.2", "1.2.9", True),
    ("<=1.2", "1.3.0", False),
    # birleşim
    ("1.2.3 || 2.x", "2.4.1", True),
    ("1.2.3 || 2.x", "3.0.0", False),
    ("*", "99.9.9", True),
]


@pytest.mark.parametrize("spek,surum,beklenen", SEMVER_ORNEKLERI)
def test_semver_referans_ornekleri(spek, surum, beklenen):
    assert kesisir(spek, surum, semver=True) is beklenen


def test_iki_lehce_ayni_yarim_operatoru_farkli_yorumlar():
    """README'de belgelenen fark: ``>20`` semver'de >=21, PEP 440'ta >20.0."""
    assert kesisir(">20", "20.5.0", semver=True) is False
    assert kesisir(">20", "20.5.0") is True
    assert kesisir(">20", "21.0.0", semver=True) is True


# --- desteklenmeyen sözdizimi: tahmin YOK, None -------------------------------

@pytest.mark.parametrize("sozdizimi", [
    "1.2.3 - 2.3.4",   # npm tire aralığı
    "!=1.2.3",         # dışlama: çelişki çıkarımı güvenli değil
    "===1.2.3",        # PEP 440 keyfî eşitlik
    "1.2.3-beta.1",    # ön sürüm soneki
    "~=3",             # PEP 440: compatible release en az İKİ bileşen ister
    "~>1.2",           # Ruby/Bundler pesimistik operatörü (semver ~ DEĞİL)
    "lts/iron",        # Node takma adı: sürüm değil
    "latest",
])
def test_desteklenmeyen_sozdizimi_coz_edilemez(sozdizimi):
    assert spek_ayristir(sozdizimi) is None


def test_gecerli_compatible_release_hala_calisir():
    # Yukarıdaki katılaştırma geçerli biçimleri bozmamalı.
    assert spek_ayristir("~=3.10") is not None
    assert kesisir("~=3.10", "3.12.1") is True
    assert kesisir("~=3.10", "4.0.0") is False
