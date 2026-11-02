"""Dockerfile ve devcontainer.json okuma.

Dockerfile: çok aşamalı ``FROM`` satırları, aşma (stage) takma adları ve
``ARG`` ile parametrelenmiş etiketler çözülür; çözülemeyen ``${...}``
ifadeleri "dinamik" işaretlenir — hata değildir.
"""

from __future__ import annotations

import re

from .bulucular import pin
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


def imaj_coz(ad: str, etiket: str) -> tuple[str | None, str]:
    """(calisma_zamani, surum_belirteci). Etiket sürüm değilse '' döner."""
    kisa = ad.lower().rsplit("/", 1)[-1]
    for eslek, cz in _İMAJ_ESLEME:
        if kisa == eslek or kisa.endswith("-" + eslek) or kisa.startswith(eslek + "-"):
            m = _ETIKET_SURUM_RE.match(etiket)
            return cz, (m.group(1) if m else "")
    return None, ""


def dockerfile(dosya: str, icerik: str) -> list[Sabitleme]:
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
                                   uyari="okunamadı: FROM satırı çözümlenemedi", satir=no))
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
        ad, _, etiket = referans.partition(":")
        cz, surum = imaj_coz(ad, etiket)
        if cz is None:
            continue  # taban imaj (ubuntu, alpine...) takip edilmiyor
        if takma:
            asmalar[takma] = referans
        if not surum:
            sonuc.append(Sabitleme(cz, dosya, "dockerfile", etiket or "(etiketsiz)",
                                   dinamik=True, satir=no))
            continue
        sonuc.append(pin(cz, dosya, "dockerfile", surum, satir=no))
    return sonuc


def _degisken_coz(referans: str, arglar: dict[str, str]) -> str | None:
    def yenisle(m: re.Match[str]) -> str:
        return arglar.get(m.group(1), m.group(0))

    cozulmus = re.sub(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?", yenisle, referans)
    if "${" in cozulmus or "$" in cozulmus:
        return None
    return cozulmus


def devcontainer(dosya: str, icerik: str) -> list[Sabitleme]:
    """devcontainer.json: `image` alanı ve features sürümleri (JSONC toleranslı)."""
    try:
        veri = _jsonc_ayristir(icerik)
    except ValueError as exc:
        return [Sabitleme("bilinmeyen", dosya, "devcontainer", "",
                          uyari=f"okunamadı: geçersiz JSONC ({exc})")]
    sonuc: list[Sabitleme] = []
    if not isinstance(veri, dict):
        return [Sabitleme("bilinmeyen", dosya, "devcontainer", "",
                          uyari="okunamadı: JSON bir nesne değil")]
    imaj = veri.get("image")
    if isinstance(imaj, str) and imaj:
        ad, _, etiket = imaj.partition(":")
        cz, surum = imaj_coz(ad, etiket)
        if cz:
            if surum:
                sonuc.append(pin(cz, dosya, "devcontainer", surum))
            else:
                sonuc.append(Sabitleme(cz, dosya, "devcontainer", etiket or "(etiketsiz)",
                                       dinamik=True, satir=None))
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
                                       ozel_surum or "(varsayılan)", dinamik=True))
            else:
                sonuc.append(pin(cz, dosya, "devcontainer-feature", ozel_surum))
    return sonuc


def _jsonc_ayristir(metin: str) -> object:
    """Yorum ve sondan virgül tolere eden JSON okuma (devcontainer.json biçimi)."""
    import json

    temiz = re.sub(r"//[^\n\"]*$", "", metin, flags=re.MULTILINE)
    temiz = re.sub(r"/\*.*?\*/", "", temiz, flags=re.DOTALL)
    temiz = re.sub(r",(\s*[}\]])", r"\1", temiz)
    return json.loads(temiz)
