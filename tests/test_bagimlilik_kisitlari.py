"""Geliştirme bağımlılığı kilitleri ↔ pyproject aralıkları tutarlılığı.

Projenin kendi tezi "sürüm sabitlemeleri tek kaynakla tutarlı olmalı". Bu
test o tezi kendi deposuna uygular: `scripts/kisitlar-dev.txt` içindeki tam
sürümler `pyproject.toml [dev]` aralıklarıyla çelişirse kapı kırmızı olur.
Böylece kilit dosyası sessizce bayatlayamaz.
"""

import re
from pathlib import Path

from runtime_pin_sync import minitoml

KOK = Path(__file__).resolve().parent.parent
KISIT = KOK / "scripts" / "kisitlar-dev.txt"
PYPROJECT = KOK / "pyproject.toml"

SATIR = re.compile(r"^(?P<ad>[A-Za-z0-9_.-]+)==(?P<surum>[0-9][0-9A-Za-z.+-]*)$")
ARALIK = re.compile(r"^(?P<ad>[A-Za-z0-9_.-]+)\s*(?P<kisit>.+)$")


def _dev_gereksinimleri() -> dict[str, str]:
    veri = minitoml.oku(PYPROJECT.read_bytes())
    ham = veri["project"]["optional-dependencies"]["dev"]
    sonuc = {}
    for satir in ham:
        metin = satir.split("#", 1)[0].strip()
        if not metin:
            continue
        e = ARALIK.match(metin)
        assert e, f"[dev] girdisi ayrıştırılamadı: {satir!r}"
        sonuc[e.group("ad").lower()] = e.group("kisit").strip()
    return sonuc


def _kilitler() -> dict[str, str]:
    sonuc = {}
    for satir in KISIT.read_text(encoding="utf-8").splitlines():
        metin = satir.strip()
        if not metin or metin.startswith("#"):
            continue
        e = SATIR.match(metin)
        assert e, f"kilit satırı tam sürüm değil: {satir!r}"
        sonuc[e.group("ad").lower()] = e.group("surum")
    return sonuc


def test_kilit_dosyasi_tam_surum_ve_bos_degil():
    kilitler = _kilitler()
    assert {"pytest", "pytest-cov", "ruff", "mypy"} <= set(kilitler)


def test_kilitler_dev_ekstrasinda_tanimli():
    dev = _dev_gereksinimleri()
    bilinmeyen = set(_kilitler()) - set(dev)
    assert not bilinmeyen, f"[dev] içinde olmayan kilit: {sorted(bilinmeyen)}"


def test_dev_araliklari_ust_siniirli():
    """Her geliştirme bağımlılığı üst sınır taşır (sınırsız sürüm sürüklenmesi yok)."""
    sinirsiz = [ad for ad, kisit in _dev_gereksinimleri().items() if "<" not in kisit]
    assert not sinirsiz, f"üst sınırı olmayan geliştirme bağımlılığı: {sinirsiz}"


def test_kilit_surumu_araligin_icinde():
    """Kesin kilit, `>= alt, < üst` aralığının dışına düşemez.

    Karşılaştırma sürüm demetleri üzerinden yapılır (9.1.1 → (9, 1, 1));
    böylece test PEP 440'ın tamamını yeniden uygulamaz, yalnız sınır ihlalini
    yakalar — asıl sözleşme bu.
    """
    def demet(metin: str) -> tuple[int, ...]:
        return tuple(int(p) for p in re.findall(r"\d+", metin)[:3])

    dev = _dev_gereksinimleri()
    for ad, kilit in _kilitler().items():
        kisit = dev[ad]
        for parca in kisit.split(","):
            parca = parca.strip()
            if not parca.startswith((">=", "<")):
                continue
            op = "<=" if parca.startswith("<=") else parca[0]
            surum = parca.lstrip("<>=").strip()
            k, s = demet(kilit), demet(surum)
            if op == ">=":
                assert k >= s, f"{ad}: {kilit} < alt sınır {surum}"
            elif op == "<":
                assert k < s, f"{ad}: {kilit} >= üst sınır {surum}"
            elif op == "<=":
                assert k <= s, f"{ad}: {kilit} > üst sınır {surum}"
