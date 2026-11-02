"""Dockerfile ve devcontainer.json okuma testleri."""

from runtime_pin_sync.docker import devcontainer, dockerfile, imaj_coz


def test_simple_from():
    (p,) = dockerfile("Dockerfile", "FROM node:22\n")
    assert (p.calisma_zamani, p.ham, p.satir) == ("node", "22", 1)


def test_multi_stage_ve_takema_ad():
    icerik = ("FROM node:20 AS derleme\n"
              "RUN yap\n"
              "FROM python:3.12-slim AS servis\n"
              "COPY --from=derleme /a /b\n"
              "FROM derleme\n")
    pimler = dockerfile("Dockerfile", icerik)
    assert [(p.calisma_zamani, p.ham) for p in pimler] == [("node", "20"),
                                                           ("python", "3.12")]
    # "FROM derleme" yeni bir imaj sabitlemesi ÜRETMEZ


def test_arg_varsayilani_cozulur():
    icerik = "ARG NODE_VERSION=20\nFROM node:${NODE_VERSION} AS a\n"
    (p,) = dockerfile("Dockerfile", icerik)
    assert p.ham == "20" and p.kullanilabilir


def test_arg_cozulemezse_dinamik():
    icerik = "ARG TAG\nFROM node:${TAG}\n"
    (p,) = dockerfile("Dockerfile", icerik)
    assert p.dinamik and not p.uyari  # uyarı değil, hata hiç değil


def test_etiketsiz_ve_latest_dinamik():
    pimler = dockerfile("Dockerfile", "FROM node\nFROM python:latest\n")
    assert len(pimler) == 2 and all(p.dinamik for p in pimler)


def test_takip_edilmeyen_imaj_sessiz():
    assert dockerfile("Dockerfile", "FROM ubuntu:24.04\nFROM alpine\n") == []


def test_platform_bayragi():
    (p,) = dockerfile("Dockerfile", "FROM --platform=linux/amd64 golang:1.23 AS b\n")
    assert (p.calisma_zamani, p.ham) == ("go", "1.23")


def test_java_ımajları():
    (p,) = dockerfile("Dockerfile", "FROM eclipse-temurin:17-jre\n")
    assert (p.calisma_zamani, p.ham) == ("java", "17")


def test_imaj_coz_sınır_durumları():
    assert imaj_coz("mcr.microsoft.com/devcontainers/python", "3.12") == ("python", "3.12")
    assert imaj_coz("node", "latest") == ("node", "")
    assert imaj_coz("hayvan/kedi", "1.0") == (None, "")


def test_devcontainer_image_ve_features():
    icerik = """
{
  // yorum: jsonc tolere edilir
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "22.11.0" },
    "ghcr.io/devcontainers/features/go:1": "1.23",
    "ghcr.io/devcontainers/features/github-cli:1": {},
    "ghcr.io/devcontainers/features/rust:1": { "version": "os-provided" }
  }
}
"""
    pimler = devcontainer(".devcontainer/devcontainer.json", icerik)
    found = {(p.calisma_zamani, p.ham, p.durum) for p in pimler}
    assert ("python", "3.12", "okundu") in found
    assert ("node", "22.11.0", "okundu") in found
    assert ("go", "1.23", "okundu") in found
    assert ("rust", "os-provided", "dinamik, atlandı") in found
    assert not any(p.calisma_zamani == "github-cli" for p in pimler)


def test_devcontainer_takip_edilmeyen_imaj():
    assert devcontainer(".devcontainer/devcontainer.json",
                        '{"image": "debian:bookworm"}') == []


def test_devcontainer_bozuk_json():
    (p,) = devcontainer(".devcontainer/devcontainer.json", '{"image": ')
    assert p.durum == "okunamadı"
    (d,) = devcontainer(".devcontainer/devcontainer.json", "[1, 2]")
    assert d.durum == "okunamadı"


def test_devcontainer_features_duz_metin():
    pimler = devcontainer("d.json", '{"features": {"java": "21"}}')
    assert pimler[0].ham == "21" and pimler[0].kullanilabilir
