"""İnsan ve makine okuyabilir rapor üretimi (tablo + JSON)."""

from __future__ import annotations

from typing import Any

from .sabitleme import Celiski, Sabitleme

__all__ = ["tablo", "json_sözlüğü"]


def _durumlar(pimler: list[Sabitleme], celiskiler: list[Celiski],
              kaynak: str | None) -> dict[tuple[str, str, str, str], str]:
    dislanan = {(c.calisma_zamani, id(p)) for c in celiskiler for p in c.dislananlar}
    referanslar = {(c.calisma_zamani, c.referans_dosya) for c in celiskiler}
    durum: dict[tuple[str, str, str, str], str] = {}
    for p in pimler:
        if p.uyari:
            d = "okunamadı"
        elif p.dinamik:
            d = "dinamik, atlandı"
        elif (p.calisma_zamani, id(p)) in dislanan:
            d = "ÇELİŞKİ"
        elif kaynak is not None and p.dosya == kaynak or (p.calisma_zamani, p.dosya) in referanslar and p.ham == next(
                c.referans_ham for c in celiskiler
                if (c.calisma_zamani, c.referans_dosya) == (p.calisma_zamani, p.dosya)):
            d = "referans"
        elif (p.calisma_zamani, p.dosya) in referanslar:
            d = "referansla uyumlu"
        else:
            d = "uyumlu"
        durum[(p.calisma_zamani, p.dosya, p.tur, p.ham)] = d
    return durum


def tablo(pimler: list[Sabitleme], celiskiler: list[Celiski],
          kaynak: str | None = None) -> str:
    """Sabit genişlikli insan tablosu + özet satırları."""
    if not pimler:
        return "Hiç sürüm kaynağı bulunamadı (.nvmrc, Dockerfile, CI, pyproject...)."
    durum = _durumlar(pimler, celiskiler, kaynak)
    başlıklar = ("ÇALIŞMA ZAMANI", "KAYNAK", "TÜR", "SABİTLEME", "DURUM")
    satirlar = [
        (p.calisma_zamani, p.dosya, p.tur, p.ham or "-",
         durum[(p.calisma_zamani, p.dosya, p.tur, p.ham)])
        for p in pimler
    ]
    genislikler = [
        max(len(b), *(len(s[i]) for s in satirlar)) if satirlar else len(b)
        for i, b in enumerate(başlıklar)
    ]

    def dize(parcalar: tuple[str, ...]) -> str:
        return "  ".join(s.ljust(g) for s, g in zip(parcalar, genislikler, strict=True)).rstrip()

    satirlar_out = [dize(başlıklar),
                    dize(tuple("-" * g for g in genislikler))]
    satirlar_out += [dize(s) for s in satirlar]
    satirlar_out.append("")
    if celiskiler:
        for c in celiskiler:
            satirlar_out.append(c.mesaj)
        n = len(celiskiler)
        satirlar_out.append(f"SONUÇ: {n} çalışma zamanında çelişki bulundu.")
    else:
        satirlar_out.append("SONUÇ: tüm sabitlemeler uyumlu ✓")
    uyarilar = [p for p in pimler if p.uyari or p.dinamik]
    if uyarilar:
        satirlar_out.append("")
        satirlar_out.append("NOTLAR:")
        for p in uyarilar:
            mesaj = p.uyari or "dinamik ifade: karşılaştırmaya girmedi"
            satirlar_out.append(f"  {p.dosya}: {mesaj}")
    return "\n".join(satirlar_out)


def json_sözlüğü(pimler: list[Sabitleme], celiskiler: list[Celiski],
                 kaynak: str | None = None) -> dict[str, Any]:
    """JSON çıktı şeması (--json). Dosya yazmaz, sözlük döner."""
    durum = _durumlar(pimler, celiskiler, kaynak)
    return {
        "sabitlemeler": [
            {
                "calisma_zamani": p.calisma_zamani,
                "dosya": p.dosya,
                "tur": p.tur,
                "ham": p.ham,
                "durum": durum[(p.calisma_zamani, p.dosya, p.tur, p.ham)],
                "uyari": p.uyari,
            }
            for p in pimler
        ],
        "celiskiler": [
            {
                "calisma_zamani": c.calisma_zamani,
                "referans": {"dosya": c.referans_dosya, "ham": c.referans_ham},
                "dislananlar": [
                    {"dosya": p.dosya, "tur": p.tur, "ham": p.ham}
                    for p in c.dislananlar
                ],
                "mesaj": c.mesaj,
            }
            for c in celiskiler
        ],
        "uyarilar": [p.uyari for p in pimler if p.uyari],
        "dinamikler": [
            {"dosya": p.dosya, "tur": p.tur, "ham": p.ham}
            for p in pimler if p.dinamik
        ],
    }
