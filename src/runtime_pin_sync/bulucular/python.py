"""Python sürüm kaynakları: .python-version, pyproject.toml requires-python."""

from __future__ import annotations

from .. import minitoml
from ..sabitleme import Sabitleme
from . import pin, satir_bul, satirlar

__all__ = ["surum_dosyasi", "pyproject"]


def surum_dosyasi(dosya: str, icerik: str) -> list[Sabitleme]:
    """.python-version: pyenv tek satır kullanır; birden çok satıra da izin verilir."""
    sonuc: list[Sabitleme] = []
    satir_list = satirlar(icerik)
    for i, s in enumerate(satir_list, start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        sonuc.append(pin("python", dosya, "python-version", t, satir=i))
    if not sonuc:
        sonuc.append(Sabitleme("python", dosya, "python-version", "",
                               uyari="okunamadı: boş dosya"))
    return sonuc


def pyproject(dosya: str, icerik: str) -> list[Sabitleme]:
    """[project].requires-python (PEP 440 aralığı)."""
    try:
        veri = minitoml.oku(icerik.encode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return [Sabitleme("python", dosya, "requires-python", "",
                          uyari=f"okunamadı: geçersiz TOML ({exc})")]
    proje = veri.get("project")
    if not isinstance(proje, dict) or "requires-python" not in proje:
        return []
    ham = proje["requires-python"]
    if not isinstance(ham, str):
        return [Sabitleme("python", dosya, "requires-python", str(ham),
                          uyari="okunamadı: requires-python bir metin değil")]
    satir_no = satir_bul(satirlar(icerik), "requires-python")
    return [pin("python", dosya, "requires-python", ham, satir=satir_no)]
