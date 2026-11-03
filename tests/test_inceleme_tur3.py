"""Tur 3 bağımsız inceleme (Codex) regresyonları — her ZORUNLU madde için.

Kapsanan maddeler: depo dışı version-file okuması, matris/adım konum karışması,
kök-dışı JSON alanına yazma, [env] vs [tools] TOML bölümü, çakışan satırın
otomatik plana geri dönmesi, çok değerli kaynak güvenliği, PEP 440/npm
karşılaştırma lehçeleri, Docker ön sürüm ve registry port ayrımı, asdf çoklu
değerleri ve tarayıcının depo sınırı.
"""

from conftest import yaz
from runtime_pin_sync import celiski, senkronla, tara
from runtime_pin_sync.bulucular import araclar, node, pin
from runtime_pin_sync.ci import is_aksi
from runtime_pin_sync.docker import (
    devcontainer,
    dockerfile,
    imaj_ad_ve_etiket,
    imaj_coz,
)
from runtime_pin_sync.versiyon import kümeler_kesisir, spek_ayristir

# --- 1. Depo dışına okuma (ci.py version-file) --------------------------------

HARICI = "GİZLİ-SIR-99\n"


def _wf(hedef: str) -> str:
    return ("jobs:\n  t:\n    steps:\n      - uses: actions/setup-node@v4\n"
            f"        with:\n          node-version-file: {hedef}\n")


def test_version_file_depo_dışına_okunamaz(tmp_path):
    (tmp_path / "gizli.txt").write_text(HARICI, encoding="utf-8")
    depo = tmp_path / "depo"
    (depo / "ci").mkdir(parents=True)
    (p,) = is_aksi("ci/.github/workflows/a.yml", _wf("../../gizli.txt"),
                   {}, str(depo))
    assert p.durum == "okunamadı"
    assert "depo sınırını aşıyor" in p.uyari
    assert "GİZLİ" not in p.uyari and "GİZLİ" not in p.ham  # içerik sızmadı
    # mutlak hedef de reddedilir
    (q,) = is_aksi("w/a.yml", _wf("/etc/passwd"), {}, str(depo))
    assert q.durum == "okunamadı"


def test_version_file_symlink_hedefi_reddedilir(tmp_path):
    (tmp_path / "gizli.txt").write_text(HARICI, encoding="utf-8")
    depo = tmp_path / "depo"
    (depo / "ci").mkdir(parents=True)
    try:
        (depo / "ci" / "nvm").symlink_to(tmp_path / "gizli.txt")
    except OSError:
        import pytest
        pytest.skip("symlink desteklenmiyor")
    (p,) = is_aksi("w/a.yml", _wf("ci/nvm"), {}, str(depo))
    assert p.durum == "okunamadı" and "GİZLİ" not in (p.uyari or "") + p.ham


def test_version_file_depo_içi_okunmaya_devam(tmp_path):
    (tmp_path / "nodemiz").write_text("20\n", encoding="utf-8")
    pimler = is_aksi("w/a.yml", _wf("nodemiz"), {}, str(tmp_path))
    assert [(p.dosya, p.ham) for p in pimler] == [("nodemiz", "20")]


# --- 2. Matris satırı adım girdisi konumu olamaz (ci.py) -----------------------

MATRİS_WF = ("jobs:\n"
             "  t:\n"
             "    strategy:\n"
             "      matrix:\n"
             "        node-version: [22, 24]\n"
             "    steps:\n"
             "      - uses: actions/setup-node@v4\n"
             "        with:\n"
             "          node-version: 22\n")


def test_matris_satırı_adım_girdisinin_konumu_olamaz():
    pimler = is_aksi("w/ci.yml", MATRİS_WF)
    adım = next(p for p in pimler if p.tur == "ci-adim")
    ızgara = next(p for p in pimler if p.tur == "ci-matriks")
    assert adım.satir == 9      # gerçek `with:` girdi satırı
    assert ızgara.satir is None  # ızgaranın tek satır hedefi olmaz


def test_sync_matrisi_değiştirip_adımı_olduğu_gibi_bırakamaz(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20\n")
    yaz(tmp_path, ".github/workflows/ci.yml", MATRİS_WF)
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert {(d.dosya, d.satir, d.eski, d.yeni) for d in otomatik} == \
        {(".github/workflows/ci.yml", 9, "22", "20")}
    assert elle  # ızgara satırı elle listededir
    uygulan, _ = senkronla(tmp_path, ".tool-versions", False)
    assert uygulan
    satirlar = (tmp_path / ".github/workflows/ci.yml").read_text(
        encoding="utf-8").splitlines()
    assert satirlar[8] == "          node-version: 20"    # ADIM yazıldı
    assert satirlar[4] == "        node-version: [22, 24]"  # MATRİS DOKUNULMADI


def test_tekrarlanan_iki_adım_kendi_satırına_bağlanır(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20\n")
    yaz(tmp_path, ".github/workflows/ci.yml",
        "jobs:\n  t:\n    steps:\n"
        "      - uses: actions/setup-node@v4\n"
        "        with:\n          node-version: 22\n"
        "      - uses: actions/setup-node@v4\n"
        "        with:\n          node-version: 22\n")
    pimler = [p for p in tara(tmp_path) if p.tur == "ci-adim"]
    assert [(p.satir, p.tüm_satırlar) for p in pimler] == [(6, (6, 9))]
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle == []
    assert {d.satir for d in otomatik} == {6, 9}  # İKİ gerçek konum da yazılır


# --- 3. Kök-dışı JSON alanına yazma (node.py) ----------------------------------

KARIŞIK_PKG = ('{\n'
               '  "custom": {"engines": {"node": "22"}},\n'
               '  "engines": {"node": "22"}\n'
               '}\n')


def test_engines_konumu_yalnız_kök_alandan():
    (p,) = node.package_json("package.json", KARIŞIK_PKG)
    assert p.satir == 3  # custom.engines DEĞİL, kök engines


def test_sync_custom_engines_alağı_dokunulmaz(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "package.json", KARIŞIK_PKG)
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle == []
    assert {d.satir for d in otomatik} == {3}
    icerik = (tmp_path / "package.json").read_text(encoding="utf-8")
    assert '"custom": {"engines": {"node": "22"}}' in icerik
    assert '"engines": {"node": "20.11.0"}' in icerik


def test_engines_birden_faazla_kök_alanda_belirsizlik_yoktur():
    # kökte tek "engines" varsa yazılır; nested tuzaklar konumu bozmaz
    (p,) = node.package_json("p.json", '{"scripts": {"node": "x"},\n'
                             ' "engines": {"node": "22"}}\n')
    assert p.satir == 2


# --- 4. Yanlış TOML bölümüne yazma (mise [env] vs [tools]) ---------------------

MISE_ENV = '[env]\nnode = "22"\n[tools]\nnode = "22"\n'


def test_mise_konumu_tools_bölümüne_bağlı():
    pimler = araclar.mise("mise.toml", MISE_ENV)
    somut = [p for p in pimler if p.kullanilabilir and p.ham == "22"]
    assert [p.satir for p in somut] == [4]


def test_sync_mise_env_satırına_dokunmaz(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "mise.toml", MISE_ENV)
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle == [] and {d.satir for d in otomatik} == {4}
    satirlar = (tmp_path / "mise.toml").read_text(encoding="utf-8").splitlines()
    assert satirlar[1] == 'node = "22"'          # [env] AYNEN
    assert satirlar[3] == 'node = "20.11.0"'     # [tools] yazıldı


def test_mise_anahtarsız_bölümde_belirsizlik_conumu_yok():
    # [tools] içinde tam anahtar satırı YOKSA (örn. inline tablo) konum=None
    pimler = araclar.mise("mise.toml", 'tools = { node = "22" }\n')
    assert all(p.satir is None for p in pimler)


# --- 5. Çakışan satır otomatik plana geri dönemez (yaz.py) ---------------------

def test_üçüncü_hedef_otomatik_plana_dönemez(tmp_path):
    yaz(tmp_path, ".tool-versions", "python 3.12.1\n")
    yaz(tmp_path, "mise.toml", '[tools]\npython = ["3.9", "3.10", "3.11"]\n')
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []  # ilk iki elle'ye gitti diye ÜÇÜNCÜ yazILMAZ
    assert len(elle) == 3
    assert all("aynı satırda birden fazla hedef" in d.gerekce for d in elle)


# --- 6. Çok değerli kaynak: ilk üye otomatik yazılmaz (karsilastir.py) ---------

def test_çok_değerli_kaynak_ilk_üyeyi_referans_yapmaz(tmp_path):
    yaz(tmp_path, "mise.toml", '[tools]\nnode = ["22", "24"]\n')
    yaz(tmp_path, ".nvmrc", "20\n")
    (c,) = celiski(tara(tmp_path), kaynak="mise.toml")
    assert c.referans_ham == "22, 24"  # ilk üye DEĞİL, birleşim
    otomatik, elle = senkronla(tmp_path, "mise.toml", False)
    assert otomatik == []
    assert elle and "sabit sürüm değil" in elle[0].gerekce
    assert (tmp_path / ".nvmrc").read_text(encoding="utf-8") == "20\n"


# --- 7. Python vs Node karşılaştırma lehçeleri (versiyon.py) -------------------

def kesis(a, b, semver=False):
    x, y = spek_ayristir(a, semver=semver), spek_ayristir(b, semver=semver)
    return x is not None and y is not None and kümeler_kesisir(x, y)


def test_pep440_yıldızlı_eşitlik_önek_gibidir():
    assert kesis("==3.12.*", "3.12.1")   # PEP 440 wildcard: eşleşmeli
    assert kesis("==3.12.*", "3.12.9")
    assert not kesis("==3.12.*", "3.13.0")
    assert not kesis("==3.12", "3.12.1")  # yıldızsız: tam değer (değişmedi)


def test_node_büyük_işaretçisi_seri_dışlar_npm_semantiği():
    assert not kesis(">20", "20.1.0", semver=True)  # >20 == >=21.0.0
    assert kesis(">20", "21.0.0", semver=True)
    assert kesis(">20.1", "20.2.0", semver=True)    # >20.1 == >=20.2.0
    assert not kesis(">20.1", "20.1.9", semver=True)
    assert kesis(">20.1.0", "20.1.1", semver=True)  # tam sürüm: dar anlam


def test_node_küçük_eşit_seri_içerir():
    assert kesis("<=20", "20.9.9", semver=True)     # <=20 == <21.0.0
    assert not kesis("<=20", "21.0.0", semver=True)


def test_python_lehçesi_dar_kalır():
    assert kesis(">20", "20.1.0")            # PEP 440: 20.1.0 > 20.0 ✓
    assert not kesis("<=3.12", "3.12.1")     # PEP 440 dar (değişmedi)


def test_pim_lehçe_seçimi_çalışma_zamanından():
    n1 = pin("node", "a", "ci-adim", "20.1.0")
    n2 = pin("node", "b", "ci-adim", ">20")
    assert not kümeler_kesisir(n1.aralik, n2.aralik)  # npm: çelişki
    p1 = pin("python", "a", "requires-python", "20.1.0")
    p2 = pin("python", "b", "requires-python", ">20")
    assert kümeler_kesisir(p1.aralik, p2.aralik)      # PEP: uyumlu


# --- 8. Docker: ön sürüm indirgenmez, registry portu kaybolmaz -----------------

def test_docker_ön_sürüm_kararlıya_indirgenmez():
    (p,) = dockerfile("Dockerfile", "FROM node:22-rc1\n")
    assert p.durum == "okunamadı" and "ön sürüm" in p.uyari
    assert p.ham == "22-rc1" and p.aralik is None
    # kararlı .nvmrc ile SAHTE çelişki/uyum ÜRETMEZ (karşılaştırma dışı)
    from runtime_pin_sync.bulucular.node import surum_dosyasi
    assert celiski([p, *surum_dosyasi(".nvmrc", "22\n")]) == []


def test_docker_bilinen_sonek_sürümü_korur():
    (p,) = dockerfile("Dockerfile", "FROM python:3.12-slim-bookworm\n")
    assert p.ham == "3.12" and p.kullanilabilir


def test_docker_bilinmeyen_sonek_uyarıyla_dışarıda():
    (p,) = dockerfile("Dockerfile", "FROM node:22-sucuk\n")
    assert p.durum == "okunamadı" and "sonek" in p.uyari


def test_registry_portlu_imaj_okunur():
    (p,) = dockerfile("Dockerfile", "FROM registry.example:5000/node:22\n")
    assert (p.calisma_zamani, p.ham, p.satir) == ("node", "22", 1)
    assert imaj_ad_ve_etiket("registry.example:5000/node") == \
        ("registry.example:5000/node", "")
    assert imaj_ad_ve_etiket("registry.example:5000/node:22") == \
        ("registry.example:5000/node", "22")
    assert imaj_coz("registry.example:5000/node", "22") == ("node", "22")


def test_devcontainer_registry_portlu_imaj():
    pimler = devcontainer("d.json", '{"image": "registry.local:5000/python:3.12"}')
    assert [(p.calisma_zamani, p.ham) for p in pimler] == [("python", "3.12")]


def test_registry_portlu_imaj_ile_adım_çelişir(tmp_path):
    # portlu kaynak artık GÖRÜNÜR: .nvmrc 20 ile gerçek çelişki raporlanır
    yaz(tmp_path, ".nvmrc", "20\n")
    yaz(tmp_path, "Dockerfile", "FROM registry.example:5000/node:22\n")
    (c,) = celiski(tara(tmp_path))
    assert c.calisma_zamani == "node"
    assert {p.dosya for p in c.dislananlar} | {c.referans_dosya} == \
        {".nvmrc", "Dockerfile"}


# --- 9. asdf çoklu değerler (.tool-versions) ------------------------------------

def test_tool_versions_çoklu_değerler_birleşim_olur():
    pimler = araclar.tool_versions(".tool-versions", "python 3.12.1 3.11.8\n")
    (p,) = pimler
    assert p.ham == "3.12.1, 3.11.8" and p.kullanilabilir
    assert not p.aralik.sabit  # ızgara: tek hedefe indirgenemez


def test_tool_versions_çoklu_ikinci_üye_ile_çelişmez():
    pimler = araclar.tool_versions(".tool-versions", "python 3.12.1 3.11.8\n")
    from runtime_pin_sync.bulucular.python import surum_dosyasi
    digeri = surum_dosyasi(".python-version", "3.11.8\n")
    assert celiski([*pimler, *digeri]) == []  # 3.11.8 kurulu — çelişki DEĞİL
    from runtime_pin_sync.bulucular.python import surum_dosyasi as sd
    assert len(celiski([*pimler, *sd(".python-version", "3.10.4\n")])) == 1


# --- 10. Tarayıcının depo sınırı (tara.py) — test_yaz.py'deki symlink testi ----
