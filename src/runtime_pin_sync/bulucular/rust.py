"""Rust sürüm kaynakları: rust-toolchain ve rust-toolchain.toml."""

from __future__ import annotations

from . import pin, satir_bul, satirlar
from .. import minitoml
from ..sabitleme import Sabitleme

__all__ = ["kanal_dosyasi", "kanal_toml"]

_KANALLAR = {"stable", "beta", "nightly", "dev"}


def _kanal(ham: str) -> tuple[str, bool]:
    """'1.84.0' -> ('1.84.0', True); 'stable'/'1.84.0-x' gibi kanallar bilinmez."""
    t = ham.strip()
    if t.lower() in _KANALLAR:
        return t, False
    if "-" in t and t.split("-")[0][:1].isdigit():
        return t.split("-")[0], True  # "1.84.0-x86_64-unknown-linux-gnu"
    return t, True


def kanal_dosyasi(dosya: str, icerik: str) -> list[Sabitleme]:
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        deger, biliniyor = _kanal(t)
        if not biliniyor:
            return [Sabitleme("rust", dosya, "toolchain", t, dinamik=True, satir=i)]
        return [pin("rust", dosya, "toolchain", deger, satir=i)]
    return [Sabitleme("rust", dosya, "toolchain", "", uyari="okunamadı: boş dosya")]


def kanal_toml(dosya: str, icerik: str) -> list[Sabitleme]:
    try:
        veri = minitoml.oku(icerik.encode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return [Sabitleme("rust", dosya, "toolchain-toml", "",
                          uyari=f"okunamadı: geçersiz TOML ({exc})")]
    arac = veri.get("toolchain")
    if not isinstance(arac, dict) or "channel" not in arac:
        return []
    ham = arac["channel"]
    if not isinstance(ham, str):
        return [Sabitleme("rust", dosya, "toolchain-toml", str(ham),
                          uyari="okunamadı: channel bir metin değil")]
    deger, biliniyor = _kanal(ham)
    satir_no = satir_bul(satirlar(icerik), "channel")
    if not biliniyor:
        return [Sabitleme("rust", dosya, "toolchain-toml", ham, dinamik=True, satir=satir_no)]
    return [pin("rust", dosya, "toolchain-toml", deger, satir=satir_no)]
