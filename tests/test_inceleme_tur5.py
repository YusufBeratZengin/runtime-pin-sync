"""Nesil etiketi Python sürümü değildir; gerçek sürümler karşılaştırılır."""

import pytest

from conftest import yaz
from runtime_pin_sync import celiski, tara
from runtime_pin_sync.cli import main
from runtime_pin_sync.docker import devcontainer, dockerfile, imaj_coz


@pytest.mark.parametrize("etiket", ["1-bookworm", "1", "2-bookworm", "1-bullseye", "latest"])
@pytest.mark.parametrize("lang", ["tr", "en"])
def test_devcontainer_nesil_ve_bilinmeyen_etiket_celiski_uretmez(tmp_path, etiket, lang, capsys):
    imaj = f"mcr.microsoft.com/devcontainers/python:{etiket}"
    yaz(tmp_path, ".python-version", "3.12.1\n")
    yaz(tmp_path, "devcontainer.json", f'{{"image": "{imaj}"}}')
    yaz(tmp_path, "Dockerfile", f"FROM {imaj}\n")

    assert celiski(tara(tmp_path)) == []
    assert imaj_coz("mcr.microsoft.com/devcontainers/python", etiket) == ("python", "")
    (dc,) = devcontainer("devcontainer.json", f'{{"image": "{imaj}"}}', lang=lang)
    (df,) = dockerfile("Dockerfile", f"FROM {imaj}\n", lang=lang)
    assert not dc.kullanilabilir
    assert not df.kullanilabilir
    assert main([str(tmp_path), "--lang", lang]) == 0
    cikti = capsys.readouterr().out
    if etiket != "latest":
        uyari = (
            "could not read: runtime version unknown in devcontainer generation tag"
            if lang == "en" else "okunamadı: devcontainer nesil etiketinde sürüm bilinmiyor"
        )
        assert dc.uyari == df.uyari == f"{uyari} ({etiket})"
        assert uyari in cikti


@pytest.mark.parametrize(
    ("ad", "etiket"),
    [
        ("mcr.microsoft.com/devcontainers/python", "1-3.12-bookworm"),
        ("mcr.microsoft.com/devcontainers/python", "3.12"),
        ("mcr.microsoft.com/devcontainers/python", "3.12-bookworm"),
        ("python", "3.12"),
    ],
)
def test_python_gercek_imaj_surumu_karsilastirilir(tmp_path, ad, etiket):
    assert imaj_coz(ad, etiket) == ("python", "3.12")
    yaz(tmp_path, "devcontainer.json", f'{{"image": "{ad}:{etiket}"}}')
    yaz(tmp_path, ".python-version", "3.12.1\n")
    assert celiski(tara(tmp_path)) == []
    yaz(tmp_path, ".python-version", "3.11.9\n")
    assert len(celiski(tara(tmp_path))) == 1
    assert main([str(tmp_path)]) == 1


def test_devcontainer_oneksiz_gercek_celiski_exit_bir(tmp_path):
    yaz(tmp_path, ".python-version", "3.12.1\n")
    yaz(tmp_path, "devcontainer.json",
        '{"image": "mcr.microsoft.com/devcontainers/python:3.11-bookworm"}')
    assert imaj_coz("mcr.microsoft.com/devcontainers/python",
                    "3.11-bookworm") == ("python", "3.11")
    assert len(celiski(tara(tmp_path))) == 1
    assert main([str(tmp_path)]) == 1
