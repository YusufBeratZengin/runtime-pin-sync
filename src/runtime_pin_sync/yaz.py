"""Güvenli senkronizasyon: ``senkronla(yol, kaynak, kuru_calis)``.

Yalnızca *kesin hedefli*, satır-içi yeniden yazılabilir sabitlemeler değişir:
hedef dosyanın yalnız ilgili satırları, yalnız sürüm belirteci değişir (diff
testi bunu doğrular). Korunanlar:

- Aralıklar (``>=18``), ``^``/``~`` gibi operatörlü değerler, ızgaralar ve
  şablonlu Dockerfile etiketleri ASLA yazılmaz — "elle düzeltilmeli" listesi.
- Referans sabit bir sürüm değilse (``>=22``, ``22, 24``) hiçbir şey yazılmaz.
- Hedef dosya depo dışında kalıyorsa veya symlink'se yazılmaz (depodan çıkış
  kapalı); ham dosya bayt düzeyinde okunur, satır sonları AYNEN korunur.
  Yazım atomiktir: aynı dizindeki geçici dosya + ``os.replace`` — kesilen ya
  da hata veren yazım hedefi eski baytlarıyla bırakır, yarım dosya oluşmaz.
- Aynı değerin birden çok satırı varsa TÜM konumlar yazılır.
- Yazmadan sonra depo yeniden taranır; giderilemeyen çelişki başarı sayılmaz,
  "elle düzeltilmeli" listesinde exit 1'e katkı koyar.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .dil import m
from .docker import _FROM_RE, imaj_ad_ve_etiket, imaj_coz
from .karsilastir import celiski
from .sabitleme import Sabitleme
from .tara import kaynak_kontrol, tara, tarama_hatalari
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
    "sdkmanrc",
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
    *,
    lang: str = "tr",
) -> tuple[list[Degisiklik], list[Degisiklik]]:
    """(otomatik değişiklikler, elle düzeltilmesi gerekenler) döndürür.

    ``kuru_calis=True`` iken hiçbir dosyaya dokunulmaz.
    """
    kok = Path(yol)
    pimler = tara(kok, degiskenler, lang=lang)
    eksik = tarama_hatalari(pimler)
    if eksik:
        raise ValueError(m(lang, "scan_incomplete",
                           dizinler=", ".join(p.dosya for p in eksik)))
    norm = _norm_yol(kaynak)
    if not kaynak_kontrol(pimler, norm):
        raise ValueError(m(lang, "source_unusable", kaynak=kaynak))
    celiskiler = celiski(pimler, kaynak=norm)
    otomatik: list[Degisiklik] = []
    elle: list[Degisiklik] = []
    hedefler: dict[tuple[str, int], Degisiklik] = {}
    çakışan: set[tuple[str, int]] = set()
    for c in celiskiler:
        hedef_deger = c.referans_ham
        for p in c.dislananlar:
            if not sabit_belirtec_mi(hedef_deger):
                elle.append(Degisiklik(
                    p.dosya, p.satir or 0, p.ham, hedef_deger,
                    m(lang, "ref_not_fixed", deger=hedef_deger)))
                continue
            for sat in _konumlar(p):
                d = _yazma_denemesi(kok, p, hedef_deger, sat, lang)
                if d.gerekce:
                    elle.append(d)
                    continue
                anahtar = (d.dosya, d.satir)
                if anahtar in hedefler or anahtar in çakışan:
                    # aynı satıra iki+ hedef: güvenli değil. Çakışan satır
                    # KALICI olarak geçersizdir — üçüncü hedef "ilk iki elle
                    # listeye gitti, sıra bende" diye otomatik plana DÖNEMEZ.
                    çakışan.add(anahtar)
                    eski = hedefler.pop(anahtar, None)
                    if eski is not None:
                        eski.gerekce = m(lang, "same_line")
                        elle.append(eski)
                    elle.append(Degisiklik(d.dosya, d.satir, d.eski, d.yeni,
                                           m(lang, "same_line")))
                    continue
                hedefler[anahtar] = d
    if kuru_calis:
        return sorted(hedefler.values(), key=lambda d: (d.dosya, d.satir)), elle
    for (dosya, _satir), d in sorted(hedefler.items()):
        try:
            _uygula(kok, d, dosya, lang)
            otomatik.append(d)
        except (OSError, ValueError) as exc:
            elle.append(Degisiklik(d.dosya, d.satir, d.eski, d.yeni,
                                   m(lang, "apply_failed", hata=exc)))
    _kalan_çelişkileri_raporla(kok, norm, elle, degiskenler, lang)
    return otomatik, elle


def _konumlar(p: Sabitleme) -> tuple[int | None, ...]:
    """Yazılacak satır konumları: tekilleştirme konumları silmiş olamaz."""
    if p.tüm_satırlar:
        return p.tüm_satırlar
    return (p.satir,)


def _kalan_çelişkileri_raporla(
    kok: Path,
    norm: str,
    elle: list[Degisiklik],
    degiskenler: dict[str, str] | None,
    lang: str = "tr",
) -> None:
    """Yazmadan sonra yeniden tarar; giderilemeyen çelişki sessiz kalmaz.

    Başarıyla yazılmış pim yeniden taramada artık dışlanmaz; burada hâlâ
    dışlanıyorsa yazım hiç uygulanmamış demektir — asla "temiz" sayılmaz.
    """
    kayıtlı = {(d.dosya, d.satir) for d in elle}
    for c in celiski(tara(kok, degiskenler, lang=lang), kaynak=norm):
        for p in c.dislananlar:
            for sat in _konumlar(p):
                anahtar = (p.dosya, sat if sat is not None else 0)
                if anahtar in kayıtlı:
                    continue  # elle listesi zaten bunu bildiriyor
                kayıtlı.add(anahtar)
                elle.append(Degisiklik(
                    p.dosya, anahtar[1], p.ham, c.referans_ham,
                    m(lang, "conflict_after_sync")))


def _güvenli_hedef(kok: Path, dosya: str, lang: str = "tr") -> Path:
    """Depo sınırını denetler: symlink ve depo dışı yol YASAK, hedef döner."""
    tam = kok / dosya
    if tam.is_symlink():
        raise ValueError(m(lang, "symlink_target", dosya=dosya))
    kök = kok.resolve()
    çözüm = tam.resolve()
    if çözüm != kök and kök not in çözüm.parents:
        raise ValueError(m(lang, "outside_target", dosya=dosya, cozum=çözüm))
    return tam


def _uygula(kok: Path, d: Degisiklik, dosya: str, lang: str = "tr") -> None:
    tam = _güvenli_hedef(kok, dosya, lang)
    icerik = tam.read_bytes().decode("utf-8")  # CRLF/LF AYNEN kalır
    satirlar = icerik.splitlines(keepends=True)
    i = d.satir - 1
    if i >= len(satirlar):
        raise ValueError(m(lang, "line_out_of_range"))
    yeni_satir = _token_degistir(satirlar[i], d.eski, d.yeni)
    if yeni_satir is None:
        raise ValueError(m(lang, "token_not_standalone", ham=d.eski))
    satirlar[i] = yeni_satir
    _atomik_yaz(tam, "".join(satirlar).encode("utf-8"))


def _atomik_yaz(hedef: Path, veri: bytes) -> None:
    """Geçici dosyaya yazıp ``os.replace`` ile hedefin üzerine koyar.

    Doğrudan ``write_bytes`` hedefi kesip yeniden yazıyordu: süreç kesilirse
    ya da disk yazımı hata verirse dosya boş/kısmi kalabiliyordu. Burada veri
    ÖNCE aynı dizindeki geçici dosyaya yazılıp ``fsync`` edilir, sonra atomik
    yeniden adlandırmayla yerine konur — hata hâlinde hedef ESKİ baytlarıyla
    kalır. Geçici dosya her durumda silinir; mevcut izinler korunur.
    """
    try:
        izin: int | None = hedef.stat().st_mode
    except OSError:  # pragma: no cover - çağrı öncesi hedef okunmuştu
        izin = None
    fd, geçici = tempfile.mkstemp(
        prefix=f".{hedef.name}.", suffix=".tmp", dir=str(hedef.parent))
    try:
        with os.fdopen(fd, "wb") as dosya:
            dosya.write(veri)
            dosya.flush()
            os.fsync(dosya.fileno())
        if izin is not None:
            with contextlib.suppress(OSError):
                os.chmod(geçici, izin)
        os.replace(geçici, hedef)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(geçici)
        raise
    _dizin_senkronla(hedef.parent)


def _dizin_senkronla(dizin: Path) -> None:
    """POSIX'te yeniden adlandırmanın diske işlemesini garanti eder."""
    o_dizin = int(getattr(os, "O_DIRECTORY", 0))
    if not o_dizin:  # pragma: no cover - Windows'ta O_DIRECTORY yok
        return
    fd: int | None = None
    try:
        fd = os.open(str(dizin), os.O_RDONLY | o_dizin)
        os.fsync(fd)
    except OSError:  # pragma: no cover - platforma bağlı
        pass
    finally:
        if fd is not None:
            os.close(fd)


def _token_degistir(satir: str, eski: str, yeni: str) -> str | None:
    """Sayısal/versiyonel belirteci satırda tam BİR kez geçiyorsa değiştirir."""
    desen = re.compile(rf"(?<![\d.]){re.escape(eski)}(?![\d.])")
    eslesen = desen.findall(satir)
    if len(eslesen) != 1:
        return None
    return desen.sub(lambda _: yeni, satir)


def _yazma_denemesi(
    kok: Path, p: Sabitleme, hedef: str, satir: int | None, lang: str = "tr"
) -> Degisiklik:
    """p sabitlemesinin satır konumunu hedef değere çevirme planı."""
    ag = Degisiklik(p.dosya, satir or 0, p.ham, hedef)
    if p.tur not in YAZILABİLİR_TÜRLER:
        ag.gerekce = m(lang, "type_not_rewritable", tur=p.tur)
        return ag
    if satir is None:
        ag.gerekce = m(lang, "line_unknown")
        return ag
    if not sabit_belirtec_mi(p.ham):
        ag.gerekce = m(lang, "target_not_fixed", ham=p.ham)
        return ag
    try:
        tam = _güvenli_hedef(kok, p.dosya, lang)
        icerik = tam.read_bytes().decode("utf-8")
    except (OSError, ValueError) as exc:
        ag.gerekce = m(lang, "file_unreadable", hata=exc)
        return ag
    satirlar = icerik.splitlines()
    if satir > len(satirlar):
        ag.gerekce = m(lang, "line_out_of_range")
        return ag
    yeni_satir = _token_degistir(satirlar[satir - 1], p.ham, hedef)
    if yeni_satir is None:
        ag.gerekce = m(lang, "token_not_standalone", ham=p.ham)
        return ag
    if p.tur == "dockerfile" and not _docker_gecerli(yeni_satir, hedef):
        ag.gerekce = m(lang, "docker_template")
        return ag
    return ag


def _docker_gecerli(satir: str, hedef: str) -> bool:
    m = _FROM_RE.match(satir)
    if not m:
        return False
    ad, etiket = imaj_ad_ve_etiket(m.group("imaj"))
    _cz, surum = imaj_coz(ad, etiket)
    return surum == hedef
