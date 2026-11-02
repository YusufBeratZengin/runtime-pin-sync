"""Güvenli senkronizasyon: ``senkronla(yol, kaynak, kuru_calis)``.

Yalnızca *kesin hedefli*, satır-içi yeniden yazılabilir sabitlemeleri değiştirir:
hedef dosyanın yalnız ilgili satırı, yalnız sürüm belirteci değişir (diff testi
bunu doğrular). Aralıklar (``>=18``), ızgaralar, dinamik ifadeler ve şablonlu
Dockerfile etikeleri asla yazılmaz — "elle düzeltilmeli" listelenir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .docker import _FROM_RE, imaj_coz
from .karsilastir import celiski
from .sabitleme import Sabitleme
from .tara import kaynak_kontrol, tara

__all__ = ["Degisiklik", "senkronla", "YAZILABİLİR_TÜRLER", "norm_yol"]


def norm_yol(yol: str) -> str:
    """Yolu depoya göreli POSIX biçimine çevirir ('./x' -> 'x')."""
    t = yol.replace("\\", "/")
    while t.startswith("./"):
        t = t[2:]
    return t.removeprefix("/")


def _norm_yol(yol: str) -> str:
    return norm_yol(yol)

YAZILABİLİR_TÜRLER = frozenset({
    "nvmrc", "node-version", "python-version", "go-version", "java-version",
    "dockerfile", "tool-versions", "mise", "engines", "ci-adim", "pom",
})


@dataclass
class Degisiklik:
    dosya: str
    satir: int
    eski: str
    yeni: str
    gerekce: str = ""


def senkronla(
    yol: str | Path,
    kaynak: str,
    kuru_calis: bool = False,
    degiskenler: dict[str, str] | None = None,
) -> tuple[list[Degisiklik], list[Degisiklik]]:
    """(otomatik değişiklikler, elle düzeltilmesi gerekenler) döndürür.

    ``kuru_calis=True`` iken hiçbir dosyaya dokunulmaz.
    """
    kok = Path(yol)
    pimler = tara(kok, degiskenler)
    norm = _norm_yol(kaynak)
    if not kaynak_kontrol(pimler, norm):
        raise ValueError(f"kaynak bulunamadı ya da sürüm üretmiyor: {kaynak}")
    celiskiler = celiski(pimler, kaynak=norm)
    otomatik: list[Degisiklik] = []
    elle: list[Degisiklik] = []
    hedefler: dict[tuple[str, int], Degisiklik] = {}
    for c in celiskiler:
        hedef_deger = c.referans_ham
        for p in c.dislananlar:
            d = _yazma_denemesi(kok, p, hedef_deger)
            if d.gerekce:
                elle.append(d)
                continue
            anahtar = (d.dosya, d.satir)
            if anahtar in hedefler:  # aynı satıra iki hedef: güvenli değil
                hedefler[anahtar].gerekce = "aynı satırda birden fazla hedef"
                elle.append(hedefler.pop(anahtar))
                elle.append(Degisiklik(d.dosya, d.satir, d.eski, d.yeni,
                                       "aynı satırda birden fazla hedef"))
                continue
            hedefler[anahtar] = d
    if kuru_calis:
        return sorted(hedefler.values(), key=lambda d: (d.dosya, d.satir)), elle
    for (dosya, _satir), d in sorted(hedefler.items()):
        try:
            _uygula(kok, d, dosya)
            otomatik.append(d)
        except (OSError, ValueError) as exc:
            elle.append(Degisiklik(d.dosya, d.satir, d.eski, d.yeni,
                                   f"uygulanamadı: {exc}"))
    return otomatik, elle


def _uygula(kok: Path, d: Degisiklik, dosya: str) -> None:
    tam = kok / dosya
    icerik = tam.read_text(encoding="utf-8")
    satirlar = icerik.splitlines(keepends=True)
    i = d.satir - 1
    if i >= len(satirlar):
        raise ValueError("satır numarası dosya sınırını aştı")
    yeni_satir = _token_degistir(satirlar[i], d.eski, d.yeni)
    if yeni_satir is None:
        raise ValueError(f"{d.eski!r} belirteci satırda tek ve bağımsız değil")
    satirlar[i] = yeni_satir
    tam.write_text("".join(satirlar), encoding="utf-8", newline="")


def _token_degistir(satir: str, eski: str, yeni: str) -> str | None:
    """Sayısal/versiyonel belirteci satırda tam BİR kez geçiyorsa değiştirir."""
    desen = re.compile(rf"(?<![\d.]){re.escape(eski)}(?![\d.])")
    eslesen = desen.findall(satir)
    if len(eslesen) != 1:
        return None
    return desen.sub(lambda _: yeni, satir)


def _yazma_denemesi(kok: Path, p: Sabitleme, hedef: str) -> Degisiklik:
    """p sabitlemesini hedef değere çevirme planı; olmazsa notlu Degisiklik."""
    ag = Degisiklik(p.dosya, p.satir or 0, p.ham, hedef)
    if p.tur not in YAZILABİLİR_TÜRLER:
        ag.gerekce = f"{p.tur}: otomatik yeniden yazma desteklenmiyor"
        return ag
    if p.satir is None:
        ag.gerekce = "satır konumu çözülemedi"
        return ag
    if not _sabit_mi(p):
        ag.gerekce = f"{p.ham!r} bir aralık/ızgara; sabit sürüme zorlanmaz"
        return ag
    try:
        icerik = (kok / p.dosya).read_text(encoding="utf-8")
    except OSError as exc:
        ag.gerekce = f"dosya okunamadı: {exc}"
        return ag
    satirlar = icerik.splitlines()
    if p.satir > len(satirlar):
        ag.gerekce = "satır numarası dosya sınırını aştı"
        return ag
    yeni_satir = _token_degistir(satirlar[p.satir - 1], p.ham, hedef)
    if yeni_satir is None:
        ag.gerekce = f"{p.ham!r} satırda tek ve bağımsız değil"
        return ag
    if p.tur == "dockerfile" and not _docker_gecerli(yeni_satir, hedef):
        ag.gerekce = "Dockerfile etiketi şablonlu; yalnız sürüm bölümü güvenle değişir"
        return ag
    return ag


def _sabit_mi(p: Sabitleme) -> bool:
    if p.aralik is None or len(p.aralik.parcalar) != 1:
        return False
    parca = p.aralik.parcalar[0]
    return parca.alt is not None and parca.ust is not None


def _docker_gecerli(satir: str, hedef: str) -> bool:
    m = _FROM_RE.match(satir)
    if not m:
        return False
    ad, _, etiket = m.group("imaj").partition(":")
    _cz, surum = imaj_coz(ad, etiket)
    return surum == hedef
