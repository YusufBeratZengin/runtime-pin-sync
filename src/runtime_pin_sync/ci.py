"""GitHub Actions iş akışlarını okuma: ``setup-*`` adımları ve sürüm matrisleri.

- ``actions/setup-node|python|go|java`` ve ``dtolnay/rust-toolchain`` adımları
- ``*-version`` ve ``*-version-file`` girdileri
- ``strategy.matrix`` listeleri (test ızgarası BirLEŞİM olarak tek sabitleme olur)
- ``${{ matrix.X }}`` şablonları iş matrisinden çözülür; çözülemezse
  "dinamik, atlandı" — asla hata değil.
"""

from __future__ import annotations

import os
import re
from typing import Any

from . import miniyaml
from .bulucular import grid_pin, pin, satirlar
from .sabitleme import Sabitleme

__all__ = ["is_aksi", "MATRIX_ANAHTARLARI"]

# eylem => (sürüm girdisi, sürüm-dosyası girdisi ya da None, çalışma zamanı)
_ADLIMLAR: tuple[tuple[str, str, str | None, str], ...] = (
    ("setup-node@", "node-version", "node-version-file", "node"),
    ("setup-python@", "python-version", "python-version-file", "python"),
    ("setup-go@", "go-version", None, "go"),
    ("setup-java@", "java-version", None, "java"),
    ("rust-toolchain@", "toolchain", None, "rust"),
)

MATRIX_ANAHTARLARI = {
    "node-version": "node", "node_version": "node", "node": "node",
    "python-version": "python", "python_version": "python", "python": "python",
    "go-version": "go", "go_version": "go", "go": "go",
    "java-version": "java", "java_version": "java", "java": "java",
    "rust-version": "rust", "toolchain": "rust",
}

_SABLON_RE = re.compile(r"\$\{\{\s*(?:matrix|env|inputs|var)\.([A-Za-z0-9_\-]+)\s*\}\}")


def is_aksi(
    dosya: str,
    icerik: str,
    degiskenler: dict[str, str] | None = None,
    depo_koku: str = "",
) -> list[Sabitleme]:
    degiskenler = degiskenler or {}
    try:
        veri = miniyaml.ayristir(icerik)
    except miniyaml.MiniYamlError as exc:
        return [Sabitleme("bilinmeyen", dosya, "ci", "",
                          uyari=f"okunamadı: desteklenmeyen YAML ({exc})")]
    if not isinstance(veri, dict):
        return [Sabitleme("bilinmeyen", dosya, "ci", "",
                          uyari="okunamadı: iş akışı bir eşleme değil")]
    isler = veri.get("jobs")
    if not isinstance(isler, dict):
        return []
    satir_list = satirlar(icerik)
    sonuc: list[Sabitleme] = []
    for ise_adi, islem in isler.items():
        if not isinstance(islem, dict):
            continue
        matris = _matris(islem)
        tuketlenen: set[str] = set()
        sonuc.extend(_adimlar(dosya, islem, matris, tuketlenen, satir_list,
                              degiskenler, depo_koku, str(ise_adi)))
        for anahtar, deger in matris.items():
            if anahtar in tuketlenen or not isinstance(deger, list):
                continue
            cz = MATRIX_ANAHTARLARI.get(str(anahtar).lower())
            if cz is None:
                continue
            sonuc.extend(_matris_sabitlemeleri(dosya, cz, str(anahtar), deger))
    return sonuc


def _matris(islem: dict[str, Any]) -> dict[str, Any]:
    strateji = islem.get("strategy")
    if isinstance(strateji, dict) and isinstance(strateji.get("matrix"), dict):
        return strateji["matrix"]
    return {}


def _adimlar(
    dosya: str,
    islem: dict[str, Any],
    matris: dict[str, Any],
    tuketlenen: set[str],
    satir_list: list[str],
    degiskenler: dict[str, str],
    depo_koku: str,
    ise_adi: str,
) -> list[Sabitleme]:
    sonuc: list[Sabitleme] = []
    adimlar = islem.get("steps")
    if not isinstance(adimlar, list):
        return sonuc
    for adim in adimlar:
        if not isinstance(adim, dict):
            continue
        uses = str(adim.get("uses") or "")
        eslesme = next(((e, g, gd, cz) for e, g, gd, cz in _ADLIMLAR if e in uses), None)
        if eslesme is None:
            continue
        _, giradi, dosya_giradi, cz = eslesme
        with_block = adim.get("with")
        with_block = with_block if isinstance(with_block, dict) else {}
        if dosya_giradi and dosya_giradi in with_block:
            sonuc.extend(_surum_dosyasi_gir(dosya, cz, str(with_block[dosya_giradi]),
                                            satir_list, depo_koku))
        if giradi not in with_block:
            continue
        deger = with_block[giradi]
        satir_no = _satir_no(satir_list, giradi)
        sonuc.extend(_deger_sabitlemeleri(dosya, cz, "ci-adim", deger, matris,
                                          tuketlenen, satir_no, degiskenler))
    return sonuc


def _deger_sabitlemeleri(
    dosya: str,
    cz: str,
    tur: str,
    deger: Any,
    matris: dict[str, Any],
    tuketlenen: set[str],
    satir_no: int | None,
    degiskenler: dict[str, str],
) -> list[Sabitleme]:
    if isinstance(deger, list):
        metinler = [str(x) for x in deger]
        dinamikler = [m for m in metinler if "${{" in m]
        somut = [m for m in metinler if "${{" not in m]
        # listeler test ızgarasıdır: satır bilgisi tek hedef göstermez
        ciktilar = [grid_pin(cz, dosya, tur, somut)] if somut else []
        for d in dinamikler:
            cozulen = _sablon_ara(d, matris, tuketlenen, degiskenler)
            if isinstance(cozulen, list):
                ciktilar.append(grid_pin(cz, dosya, tur, [str(x) for x in cozulen]))
            else:
                ciktilar.append(Sabitleme(cz, dosya, tur, d, dinamik=True))
        return ciktilar
    metin = str(deger)
    if "${{" in metin:
        cozulen = _sablon_ara(metin, matris, tuketlenen, degiskenler)
        if isinstance(cozulen, list):
            return [grid_pin(cz, dosya, tur, [str(x) for x in cozulen])]
        if isinstance(cozulen, str):
            return [pin(cz, dosya, tur, cozulen, satir=None)]
        return [Sabitleme(cz, dosya, tur, metin, dinamik=True, satir=satir_no)]
    return [pin(cz, dosya, tur, metin, satir=satir_no)]


def _sablon_ara(
    sablon: str,
    matris: dict[str, Any],
    tuketlenen: set[str],
    degiskenler: dict[str, str],
) -> Any:
    """``${{ matrix.X }}`` tüm ifadeyse X'in matris değerini, tek değerliyse
    metni döndürür; bulamazsa ``None``."""
    tam = _SABLON_RE.fullmatch(sablon.strip())
    if tam:
        ad = tam.group(1)
        if ad in degiskenler:
            return degiskenler[ad]
        if ad in matris:
            tuketlenen.add(ad)
            return matris[ad]
        return None
    kismiler = _SABLON_RE.findall(sablon)
    if len(kismiler) == 1 and (ad := kismiler[0]):
        if ad in degiskenler:
            return _SABLON_RE.sub(degiskenler[ad], sablon)
    return None


def _matris_sabitlemeleri(dosya: str, cz: str, anahtar: str, degerler: list[Any]) -> list[Sabitleme]:
    metinler = [str(x) for x in degerler]
    somut = [m for m in metinler if "${{" not in m]
    dinamik = [m for m in metinler if "${{" in m]
    sonuc: list[Sabitleme] = []
    if somut:
        sonuc.append(grid_pin(cz, dosya, "ci-matriks", somut))
    for d in dinamik:
        sonuc.append(Sabitleme(cz, dosya, "ci-matriks", d, dinamik=True))
    return sonuc


def _surum_dosyasi_gir(
    dosya: str, cz: str, hedef: str, satir_list: list[str], depo_koku: str
) -> list[Sabitleme]:
    """node-version-file gibi yönlendirmeler: hedef dosya zaten taranır;
    yalnız hedef YOKSA uyarı üret."""
    hedef = hedef.strip()
    if "${{" in hedef:
        return [Sabitleme(cz, dosya, "ci-dosya", hedef, dinamik=True,
                          satir=_satir_no(satir_list, "version-file"))]
    tam = os.path.join(depo_koku, *hedef.split("/"))
    if os.path.isfile(tam):
        return []  # asıl dosya zaten taranacak — tutarlılık kendiliğinden
    return [Sabitleme(cz, dosya, "ci-dosya", hedef,
                      uyari=f"okunamadı: version-file {hedef!r} bulunamadı",
                      satir=_satir_no(satir_list, "version-file"))]


def _satir_no(satir_list: list[str], iplik: str) -> int | None:
    for i, s in enumerate(satir_list, start=1):
        if iplik in s:
            return i
    return None