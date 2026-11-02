"""Sürüm aralığı motoru: semver/PEP 440 ayrıştırma ve kesişim."""

import pytest

from runtime_pin_sync.versiyon import Aralik, AralikKumesi, spek_ayristir, kümeler_kesisir


def kesis(ru, digeri):
    a, b = spek_ayristir(ru), spek_ayristir(digeri)
    if a is None or b is None:
        return False
    return kümeler_kesisir(a, b)


# --- kabul ölçütü 2: aralık karşılaştırması ---------------------------------

def test_pep440_aralık_ile_dusuk_sabit_celisir():
    # >=3.10 ile 3.9 KESIŞMEZ (çelişki)
    assert not kesis(">=3.10", "3.9")


def test_pep440_aralık_ile_yuksek_sabit_celismez():
    # 3.12 ile >=3.10 kesişir (çelişmez)
    assert kesis("3.12", ">=3.10")


def test_iki_ayni_aralik_kesisir():
    assert kesis(">=3.10,<4.0", "3.11")


# --- ön ek / yıldız / tam sürüm ----------------------------------------------

@pytest.mark.parametrize("a,b", [
    ("20", "20.*"),        # tuzak: 20 ile 20.* aynı şey
    ("20", "20.11.0"),     # 20 bir ön ek: 20.11.0 içerilir
    ("3.12", "3.12.1"),    # tuzak: Python için de aynı
    ("20.x", "20.11.0"),
])
def test_on_ek_kapsar(a, b):
    assert kesis(a, b)


def test_farkli_major_celisir():
    assert not kesis("20", "22")


def test_tam_surbum_farki_celisir():
    assert not kesis("3.12.1", "3.12.2")


def test_yildiz_her_surbimle_kesisir():
    assert kesis("*", "1.2.3")
    assert kesis("lts", "lts") is False  # 'lts' tek başına çözümlenemez


# --- operatörler ---------------------------------------------------------------

def test_katı_küçük_aralıklar_boş_kümedir():
    assert not kesis(">=4", "<3")


def test_kesişmeyen_iki_aralık():
    assert not kesis(">=18", "<16")


def test_kesişen_iki_aralık():
    assert kesis(">=18", "<21")


def test_or_semantik_birlesim():
    # 18 || 20 birleşimi 20 ile kesişir, 22 ile kesişmez
    assert kesis("18 || 20", "20")
    assert not kesis("18 || 20", "22")


def test_caret():
    assert kesis("^20.1.0", "20.9.9")
    assert not kesis("^20.1.0", "21.0.0")
    assert kesis("^0.2.3", "0.2.9")
    assert not kesis("^0.2.3", "0.3.0")


def test_tilde():
    assert kesis("~20.1", "20.1.5")
    assert not kesis("~20.1", "20.2.0")


def test_pep440_compatible_release():
    assert kesis("~=3.12.1", "3.12.9")
    assert not kesis("~=3.12.1", "3.13.0")


def test_kesin_esit_sonraki_surbumu_dislar():
    # ==3.12 tam değerdir; 3.12.1 != 3.12 (PEP 440)
    assert not kesis("==3.12", "3.12.1")
    assert kesis("==3.12", "3.12")


def test_buyuk_esit_ust_sinir_dahil():
    assert kesis("<=3.12", "3.12")
    assert not kesis("<=3.12", "3.12.1")


def test_v_oneki_ve_build_meta():
    assert kesis("v20", "20")
    assert kesis("17.0.2+8", "17.0.2")


# --- çözülemeyen girdiler ------------------------------------------------------

@pytest.mark.parametrize("bozuk", [
    "", " ", "lts/iron", "stable", "latest", ">=abc", "20-rc1", "3.10!4",
    "!=", "!=3.10", "3.10,<", ">",
])
def test_cozulemeyen_none_donер(bozuk):
    assert spek_ayristir(bozuk) is None


def test_aralik_kumesi_bos_mu():
    kume = spek_ayristir("20")
    assert not kume.bos
    assert kume.sabit
    acik = spek_ayristir(">=20")
    assert not acik.sabit  # üst sınırı yok: referans/sync adayı değil


def test_tek_bos_aralik_nesnesi():
    assert Aralik(alt=(5,), ust=(3,)).bos
    assert Aralik(alt=(5,), ust=(5,), ust_kapsar=True).bos is False
    assert Aralik(alt=(5,), ust=(5,)).bos
    assert str(Aralik(alt=(20,), ust=(21,))) == "[20,21)"
    assert str(Aralik()) == "-inf,+inf"


def test_bos_kume_celiskidir():
    bos = AralikKumesi((Aralik(alt=(5,), ust=(3,)),))
    her_sey = AralikKumesi((Aralik(),))
    assert not kümeler_kesisir(bos, her_sey)
