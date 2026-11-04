"""İnsan ve makine okuyabilir rapor üretimi (tablo + JSON)."""

from __future__ import annotations

from typing import Any

from .sabitleme import Celiski, Sabitleme

__all__ = ["tablo", "json_sözlüğü", "uyari_cevir"]

_CEVIRI_TABLOSU: list[tuple[str, str]] = [
    ("okunamadı:", "could not read:"),
    ("boş dosya", "empty file"),
    ("boş belirteç", "empty token"),
    ("sürüm belirteçi çözümlenemedi", "could not parse version token"),
    ("çözümlenemeyen etiket", "unresolvable tag"),
    ("desteklenmeyen etiket soneki", "unsupported tag suffix"),
    ("ön sürüm etiketi karşılaştırmaya girmez",
     "prerelease tag excluded from comparison"),
    ("girinti için sekme kullanılamaz", "tabs cannot be used for indentation"),
    ("beklenmeyen girinti", "unexpected indentation"),
    ("eşleme beklenirken", "expected a mapping"),
    ("okuma reddedildi", "read refused"),
    ("desteklenmeyen YAML", "unsupported YAML"),
    ("iş akışı bir eşleme değil", "workflow is not a mapping"),
    ("geçersiz JSONC", "invalid JSONC"),
    ("geçersiz JSON", "invalid JSON"),
    ("geçersiz TOML", "invalid TOML"),
    ("JSON bir nesne değil", "JSON is not an object"),
    ("engines.node bir metin değil", "engines.node is not a string"),
    ("requires-python bir metin değil", "requires-python is not a string"),
    ("channel bir metin değil", "channel is not a string"),
    ("go.mod içinde 'go' satırı yok", "no 'go' directive in go.mod"),
    ("FROM satırı çözümlenemedi", "could not parse FROM line"),
    ("bağlantı depo dışına işaret ediyor", "link points outside repository"),
    ("depo sınırını aşıyor", "points outside repository"),
    ("ön sürüm karşılaştırmaya girmez", "prerelease excluded from comparison"),
    ("tanınmayan", "unrecognized"),
    ("bulunamadı", "not found"),
]


def uyari_cevir(uyari: str | None, lang: str = "tr") -> str:
    """Uyarı metnini istenen dile çevirir (varsayılan: tr)."""
    if uyari is None:
        return ""
    if lang != "en":
        return uyari
    sonuc = uyari
    for tr, en in _CEVIRI_TABLOSU:
        sonuc = sonuc.replace(tr, en)
    return sonuc


def _durumlar(pimler: list[Sabitleme], celiskiler: list[Celiski],
              kaynak: str | None, lang: str = "tr") -> dict[tuple[str, str, str, str], str]:
    dislanan = {(c.calisma_zamani, id(p)) for c in celiskiler for p in c.dislananlar}
    referanslar = {(c.calisma_zamani, c.referans_dosya) for c in celiskiler}
    durum: dict[tuple[str, str, str, str], str] = {}
    is_en = (lang == "en")
    for p in pimler:
        if p.uyari:
            d = "could not read" if is_en else "okunamadı"
        elif p.dinamik:
            d = "dynamic, skipped" if is_en else "dinamik, atlandı"
        elif (p.calisma_zamani, id(p)) in dislanan:
            d = "CONFLICT" if is_en else "ÇELİŞKİ"
        elif kaynak is not None and p.dosya == kaynak or (p.calisma_zamani, p.dosya) in referanslar and p.ham == next(
                c.referans_ham for c in celiskiler
                if (c.calisma_zamani, c.referans_dosya) == (p.calisma_zamani, p.dosya)):
            d = "reference" if is_en else "referans"
        elif (p.calisma_zamani, p.dosya) in referanslar:
            d = "consistent with reference" if is_en else "referansla uyumlu"
        else:
            d = "consistent" if is_en else "uyumlu"
        durum[(p.calisma_zamani, p.dosya, p.tur, p.ham)] = d
    return durum


def tablo(pimler: list[Sabitleme], celiskiler: list[Celiski],
          kaynak: str | None = None, lang: str = "tr") -> str:
    """Sabit genişlikli insan tablosu + özet satırları."""
    is_en = (lang == "en")
    if not pimler:
        return (
            "No version sources found (.nvmrc, Dockerfile, CI, pyproject...)."
            if is_en
            else "Hiç sürüm kaynağı bulunamadı (.nvmrc, Dockerfile, CI, pyproject...)."
        )
    durum = _durumlar(pimler, celiskiler, kaynak, lang=lang)
    başlıklar = (
        ("RUNTIME", "SOURCE", "TYPE", "PIN", "STATUS")
        if is_en
        else ("ÇALIŞMA ZAMANI", "KAYNAK", "TÜR", "SABİTLEME", "DURUM")
    )
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
            if is_en:
                msg = c.mesaj.replace(" → ÇELİŞKİ: ", " → CONFLICT: ")
                satirlar_out.append(msg)
            else:
                satirlar_out.append(c.mesaj)
        n = len(celiskiler)
        if is_en:
            runtime_str = "runtime has conflicts" if n == 1 else "runtimes have conflicts"
            satirlar_out.append(f"RESULT: {n} {runtime_str}.")
        else:
            satirlar_out.append(f"SONUÇ: {n} çalışma zamanında çelişki bulundu.")
    else:
        if is_en:
            satirlar_out.append("RESULT: all pins are consistent ✓")
        else:
            satirlar_out.append("SONUÇ: tüm sabitlemeler uyumlu ✓")
    uyarilar = [p for p in pimler if p.uyari or p.dinamik]
    if uyarilar:
        satirlar_out.append("")
        satirlar_out.append("NOTES:" if is_en else "NOTLAR:")
        for p in uyarilar:
            if is_en:
                mesaj = uyari_cevir(p.uyari, "en") if p.uyari else "dynamic expression: not compared"
            else:
                mesaj = p.uyari or "dinamik ifade: karşılaştırmaya girmedi"
            satirlar_out.append(f"  {p.dosya}: {mesaj}")
    return "\n".join(satirlar_out)


def json_sözlüğü(pimler: list[Sabitleme], celiskiler: list[Celiski],
                 kaynak: str | None = None, lang: str = "tr") -> dict[str, Any]:
    """JSON çıktı şeması (--json). Dosya yazmaz, sözlük döner."""
    durum = _durumlar(pimler, celiskiler, kaynak, lang=lang)
    is_en = (lang == "en")
    return {
        "sabitlemeler": [
            {
                "calisma_zamani": p.calisma_zamani,
                "dosya": p.dosya,
                "tur": p.tur,
                "ham": p.ham,
                "durum": durum[(p.calisma_zamani, p.dosya, p.tur, p.ham)],
                "uyari": uyari_cevir(p.uyari, "en") if (is_en and p.uyari) else p.uyari,
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
                "mesaj": c.mesaj.replace(" → ÇELİŞKİ: ", " → CONFLICT: ") if is_en else c.mesaj,
            }
            for c in celiskiler
        ],
        "uyarilar": [
            uyari_cevir(p.uyari, "en") if is_en else p.uyari
            for p in pimler if p.uyari
        ],
        "dinamikler": [
            {"dosya": p.dosya, "tur": p.tur, "ham": p.ham}
            for p in pimler if p.dinamik
        ],
    }
