"""Çelişki tespiti: aynı çalışma zamanının sabitlemelerini karşılaştırır.

Çelişki, KESİŞMEYEN herhangi bir sabitleme çiftidir; çelişen çiftler bir
bileşen (graph component) olarak tek ``Celiski`` kaydında toplanır. Böylece
referans seçimi, diğer kaynaklar arasındaki gerçek çelişkileri gizleyemez
(``20`` hub olsa bile ``20.11.0`` ile ``20.12.0`` çelişkisi rapor edilir).

Referans: ``kaynak`` verilmişse o dosyanın sabitlemesi (kaynak modunda kaynak
sabitlemesi olmayan çalışma zamanı atlanır); değilse bileşen içinden en çok
kesişen somut aday (medoid). Test ızgaraları referans adayı değildir.
"""

from __future__ import annotations

from .sabitleme import Celiski, Sabitleme
from .versiyon import AralikKumesi, kümeler_kesisir

__all__ = ["celiski"]


def _kume(p: Sabitleme) -> AralikKumesi:
    assert p.aralik is not None
    return p.aralik


def _kesisir(a: Sabitleme, b: Sabitleme) -> bool:
    return kümeler_kesisir(_kume(a), _kume(b))


def _somut_referans_mi(p: Sabitleme) -> bool:
    return p.aralik is not None and len(p.aralik.parcalar) == 1 and p.aralik.sabit


def _çelişen_bileşenler(havuz: list[Sabitleme]) -> list[list[Sabitleme]]:
    """Kesişmeyen çift kenarlarıyla birleşim-bul: kenarı olan bileşenler."""
    ebeveyn = list(range(len(havuz)))

    def bul(i: int) -> int:
        while ebeveyn[i] != i:
            ebeveyn[i] = ebeveyn[ebeveyn[i]]
            i = ebeveyn[i]
        return i

    kenar_var = [False] * len(havuz)
    for i in range(len(havuz)):
        for j in range(i + 1, len(havuz)):
            if not _kesisir(havuz[i], havuz[j]):
                a, b = bul(i), bul(j)
                if a != b:
                    ebeveyn[a] = b
                kenar_var[i] = kenar_var[j] = True
    gruplar: dict[int, list[Sabitleme]] = {}
    ilk_no: dict[int, int] = {}
    for i, p in enumerate(havuz):
        if kenar_var[i]:
            r = bul(i)
            ilk_no.setdefault(r, i)
            gruplar.setdefault(r, []).append(p)
    return [gruplar[k] for k in sorted(gruplar, key=lambda k: ilk_no[k])]


def _kesişim_sayısı(p: Sabitleme, havuz: list[Sabitleme]) -> int:
    return sum(1 for q in havuz if q is not p and _kesisir(p, q))


def _medoid(bileşen: list[Sabitleme], havuz: list[Sabitleme]) -> Sabitleme:
    """Bileşen içinden referans adayı.

    - İki+ somut aday: en çok kesişen somut (eşitlikte tarama sırası).
      Izgaralar somut değildir (çok parçalı), referans adayı olamaz.
    - TEK somut + başka beyanlar (aralık/ızgara) bileşende duruyorsa:
      BEYANLAR referanstır; uymayan tek somut dışlanır
      (``>=3.10`` politikası yanında ``3.9`` sapkın olan şeydir).
    - Somut yoksa: bileşen geneli.
    """

    def sıra_no(p: Sabitleme) -> int:
        for i, q in enumerate(havuz):
            if q is p:
                return i
        return len(havuz)

    def en_iyi(adaylar: list[Sabitleme]) -> Sabitleme:
        return max(adaylar, key=lambda p: (_kesişim_sayısı(p, havuz), -sıra_no(p)))

    somut = [p for p in bileşen if _somut_referans_mi(p)]
    if len(somut) >= 2:
        return en_iyi(somut)
    if len(somut) == 1 and len(bileşen) > 1:
        return en_iyi([p for p in bileşen if p is not somut[0]])
    return en_iyi(bileşen)


def _bileşen_hedefleri(bileşen: list[Sabitleme], havuz: list[Sabitleme],
                       kaynak: str | None) -> tuple[Sabitleme, list[Sabitleme]] | None:
    """(referans, dışlananlar). Kaynak modunda referans kaynaktır; kaynakla
    uyuşmayanlar dışlanır. Kaynak hiçbir şeyi dışlamıyorsa bileşen İÇİNDEKİ
    çelişki yine rapor edilir (hub referans çelişkiyi gizleyemez)."""
    if kaynak is not None:
        kaynak_pimler = [p for p in havuz if p.dosya == kaynak]
        if not any(p.dosya == kaynak for p in bileşen):
            # bileşen kaynakla ilgili değil: yine de gerçek bir çelişkidir,
            # otomatik mod gibi raporla (kaynak listesi hedefleri seçmez)
            referans = _medoid(bileşen, havuz)
            dislanan = [p for p in bileşen if p is not referans
                        and not _kesisir(referans, p)]
            return (referans, dislanan) if dislanan else _iç_çelişki(bileşen, havuz)
        referans = kaynak_pimler[0]
        ref_küme = AralikKumesi(tuple(par for p in kaynak_pimler
                                       for par in _kume(p).parcalar))
        dislanan = [p for p in bileşen if p.dosya != kaynak
                    and not kümeler_kesisir(ref_küme, _kume(p))]
        if dislanan:
            return referans, dislanan
        return _iç_çelişki(bileşen, havuz)
    referans = _medoid(bileşen, havuz)
    dislanan = [p for p in bileşen if p is not referans and not _kesisir(referans, p)]
    if dislanan:
        return referans, dislanan
    return _iç_çelişki(bileşen, havuz)


def _iç_çelişki(bileşen: list[Sabitleme],
                havuz: list[Sabitleme]) -> tuple[Sabitleme, list[Sabitleme]] | None:
    """Referans herkesle kesişiyor ama bileşen içinde kesişmeyen çiftler var:
    çelişenler birbiridir — en az bağlantılı aday dışlanan olur."""
    çelişenler = [p for p in bileşen
                  if any(q is not p and not _kesisir(p, q) for q in bileşen)]
    if not çelişenler:
        return None
    referans = _medoid(çelişenler, havuz)
    dislanan = [p for p in çelişenler if p is not referans
                and not _kesisir(referans, p)]
    if not dislanan:  # aday birbirinin aynısı iki pim: ikincisi dışlanır
        dislanan = çelişenler[1:]
    return referans, dislanan


def celiski(sabitlemeler: list[Sabitleme], kaynak: str | None = None) -> list[Celiski]:
    """Sabitleme listesinden çalışma zamanı başına çelişkileri döndürür."""
    by_rt: dict[str, list[Sabitleme]] = {}
    for p in sabitlemeler:
        if p.kullanilabilir:
            by_rt.setdefault(p.calisma_zamani, []).append(p)
    sonuclar: list[Celiski] = []
    for rt, kullanim in sorted(by_rt.items()):
        if len(kullanim) < 2:
            continue
        if kaynak is not None and not any(p.dosya == kaynak for p in kullanim):
            continue  # kaynak modu: bu çalışma zamanında kaynak sabitlemesi yok
        for bileşen in _çelişen_bileşenler(kullanim):
            hedef = _bileşen_hedefleri(bileşen, kullanim, kaynak)
            if hedef is None:
                continue
            referans, dislanan = hedef
            adlar = " | ".join(f"{_kisa(p.dosya)}={p.ham}" for p in kullanim)
            hedefler = ", ".join(p.dosya for p in dislanan)
            sonuclar.append(Celiski(
                calisma_zamani=rt,
                referans_dosya=referans.dosya,
                referans_ham=referans.ham,
                dislananlar=dislanan,
                mesaj=f"{rt}: {adlar} → ÇELİŞKİ: {hedefler}",
            ))
    return sonuclar


def _kisa(yol: str) -> str:
    return yol.rsplit("/", 1)[-1]
