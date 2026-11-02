"""Güvenli senkronizasyon: ``senkronla(yol, kaynak, kuru_calis)``.

Yalnızca *kesin hedefli*, satır-içi yeniden yazılabilir sabitlemeler değişir:
hedef dosyanın yalnız ilgili satırları, yalnız sürüm belirteci değişir (diff
testi bunu doğrular). Korunanlar:

- Aralıklar (``>=18``), ``^``/``~`` gibi operatörlü değerler, ızgaralar ve
  şablonlu Dockerfile etiketleri ASLA yazılmaz — "elle düzeltilmeli" listesi.
- Referans sabit bir sürüm değilse (``>=22``, ``22, 24``) hiçbir şey yazılmaz.
- Hedef dosya depo dışında kalıyorsa veya symlink'se yazılmaz (depodan çıkış
  kapalı); ham dosya bayt düzeyinde okunur, satır sonları AYNEN korunur.
- Aynı değerin birden çok satırı varsa TÜM konumlar yazılır.
- Yazmadan sonra depo yeniden taranır; giderilemeyen çelişki başarı sayılmaz,
  "elle düzeltilmeli" listesinde exit 1'e katkı koyar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .docker import _FROM_RE, imaj_coz
from .karsilastir import celiski
from .sabitleme import Sabitleme
from .tara import kaynak_kontrol, tara
from .versiyon import sabit_belirtec_mi

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
            if not sabit_belirtec_mi(hedef_deger):
                elle.append(Degisiklik(
                    p.dosya, p.satir or 0, p.ham, hedef_deger,
                    f"referans {hedef_deger!r} bir aralık/ızgridir; "
                    "sabit değere zorlanmaz"))
                continue
            for sat in _konumlar(p):
                d = _yazma_denemesi(kok, p, hedef_deger, sat)
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
    _kalan_çelişkileri_raporla(kok, norm, hedefler, elle, degiskenler)
    return otomatik, elle


def _konumlar(p: Sabitleme) -> tuple[int | None, ...]:
    """Yazılacak satır konumları: tekilleştirme konumları silmiş olamaz."""
    if p.tüm_satırlar:
        return p.tüm_satırlar
    return (p.satir,)


def _kalan_çelişkileri_raporla(
    kok: Path,
    norm: str,
    hedefler: dict[tuple[str, int], Degisiklik],
    elle: list[Degisiklik],
    degiskenler: dict[str, str] | None,
) -> None:
    """Yazmadan sonra yeniden tarar; giderilemeyen çelişki sessiz kalmaz."""
    if not hedefler:
        return
    kayıtlı = {(d.dosya, d.satir) for d in elle}
    for c in celiski(tara(kok, degiskenler), kaynak=norm):
        for p in c.dislananlar:
            for sat in _konumlar(p):
                anahtar = (p.dosya, sat if sat is not None else 0)
                if anahtar in hedefler or anahtar in kayıtlı:
                    continue  # zaten uygulandı ya da elle listeye alındı
                kayıtlı.add(anahtar)
                elle.append(Degisiklik(
                    p.dosya, anahtar[1], p.ham, c.referans_ham,
                    "senkron sonrası çelişki giderilmedi"))


def _güvenli_hedef(kok: Path, dosya: str) -> Path:
    """Depo sınırını denetler: symlink ve depo dışı yol YASAK, hedef döner."""
    tam = kok / dosya
    if tam.is_symlink():
        raise ValueError(f"{dosya}: hedef bir dosya bağlantısı (symlink)")
    kök = kok.resolve()
    çözüm = tam.resolve()
    if çözüm != kök and kök not in çözüm.parents:
        raise ValueError(f"{dosya}: hedef depo dışında ({çözüm})")
    return tam


def _uygula(kok: Path, d: Degisiklik, dosya: str) -> None:
    tam = _güvenli_hedef(kok, dosya)
    icerik = tam.read_bytes().decode("utf-8")  # CRLF/LF AYNEN kalır
    satirlar = icerik.splitlines(keepends=True)
    i = d.satir - 1
    if i >= len(satirlar):
        raise ValueError("satır numarası dosya sınırını aştı")
    yeni_satir = _token_degistir(satirlar[i], d.eski, d.yeni)
    if yeni_satir is None:
        raise ValueError(f"{d.eski!r} belirteci satırda tek ve bağımsız değil")
    satirlar[i] = yeni_satir
    tam.write_bytes("".join(satirlar).encode("utf-8"))


def _token_degistir(satir: str, eski: str, yeni: str) -> str | None:
    """Sayısal/versiyonel belirteci satırda tam BİR kez geçiyorsa değiştirir."""
    desen = re.compile(rf"(?<![\d.]){re.escape(eski)}(?![\d.])")
    eslesen = desen.findall(satir)
    if len(eslesen) != 1:
        return None
    return desen.sub(lambda _: yeni, satir)


def _yazma_denemesi(
    kok: Path, p: Sabitleme, hedef: str, satir: int | None
) -> Degisiklik:
    """p sabitlemesinin satır konumunu hedef değere çevirme planı."""
    ag = Degisiklik(p.dosya, satir or 0, p.ham, hedef)
    if p.tur not in YAZILABİLİR_TÜRLER:
        ag.gerekce = f"{p.tur}: otomatik yeniden yazma desteklenmiyor"
        return ag
    if satir is None:
        ag.gerekce = "satır konumu çözülemedi"
        return ag
    if not sabit_belirtec_mi(p.ham):
        ag.gerekce = f"{p.ham!r} bir aralık/ızgara; sabit sürüme zorlanmaz"
        return ag
    try:
        tam = _güvenli_hedef(kok, p.dosya)
        icerik = tam.read_bytes().decode("utf-8")
    except (OSError, ValueError) as exc:
        ag.gerekce = f"dosya okunamadı: {exc}"
        return ag
    satirlar = icerik.splitlines()
    if satir > len(satirlar):
        ag.gerekce = "satır numarası dosya sınırını aştı"
        return ag
    yeni_satir = _token_degistir(satirlar[satir - 1], p.ham, hedef)
    if yeni_satir is None:
        ag.gerekce = f"{p.ham!r} satırda tek ve bağımsız değil"
        return ag
    if p.tur == "dockerfile" and not _docker_gecerli(yeni_satir, hedef):
        ag.gerekce = "Dockerfile etiketi şablonlu; yalnız sürüm bölümü güvenle değişir"
        return ag
    return ag


def _docker_gecerli(satir: str, hedef: str) -> bool:
    m = _FROM_RE.match(satir)
    if not m:
        return False
    ad, _, etiket = m.group("imaj").partition(":")
    _cz, surum = imaj_coz(ad, etiket)
    return surum == hedef
