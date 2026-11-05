"""Rust sürüm kaynakları: rust-toolchain ve rust-toolchain.toml."""

from __future__ import annotations

from .. import minitoml
from ..dil import m as _m
from ..sabitleme import Sabitleme
from . import pin, satir_bul, satirlar

__all__ = ["kanal_dosyasi", "kanal_toml"]

_KANALLAR = {"stable", "beta", "nightly", "dev"}

# Hedef üçlüsü (target triple) ilk alanları: "1.84.0-x86_64-unknown-linux-gnu"
# sürümdür, "1.85.0-rc1" ÖN SÜRÜMDÜR. Ayrım buna göre yapılır.
_MİMARİLİKLER = (
    "x86_64", "aarch64", "armv", "arm", "i386", "i586", "i686", "loongarch",
    "mips", "mips64", "powerpc", "powerpc64", "riscv", "s390x", "sparc64",
    "thumbv", "wasm32", "wasm64",
)


def _kanal(ham: str) -> tuple[str, str]:
    """(değer, durum): durum "sürüm" | "kanal" | "ön-sürüm".

    '1.84.0' -> ('1.84.0', 'sürüm'); 'stable' -> kanal;
    '1.84.0-x86_64-unknown-linux-gnu' -> hedef üçlüsü atılır, sürüm kalır;
    '1.85.0-rc1' -> ÖN SÜRÜM: kararlıya indirgenmez, karşılaştırılmaz.
    """
    t = ham.strip()
    if t.lower() in _KANALLAR:
        return t, "kanal"
    if "-" in t and t.split("-", 1)[0][:1].isdigit():
        taban, sonek = t.split("-", 1)
        ilk = sonek.split("-")[0].lower()
        if ilk.startswith(_MİMARİLİKLER):
            return taban, "sürüm"
        return t, "ön-sürüm"
    return t, "sürüm"


def _çöz(dosya: str, tur: str, ham: str, satir: int | None, *,
         lang: str = "tr") -> list[Sabitleme]:
    deger, durum = _kanal(ham)
    if durum == "kanal":
        return [Sabitleme("rust", dosya, tur, ham, dinamik=True, satir=satir)]
    if durum == "ön-sürüm":
        return [Sabitleme("rust", dosya, tur, ham, dinamik=True, satir=satir,
                          uyari=_m(lang, "w_prerelease", ham=ham))]
    return [pin("rust", dosya, tur, deger, satir=satir, lang=lang)]


def kanal_dosyasi(dosya: str, icerik: str, *,
                   lang: str = "tr") -> list[Sabitleme]:
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        return _çöz(dosya, "toolchain", t, i, lang=lang)
    return [Sabitleme("rust", dosya, "toolchain", "",
                      uyari=_m(lang, "w_empty_file"))]


def kanal_toml(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    try:
        veri = minitoml.oku(icerik.encode("utf-8"), lang=lang)
    except (ValueError, UnicodeDecodeError) as exc:
        return [Sabitleme("rust", dosya, "toolchain-toml", "",
                          uyari=_m(lang, "w_invalid_toml", hata=exc))]
    arac = veri.get("toolchain")
    if not isinstance(arac, dict) or "channel" not in arac:
        return []
    ham = arac["channel"]
    if not isinstance(ham, str):
        return [Sabitleme("rust", dosya, "toolchain-toml", str(ham),
                          uyari=_m(lang, "w_channel_not_text"))]
    return _çöz(dosya, "toolchain-toml", ham,
                satir_bul(satirlar(icerik), "channel"), lang=lang)
