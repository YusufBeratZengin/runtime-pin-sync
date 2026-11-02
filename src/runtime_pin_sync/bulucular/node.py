"""Node sürüm kaynakları: .nvmrc, .node-version, package.json engines.node."""

from __future__ import annotations

import json
import re

from ..sabitleme import Sabitleme
from . import pin, satirlar

__all__ = ["surum_dosyasi", "package_json", "lts_coz"]

# Node LTS takma adları. Kaynak: nodejs/Release schedule.json
# (https://raw.githubusercontent.com/nodejs/Release/main/schedule.json).
# Hydrogen 18'dir (16 DEĞİL — 16'nın adı Gallium'dur). Bilinmeyen takma ad
# tahmin edilmez; "dinamik, atlandı" işaretlenir. Tablo elle tutulur ve yeni
# LTS serisi çıktığında güncellenmelidir.
LTS_ADLARI = {
    "gallium": "16",
    "hydrogen": "18",
    "iron": "20",
    "jod": "22",
    "krypton": "24",
}
LTS_VAR = "*"


def lts_coz(ham: str) -> tuple[str, bool]:
    """`.nvmrc` belirtecini çözer: (değer, biliniyor mu).

    ``lts/iron`` -> ("20", True); ``lts/uzayli`` -> ("lts/uzayli", False).
    ``lts/*`` HAREKETLİ takma addır: tablonun en büyüğünü güncel gerçekmiş
    gibi döndürmeyiz — doğrulanamadığı için dinamik sayılır (False).
    """
    t = ham.strip().lower()
    if t.startswith("lts/"):
        ad = t[len("lts/"):]
        if ad == LTS_VAR:
            return ham.strip(), False  # güncelliği doğrulanamayan hareketli alias
        if ad in LTS_ADLARI:
            return LTS_ADLARI[ad], True
        return ham.strip(), False
    return ham.strip(), True


def surum_dosyasi(dosya: str, icerik: str, tur: str = "nvmrc") -> list[Sabitleme]:
    """.nvmrc / .node-version: ilk boş olmayan satır tek belirteçtir."""
    satir_list = satirlar(icerik)
    for i, s in enumerate(satir_list, start=1):
        t = s.strip()
        if not t or t.startswith("#"):
            continue
        deger, biliniyor = lts_coz(t)
        if not biliniyor:
            return [Sabitleme("node", dosya, tur, t, dinamik=True, satir=i)]
        return [pin("node", dosya, tur, deger, satir=i)]
    return [Sabitleme("node", dosya, tur, "", uyari="okunamadı: boş dosya")]


def package_json(dosya: str, icerik: str) -> list[Sabitleme]:
    try:
        veri = json.loads(icerik)
    except (ValueError, TypeError) as exc:
        return [Sabitleme("node", dosya, "engines", "",
                          uyari=f"okunamadı: geçersiz JSON ({exc})")]
    if not isinstance(veri, dict):
        return [Sabitleme("node", dosya, "engines", "",
                          uyari="okunamadı: JSON bir nesne değil")]
    engines = veri.get("engines")
    if not isinstance(engines, dict) or "node" not in engines:
        return []
    ham = engines["node"]
    if not isinstance(ham, str):
        return [Sabitleme("node", dosya, "engines", str(ham),
                          uyari="okunamadı: engines.node bir metin değil")]
    return [pin("node", dosya, "engines", ham,
                satir=_engines_node_satırı(icerik, ham))]


def _engines_node_satırı(metin: str, ham: str) -> int | None:
    """Ayrıştırılan engines.node DEĞERİNİN kesin satırı.

    Metindeki ilk "node" araması yanılır: `{"dependencies": {"node": "22"},
    "engines": {"node": "22"}}` içinde yanlış alanı bulur. `"engines"` nesne
    girişinden sonrasındaki ilk `node` anahtarına bakar; eşleşme belirsiz veya
    değer farklıysa konum YOK (sync bu durumda yazmaz).
    """
    m = re.search(r'"engines"\s*:\s*\{', metin)
    if not m:
        return None
    kuyruk = metin[m.end():]
    vm = re.search(r'"node"\s*:\s*"((?:[^"\\]|\\.)*)"', kuyruk)
    if vm is None or "}" in kuyruk[:vm.start()]:
        return None  # engines.node konumu çözülemedi
    if vm.group(1) != ham:
        return None  # kaçışlı/bayt farklı değeri: konumdan emin değiliz
    return metin[:m.end() + vm.start()].count("\n") + 1
