"""Python sürüm kaynakları: .python-version, pyproject.toml requires-python."""

from __future__ import annotations

from .. import minitoml
from ..dil import m as _m
from ..sabitleme import Sabitleme
from . import grid_pin, pin, satir_bul, satirlar

__all__ = ["surum_dosyasi", "pyproject"]


def surum_dosyasi(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    """pyenv çoklu sürümleri tek birleşimdir; satır satır yeniden yazılmaz."""
    girdiler = [(i, s.strip()) for i, s in enumerate(satirlar(icerik), start=1)
                if s.strip() and not s.strip().startswith("#")]
    if not girdiler:
        return [Sabitleme("python", dosya, "python-version", "",
                          uyari=_m(lang, "w_empty_file"))]
    if len(girdiler) == 1:
        i, t = girdiler[0]
        return [pin("python", dosya, "python-version", t, satir=i, lang=lang)]
    degerler = [t for _, t in girdiler]
    pimler = [pin("python", dosya, "python-version", t, satir=i, lang=lang)
              for i, t in girdiler]
    if any(not p.kullanilabilir for p in pimler):
        # Kısmen çözülen birleşim gerçek kümeyi eksik gösterir.
        return [Sabitleme("python", dosya, "python-version", ", ".join(degerler),
                          uyari=_m(lang, "w_multiline_unparsable"))]
    return [grid_pin("python", dosya, "python-version", degerler)]


def pyproject(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    """[project].requires-python (PEP 440 aralığı)."""
    try:
        veri = minitoml.oku(icerik.encode("utf-8"), lang=lang)
    except (ValueError, UnicodeDecodeError) as exc:
        return [Sabitleme("python", dosya, "requires-python", "",
                          uyari=_m(lang, "w_invalid_toml", hata=exc))]
    proje = veri.get("project")
    if not isinstance(proje, dict) or "requires-python" not in proje:
        return []
    ham = proje["requires-python"]
    if not isinstance(ham, str):
        return [Sabitleme("python", dosya, "requires-python", str(ham),
                          uyari=_m(lang, "w_requires_python_not_text"))]
    satir_no = satir_bul(satirlar(icerik), "requires-python")
    return [pin("python", dosya, "requires-python", ham, satir=satir_no,
                lang=lang)]
