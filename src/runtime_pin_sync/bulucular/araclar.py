"""Araç yöneticisi dosyaları: .tool-versions (asdf) ve mise.toml.

Bu dosyalar çoklu çalışma zamanını tek yerde tutar; kartın varsayılan
"tek kaynak" adaylarıdır. Bilinmeyen araç adları sessizce yoksayılır.
"""

from __future__ import annotations

from .. import minitoml
from ..sabitleme import Sabitleme
from . import pin, satirlar

__all__ = ["tool_versions", "mise", "TAKMA_ADLAR"]

TAKMA_ADLAR = {
    "node": "node", "nodejs": "node",
    "python": "python", "python3": "python",
    "go": "go", "golang": "go",
    "rust": "rust", "rustlang": "rust",
    "java": "java",
}
_BILINMEYEN_DEGERLER = {"latest", "latest-stable", "current", "system", "default"}


def tool_versions(dosya: str, icerik: str) -> list[Sabitleme]:
    sonuc: list[Sabitleme] = []
    for i, s in enumerate(satirlar(icerik), start=1):
        govde = s.split("#", 1)[0].strip()
        if not govde:
            continue
        parcalar = govde.split()
        if len(parcalar) < 2:
            continue
        ad, deger = parcalar[0], parcalar[1]
        cz = TAKMA_ADLAR.get(ad.lower())
        if cz is None:
            continue
        if deger.lower() in _BILINMEYEN_DEGERLER:
            sonuc.append(Sabitleme(cz, dosya, "tool-versions", deger, dinamik=True, satir=i))
        else:
            sonuc.append(pin(cz, dosya, "tool-versions", deger, satir=i))
    return sonuc


def mise(dosya: str, icerik: str) -> list[Sabitleme]:
    try:
        veri = minitoml.oku(icerik.encode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return [Sabitleme("node", dosya, "mise", "",
                          uyari=f"okunamadı: geçersiz TOML ({exc})")]
    araclar = veri.get("tools")
    if not isinstance(araclar, dict):
        return []
    sonuc: list[Sabitleme] = []
    for ad, deger in araclar.items():
        cz = TAKMA_ADLAR.get(str(ad).lower())
        if cz is None:
            continue
        degerler = deger if isinstance(deger, list) else [deger]
        for d in degerler:
            if not isinstance(d, str):
                d = str(d)
            metin = d.strip()
            if not metin:
                continue
            if "${{" in metin:
                sonuc.append(Sabitleme(cz, dosya, "mise", metin, dinamik=True))
            elif metin.lower() in _BILINMEYEN_DEGERLER:
                sonuc.append(Sabitleme(cz, dosya, "mise", metin, dinamik=True,
                                       satir=_satir_bul_adi(satirlar(icerik), str(ad))))
            else:
                sonuc.append(pin(cz, dosya, "mise", metin,
                                 satir=_satir_bul_adi(satirlar(icerik), str(ad))))
    return sonuc


def _satir_bul_adi(satir_list: list[str], ad: str) -> int | None:
    for i, s in enumerate(satir_list, start=1):
        if ad in s and "=" in s:
            return i
    return None
