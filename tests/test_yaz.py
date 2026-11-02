"""senkronla testleri — kabul ölçütü 3: diff yalnız hedef satırı gösterir."""

from runtime_pin_sync import celiski, senkronla, tara
from conftest import yaz


def depo_kur(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, ".nvmrc", "22\n")
    yaz(tmp_path, "Dockerfile", "FROM node:22 AS base\nWORKDIR /app\n")
    yaz(tmp_path, "package.json",
        '{"engines": {"node": ">=18"}}\n')
    return tmp_path


def test_kabul3_dry_run_dosyaları_değiştirmez(tmp_path):
    depo = depo_kur(tmp_path)
    önce = {p: (depo / p).read_bytes() for p in
            (".tool-versions", ".nvmrc", "Dockerfile", "package.json")}
    otomatik, elle = senkronla(depo, ".tool-versions", kuru_calis=True)
    sonra = {p: (depo / p).read_bytes() for p in önce}
    assert sonra == önce                       # bit bit aynı
    assert {(d.dosya, d.eski, d.yeni) for d in otomatik} == {
        (".nvmrc", "22", "20.11.0"), ("Dockerfile", "22", "20.11.0")}
    assert elle == []
    # plan boş değil mi? iki hedef satır
    assert len(otomatik) == 2


def test_kabul3_gerçek_sync_yalnız_hedef_satır(tmp_path):
    depo = depo_kur(tmp_path)
    docker_önce = (depo / "Dockerfile").read_text(encoding="utf-8").splitlines()
    senkronla(depo, ".tool-versions", kuru_calis=False)
    assert (depo / ".nvmrc").read_text(encoding="utf-8") == "20.11.0\n"
    docker_sonra = (depo / "Dockerfile").read_text(encoding="utf-8").splitlines()
    assert docker_sonra[0] == "FROM node:20.11.0 AS base"
    assert docker_sonra[1] == docker_önce[1]     # diğer satırlar aynen duruyor
    # senkron sonrası çelişki kalmaz (engines aralığı zaten uyumlu)
    assert celiski(tara(depo)) == []


def test_kaynak_olmayansa_hata(tmp_path):
    depo = depo_kur(tmp_path)
    import pytest
    with pytest.raises(ValueError, match="kaynak bulunamadı"):
        senkronla(depo, "yok-boyle", kuru_calis=True)


def test_aralık_hedef_elle_düzeltmeye_gider(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "package.json", '{"engines": {"node": ">=22"}}\n')
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []
    assert elle[0].dosya == "package.json"
    assert "aralık" in elle[0].gerekce


def test_şablonlu_dockerfile_elle_gider(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "Dockerfile", "ARG TAG=22-slim\nFROM node:${TAG}\n")
    # FROM çözülünce 22 çıkar; satırda "22" şablonun içinde → tek başına değil
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []
    assert elle[0].dosya == "Dockerfile"


def test_aynı_satıra_iki_hedef_elle_gider(tmp_path):
    # mise listesindeki iki python sürümü AYNI satırda: ikisi de dışlanırsa
    # tek satıra iki hedef düşer → güvenli değil, elle listelenir
    yaz(tmp_path, ".tool-versions", "python 3.12.1\n")
    yaz(tmp_path, "mise.toml", '[tools]\npython = ["3.9", "3.10"]\n')
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []
    assert len(elle) == 2
    assert all("aynı satırda birden fazla hedef" in d.gerekce for d in elle)
    assert (tmp_path / "mise.toml").read_text(encoding="utf-8") == \
        '[tools]\npython = ["3.9", "3.10"]\n'


def test_uygulanamayan_değişiklik_elle_düşer(tmp_path, monkeypatch):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, ".nvmrc", "22\n")
    from runtime_pin_sync import yaz as yaz_modul

    def patlayan(_kok, _d, _dosya):
        raise OSError("sahte disk hatası")

    monkeypatch.setattr(yaz_modul, "_uygula", patlayan)
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert otomatik == []
    assert "uygulanamadı" in elle[-1].gerekce
    assert "sahte disk hatası" in elle[-1].gerekce


def test_senkronla_dry_run_sonra_gerçek_aynı_plani_verir(tmp_path):
    depo = depo_kur(tmp_path)
    plan, _ = senkronla(depo, ".tool-versions", True)
    uygulan, _ = senkronla(depo, ".tool-versions", False)
    assert {(d.dosya, d.satir, d.eski, d.yeni) for d in plan} == \
           {(d.dosya, d.satir, d.eski, d.yeni) for d in uygulan}


def test_token_satırda_tek_değilse_yazmaz(tmp_path):
    from runtime_pin_sync.yaz import _token_degistir
    assert _token_degistir("FROM node:22\n", "22", "20") == "FROM node:20\n"
    assert _token_degistir("FROM node:22 AS 22\n", "22", "20") is None
    assert _token_degistir("FROM node:222\n", "22", "20") is None
    assert _token_degistir("x: 3.12\n", "3.1", "3.2") is None


def test_norm_yol():
    from runtime_pin_sync.yaz import norm_yol
    assert norm_yol("./.tool-versions") == ".tool-versions"
    assert norm_yol("alt\\.nvmrc") == "alt/.nvmrc"
    assert norm_yol("/x") == "x"
