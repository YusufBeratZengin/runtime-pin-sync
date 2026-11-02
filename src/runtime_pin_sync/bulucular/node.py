"""Node sürüm kaynakları: .nvmrc, .node-version, package.json engines.node."""

from __future__ import annotations

import json

from . import pin, satirlar
from ..sabitleme import Sabitleme

__all__ = ["surum_dosyasi", "package_json", "lts_coz"]

# Node LTS takma adları (kaynak: nodejs.org Release Schedule).
# Bilinmeyen takma ad tahmin edilmez; "dinamik, atlandı" işaretlenir.
LTS_ADLARI = {
    "hydrogen": "16",
    "iron": "20",
    "jod": "22",
    "krypton": "24",
}
LTS_VAR = "*"


def lts_coz(ham: str) -> tuple[str, bool]:
    """.nvmrc belirtecini çözer: (değer, biliniyor mu).

    ``lts/iron`` -> ("20", True); ``lts/uzayli`` -> ("lts/uzayli", False).
    """
    t = ham.strip().lower()
    if t.startswith("lts/"):
        ad = t[len("lts/"):]
        if ad == LTS_VAR:
            en_yeni = max(LTS_ADLARI.values(), key=lambda v: int(v))
            return en_yeni, True
        if ad in LTS_ADLARI:
            return LTS_ADLARI[ad], True
        return ham.strip(), False
    return ham.strip(), True


def surum_dosyasi(dosya: str, icerik: str, tur: str = "nvmrc") -> list[Sabitleme]:
    """.nvmrc / .node-version: ilk boş olmayan satır tek belirteçtir."""
    satir_list = satirlar(icerik)
    for i, s in enumerate(satir_list, start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        deger, biliniyor = lts_coz(t)
        if not biliniyor:
            return [Sabitleme("node", dosya, tur, t, dinamik=True, satir=i)]
        return [pin("node", dosya, tur, deger, satir=i)]
    return [Sabitleme("node", dosya, tur, "", uyari="okunamadı: boş dosya")]


def package_json(dosya: str, icerik: str) -> list[Sabitleme]:
    try:
        veri = json.loads(icerik)
    except (ValueError, TypeError) as exc:
        return [Sabitleme("node", dosya, "engines", "",
                          uyari=f"okunamadı: geçersiz JSON ({exc})")]
    if not isinstance(veri, dict):
        return [Sabitleme("node", dosya, "engines", "",
                          uyari="okunamadı: JSON bir nesne değil")]
    engines = veri.get("engines")
    if not isinstance(engines, dict) or "node" not in engines:
        return []
    ham = engines["node"]
    if not isinstance(ham, str):
        return [Sabitleme("node", dosya, "engines", str(ham),
                          uyari="okunamadı: engines.node bir metin değil")]
    satir_list = satirlar(icerik)
    satir_no = None
    for i, s in enumerate(satir_list, start=1):
        if '"node"' in s and ham in s:
            satir_no = i
            break
    return [pin("node", dosya, "engines", ham, satir=satir_no)]
