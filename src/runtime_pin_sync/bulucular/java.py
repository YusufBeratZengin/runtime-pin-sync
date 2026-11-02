"""Java sürüm kaynakları: .java-version ve pom.xml derleyici özellikleri."""

from __future__ import annotations

import re

from . import pin, satirlar
from ..sabitleme import Sabitleme

__all__ = ["surum_dosyasi", "pom"]

# pom.xml'de aranan anahtarlar (öncelik sırasıyla)
_POM_ANAHTARLAR = (
    "maven.compiler.release",
    "maven.compiler.source",
    "java.version",
    "release",
)


def surum_dosyasi(dosya: str, icerik: str) -> list[Sabitleme]:
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        return [pin("java", dosya, "java-version", t, satir=i)]
    return [Sabitleme("java", dosya, "java-version", "", uyari="okunamadı: boş dosya")]


def pom(dosya: str, icerik: str) -> list[Sabitleme]:
    satir_list = satirlar(icerik)
    sonuc: list[Sabitleme] = []
    for anahtar in _POM_ANAHTARLAR:
        desen = re.compile(rf"<{re.escape(anahtar)}>([^<]+)</{re.escape(anahtar)}>")
        for i, s in enumerate(satir_list, start=1):
            m = desen.search(s)
            if m:
                ham = m.group(1).strip()
                if "${" in ham:  # <java.version>${java.home}</...> gibi
                    sonuc.append(Sabitleme("java", dosya, "pom", ham, dinamik=True, satir=i))
                else:
                    sonuc.append(pin("java", dosya, "pom", ham, satir=i))
                break  # her anahtarın yalnız ilk geçişi
    return sonuc
