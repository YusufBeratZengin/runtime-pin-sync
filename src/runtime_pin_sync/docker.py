"""Dockerfile ve devcontainer.json okuma.

Dockerfile: çok aşamalı ``FROM`` satırları, aşma (stage) takma adları ve
``ARG`` ile parametrelenmiş etiketler çözülür; çözülemeyen ``${...}``
ifadeleri "dinamik" işaretlenir — hata değildir.
"""

from __future__ import annotations

import re

from .bulucular import pin
from .dil import m as _m
from .sabitleme import Sabitleme

__all__ = ["dockerfile", "devcontainer", "imaj_coz"]

_ARG_RE = re.compile(r"^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_FROM_RE = re.compile(
    r"^\s*FROM\s+(?:--platform=\S+\s+)?(?P<imaj>[^\s]+)(?:\s+AS\s+(?P<takma>\S+))?",
    re.IGNORECASE,
)
_ETIKET_SURUM_RE = re.compile(r"^v?(\d+(?:\.\d+)*)")

# imaj adı -> çalışma zamanı
_İMAJ_ESLEME = (
    ("node", "node"),
    ("python", "python"),
    ("golang", "go"),
    ("rust", "rust"),
    ("eclipse-temurin", "java"),
    ("temurin", "java"),
    ("openjdk", "java"),
    ("amazoncorretto", "java"),
    ("azul/zulu", "java"),
    ("ibm-semeru", "java"),
)

# Dağıtım/varyant sonekleri: `python:3.12-slim-bookworm` sürüm 3.12'dir.
_VARYANTLAR = frozenset({
    "alpine", "slim", "base", "full", "latest", "os", "default", "minimal",
    "bullseye", "bookworm", "trixie", "buster", "bullseye-slim",
    "bionic", "focal", "jammy", "noble", "oracular", "resolute", "sid",
    "stretch", "xenial", "jdk", "jre", "server-jre", "jdk-alpine",
    "jre-alpine", "nanoserver", "windowsservercore", "ltsc",
})
# Ön sürüm sözcükleri: `node:22-rc1` KARARLI 22'ye indirgenmez.
_ÖN_SÜRÜM_RE = re.compile(
    r"(?:rc|alpha|beta|pre|preview|canary|nightly|next|insider|snapshot|dev)"
    r"\d*$", re.IGNORECASE)


def imaj_ad_ve_etiket(referans: str) -> tuple[str, str]:
    """İmaj referansını (ad, etiket) ayırır — REGISTRY PORTU tuzağına düşmez.

    `registry.example:5000/node:22` tek `partition(":")` ile
    (`registry.example`, `5000/node:22`) olurdu; etiket yalnız SON YOL
    BİLEŞENİNDEKİ ikili noktadır.
    """
    son = referans.rsplit("/", 1)[-1]
    if ":" in son:
        i = referans.rfind(":")
        return referans[:i], referans[i + 1:]
    return referans, ""


def etiket_sınıflandır(etiket: str, *,
                       lang: str = "tr") -> tuple[str, str, str | None]:
    """(sürüm, durum, uyarı): durum "sürüm" | "etiketsiz" | "ön-sürüm" | "bilinmeyen".

    Ön sürümler (`22-rc1`) ve tanınmayan sonekler karşılaştırma DIŞIDIR ve
    açık uyarı üretir; bilinen dağıtım sonekleri (`3.12-slim-bookworm`)
    sürümü korur. Böylece ön sürüm sessizce kararlıya indirgenmez.
    """
    m = _ETIKET_SURUM_RE.match(etiket)
    if not m:
        return "", "etiketsiz", None
    sürüm = m.group(1)
    kalan = etiket[m.end():]
    if not kalan:
        return sürüm, "sürüm", None
    if kalan.startswith("+"):  # PEP 440 yapısal meta verisi: yok sayılır
        return sürüm, "sürüm", None
    if kalan[0] not in "-._":
        return sürüm, "bilinmeyen", _m(lang, "w_tag_unparsable", etiket=etiket)
    parçalar = [p.lower() for p in re.split(r"[-._]", kalan.lstrip("-._")) if p]
    if any(_ÖN_SÜRÜM_RE.fullmatch(p) for p in parçalar):
        return sürüm, "ön-sürüm", \
        _m(lang, "w_tag_prerelease", etiket=etiket)
    if all(p in _VARYANTLAR or p.isdigit() for p in parçalar):
        return sürüm, "sürüm", None
    return sürüm, "bilinmeyen", \
        _m(lang, "w_tag_suffix", etiket=etiket)


def imaj_coz(ad: str, etiket: str) -> tuple[str | None, str]:
    """(calisma_zamani, surum_belirteci). Etiket sürüm DEĞİLSE ya da
    karşılaştırma dışıysa (ön sürüm/bilinmeyen) sürüm '' döner."""
    cz, sürüm, _ = imaj_durumu(ad, etiket)
    return cz, sürüm


def imaj_durumu(ad: str, etiket: str, *,
                lang: str = "tr") -> tuple[str | None, str, str | None]:
    """(calisma_zamani, sürüm|'', uyarı|None) — dockerfile/devcontainer ortak."""
    kisa = ad.lower().rsplit("/", 1)[-1]
    for eslek, cz in _İMAJ_ESLEME:
        if kisa == eslek or kisa.endswith("-" + eslek) or kisa.startswith(eslek + "-"):
            sürüm, durum, uyari = etiket_sınıflandır(etiket, lang=lang)
            if durum != "sürüm":
                return cz, "", uyari  # "bilinmeyen" uyarılı, "ön-sürüm"/"etiketsiz" uyarısız ya da uyarılı
            return cz, sürüm, None
    return None, "", None


def dockerfile(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    arglar: dict[str, str] = {}
    asmalar: dict[str, str] = {}  # takma ad -> "imaj:etiket"
    sonuc: list[Sabitleme] = []
    for no, ham_satir in enumerate(icerik.splitlines(), start=1):
        m = _ARG_RE.match(ham_satir)
        if m:
            arglar[m.group(1)] = m.group(2).strip().strip('"').strip("'")
            continue
        if not re.match(r"^\s*FROM\s+", ham_satir, re.IGNORECASE):
            continue
        fm = _FROM_RE.match(ham_satir)
        if not fm:
            sonuc.append(Sabitleme("bilinmeyen", dosya, "dockerfile", ham_satir.strip(),
                                   uyari=_m(lang, "w_from_line"), satir=no))
            continue
        referans = fm.group("imaj")
        takma = (fm.group("takma") or "").lower()
        # değişkenleri ARG varsayılanlarıyla çöz
        if "${" in referans:
            cozulmus = _degisken_coz(referans, arglar)
            if cozulmus is None:
                sonuc.append(Sabitleme("bilinmeyen", dosya, "dockerfile", referans,
                                       dinamik=True, satir=no))
                continue
            referans = cozulmus
        # önceki aşmanın takma adı: "FROM builder" — yeni imaj değil, tekrar sayılmaz
        if referans.lower() in asmalar:
            continue
        ad, etiket = imaj_ad_ve_etiket(referans)
        cz, sürüm, uyari = imaj_durumu(ad, etiket, lang=lang)
        if cz is None:
            continue  # taban imaj (ubuntu, alpine...) takip edilmiyor
        if takma:
            asmalar[takma] = referans
        if sürüm:
            sonuc.append(pin(cz, dosya, "dockerfile", sürüm, satir=no,
                             lang=lang))
        else:
            sonuc.append(Sabitleme(cz, dosya, "dockerfile",
                                   etiket or _m(lang, "untagged"), dinamik=True,
                                   satir=no, uyari=uyari))
    return sonuc


def _degisken_coz(referans: str, arglar: dict[str, str]) -> str | None:
    def yenisle(m: re.Match[str]) -> str:
        return arglar.get(m.group(1), m.group(0))

    cozulmus = re.sub(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?", yenisle, referans)
    if "${" in cozulmus or "$" in cozulmus:
        return None
    return cozulmus


def devcontainer(dosya: str, icerik: str, *,
                 lang: str = "tr") -> list[Sabitleme]:
    """devcontainer.json: `image` alanı ve features sürümleri (JSONC toleranslı)."""
    try:
        veri = _jsonc_ayristir(icerik)
    except ValueError as exc:
        return [Sabitleme("bilinmeyen", dosya, "devcontainer", "",
                          uyari=_m(lang, "w_invalid_jsonc", hata=exc))]
    sonuc: list[Sabitleme] = []
    if not isinstance(veri, dict):
        return [Sabitleme("bilinmeyen", dosya, "devcontainer", "",
                          uyari=_m(lang, "w_json_not_object"))]
    imaj = veri.get("image")
    if isinstance(imaj, str) and imaj:
        ad, etiket = imaj_ad_ve_etiket(imaj)
        cz, sürüm, uyari = imaj_durumu(ad, etiket, lang=lang)
        if cz:
            if sürüm:
                sonuc.append(pin(cz, dosya, "devcontainer", sürüm,
                                 lang=lang))
            else:
                sonuc.append(Sabitleme(cz, dosya, "devcontainer",
                                       etiket or _m(lang, "untagged"),
                                       dinamik=True, satir=None, uyari=uyari))
    ozellikler = veri.get("features")
    if isinstance(ozellikler, dict):
        for ad, ayar in ozellikler.items():
            kisa = str(ad).lower().rsplit("/", 1)[-1].split(":")[0]
            cz = {"node": "node", "python": "python", "go": "go",
                  "rust": "rust", "java": "java"}.get(kisa)
            if cz is None:
                continue
            ozel_surum: str | None = None
            if isinstance(ayar, dict):
                v = ayar.get("version")
                ozel_surum = str(v) if v is not None else None
            elif isinstance(ayar, str):
                ozel_surum = ayar
            if ozel_surum is None or ozel_surum.lower() in (
                    "latest", "os-provided", "default"):
                sonuc.append(Sabitleme(cz, dosya, "devcontainer-feature",
                                       ozel_surum or _m(lang, "default_feature"),
                                       dinamik=True))
            else:
                sonuc.append(pin(cz, dosya, "devcontainer-feature", ozel_surum,
                                 lang=lang))
    return sonuc


def _jsonc_ayristir(metin: str) -> object:
    """Yorum ve sondan virgül tolere eden JSON okuma (devcontainer.json biçimi)."""
    import json

    temiz = re.sub(r"//[^\n\"]*$", "", metin, flags=re.MULTILINE)
    temiz = re.sub(r"/\*.*?\*/", "", temiz, flags=re.DOTALL)
    temiz = re.sub(r",(\s*[}\]])", r"\1", temiz)
    return json.loads(temiz)
