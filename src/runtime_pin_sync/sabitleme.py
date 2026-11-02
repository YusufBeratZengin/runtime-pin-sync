"""Veri modelleri: ``Sabitleme`` (bir dosyadan çıkan sürüm) ve ``Celiski``."""

from __future__ import annotations

from dataclasses import dataclass, field

from .versiyon import AralikKumesi

__all__ = ["Sabitleme", "Celiski", "CALISMA_ZAMANLARI"]

CALISMA_ZAMANLARI = ("node", "python", "go", "rust", "java")


@dataclass
class Sabitleme:
    """Tek bir dosyadan çıkarılmış tek bir sürüm sabitlemesi."""

    calisma_zamani: str            # node | python | go | rust | java
    dosya: str                     # depoya göreli, POSIX ayraçlı yol
    tur: str                       # nvmrc | engines | dockerfile | ci-adim | ...
    ham: str                       # dosyada yazan ham belirteç
    aralik: AralikKumesi | None = None
    dinamik: bool = False          # ${{ ... }} ya da çözülemeyen takma ad
    uyari: str | None = None       # "okunamadı: ..." — dosya hataya düşürmez
    satir: int | None = None       # 1-tabanlı satır (sync için)
    yeniden_yazilabilir: bool = False

    @property
    def kullanilabilir(self) -> bool:
        return self.aralik is not None and not self.dinamik and self.uyari is None

    @property
    def durum(self) -> str:
        if self.uyari:
            return "okunamadı"
        if self.dinamik:
            return "dinamik, atlandı"
        if self.aralik is None:
            return "okunamadı"
        return "okundu"


@dataclass
class Celiski:
    """Bir çalışma zamanı için referansla uyuşmayan sabitleme grubu."""

    calisma_zamani: str
    referans_dosya: str
    referans_ham: str
    dislananlar: list[Sabitleme] = field(default_factory=list)
    mesaj: str = ""
