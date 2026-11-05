"""Node sürüm kaynakları: .nvmrc, .node-version, package.json engines.node."""

from __future__ import annotations

import json
import re

from ..dil import m as _m
from ..sabitleme import Sabitleme
from . import pin, satirlar

__all__ = ["surum_dosyasi", "package_json", "lts_coz"]

# Node LTS takma adları. Kaynak: nodejs/Release schedule.json
# (https://raw.githubusercontent.com/nodejs/Release/main/schedule.json).
# Hydrogen 18'dir (16 DEĞİL — 16'nın adı Gallium'dur). Bilinmeyen takma ad
# tahmin edilmez; "dinamik, atlandı" işaretlenir. Tablo elle tutulur ve yeni
# LTS serisi çıktığında güncellenmelidir.
LTS_ADLARI = {
    "gallium": "16",
    "hydrogen": "18",
    "iron": "20",
    "jod": "22",
    "krypton": "24",
}
LTS_VAR = "*"


def lts_coz(ham: str) -> tuple[str, bool]:
    """`.nvmrc` belirtecini çözer: (değer, biliniyor mu).

    ``lts/iron`` -> ("20", True); ``lts/uzayli`` -> ("lts/uzayli", False).
    ``lts/*`` HAREKETLİ takma addır: tablonun en büyüğünü güncel gerçekmiş
    gibi döndürmeyiz — doğrulanamadığı için dinamik sayılır (False).
    """
    t = ham.strip().lower()
    if t.startswith("lts/"):
        ad = t[len("lts/"):]
        if ad == LTS_VAR:
            return ham.strip(), False  # güncelliği doğrulanamayan hareketli alias
        if ad in LTS_ADLARI:
            return LTS_ADLARI[ad], True
        return ham.strip(), False
    return ham.strip(), True


def surum_dosyasi(dosya: str, icerik: str, tur: str = "nvmrc", *,
                   lang: str = "tr") -> list[Sabitleme]:
    """.nvmrc / .node-version: ilk boş olmayan satır tek belirteçtir."""
    satir_list = satirlar(icerik)
    for i, s in enumerate(satir_list, start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        deger, biliniyor = lts_coz(t)
        if not biliniyor:
            return [Sabitleme("node", dosya, tur, t, dinamik=True, satir=i)]
        return [pin("node", dosya, tur, deger, satir=i, lang=lang)]
    return [Sabitleme("node", dosya, tur, "", uyari=_m(lang, "w_empty_file"))]


def package_json(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    try:
        veri = json.loads(icerik)
    except (ValueError, TypeError) as exc:
        return [Sabitleme("node", dosya, "engines", "",
                          uyari=_m(lang, "w_invalid_json", hata=exc))]
    if not isinstance(veri, dict):
        return [Sabitleme("node", dosya, "engines", "",
                          uyari=_m(lang, "w_json_not_object"))]
    engines = veri.get("engines")
    if not isinstance(engines, dict) or "node" not in engines:
        return []
    ham = engines["node"]
    if not isinstance(ham, str):
        return [Sabitleme("node", dosya, "engines", str(ham),
                          uyari=_m(lang, "w_engines_not_text"))]
    return [pin("node", dosya, "engines", ham, lang=lang,
                satir=_engines_node_satırı(icerik, ham))]


def _kök_anahtar_başlangıcı(metin: str, anahtar: str) -> int | None:
    """KÖK nesnede (derinlik 1) `"anahtar": {` girişinin '{' konumu.

    Basit `re.search('"anahtar"\\s*:\\s*\\{')` her derinlikte bulur:
    `{"custom": {"engines": {"node": "22"}}, "engines": {...}}` içinde
    yanlış alanı (custom.engines) seçer. Burada tırnak/kaçış durumunu
    izleyerek AYNI KÖK NESNEDEKİ anahtarlar taranır; birebir tek eşleşme
    yoksa konum belirsizdir → None.
    """
    derinlik = 0
    i = 0
    n = len(metin)
    bulunan: list[int] = []
    while i < n:
        c = metin[i]
        if c == '"':
            son = _dize_sonu(metin, i)
            if derinlik == 1:
                # anahtar mı? sonrası ':' olmalı (beyazlık boşluk tolere)
                j = son
                while j < n and metin[j] in " \t\r\n":
                    j += 1
                if j < n and metin[j] == ":":
                    ad = metin[i + 1:son - 1]
                    if ad == anahtar:
                        k = j + 1
                        while k < n and metin[k] in " \t\r\n":
                            k += 1
                        if k < n and metin[k] == "{":
                            bulunan.append(k)
            i = son
        elif c in "{[":
            derinlik += 1
            i += 1
        elif c in "}]":
            derinlik -= 1
            i += 1
        else:
            i += 1
    return bulunan[0] if len(bulunan) == 1 else None


def _dize_sonu(metin: str, baş: int) -> int:
    """baş'daki açtırma tırnağının KAPANIŞından sonraki indek."""
    i = baş + 1
    n = len(metin)
    while i < n:
        if metin[i] == "\\":
            i += 2
            continue
        if metin[i] == '"':
            return i + 1
        i += 1
    return n


def _eşleşen_kapanış(metin: str, açık: int) -> int:
    """'{' indeksinden sonra gelen eşleşen '}' indeksi (tırnak sezgili)."""
    derinlik = 0
    i = açık
    n = len(metin)
    while i < n:
        c = metin[i]
        if c == '"':
            i = _dize_sonu(metin, i)
            continue
        if c == "{":
            derinlik += 1
        elif c == "}":
            derinlik -= 1
            if derinlik == 0:
                return i
        i += 1
    return n


def _engines_node_satırı(metin: str, ham: str) -> int | None:
    """Ayrıştırılan KÖK engines.node DEĞERİNİN kesin satırı.

    Yalnız kök nesnedeki `engines` anahtarı izlenir (`custom.engines.node`
    tuzağı); nesne içinde `"node"` anahtarı birebir tek ve değeri ham ile
    bayt birebir aynıysa konum vardır. Belirsizlikte konum YOK (sync yazmaz).
    """
    açık = _kök_anahtar_başlangıcı(metin, "engines")
    if açık is None:
        return None
    nesne = metin[açık + 1:_eşleşen_kapanış(metin, açık)]
    eşleşen = list(re.finditer(r'"node"\s*:\s*"((?:[^"\\]|\\.)*)"', nesne))
    if len(eşleşen) != 1 or eşleşen[0].group(1) != ham:
        return None  # belirsiz ya da kaçışlı/farklı değer: konumdan emin değiliz
    return metin[:açık + 1 + eşleşen[0].start()].count("\n") + 1
