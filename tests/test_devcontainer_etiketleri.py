"""Devcontainer tags whose leading number is the runtime major, not a generation."""

import pytest

from runtime_pin_sync.docker import imaj_coz

MCR = "mcr.microsoft.com/devcontainers/"


@pytest.mark.parametrize(
    ("ad", "etiket", "beklenen"),
    [
        (MCR + "javascript-node", "22", ("node", "22")),
        (MCR + "javascript-node", "22-bookworm", ("node", "22")),
        (MCR + "typescript-node", "20", ("node", "20")),
        (MCR + "python", "3", ("python", "3")),
        (MCR + "python", "3-bookworm", ("python", "3")),
        (MCR + "python", "1-3.12-bookworm", ("python", "3.12")),
        (MCR + "javascript-node", "1-20-bookworm", ("node", "20")),
    ],
)
def test_runtime_major_tags_are_still_read(ad, etiket, beklenen):
    assert imaj_coz(ad, etiket) == beklenen


@pytest.mark.parametrize("etiket", ["1", "2", "1-bookworm", "2-bullseye"])
def test_generation_only_tags_stay_unknown(etiket):
    assert imaj_coz(MCR + "python", etiket) == ("python", "")
