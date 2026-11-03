"""Depo taraması: ``tara(yol) -> list[Sabitleme]``.

Bilinen sürüm kaynak dosyalarını bulur, ilgili bulucuya besler. Okuma ya da
çözümleme hatası asla dışarı fırlamaz — o dosyadan "okunamadı" uyarılı bir
Sabitleme çıkar (kabul ölçütü 4).
"""

from __future__ import annotations

import os
from pathlib import Path

from .bulucular import araclar, go, java, node, python, rust
from .ci import is_aksi
from .docker import devcontainer, dockerfile
from .sabitleme import Sabitleme

__all__ = ["tara", "ATLANAN_DİZİNLER"]

ATLANAN_DİZİNLER = frozenset({
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    "target", "site-packages", ".terraform", "vendor", ".next", ".nuxt",
})

# zaten taranan tek sürümlük dosya adları (ci version-file yinelenmesin)
BİLİNEN_DOSYALAR = frozenset({
    ".nvmrc", ".node-version", "package.json", ".python-version",
    "pyproject.toml", "go.mod", ".go-version", "rust-toolchain",
    "rust-toolchain.toml", ".java-version", "pom.xml", ".tool-versions",
    "mise.toml", ".mise.toml", "devcontainer.json",
})


def tara(yol: str | Path, degiskenler: dict[str, str] | None = None) -> list[Sabitleme]:
    """Depo kökünü tara; bulunan tüm sabitlemeleri sıralı döndür.

    Atlanan dizinlere `os.walk` ile BUDANARAK girilmez (büyük `node_modules`
    ağaçlarında tarama maliyeti düşer). Aynı dosya/tür/değer yinelenirse tek
    sabitleme tutulur ama DEĞİŞTİRİLECEK TÜM SATIR KONUMLARI korunur.
    """
    kok = Path(yol)
    if not kok.is_dir():
        raise ValueError(f"depo klasörü değil: {yol}")
    sonuc: dict[tuple[str, str, str, str], Sabitleme] = {}
    for yürütülen, dizinler, dosyalar in os.walk(kok):
        dizinler[:] = sorted(d for d in dizinler if d not in ATLANAN_DİZİNLER)
        for ad in sorted(dosyalar):
            alt = Path(yürütülen) / ad
            parca_yol = alt.relative_to(kok).as_posix()
            if alt.name in ATLANAN_DİZİNLER:
                continue
            if not alt.is_file():
                continue
            for p in _dosya_işle(kok, parca_yol, alt, degiskenler):
                anahtar = (p.calisma_zamani, p.dosya, p.tur, p.ham)
                onceki = sonuc.get(anahtar)
                if onceki is None:
                    sonuc[anahtar] = p
                elif p.satir is not None:
                    # tekilleştirme konumları SİLMEMELİ: hepsi yazılacak
                    tüm = onceki.tüm_satırlar or (
                        (onceki.satir,) if onceki.satir else ())
                    onceki.tüm_satırlar = tuple(dict.fromkeys(tüm + (p.satir,)))
    return sorted(sonuc.values(), key=lambda p: (p.calisma_zamani, p.dosya,
                                                 p.satir or 0, p.tur))


def _dosya_işle(
    kok: Path, göreli: str, yol: Path, degiskenler: dict[str, str] | None
) -> list[Sabitleme]:
    ad = yol.name
    # DEPONUN KENDİSİ tarama sınırıdır: depo içinden çıkan bir symlink'in
    # hedefi depo içeriği SAYILMAZ (okumadan önce denetlenir; dışarıdaki
    # içerik hiçbir uyarıya/aleve taşınmaz).
    if yol.is_symlink():
        try:
            çözüm = yol.resolve()
            kök_çözüm = kok.resolve()
        except OSError as exc:
            return [Sabitleme("bilinmeyen", göreli, "dosya", "",
                              uyari=f"okunamadı: {exc}")]
        if çözüm != kök_çözüm and kök_çözüm not in çözüm.parents:
            return [Sabitleme("bilinmeyen", göreli, "dosya", "",
                              uyari="okunamadı: bağlantı depo dışına işaret "
                                    "ediyor (okuma reddedildi)")]
    try:
        if ad in (".nvmrc", ".node-version"):
            return node.surum_dosyasi(göreli, _metin(yol),
                                      "nvmrc" if ad == ".nvmrc" else "node-version")
        if ad == "package.json":
            return node.package_json(göreli, _metin(yol))
        if ad == ".python-version":
            return python.surum_dosyasi(göreli, _metin(yol))
        if ad == "pyproject.toml":
            return python.pyproject(göreli, _metin(yol))
        if ad == "go.mod":
            return go.gomod(göreli, _metin(yol))
        if ad == ".go-version":
            return go.surum_dosyasi(göreli, _metin(yol))
        if ad == "rust-toolchain":
            return rust.kanal_dosyasi(göreli, _metin(yol))
        if ad == "rust-toolchain.toml":
            return rust.kanal_toml(göreli, _metin(yol))
        if ad == ".java-version":
            return java.surum_dosyasi(göreli, _metin(yol))
        if ad == "pom.xml":
            return java.pom(göreli, _metin(yol))
        if ad == ".tool-versions":
            return araclar.tool_versions(göreli, _metin(yol))
        if ad in ("mise.toml", ".mise.toml"):
            return araclar.mise(göreli, _metin(yol))
        if ad == "Dockerfile" or ad.startswith("Dockerfile.") or ad.endswith(".dockerfile"):
            return dockerfile(göreli, _metin(yol))
        if ad == "devcontainer.json":
            return devcontainer(göreli, _metin(yol))
        if ad.endswith((".yml", ".yaml")) and "/.github/workflows/" in f"/{göreli}":
            return is_aksi(göreli, _metin(yol), degiskenler, str(kok))
    except OSError as exc:
        return [Sabitleme("bilinmeyen", göreli, "dosya", "",
                          uyari=f"okunamadı: {exc}")]
    return []


def _metin(yol: Path) -> str:
    return yol.read_text(encoding="utf-8", errors="replace")


def kaynak_kontrol(pimler: list[Sabitleme], kaynak: str) -> bool:
    """--kaynak ile verilen yol depoda gerçekten bir sabitleme üretti mi?"""
    norm = os.path.normpath(kaynak).replace(os.sep, "/")
    return any(p.dosya == norm or p.dosya == kaynak for p in pimler)
