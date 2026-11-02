"""TOML okuma: ``tomllib`` varsa o, yoksa (Python 3.10) mini bir yedek.

Yedek ayrıştırıcı yalnız ``[tablo]`` başlıkları ve ``anahtar = "metin"``
satırlarını tanır — projemizin okuduğu ``mise.toml``, ``rust-toolchain.toml``
ve ``pyproject.toml`` alanları için yeterli. Biçim bozuksa ``ValueError``.
"""

from __future__ import annotations

import re
from typing import Any

try:  # Python 3.11+
    import tomllib as _tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - 3.10 yolunda test edilir
    _tomllib = None

__all__ = ["oku", "mini_ayristir"]

_MINI_SATIR = re.compile(r'^([A-Za-z0-9_.\-"]+)\s*=\s*(.+)$')


def oku(veri: bytes) -> dict[str, Any]:
    """TOML baytlarını sözlüğe çevirir; bozuksa ValueError fırlatır."""
    if _tomllib is not None:
        veri_sözlük: dict[str, Any] = _tomllib.loads(veri.decode("utf-8"))
        return veri_sözlük
    return mini_ayristir(veri.decode("utf-8"))


def mini_ayristir(metin: str) -> dict[str, Any]:
    sonuc: dict[str, Any] = {}
    aktif: dict[str, Any] = sonuc
    for no, ham in enumerate(metin.splitlines(), start=1):
        govde = _yorum_temizle(ham.strip())
        if not govde:
            continue
        if govde.startswith("[") and govde.endswith("]"):
            ad = govde[1:-1].strip().strip('"')
            if "[" in ad or "]" in ad:
                raise ValueError(f"mini TOML: desteklenmeyen tablo başlığı (satır {no})")
            hedef: Any = sonuc
            for parca in ad.split("."):
                hedef = hedef.setdefault(parca, {})
                if not isinstance(hedef, dict):
                    raise ValueError(f"mini TOML: çakışan anahtar (satır {no})")
            aktif = hedef
            continue
        m = _MINI_SATIR.match(govde)
        if not m:
            raise ValueError(f"mini TOML: çözülemeyen satır {no}: {govde!r}")
        anahtar = m.group(1).strip('"')
        aktif[anahtar] = _deger(m.group(2).strip())
    return sonuc


def _yorum_temizle(govde: str) -> str:
    out: list[str] = []
    tirnak = ""
    for idx, ch in enumerate(govde):
        if tirnak:
            out.append(ch)
            if ch == tirnak:
                tirnak = ""
        elif ch in "\"'":
            tirnak = ch
            out.append(ch)
        elif ch == "#" and (idx == 0 or govde[idx - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def _deger(ham: str) -> Any:
    if len(ham) >= 2 and ham[0] == ham[-1] and ham[0] in "\"'":
        return ham[1:-1]
    if ham.startswith("[") and ham.endswith("]"):
        icerik = ham[1:-1].strip()
        if not icerik:
            return []
        return [_deger(p.strip()) for p in icerik.split(",")]
    if ham in ("true", "false"):
        return ham == "true"
    try:
        return int(ham)
    except ValueError:
        return ham
