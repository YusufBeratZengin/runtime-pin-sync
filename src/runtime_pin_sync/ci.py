"""GitHub Actions iş akışlarını okuma: ``setup-*`` adımları ve sürüm matrisleri.

- ``actions/setup-node|python|go|java`` ve ``dtolnay/rust-toolchain`` adımları
- ``*-version`` ve ``*-version-file`` girdileri
- ``strategy.matrix`` listeleri (test ızgarası BirLEŞİM olarak tek sabitleme olur)
- ``${{ matrix.X }}`` şablonları iş matrisinden çözülür; çözülemezse
  "dinamik, atlandı" — asla hata değil.
"""

from __future__ import annotations

import os
import re
from typing import Any

from . import miniyaml
from .bulucular import go, grid_pin, java, node, pin, python, satirlar
from .sabitleme import Sabitleme

__all__ = ["is_aksi", "MATRIX_ANAHTARLARI"]

# eylem => (sürüm girdisi, sürüm-dosyası girdisi ya da None, çalışma zamanı)
_ADLIMLAR: tuple[tuple[str, str, str | None, str], ...] = (
    ("setup-node@", "node-version", "node-version-file", "node"),
    ("setup-python@", "python-version", "python-version-file", "python"),
    ("setup-go@", "go-version", None, "go"),
    ("setup-java@", "java-version", None, "java"),
    ("rust-toolchain@", "toolchain", None, "rust"),
)

# Tara'nın zaten tek sürümlük dosya olarak okuduğu adlar: version-file bunlardan
# birini gösteriyorsa içerik YİNE okunmaz (çift kayıt olmaz).
TARANAN_SÜRÜM_DOSYALARI = frozenset({
    ".nvmrc", ".node-version", ".python-version", ".go-version",
    ".java-version",
})

MATRIX_ANAHTARLARI = {
    "node-version": "node", "node_version": "node", "node": "node",
    "python-version": "python", "python_version": "python", "python": "python",
    "go-version": "go", "go_version": "go", "go": "go",
    "java-version": "java", "java_version": "java", "java": "java",
    "rust-version": "rust", "toolchain": "rust",
}

_SABLON_RE = re.compile(r"\$\{\{\s*(?:matrix|env|inputs|var)\.([A-Za-z0-9_\-]+)\s*\}\}")


def is_aksi(
    dosya: str,
    icerik: str,
    degiskenler: dict[str, str] | None = None,
    depo_koku: str = "",
) -> list[Sabitleme]:
    """GitHub Actions iş akışını (YAML) ayrıştırıp sürüm sabitlemelerini çıkarır.

    Ayrıştırma, sıfır bağımlılık ilkesi gereği ``miniyaml.ayristir`` ile yapılır.
    Desteklenen alt küme:
      - İç içe eşlemeler (ör. ``jobs.<id>.steps``, ``strategy.matrix``)
      - Blok diziler (``- uses: ...``) ve akış dizileri (``[20, 22]``)
      - Düz, tek tırnaklı ve çift tırnaklı skalerler, blok metinleri (``|``, ``>``)
      - Yorumlar (``#``)

    Desteklenmeyen yapılar (YAML çıpaları/takma adları ``&``/``*``, birleştirme
    anahtarları ``<<``, özel etiketler ``!``) karşılaşıldığında çökmek yerine
    güvenli ve açık bir ``okunamadı: desteklenmeyen YAML (...)`` uyarısı üretir.
    Genel amaçlı PyYAML veya ruamel.yaml'a kıyasla sıfır harici bağımlılık sağlar,
    C-derleme gerektirmez ve CI kurulum süresini sıfıra indirir.
    """
    degiskenler = degiskenler or {}
    try:
        veri = miniyaml.ayristir(icerik)
    except miniyaml.MiniYamlError as exc:
        return [Sabitleme("bilinmeyen", dosya, "ci", "",
                          uyari=f"okunamadı: desteklenmeyen YAML ({exc})")]
    if not isinstance(veri, dict):
        return [Sabitleme("bilinmeyen", dosya, "ci", "",
                          uyari="okunamadı: iş akışı bir eşleme değil")]
    isler = veri.get("jobs")
    if not isinstance(isler, dict):
        return []
    satir_list = satirlar(icerik)
    # her ADIM için ham metindeki (başlangıç, bitiş) satır aralığı: girdi
    # konumları adım bloğunun DIŞINA (strategy.matrix satırlarına) taşamaz
    pencereler = _adım_pencereleri(satir_list)
    hizma = _pencereler_hizmalı(isler, pencereler)
    sonuc: list[Sabitleme] = []
    imleç = [0]
    for ise_adi, islem in isler.items():
        if not isinstance(islem, dict):
            continue
        matris = _matris(islem)
        tuketlenen: set[str] = set()
        sonuc.extend(_adimlar(dosya, islem, matris, tuketlenen, satir_list,
                              degiskenler, depo_koku, str(ise_adi),
                              pencereler if hizma else None, imleç))
        for anahtar, deger in matris.items():
            if anahtar in tuketlenen or not isinstance(deger, list):
                continue
            cz = MATRIX_ANAHTARLARI.get(str(anahtar).lower())
            if cz is None:
                continue
            sonuc.extend(_matris_sabitlemeleri(dosya, cz, str(anahtar), deger))
    return sonuc


def _adım_sayısı(isler: dict[str, Any]) -> int:
    toplam = 0
    for islem in isler.values():
        if isinstance(islem, dict) and isinstance(islem.get("steps"), list):
            toplam += len(islem["steps"])
    return toplam


def _pencereler_hizmalı(isler: dict[str, Any],
                        pencereler: list[tuple[int, int]]) -> bool:
    """Ham tarayıcının adım aralıkları ayrıştırılmış adımlarla birebir mi?

    Eşleşmezse (akış biçimi `steps: [...]`, bozuk girinti...) hiçbir adımı
    YANLIŞ satıra bağlamaktansa konumsuz bırakırız — sync konumsuz hedefi
    otomatik yazmaz.
    """
    return len(pencereler) == _adım_sayısı(isler)


def _adım_pencereleri(satir_list: list[str]) -> list[tuple[int, int]]:
    """Her blok-dizi ADIMının ham metindeki 1-tabanlı (başlangıç, bitiş)
    satır aralığı — belge sırasıyla.

    `steps:` anahtarının altındaki `- ` öğeleri girintiyle sınırlanır;
    böylece bir adımın girdi satırı arama alanı, aynı dosyadaki
    `strategy.matrix` satırlarını içerMEZ.
    """
    pencereler: list[tuple[int, int]] = []
    n = len(satir_list)
    i = 0
    while i < n:
        s = satir_list[i]
        m = re.match(r"^([ \t]*)steps[ \t]*:[ \t]*(\S.*)?$", s)
        if m and not s.lstrip().startswith("#"):
            adım_kir = len(m.group(1))
            kalabilir = m.group(2)
            if kalabilir and kalabilir.startswith("["):
                # akış biçimi: steps: [run: x, ...] — her öğe tek satır
                from .miniyaml import _virgulle_ayir

                for _ in _virgulle_ayir(kalabilir[1:].rsplit("]", 1)[0]):
                    pencereler.append((i + 1, i + 1))
                i += 1
                continue
            j = i + 1
            while j < n:
                t = satir_list[j]
                if not t.strip() or t.lstrip().startswith("#"):
                    j += 1
                    continue
                kir = len(t) - len(t.lstrip())
                if not t.lstrip().startswith("- "):
                    if t.lstrip() == "-":
                        pass
                    elif kir <= adım_kir:
                        break
                    else:
                        break
                öğe_kir = kir
                baş = j + 1
                j += 1
                while j < n:
                    t2 = satir_list[j]
                    if not t2.strip() or t2.lstrip().startswith("#"):
                        j += 1
                        continue
                    if len(t2) - len(t2.lstrip()) <= öğe_kir:
                        break
                    j += 1
                pencereler.append((baş, j))  # bitiş: SONRAKİ öğe (dahil değil)
            i = j if j > i else i + 1
        else:
            i += 1
    return pencereler


def _matris(islem: dict[str, Any]) -> dict[str, Any]:
    strateji = islem.get("strategy")
    if isinstance(strateji, dict) and isinstance(strateji.get("matrix"), dict):
        matris: dict[str, Any] = strateji["matrix"]
        return matris
    return {}


def _adimlar(
    dosya: str,
    islem: dict[str, Any],
    matris: dict[str, Any],
    tuketlenen: set[str],
    satir_list: list[str],
    degiskenler: dict[str, str],
    depo_koku: str,
    ise_adi: str,
    pencereler: list[tuple[int, int]] | None,
    imleç: list[int],
) -> list[Sabitleme]:
    sonuc: list[Sabitleme] = []
    adimlar = islem.get("steps")
    if not isinstance(adimlar, list):
        return sonuc
    for adim in adimlar:
        # her ayrıştırılmış adım ham listedeki bir öğeye denk gelir (hizma
        # denetimi is_aksi'de); pencere yoksa konum arama, YANLIŞ satır YAZMA
        no = imleç[0]
        imleç[0] += 1
        pencere = pencereler[no] if pencereler is not None and no < len(pencereler) else None
        if not isinstance(adim, dict):
            continue
        uses = str(adim.get("uses") or "")
        eslesme = next(((e, g, gd, cz) for e, g, gd, cz in _ADLIMLAR if e in uses), None)
        if eslesme is None:
            continue
        _, giradi, dosya_giradi, cz = eslesme
        with_block = adim.get("with")
        with_block = with_block if isinstance(with_block, dict) else {}
        if dosya_giradi and dosya_giradi in with_block:
            sonuc.extend(_surum_dosyasi_gir(dosya, cz, str(with_block[dosya_giradi]),
                                            satir_list, depo_koku, dosya_giradi,
                                            pencere))
        if giradi not in with_block:
            # `dtolnay/rust-toolchain@1.85.0` gibi eylemler sürümü uses
            # referansından alır; girdi yoksa referans OKUNUR (sessiz kaybolmaz).
            if cz == "rust" and "rust-toolchain@" in uses:
                ref = uses.rsplit("@", 1)[-1]
                sonuc.append(pin("rust", dosya, "ci-eylem", ref,
                                 satir=_tam_satır(satir_list, uses)))
            continue
        deger = with_block[giradi]
        deger_metni = None if isinstance(deger, list) else str(deger)
        satir_no = _girdi_satırı(satir_list, giradi, deger_metni, pencere)
        sonuc.extend(_deger_sabitlemeleri(dosya, cz, "ci-adim", deger, matris,
                                          tuketlenen, satir_no, degiskenler))
    return sonuc


def _deger_sabitlemeleri(
    dosya: str,
    cz: str,
    tur: str,
    deger: Any,
    matris: dict[str, Any],
    tuketlenen: set[str],
    satir_no: int | None,
    degiskenler: dict[str, str],
) -> list[Sabitleme]:
    if isinstance(deger, list):
        metinler = [str(x) for x in deger]
        dinamikler = [m for m in metinler if "${{" in m]
        somut = [m for m in metinler if "${{" not in m]
        # listeler test ızgarasıdır: satır bilgisi tek hedef göstermez
        ciktilar = [grid_pin(cz, dosya, tur, somut)] if somut else []
        for d in dinamikler:
            cozulen = _sablon_ara(d, matris, tuketlenen, degiskenler)
            if isinstance(cozulen, list):
                ciktilar.append(grid_pin(cz, dosya, tur, [str(x) for x in cozulen]))
            else:
                ciktilar.append(Sabitleme(cz, dosya, tur, d, dinamik=True))
        return ciktilar
    metin = str(deger)
    if "${{" in metin:
        cozulen = _sablon_ara(metin, matris, tuketlenen, degiskenler)
        if isinstance(cozulen, list):
            return [grid_pin(cz, dosya, tur, [str(x) for x in cozulen])]
        if isinstance(cozulen, str):
            return [pin(cz, dosya, tur, cozulen, satir=None)]
        return [Sabitleme(cz, dosya, tur, metin, dinamik=True, satir=satir_no)]
    return [pin(cz, dosya, tur, metin, satir=satir_no)]


def _sablon_ara(
    sablon: str,
    matris: dict[str, Any],
    tuketlenen: set[str],
    degiskenler: dict[str, str],
) -> Any:
    """``${{ matrix.X }}`` tüm ifadeyse X'in matris değerini, tek değerliyse
    metni döndürür; bulamazsa ``None``."""
    tam = _SABLON_RE.fullmatch(sablon.strip())
    if tam:
        ad = tam.group(1)
        if ad in degiskenler:
            return degiskenler[ad]
        if ad in matris:
            tuketlenen.add(ad)
            return matris[ad]
        return None
    kismiler = _SABLON_RE.findall(sablon)
    if len(kismiler) == 1 and (ad := kismiler[0]) and ad in degiskenler:
        return _SABLON_RE.sub(degiskenler[ad], sablon)
    return None


def _matris_sabitlemeleri(dosya: str, cz: str, anahtar: str, degerler: list[Any]) -> list[Sabitleme]:
    metinler = [str(x) for x in degerler]
    somut = [m for m in metinler if "${{" not in m]
    dinamik = [m for m in metinler if "${{" in m]
    sonuc: list[Sabitleme] = []
    if somut:
        sonuc.append(grid_pin(cz, dosya, "ci-matriks", somut))
    for d in dinamik:
        sonuc.append(Sabitleme(cz, dosya, "ci-matriks", d, dinamik=True))
    return sonuc


def _surum_dosyasi_gir(
    dosya: str, cz: str, hedef: str, satir_list: list[str], depo_koku: str,
    giradi: str = "version-file",
    pencere: tuple[int, int] | None = None,
) -> list[Sabitleme]:
    """node-version-file gibi yönlendirmeler:

    - Hedef YALNIZ depo içindeyse ve symlink içermiyorsa okunur; depo
      dışına çıkan ya da bağlantı olan hedefler İÇERİK SIZDIRMADAN reddedilir
      (`../../DOSYA` sınırı aşar — uyarı yalnız yolu tekrarlar, içeriği değil).
    - Hedef yoksa açık uyarı üretilir.
    - Hedef, Tara'nın zaten okuduğu bilinen bir sürüm dosyasıysa sessiz geçilir
      (çift kayıt olmaz).
    - Özel adlı hedef dosya MEVCUTSA İÇERİĞİ okunur (varsayılan ad dışındaki
      sürüm dosyaları kaybolmaz).
    """
    hedef = hedef.strip()
    satir_no = _girdi_satırı(satir_list, giradi, None, pencere)
    if "${{" in hedef:
        return [Sabitleme(cz, dosya, "ci-dosya", hedef, dinamik=True,
                          satir=satir_no)]
    güvenli = _depo_içi_hedef(depo_koku, hedef)
    if güvenli is None:
        return [Sabitleme(cz, dosya, "ci-dosya", hedef,
                          uyari=f"okunamadı: version-file {hedef!r} depo sınırını "
                                "aşıyor ya da dosya bağlantısı (rededildi)",
                          satir=satir_no)]
    tam, hedef_ad = güvenli
    if not os.path.isfile(tam):
        return [Sabitleme(cz, dosya, "ci-dosya", hedef,
                          uyari=f"okunamadı: version-file {hedef!r} bulunamadı",
                          satir=satir_no)]
    if hedef_ad in TARANAN_SÜRÜM_DOSYALARI:
        return []  # asıl dosya zaten taranacak — tutarlılık kendiliğinden
    try:
        with open(tam, encoding="utf-8", errors="replace") as fh:
            icerik = fh.read()
    except OSError as exc:
        return [Sabitleme(cz, dosya, "ci-dosya", hedef,
                          uyari=f"okunamadı: version-file {hedef!r} ({exc})",
                          satir=satir_no)]
    pimler = _sürüm_dosyası_oku(cz, hedef, icerik)
    for p in pimler:
        p.tur = "ci-dosya"
    return pimler


def _depo_içi_hedef(depo_koku: str, hedef: str) -> tuple[str, str] | None:
    """(okunabilir yol, taban ad) ya da None (REDDEDİLDİ).

    Red gerekçeleri: depo kökü bilinmiyor, mutlak yol, `..` bileşeni,
    çözümlenmiş yol depo dışında (symlink dahil) — okuma ÖNCE denetlenir,
    dışarıdaki içerik hiçbir yere (uyarıya bile) taşınmaz.
    """
    if not depo_koku:
        return None
    t = hedef.replace("\\", "/")
    if t.startswith("/") or re.match(r"^[A-Za-z]:", t):
        return None
    parcalar = t.split("/")
    if any(p == ".." for p in parcalar):
        return None
    tam = os.path.normpath(os.path.join(depo_koku, *parcalar))
    kök = os.path.realpath(depo_koku)
    gerçek = os.path.realpath(tam)
    if gerçek != kök and not gerçek.startswith(kök + os.sep):
        return None  # çözümlenen yol depo dışında (symlink dahil)
    # depo kökündeki host bağları (macOS /tmp) meşrudur; RED yalnız depo
    # İÇİNDEKİ bileşenlerin symlink olması hâlidir:
    adım = depo_koku
    for p in parcalar:
        adım = os.path.join(adım, p)
        if os.path.islink(adım):
            return None
    return tam, os.path.basename(tam)


def _sürüm_dosyası_oku(cz: str, hedef: str, icerik: str) -> list[Sabitleme]:
    """Özel adlı sürüm dosyasının içeriğini ilgili bulucuya verir."""
    if cz == "node":
        return node.surum_dosyasi(hedef, icerik)
    if cz == "python":
        return python.surum_dosyasi(hedef, icerik)
    if cz == "go":
        return go.surum_dosyasi(hedef, icerik)
    if cz == "java":
        return java.surum_dosyasi(hedef, icerik)
    return []


def _girdi_satırı(
    satir_list: list[str], anahtar: str, deger_metni: str | None = None,
    pencere: tuple[int, int] | None = None,
) -> int | None:
    r"""YAML GİRDİ ANAHTARININ satırı: `^\s*<anahtar>:` biçimi.

    Serbest metin araması yanılır: `- name: node-version 22 installation`
    satırı gerçek `node-version: 20` girdisinden önce gelir. Anahtar verilse
    bile değer aynı satırda beklenir; bulunamazsa konum belirsizdir → None.

    `pencere` verilirse arama YALNIZ o adım bloğunun satırlarında yapılır:
    `strategy.matrix` içindeki aynı adlı satır (`node-version: [22, 24]`)
    adımın konumu OLAMAZ. Kalan birden çok aday belirsizdir → None.
    """
    desen = re.compile(rf"^[ \t]*{re.escape(anahtar)}[ \t]*:")
    anahtar_satırları = [i for i, s in enumerate(satir_list, start=1)
                         if desen.match(s)
                         and (pencere is None or pencere[0] <= i <= pencere[1])]
    if not anahtar_satırları:
        return None
    if deger_metni is None:
        return anahtar_satırları[0] if len(anahtar_satırları) == 1 else None
    hedefler = [i for i in anahtar_satırları
                if deger_metni in satir_list[i - 1]]
    return hedefler[0] if len(hedefler) == 1 else None


def _tam_satır(satir_list: list[str], iplik: str) -> int | None:
    """Tam ipliğin (ör. uses değeri) tek geçtiği satır; belirsizse None."""
    eşleşen = [i for i, s in enumerate(satir_list, start=1) if iplik in s]
    return eşleşen[0] if len(eşleşen) == 1 else None
