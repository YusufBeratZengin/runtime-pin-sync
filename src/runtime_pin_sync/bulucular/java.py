"""Java sürüm kaynakları: .java-version, .sdkmanrc ve pom.xml."""

from __future__ import annotations

import re

from ..dil import m as _m
from ..sabitleme import Sabitleme
from . import pin, satirlar

__all__ = ["surum_dosyasi", "sdkmanrc", "pom"]

# pom.xml'de aranan anahtarlar (öncelik sırasıyla)
_POM_ANAHTARLAR = (
    "maven.compiler.release",
    "maven.compiler.source",
    "java.version",
    "release",
)


def surum_dosyasi(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        return [pin("java", dosya, "java-version", t, satir=i, lang=lang)]
    return [Sabitleme("java", dosya, "java-version", "",
                      uyari=_m(lang, "w_empty_file"))]


#: `.sdkmanrc` satırı: ``java=17.0.2+8`` / ``java=21.0.1-tem``
_SDKMAN_SATIR = re.compile(r"^\s*([A-Za-z][\w.-]*)\s*=\s*(.*?)\s*$")
#: sürüm gövdesi + isteğe bağlı yapı bilgisi (+8) + isteğe bağlı dağıtım eki
#: (-tem, -zulu ...). Dağıtım eki SÜRÜMÜ değiştirmez; yazarken korunur.
_SDKMAN_SURUM = re.compile(r"^v?(\d+(?:\.\d+)*)(\+\d+)?(?:-[A-Za-z][\w.]*)?$")


def sdkmanrc(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
    """SDKMAN! `.sdkmanrc` içindeki ``java=`` satırını okur.

    Biçim ``anahtar=değer`` satırlarıdır; yalnız ``java`` anahtarı Java
    çalışma zamanına karşılık gelir, diğer araçlar (maven, gradle) kapsam
    dışıdır. ``+8`` yapı bilgisi sürümle birlikte tutulur, ``-tem`` gibi
    dağıtım eki sürüm karşılaştırmasına girmez ve yeniden yazarken korunur.
    Sürüm olmayan değer (``latest``) ve boş değer hata fırlatmaz: sırasıyla
    dinamik/uyarılı Sabitleme üretir.
    """
    for i, s in enumerate(satirlar(icerik), start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        m = _SDKMAN_SATIR.match(t)
        if m is None or m.group(1).lower() != "java":
            continue
        deger = m.group(2)
        if not deger:
            return [Sabitleme("java", dosya, "sdkmanrc", "",
                              uyari=_m(lang, "w_empty_token"))]
        sm = _SDKMAN_SURUM.match(deger)
        if sm is None:
            return [Sabitleme("java", dosya, "sdkmanrc", deger,
                              dinamik=True, satir=i)]
        ham = sm.group(1) + (sm.group(2) or "")
        return [pin("java", dosya, "sdkmanrc", ham, satir=i, lang=lang)]
    return []


def pom(dosya: str, icerik: str, *, lang: str = "tr") -> list[Sabitleme]:
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
                    sonuc.append(pin("java", dosya, "pom", ham, satir=i,
                                     lang=lang))
                break  # her anahtarın yalnız ilk geçişi
    return sonuc
