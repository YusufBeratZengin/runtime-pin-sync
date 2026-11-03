"""Araç yöneticisi dosyaları: .tool-versions (asdf) ve mise.toml.

Bu dosyalar çoklu çalışma zamanını tek yerde tutar; kartın varsayılan
"tek kaynak" adaylarıdır. Bilinmeyen araç adları sessizce yoksayılır.
"""

from __future__ import annotations

import re

from .. import minitoml
from ..sabitleme import Sabitleme
from . import grid_pin, pin, satirlar

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
        ad, degerler = parcalar[0], parcalar[1:]
        cz = TAKMA_ADLAR.get(ad.lower())
        if cz is None:
            continue
        if any(d.lower() in _BILINMEYEN_DEGERLER for d in degerler):
            sonuc.append(Sabitleme(cz, dosya, "tool-versions",
                                   " ".join(degerler), dinamik=True, satir=i))
        elif len(degerler) == 1:
            sonuc.append(pin(cz, dosya, "tool-versions", degerler[0], satir=i))
        else:
            # asdf çoklu kurulum: "python 3.12.1 3.11.8" İKİSİNİ birden
            # kurar → BİRLİŞİM (ızgara) olarak modellenir; ilk değere
            # indirgenmez, hiçbir üyeyle tek başına çelişki sayılmaz.
            sonuc.append(grid_pin(cz, dosya, "tool-versions", degerler))
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
                                       satir=_tools_satırı(satirlar(icerik), str(ad))))
            else:
                sonuc.append(pin(cz, dosya, "mise", metin,
                                 satir=_tools_satırı(satirlar(icerik), str(ad))))
    return sonuc


_BÖLÜM_RE = re.compile(r"^\s*\[\[?([^\]]+)\]?\]")


def _tools_satırı(satir_list: list[str], ad: str) -> int | None:
    """[tools] bölümündeki TAM anahtar satırı.

    Serbest arama `[env] node = "22"` gibi Ortam değişkeni satırlarını da
    bulur ve sync yanlış bölümü değiştirirdi. Yalnız akış-dışı (inline
    olmayan) `[tools]` tablosundaki `ad = ...` satırları sayılır; birebir
    tek eşleşme yoksa konum belirsizdir → None (sync yazmaz).
    """
    desen = re.compile(rf"^\s*(?:\"{re.escape(ad)}\"|'{re.escape(ad)}'|{re.escape(ad)})\s*=")
    bölüm = ""
    hedefler: list[int] = []
    for i, s in enumerate(satir_list, start=1):
        b = _BÖLÜM_RE.match(s)
        if b:
            bölüm = b.group(1).strip().strip("\"'")
            continue
        if bölüm == "tools" and desen.match(s):
            hedefler.append(i)
    return hedefler[0] if len(hedefler) == 1 else None
