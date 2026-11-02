"""Go sürüm kaynakları: go.mod ``go``/``toolchain`` doğrudanları, .go-version."""

from __future__ import annotations

import re

from . import pin, satirlar
from ..sabitleme import Sabitleme

__all__ = ["gomod", "surum_dosyasi"]

_GO_RE = re.compile(r"^go\s+(\S+)")
_TOOLCHAIN_RE = re.compile(r"^toolchain\s+(\S+)")


def gomod(dosya: str, icerik: str) -> list[Sabitleme]:
    sonuc: list[Sabitleme] = []
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        m = _GO_RE.match(t)
        if m:
            sonuc.append(pin("go", dosya, "gomod", m.group(1), satir=i))
            continue
        m = _TOOLCHAIN_RE.match(t)
        if m:
            sonuc.append(pin("go", dosya, "gomod-toolchain", m.group(1), satir=i))
    if not sonuc:
        sonuc.append(Sabitleme("go", dosya, "gomod", "",
                               uyari="okunamadı: go.mod içinde 'go' satırı yok"))
    return sonuc


def surum_dosyasi(dosya: str, icerik: str) -> list[Sabitleme]:
    satir_list = satirlar(icerik)
    for i, s in enumerate(satir_list, start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        return [pin("go", dosya, "go-version", t, satir=i)]
    return [Sabitleme("go", dosya, "go-version", "", uyari="okunamadı: boş dosya")]
