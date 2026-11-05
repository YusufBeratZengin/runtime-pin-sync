"""Go sürüm kaynakları: go.mod ``go``/``toolchain`` doğrudanları, .go-version.

``go`` direktifi SABİTLEME değil, MİNİMUM gereksinimdir (go.dev/doc/modules/
gomod-ref#go): `go 1.22` + `toolchain go1.23.1` GEÇERLİDİR ve çelişki değil-
dir. Bu yüzden ``go`` satırının aralığı [v, +sonsuz) olarak modellenir.
"""

from __future__ import annotations

import re

from ..dil import m as _m
from ..sabitleme import Sabitleme
from ..versiyon import Aralik, AralikKumesi
from . import pin, satirlar

__all__ = ["gomod", "surum_dosyasi"]

_GO_RE = re.compile(r"^go\s+(\S+)")
_TOOLCHAIN_RE = re.compile(r"^toolchain\s+(\S+)")


def _minimum_yap(p: Sabitleme) -> None:
    """'go' direktifini alt-sınırlı açık aralığa çevir (minimum gereksinim)."""
    if p.aralik is None or not p.aralik.parcalar:
        return
    alt = p.aralik.parcalar[0].alt
    if alt is None:
        return
    p.aralik = AralikKumesi((Aralik(alt=alt, alt_kapsar=True),))


def gomod(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    sonuc: list[Sabitleme] = []
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        m = _GO_RE.match(t)
        if m:
            p = pin("go", dosya, "gomod", m.group(1), satir=i, lang=lang)
            _minimum_yap(p)
            sonuc.append(p)
            continue
        m = _TOOLCHAIN_RE.match(t)
        if m:
            sonuc.append(pin("go", dosya, "gomod-toolchain",
                             m.group(1).removeprefix("go"), satir=i, lang=lang))
    if not sonuc:
        sonuc.append(Sabitleme("go", dosya, "gomod", "",
                               uyari=_m(lang, "w_gomod_no_go")))
    return sonuc


def surum_dosyasi(dosya: str, icerik: str, *,
                  lang: str = "tr") -> list[Sabitleme]:
    satir_list = satirlar(icerik)
    for i, s in enumerate(satir_list, start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        return [pin("go", dosya, "go-version", t, satir=i, lang=lang)]
    return [Sabitleme("go", dosya, "go-version", "",
                      uyari=_m(lang, "w_empty_file"))]
