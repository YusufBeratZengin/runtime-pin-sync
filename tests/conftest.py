import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ornek-depolar"))

ORNEK_KOK = Path(__file__).resolve().parent.parent / "ornek-depolar"


@pytest.fixture
def uyumsuz():
    return ORNEK_KOK / "uyumsuz"


@pytest.fixture
def tutarli():
    return ORNEK_KOK / "tutarli"


@pytest.fixture
def bozuk():
    return ORNEK_KOK / "bozuk"


def yaz(kok: Path, goreli: str, icerik: str) -> Path:
    """tmp_path içine göreli yolda dosya oluştur."""
    tam = kok / goreli
    tam.parent.mkdir(parents=True, exist_ok=True)
    tam.write_text(icerik, encoding="utf-8")
    return tam
