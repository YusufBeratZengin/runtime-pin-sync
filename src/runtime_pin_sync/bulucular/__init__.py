"""Bulucular (finders) paketi: ortak yardımcılar.

Her bulucu bir dosya içeriğinden ``Sabitleme`` listesi üretir; hiçbir bulucu
istisna fırlatmaz — çözülemeyen girdi ``uyari``/``dinamik`` işaretli Sabitleme
olarak döner (kabul ölçütü 4).
"""

from __future__ import annotations

from ..dil import m as _m
from ..sabitleme import Sabitleme
from ..versiyon import spek_ayristir

__all__ = ["pin", "grid_pin", "satirlar", "satir_bul", "DINAMIK_İŞARET"]

DINAMIK_İŞARET = "${{"

# npm/semver dünyası: yarım sürümlü `>`/`<=` seri sınırını kaydırır
# (node-semver replaceXRanges: `>20` == `>=21.0.0`). Python PEP 440 dar
# kalır; go/java araç dosyalarında operatörlü aralık geleneği yoktur.
_SEMVER_AİLESİ = frozenset({"node", "rust", "java", "go"})


def _semver_mi(calisma_zamani: str) -> bool:
    return calisma_zamani in _SEMVER_AİLESİ


def pin(
    calisma_zamani: str,
    dosya: str,
    tur: str,
    ham: str,
    satir: int | None = None,
    yeniden_yazilabilir: bool = True,
    *,
    lang: str = "tr",
) -> Sabitleme:
    """Ham belirteçten Sabitleme üretir; çözülemeyeni uyarı, dinamiği atlanır yapar."""
    ham = (ham or "").strip()
    if DINAMIK_İŞARET in ham:
        return Sabitleme(calisma_zamani, dosya, tur, ham, dinamik=True, satir=satir)
    aralik = spek_ayristir(ham, semver=_semver_mi(calisma_zamani)) if ham else None
    if aralik is None:
        uyari = (_m(lang, "w_token_unparsable", ham=ham) if ham
                 else _m(lang, "w_empty_token"))
        return Sabitleme(calisma_zamani, dosya, tur, ham, uyari=uyari, satir=satir)
    return Sabitleme(calisma_zamani, dosya, tur, ham, aralik=aralik, satir=satir,
                     yeniden_yazilabilir=yeniden_yazilabilir)


def grid_pin(
    calisma_zamani: str,
    dosya: str,
    tur: str,
    degerler: list[str],
    satir: int | None = None,
) -> Sabitleme:
    """Test ızgarası (CI matrisi ya da liste): öğelerin BİRLEŞİMİ tek sabitleme olur.

    Izgara 20 VE 22'yi test ediyorsa 20 tek başına çelişki değildir; yalnızca
    ızgaranın hiçbiriyle kesişmeyen sabitleme çelişir. ``satir`` yalnız raporda
    ve "elle düzeltilmeli" kaydında gösterilir; ızgara hiçbir zaman otomatik
    yazılmaz (``sabit_belirtec_mi`` birleşimi reddeder).
    """
    from ..versiyon import Aralik, AralikKumesi

    ham = ", ".join(degerler)
    parcalar: list[Aralik] = []
    for d in degerler:
        a = spek_ayristir(d, semver=_semver_mi(calisma_zamani))
        if a is None:
            continue
        parcalar.extend(a.parcalar)
    if not parcalar:
        return Sabitleme(calisma_zamani, dosya, tur, ham,
                         dinamik=True, satir=satir)
    return Sabitleme(calisma_zamani, dosya, tur, ham,
                     aralik=AralikKumesi(tuple(parcalar)), satir=satir)


def satirlar(metin: str) -> list[str]:
    return metin.splitlines()


def satir_bul(satirlar_list: list[str], iplik: str) -> int | None:
    """İpliğin ilk geçtiği satırın 1-tabanlı numarası."""
    for i, s in enumerate(satirlar_list, start=1):
        if iplik in s:
            return i
    return None
