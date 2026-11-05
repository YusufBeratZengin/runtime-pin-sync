"""TOML okuma: ``tomllib`` varsa o, yoksa (Python 3.10) mini bir yedek.

Yedek ayrıştırıcı ``[tablo]`` ve ``[[dizi.tablo]]`` başlıkları ile
``anahtar = "metin"`` satırlarını ve ÇOK SATIRLI dizi/tablo değerlerini tanır
(``keywords = [`` ile başlayıp ``]`` ile biten) — projemizin okuduğu
``mise.toml``, ``rust-toolchain.toml`` ve tipik ``pyproject.toml`` dosyaları
(içlerinde ``requires-python`` varsa) bu yolla çözülebilir. Biçim bozuksa
``ValueError``.
"""

from __future__ import annotations

import re
from typing import Any

from .dil import m as _m

try:  # Python 3.11+
    import tomllib as _tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - 3.10 yolunda test edilir
    _tomllib = None

__all__ = ["oku", "mini_ayristir"]

_MINI_SATIR = re.compile(r'^([A-Za-z0-9_.\-"]+)\s*=\s*(.+)$')


def oku(veri: bytes, *, lang: str = "tr") -> dict[str, Any]:
    """TOML baytlarını sözlüğe çevirir; bozuksa ValueError fırlatır.

    ``lang`` yalnız YEDEK ayrıştırıcının hata metnini etkiler; ``tomllib``
    hataları stdlib'in kendi (İngilizce) metnidir ve olduğu gibi aktarılır.
    """
    if _tomllib is not None:
        veri_sözlük: dict[str, Any] = _tomllib.loads(veri.decode("utf-8"))
        return veri_sözlük
    return mini_ayristir(veri.decode("utf-8"), lang=lang)


def mini_ayristir(metin: str, *, lang: str = "tr") -> dict[str, Any]:
    sonuc: dict[str, Any] = {}
    aktif: dict[str, Any] = sonuc
    ham_satirlar = metin.splitlines()
    i = 0
    while i < len(ham_satirlar):
        no = i + 1
        govde = _yorum_temizle(ham_satirlar[i].strip())
        i += 1
        if not govde:
            continue
        if govde.startswith("[[") and govde.endswith("]]"):
            aktif = _dizi_tablo(sonuc, govde[2:-2].strip().strip('"'), no,
                                lang=lang)
            continue
        if govde.startswith("[") and govde.endswith("]"):
            ad = govde[1:-1].strip().strip('"')
            if "[" in ad or "]" in ad:
                raise ValueError(_m(lang, "toml_unsupported_header", no=no))
            hedef: Any = sonuc
            for parca in ad.split("."):
                hedef = hedef.setdefault(parca, {})
                if not isinstance(hedef, dict):
                    raise ValueError(_m(lang, "toml_conflicting_key", no=no))
            aktif = hedef
            continue
        m = _MINI_SATIR.match(govde)
        if not m:
            raise ValueError(_m(lang, "toml_unparsable_line", no=no, govde=govde))
        anahtar = m.group(1).strip('"')
        deger = m.group(2).strip()
        # çok satırlı dizi/tablo: "[ ... satır satır ... ]" kapanana kadar topla
        while not _dengede(deger) and i < len(ham_satirlar):
            ek = _yorum_temizle(ham_satirlar[i].strip())
            i += 1
            if ek:
                deger = f"{deger} {ek}"
        if not _dengede(deger):
            raise ValueError(_m(lang, "toml_unclosed", no=no))
        aktif[anahtar] = _deger(deger)
    return sonuc


def _dizi_tablo(sonuc: dict[str, Any], ad: str, no: int, *,
                lang: str = "tr") -> dict[str, Any]:
    """[[a.b]] bloğu: listesizse açar, yeni sözlük ekler, ona bağlar."""
    if "[" in ad or "]" in ad:
        raise ValueError(_m(lang, "toml_unsupported_header", no=no))
    parcalar = ad.split(".")
    hedef: Any = sonuc
    for parca in parcalar[:-1]:
        hedef = hedef.setdefault(parca, {})
        if not isinstance(hedef, dict):
            raise ValueError(_m(lang, "toml_conflicting_key", no=no))
    liste = hedef.setdefault(parcalar[-1], [])
    if not isinstance(liste, list):
        raise ValueError(_m(lang, "toml_conflicting_key", no=no))
    yeni: dict[str, Any] = {}
    liste.append(yeni)
    return yeni


def _dengede(deger: str) -> bool:
    """Tırnak dışı [ { kapanmış mı? (çok satırlı değer tespiti)"""
    derinlik = 0
    tirnak = ""
    for ch in deger:
        if tirnak:
            if ch == tirnak:
                tirnak = ""
        elif ch in "\"'":
            tirnak = ch
        elif ch in "[{":
            derinlik += 1
        elif ch in "]}":
            derinlik -= 1
    return derinlik <= 0


def _yorum_temizle(govde: str) -> str:
    out: list[str] = []
    tirnak = ""
    for idx, ch in enumerate(govde):
        if tirnak:
            out.append(ch)
            if ch == tirnak:
                tirnak = ""
        elif ch in "\"'":
            tirnak = ch
            out.append(ch)
        elif ch == "#" and (idx == 0 or govde[idx - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def _deger(ham: str) -> Any:
    if len(ham) >= 2 and ham[0] == ham[-1] and ham[0] in "\"'":
        return ham[1:-1]
    if ham.startswith("[") and ham.endswith("]"):
        icerik = ham[1:-1].strip()
        if not icerik:
            return []
        return [_deger(p.strip()) for p in _virgül_ayır(icerik)]
    if ham.startswith("{") and ham.endswith("}"):
        return {k.strip().strip('"'): _deger(v.strip())
                for k, _, v in (öğ.partition("=") for öğ in _virgül_ayır(ham[1:-1])
                                if "=" in öğ)}
    if ham in ("true", "false"):
        return ham == "true"
    try:
        return int(ham)
    except ValueError:
        return ham


def _virgül_ayır(icerik: str) -> list[str]:
    """Üst düzey virgüllerle böl: tırnak ve iç içe [ { virgülleri yutulmaz."""
    ögeler: list[str] = []
    tampon = ""
    derinlik = 0
    tirnak = ""
    for ch in icerik:
        if tirnak:
            tampon += ch
            if ch == tirnak:
                tirnak = ""
            continue
        if ch in "\"'":
            tirnak = ch
            tampon += ch
            continue
        if ch in "[{":
            derinlik += 1
        elif ch in "]}":
            derinlik -= 1
        if ch == "," and derinlik == 0:
            ögeler.append(tampon)
            tampon = ""
        else:
            tampon += ch
    if tampon.strip():
        ögeler.append(tampon)
    return ögeler
