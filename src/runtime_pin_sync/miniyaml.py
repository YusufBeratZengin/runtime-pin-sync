"""GitHub Actions iş akışları için küçük, bağımlılıksız YAML ayrıştırıcı.

Amaç genel amaçlı bir YAML motoru olmak değil; GitHub Actions ve benzeri CI
iş akışlarında ihtiyaç duyulan alt kümeyi sıfır bağımlılıkla ve güvenle ayrıştırmaktır.

Desteklenen YAML alt kümesi:
  - İç içe eşlemeler (ör. ``jobs:``, ``strategy:``, ``with:``)
  - Blok diziler (``- uses: actions/setup-node@v4``)
  - Akış dizileri (``node: [20, 22]``, ``[3.10, 3.12]``)
  - Tırnaksız düz değerler, tek/çift tırnaklı dizgiler
  - Çok satırlı değişmez/katlanmış blok metinler (``|``, ``>``, ``|-``, ``>-``)
  - Yorumlar (satır başı veya satır içi ``#``)

Kasıtlı olarak desteklenmeyen yapılar:
  - Çıpa ve takma adlar (``&ref``, ``*ref``)
  - Birleştirme anahtarları (``<<: *defaults``)
  - Özel veri tipi etiketleri (``!!str``, ``!custom``)
  - Karmaşık / çok satırlı anahtar söz dizimi (``? anahtar``)
  - Girintide sekme (TAB) karakteri kullanımı (kesinlikle yasaktır)

Davranış:
  Alt küme dışı veya bozuk bir söz diziminde ``MiniYamlError`` fırlatılır.
  Çağıran katman (``ci.py``) bunu yakalar ve süreci çökertmek yerine açık bir
  "okunamadı: desteklenmeyen YAML (...)" uyarısı üretir.
"""

from __future__ import annotations

__all__ = ["ayristir", "MiniYamlError"]

from typing import Any


class MiniYamlError(ValueError):
    pass


def ayristir(metin: str) -> Any:
    satirlar = _hazirla(metin)
    deger, _ = _blok(satirlar, 0, 0)
    return deger


def _hazirla(metin: str) -> list[tuple[int, str]]:
    satirlar: list[tuple[int, str]] = []
    for ham in metin.splitlines():
        if "\t" in ham[: len(ham) - len(ham.lstrip())]:
            raise MiniYamlError("girinti için sekme kullanılamaz")
        kiris = len(ham) - len(ham.lstrip(" "))
        govde = ham.strip()
        if not govde or govde.startswith("#"):
            continue
        if govde in ("---", "..."):
            continue
        satirlar.append((kiris, govde))
    return satirlar


def _satiri_atla(satirlar: list[tuple[int, str]], i: int, kiris: int) -> int:
    while i < len(satirlar) and satirlar[i][0] >= kiris:
        i += 1
    return i


def _blok(satirlar: list[tuple[int, str]], i: int, kiris: int) -> tuple[Any, int]:
    if i >= len(satirlar):
        return None, i
    if satirlar[i][1].startswith("- "):
        return _dizi(satirlar, i, satirlar[i][0])
    if satirlar[i][1] == "-":
        return _dizi(satirlar, i, satirlar[i][0])
    return _esleme(satirlar, i, kiris)


def _esleme(satirlar: list[tuple[int, str]], i: int, kiris: int) -> tuple[dict[str, Any], int]:
    sonuc: dict[str, Any] = {}
    while i < len(satirlar):
        gir, govde = satirlar[i]
        if gir < kiris:
            break
        if gir > kiris:
            raise MiniYamlError(f"beklenmeyen girinti: {govde!r}")
        if govde.startswith("- "):
            break
        anahtar, ayrac, deger = govde.partition(":")
        if not ayrac:
            raise MiniYamlError(f"eşleme beklenirken: {govde!r}")
        anahtar = _duz(anahtar)
        deger = _yorum_temizle(deger.strip())
        if deger in ("|", ">", "|-", ">-", "|+", ">+"):
            bits, i = _blok_metin(satirlar, i + 1, gir)
            sonuc[anahtar] = " ".join(bits)
        elif deger:
            sonuc[anahtar] = _deger(deger)
            i += 1
        else:
            i += 1
            if i < len(satirlar) and satirlar[i][0] > gir:
                sonuc[anahtar], i = _blok(satirlar, i, satirlar[i][0])
            elif i < len(satirlar) and satirlar[i][0] == gir and satirlar[i][1].startswith("-"):
                sonuc[anahtar], i = _dizi(satirlar, i, gir)
            else:
                sonuc[anahtar] = None
    return sonuc, i


def _dizi(satirlar: list[tuple[int, str]], i: int, kiris: int) -> tuple[list[Any], int]:
    sonuc: list[Any] = []
    while i < len(satirlar):
        gir, govde = satirlar[i]
        if gir != kiris or not (govde == "-" or govde.startswith("- ")):
            break
        govde = govde[1:].strip()
        if not govde:
            i += 1
            if i < len(satirlar) and satirlar[i][0] > kiris:
                deger, i = _blok(satirlar, i, satirlar[i][0])
                sonuc.append(deger)
            else:
                sonuc.append(None)
        elif ":" in govde and not govde.startswith(("'", '"')):
            # "- key: value" — aynı satırda başlayan eşleme, girinti = kiris + 2
            satir_kiris = kiris + 2
            i += 1
            esleme, i = _esleme(satirlar, i, satir_kiris)
            anahtar, _, deger = govde.partition(":")
            anahtar = _duz(anahtar)
            deger = _yorum_temizle(deger.strip())
            if deger:
                esleme = {anahtar: _deger(deger), **esleme}
            else:
                if i < len(satirlar) and satirlar[i][0] > satir_kiris:
                    alt, i = _blok(satirlar, i, satirlar[i][0])
                else:
                    alt = None
                esleme = {anahtar: alt, **esleme}
            sonuc.append(esleme)
        else:
            sonuc.append(_deger(_yorum_temizle(govde)))
            i += 1
    return sonuc, i


def _blok_metin(satirlar: list[tuple[int, str]], i: int, kiris: int) -> tuple[list[str], int]:
    bits: list[str] = []
    while i < len(satirlar) and satirlar[i][0] > kiris:
        bits.append(satirlar[i][1])
        i += 1
    return bits, i


def _yorum_temizle(govde: str) -> str:
    # Tırnak içinde olmayan ' #' yorumunu kırp
    out: list[str] = []
    tirnak = ""
    for idx, ch in enumerate(govde):
        if tirnak:
            out.append(ch)
            if ch == tirnak:
                tirnak = ""
        elif ch in "'\"":
            tirnak = ch
            out.append(ch)
        elif ch == "#" and (idx == 0 or govde[idx - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def _deger(ham: str) -> Any:
    ham = ham.strip()
    if ham.startswith("[") and ham.endswith("]"):
        icerik = ham[1:-1].strip()
        if not icerik:
            return []
        return [_deger(parca) for parca in _virgulle_ayir(icerik)]
    if ham.startswith("{") and ham.endswith("}"):
        icerik = ham[1:-1].strip()
        sonuc: dict[str, Any] = {}
        if icerik:
            for parca in _virgulle_ayir(icerik):
                a, _, d = parca.partition(":")
                sonuc[_duz(a)] = _deger(d)
        return sonuc
    return _duz(ham)


def _virgulle_ayir(metin: str) -> list[str]:
    parcalar: list[str] = []
    derinlik = 0
    tirnak = ""
    aktif: list[str] = []
    for ch in metin:
        if tirnak:
            aktif.append(ch)
            if ch == tirnak:
                tirnak = ""
        elif ch in "'\"":
            tirnak = ch
            aktif.append(ch)
        elif ch in "[{":
            derinlik += 1
            aktif.append(ch)
        elif ch in "]}":
            derinlik -= 1
            aktif.append(ch)
        elif ch == "," and derinlik == 0:
            parcalar.append("".join(aktif).strip())
            aktif = []
        else:
            aktif.append(ch)
    if aktif:
        parcalar.append("".join(aktif).strip())
    return parcalar


def _duz(ham: str) -> str:
    ham = ham.strip()
    if len(ham) >= 2 and ham[0] == ham[-1] and ham[0] in "'\"":
        return ham[1:-1]
    if ham in ("null", "~"):
        return ""
    if ham in ("true", "True", "yes"):
        return "true"
    if ham in ("false", "False", "no"):
        return "false"
    return ham
