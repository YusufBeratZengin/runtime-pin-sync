"""runtime-pin-sync: dağılmış sürüm sabitlemelerini denetle ve senkronla.

Kütüphane arayüzü (kartta tanımlı):

    from runtime_pin_sync import tara, celiski
    pimler = tara(".")                 # list[Sabitleme]
    celiskiler = celiski(pimler)       # list[Celiski]

İngilizce takma adlar da vardır: ``scan`` == ``tara``, ``conflicts`` == ``celiski``.
"""

from __future__ import annotations

from .karsilastir import celiski
from .sabitleme import CALISMA_ZAMANLARI, Celiski, Sabitleme
from .tara import tara
from .versiyon import Aralik, AralikKumesi, spek_ayristir, kümeler_kesisir
from .yaz import Degisiklik, senkronla

__version__ = "0.1.0"

# İngilizce takma adlar
scan = tara
conflicts = celiski

__all__ = [
    "tara", "celiski", "senkronla", "Degisiklik",
    "Sabitleme", "Celiski", "Aralik", "AralikKumesi",
    "spek_ayristir", "kümeler_kesisir", "CALISMA_ZAMANLARI",
    "scan", "conflicts", "__version__",
]
