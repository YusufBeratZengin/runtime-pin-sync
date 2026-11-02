"""Sürüm belirteçlerini (semver / PEP 440 karışımı) aralık kümelerine çevirir.

Her sabitleme bir ``AralıkKümesi``'ne indirgenir: kesişimi olmayan iki küme
"çelişir". Sabit sürüm, ön ek (``20`` -> ``20.x``), ``>=``/``<=`` aralıkları,
semver ``^``/``~`` ve PEP 440 ``~=`` desteklenir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Aralik", "AralikKumesi", "spek_ayristir", "kümeler_kesisir",
           "sabit_belirtec_mi"]

_T = tuple[int, ...]

# v17 / 17.0.2 / 3.12.* / 20.x
_SURUM = r"v?(\d+(?:\.\d+)*)(?:\.[*x])?"
_KISIT_RE = re.compile(rf"(?P<op>>=|<=|==|=|~=|~>|!=|\^|~|>|<)?\s*(?P<surum>{_SURUM})(?P<kuyruk>.*)")


def _pad(a: _T, b: _T) -> tuple[_T, _T]:
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)), b + (0,) * (n - len(b))


def _cmp(a: _T, b: _T) -> int:
    pa, pb = _pad(a, b)
    return (pa > pb) - (pa < pb)


def _sonraki(v: _T) -> _T:
    """Ön ek aralığının açık üst sınırı: (20,) -> (21,), (20,1) -> (20,2)."""
    return v[:-1] + (v[-1] + 1,)


@dataclass(frozen=True)
class Aralik:
    """Tek aralık: [alt, ust] uçları ayrı ayrı kapalı/açık olabilir."""

    alt: _T | None = None       # None = -sonsuz
    alt_kapsar: bool = True
    ust: _T | None = None       # None = +sonsuz
    ust_kapsar: bool = False

    @property
    def bos(self) -> bool:
        if self.alt is None or self.ust is None:
            return False
        c = _cmp(self.alt, self.ust)
        if c > 0:
            return True
        return c == 0 and not (self.alt_kapsar and self.ust_kapsar)

    def kesis(self, o: Aralik) -> Aralik:
        alt, alt_k = self._max_alt(o)
        ust, ust_k = self._min_ust(o)
        return Aralik(alt, alt_k, ust, ust_k)

    def _max_alt(self, o: Aralik) -> tuple[_T | None, bool]:
        if self.alt is None:
            return o.alt, o.alt_kapsar
        if o.alt is None:
            return self.alt, self.alt_kapsar
        c = _cmp(self.alt, o.alt)
        if c > 0:
            return self.alt, self.alt_kapsar
        if c < 0:
            return o.alt, o.alt_kapsar
        return self.alt, (self.alt_kapsar and o.alt_kapsar)

    def _min_ust(self, o: Aralik) -> tuple[_T | None, bool]:
        if self.ust is None:
            return o.ust, o.ust_kapsar
        if o.ust is None:
            return self.ust, self.ust_kapsar
        c = _cmp(self.ust, o.ust)
        if c < 0:
            return self.ust, self.ust_kapsar
        if c > 0:
            return o.ust, o.ust_kapsar
        return self.ust, (self.ust_kapsar and o.ust_kapsar)

    def __str__(self) -> str:
        alt = "-inf" if self.alt is None else f"{'[' if self.alt_kapsar else '('}{_nokta(self.alt)}"
        ust = "+inf" if self.ust is None else f"{_nokta(self.ust)}{']' if self.ust_kapsar else ')'}"
        return f"{alt},{ust}"


def _nokta(v: _T) -> str:
    return ".".join(str(x) for x in v)


@dataclass(frozen=True)
class AralikKumesi:
    """Aralıkların birleşimi (``||`` dalları)."""

    parcalar: tuple[Aralik, ...]

    @property
    def bos(self) -> bool:
        return all(p.bos for p in self.parcalar)

    @property
    def sabit(self) -> bool:
        """Dar, İKİ yanı sınırlı sabit/ön ek aralığı mı? (sync ve referans için)"""
        return (len(self.parcalar) == 1 and self.parcalar[0].alt is not None
                and self.parcalar[0].ust is not None)


def kümeler_kesisir(a: AralikKumesi, b: AralikKumesi) -> bool:
    return any(not p.kesis(q).bos for p in a.parcalar for q in b.parcalar)


def _kismi_aralik(v: _T) -> Aralik:
    """``20`` / ``20.x`` -> [20, 21); ``3.12.1`` -> [3.12.1, 3.12.2)."""
    return Aralik(alt=v, alt_kapsar=True, ust=_sonraki(v), ust_kapsar=False)


def _tek_kisit(op: str, v: _T, yildiz: bool) -> Aralik:
    if op in ("", "="):
        # Tam belirtilmiş sürüm (üç+ bileşen) NOKTADIR: "20.1.0" kendi dışındaki
        # ">20.1.0" ile kesişmez. Kısa belirteç ("20", "20.1", "20.x") önektir.
        if not yildiz and len(v) >= 3:
            return Aralik(alt=v, alt_kapsar=True, ust=v, ust_kapsar=True)
        return _kismi_aralik(v)
    if op == "==":  # PEP 440: ==3.12 tam değerdir (0.9.10 eşleşmesi yok)
        return Aralik(alt=v, alt_kapsar=True, ust=v, ust_kapsar=True)
    if op == ">=":
        return Aralik(alt=v, alt_kapsar=True)
    if op == ">":
        return Aralik(alt=v, alt_kapsar=False)
    if op == "<=":
        return Aralik(ust=v, ust_kapsar=True)
    if op == "<":
        return Aralik(ust=v, ust_kapsar=False)
    if op in ("~", "~>"):  # semver ~ : ~20.1 -> [20.1, 20.2); ~20.1.5 -> [20.1.5, 20.2)
        ust = _sonraki(v[:2]) if len(v) >= 3 else _sonraki(v)
        return Aralik(alt=v, alt_kapsar=True, ust=ust, ust_kapsar=False)
    if op == "~=":  # PEP 440 compatible: ~=3.12.1 -> [3.12.1, 3.13)
        if len(v) < 2:
            return Aralik(alt=v, alt_kapsar=True, ust=_sonraki(v), ust_kapsar=False)
        return Aralik(alt=v, alt_kapsar=True, ust=_sonraki(v[:-1]), ust_kapsar=False)
    if op == "^":  # semver caret
        if v[0] > 0 or len(v) == 1:
            ust = _sonraki(v[:1])
        elif v[1] > 0 or len(v) == 2:
            ust = _sonraki(v[:2])
        else:
            ust = _sonraki(v)
        return Aralik(alt=v, alt_kapsar=True, ust=ust, ust_kapsar=False)
    return Aralik()  # ulaşılamaz


def spek_ayristir(ham: str) -> AralikKumesi | None:
    """Bir sürüm belirtecini aralık kümesine çevirir; çözülemezse ``None``."""
    metin = (ham or "").strip()
    if not metin:
        return None
    if metin in ("*", "x", "X", "any"):
        return AralikKumesi((Aralik(),))
    parcalar: list[Aralik] = []
    for dal in metin.split("||"):
        dal = dal.strip()
        if not dal:
            return None
        # ">=18 <20" ve ">=3.10,<4.0" => aynı dalın VE kısıtları
        kisitlar = re.split(r",|\s+", dal)
        parca: Aralik | None = None
        for k in kisitlar:
            if not k:
                continue
            a = _kisit(k)
            if a is None:
                return None
            parca = a if parca is None else parca.kesis(a)
        if parca is None:
            return None
        parcalar.append(parca)
    return AralikKumesi(tuple(parcalar)) if parcalar else None


def _kisit(token: str) -> Aralik | None:
    m = _KISIT_RE.fullmatch(token)
    if not m:
        return None
    op = m.group("op") or ""
    if op == "!=":  # dışlama kümesi: güvenli çelişki çıkarımı yapılamaz
        return None
    # "17.0.2+8" gibi yapısal meta veriyi yok say; ön sürüm soneklerini destekleme
    kuyruk = m.group("kuyruk") or ""
    if kuyruk and kuyruk not in (".*", ".x") and not kuyruk.startswith("+"):
        return None
    v_text = m.group("surum").lstrip("vV")
    v_text = re.sub(r"\.(?:[*xX])$", "", v_text)
    try:
        v = tuple(int(x) for x in v_text.split("."))
    except ValueError:
        return None
    yildiz = ".*" in token or token.endswith(".x") or token.endswith(".X")
    return _tek_kisit(op, v, yildiz)


# Operatörü, birleşimi veya listesi OLMAYAN düz sürüm belirteci:
# "20", "20.11.0", "v22", "20.x", "17.0.2+8". "^22", ">=18", "22 || 24",
# "22, 24", "lts/iron" GİRMEZ — sync yalnız bu biçimdeki değerleri yazar.
_TAM_SABİT_RE = re.compile(
    r"^v?\d+(?:\.\d+){0,3}(?:\.[xX*])?(?:\+[0-9A-Za-z.\-]+)?$")


def sabit_belirtec_mi(ham: str) -> bool:
    """Ham belirteç gerçekten sabit/öneke bir sürüm mü (aralık/matris değil)?"""
    t = (ham or "").strip()
    if not _TAM_SABİT_RE.match(t):
        return False
    return spek_ayristir(t) is not None
