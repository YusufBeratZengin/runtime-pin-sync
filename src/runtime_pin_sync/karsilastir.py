"""Çelişki tespiti: aynı çalışma zamanının sabitlemelerini karşılaştırır.

Referans seçimi: ``kaynak`` verilmişse o dosyanın sabitlemesi; değilse diğer
sabitlemelerin en çoğuyla kesişen "konsensüs" sabitleme (medoid). Test
ızgaraları (CI matrisi) referans adayı değildir, yalnız kesişim ortağıdır.
"""

from __future__ import annotations

from .sabitleme import Celiski, Sabitleme
from .versiyon import AralikKumesi, kümeler_kesisir

__all__ = ["celiski"]


def _kume(p: Sabitleme) -> AralikKumesi:
    assert p.aralik is not None
    return p.aralik


def _somut_referans_mi(p: Sabitleme) -> bool:
    return p.aralik is not None and len(p.aralik.parcalar) == 1 and p.aralik.sabit


def _referans_sec(kullanim: list[Sabitleme]) -> Sabitleme:
    """En çok sabitlemeyle kesişen aday; eşitlikte tarama sırasındaki ilk."""
    adaylar = [p for p in kullanim if _somut_referans_mi(p)] or kullanim
    en_iyi = max(
        range(len(adaylar)),
        key=lambda i: (
            sum(1 for q in kullanim if q is not adaylar[i] and kümeler_kesisir(_kume(adaylar[i]), _kume(q))),
            -i,
        ),
    )
    return adaylar[en_iyi]


def celiski(sabitlemeler: list[Sabitleme], kaynak: str | None = None) -> list[Celiski]:
    """Sabitleme listesinden çalışma zamanı başına çelişkileri döndürür."""
    by_rt: dict[str, list[Sabitleme]] = {}
    for p in sabitlemeler:
        if p.kullanilabilir:
            by_rt.setdefault(p.calisma_zamani, []).append(p)
    sonuclar: list[Celiski] = []
    for rt, kullanim in sorted(by_rt.items()):
        if len(kullanim) < 2:
            continue
        if kaynak is not None:
            ref_pimler = [p for p in kullanim if p.dosya == kaynak]
            if not ref_pimler:
                continue
            ref_kume = AralikKumesi(
                tuple(par for p in ref_pimler for par in _kume(p).parcalar)
            )
            referans = ref_pimler[0]
            dislanan = [p for p in kullanim
                        if p not in ref_pimler and not _kesisir(ref_kume, _kume(p))]
        else:
            referans = _referans_sec(kullanim)
            dislanan = [p for p in kullanim if p is not referans
                        and not kümeler_kesisir(_kume(referans), _kume(p))]
        if not dislanan:
            continue
        adlar = " | ".join(f"{_kisa(p.dosya)}={p.ham}" for p in kullanim)
        hedefler = ", ".join(p.dosya for p in dislanan)
        sonuclar.append(Celiski(
            calisma_zamani=rt,
            referans_dosya=referans.dosya,
            referans_ham=referans.ham,
            dislananlar=dislanan,
            mesaj=f"{rt}: {adlar} → ÇELİŞKİ: {hedefler}",
        ))
    return sonuclar


def _kesisir(a: AralikKumesi, b: AralikKumesi) -> bool:
    return kümeler_kesisir(a, b)


def _kisa(yol: str) -> str:
    return yol.rsplit("/", 1)[-1]
