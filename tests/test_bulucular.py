"""Bulucu birim testleri: her dosya biçimi + hata yolları."""

from runtime_pin_sync.bulucular import araclar, go, java, node, python, rust


def durumlar(pimler):
    return [(p.ham, p.durum) for p in pimler]


# --- Node ---------------------------------------------------------------

def test_nvmrc_sabit():
    (p,) = node.surum_dosyasi(".nvmrc", "20.11.0\n")
    assert p.ham == "20.11.0" and p.kullanilabilir and p.satir == 1


def test_nvmrc_lts_takma_adlari_tuzak():
    (p,) = node.surum_dosyasi(".nvmrc", "lts/iron\n")
    assert p.ham == "20" and p.kullanilabilir
    (h,) = node.surum_dosyasi(".nvmrc", "lts/hydrogen\n")
    assert h.ham == "18" and h.kullanilabilir  # Hydrogen 18'dir, 16 DEĞİL
    (g,) = node.surum_dosyasi(".nvmrc", "lts/gallium\n")
    assert g.ham == "16"
    (y,) = node.surum_dosyasi(".nvmrc", "lts/*\n")
    assert y.dinamik and not y.kullanilabilir  # hareketli alias: tahmin YOK
    (b,) = node.surum_dosyasi(".nvmrc", "lts/uzayli\n")
    assert b.dinamik and not b.kullanilabilir  # tahmin YOK


def test_nvmrc_yorum_ve_bos():
    (p,) = node.surum_dosyasi(".nvmrc", "# yorum\n22\n")
    assert p.ham == "22" and p.satir == 2
    (b,) = node.surum_dosyasi(".nvmrc", "\n\n")
    assert b.durum == "okunamadı"


def test_package_json_engines():
    icerik = '{"engines": {"node": ">=18 <21"}}\n'
    (p,) = node.package_json("package.json", icerik)
    assert p.ham == ">=18 <21" and p.kullanilabilir and p.satir == 1


def test_package_json_engines_yok():
    assert node.package_json("p.json", '{"name": "x"}') == []


def test_package_json_bozuk_hata_vermez():
    (p,) = node.package_json("p.json", "{bozuk json")
    assert p.durum == "okunamadı"
    (d,) = node.package_json("p.json", "[1,2]")
    assert d.durum == "okunamadı"
    (e,) = node.package_json("p.json", '{"engines": {"node": 20}}')
    assert e.durum == "okunamadı"


# --- Python -------------------------------------------------------------

def test_python_version_dosyasi():
    (p,) = python.surum_dosyasi(".python-version", "3.12.1\n")
    assert p.ham == "3.12.1" and p.satir == 1
    (b,) = python.surum_dosyasi(".python-version", "")
    assert b.durum == "okunamadı"


def test_pyproject_requires_python():
    icerik = '[project]\nname = "x"\nrequires-python = ">=3.10"\n'
    (p,) = python.pyproject("pyproject.toml", icerik)
    assert p.ham == ">=3.10" and p.satir == 3


def test_pyproject_yoksa_sessiz():
    assert python.pyproject("pyproject.toml", '[project]\nname = "x"\n') == []


def test_pyproject_bozuk():
    (p,) = python.pyproject("pyproject.toml", "bu toml değil [[[\n")
    assert p.durum == "okunamadı"
    (t,) = python.pyproject("pyproject.toml", '[project]\nrequires-python = 42\n')
    assert t.durum == "okunamadı"


# --- Go / Rust / Java -----------------------------------------------------

def test_go_mod():
    icerik = "module örnek\n\ngo 1.22.3\n\ntoolchain go1.22.5\n"
    pimler = go.gomod("go.mod", icerik)
    assert [(p.tur, p.ham) for p in pimler] == [("gomod", "1.22.3"),
                                                ("gomod-toolchain", "1.22.5")]


def test_go_directifi_minimum_gereksinimdir_toolchain_ile_çelişmez():
    # go.dev/doc/modules/gomod-ref#go: `go` = minimum, toolchain daha yeni OLUR.
    icerik = "module x\n\ngo 1.22\n\ntoolchain go1.23.1\n"
    pimler = go.gomod("go.mod", icerik)
    assert all(p.kullanilabilir for p in pimler)
    from runtime_pin_sync import celiski
    assert celiski(list(pimler)) == []
    gomod_pim = pimler[0]
    assert gomod_pim.aralik is not None
    assert not gomod_pim.aralik.sabit  # açık üst uç: sabitleme/referans değil


def test_go_minimum_toolchain_altında_ise_çelişkidir():
    # go 1.24 = minimum gereksinim; toolchain go1.23.1 bunun ALTINDA → gerçek
    # çelişki raporlanır (araç bu dosyayla 1.23'ü hiç çalıştıramaz).
    icerik = "module x\n\ngo 1.24\n\ntoolchain go1.23.1\n"
    pimler = go.gomod("go.mod", icerik)
    from runtime_pin_sync import celiski
    assert len(celiski(list(pimler))) == 1


def test_go_mod_satirsiz():
    (p,) = go.gomod("go.mod", "module x\n")
    assert p.durum == "okunamadı"


def test_go_version_dosyasi():
    (p,) = go.surum_dosyasi(".go-version", "1.22\n")
    assert p.ham == "1.22"
    (b,) = go.surum_dosyasi(".go-version", "\n")
    assert b.durum == "okunamadı"


def test_rust_kanal_dosyasi():
    (p,) = rust.kanal_dosyasi("rust-toolchain", "1.84.0\n")
    assert p.ham == "1.84.0"
    (s,) = rust.kanal_dosyasi("rust-toolchain", "stable\n")
    assert s.dinamik  # "stable" bir sürüm değildir
    (t,) = rust.kanal_dosyasi("rust-toolchain", "1.84.0-x86_64-unknown-linux-gnu\n")
    assert t.ham == "1.84.0"


def test_rust_toml():
    (p,) = rust.kanal_toml("rust-toolchain.toml", '[toolchain]\nchannel = "1.85.0"\n')
    assert p.ham == "1.85.0" and p.satir == 2
    assert rust.kanal_toml("rust-toolchain.toml", "[other]\nx = 1\n") == []
    (b,) = rust.kanal_toml("rust-toolchain.toml", "[[[" * 10)
    assert b.durum == "okunamadı"
    (t,) = rust.kanal_toml("rust-toolchain.toml", '[toolchain]\nchannel = true\n')
    assert t.durum == "okunamadı"
    (e,) = rust.kanal_dosyasi("rust-toolchain", "\n")
    assert e.durum == "okunamadı"


def test_rust_ön_sürüm_kararlıya_çevrilmez():
    # 1.85.0-rc1 KULLANILABİLİR 1.85.0 OLAMAZ: karşılaştırmaya girmez, uyarır.
    (p,) = rust.kanal_dosyasi("rust-toolchain", "1.85.0-rc1\n")
    assert p.ham == "1.85.0-rc1"
    assert not p.kullanilabilir and not p.aralik
    assert p.uyari and "ön sürüm" in p.uyari
    (q,) = rust.kanal_toml("rust-toolchain.toml",
                           '[toolchain]\nchannel = "1.85.0-beta.3"\n')
    assert q.ham == "1.85.0-beta.3" and not q.kullanilabilir
    # hedef üçlüsü ise eskisi gibi sürüme indirgenir:
    (t,) = rust.kanal_dosyasi("rust-toolchain",
                              "1.84.0-aarch64-apple-darwin\n")
    assert t.ham == "1.84.0" and t.kullanilabilir


def test_java():
    (p,) = java.surum_dosyasi(".java-version", "21\n")
    assert p.ham == "21"
    (b,) = java.surum_dosyasi(".java-version", "")
    assert b.durum == "okunamadı"
    pom = ("<project>\n  <properties>\n"
           "    <maven.compiler.release>17</maven.compiler.release>\n"
           "    <java.version>${java.home}</java.version>\n"
           "  </properties>\n</project>\n")
    pimler = java.pom("pom.xml", pom)
    assert durumlar(pimler) == [("17", "okundu"),
                                ("${java.home}", "dinamik, atlandı")]
    assert pimler[0].kullanilabilir


def test_java_pom_dinamik():
    (p,) = java.pom("pom.xml", "<java.version>${env.JV}</java.version>\n")
    assert p.dinamik
    assert java.pom("pom.xml", "<project/>") == []


# --- Araç yöneticileri ------------------------------------------------------

def test_tool_versions():
    icerik = ("node 20.11.0 # LTS\n"
              "python 3.12.1\n"
              "golang 1.22.3\n"
              "ruby 3.3.0\n"
              "java latest\n"
              "bozuk satır\n")
    pimler = araclar.tool_versions(".tool-versions", icerik)
    assert [(p.calisma_zamani, p.ham) for p in pimler] == [
        ("node", "20.11.0"), ("python", "3.12.1"), ("go", "1.22.3"),
        ("java", "latest"),
    ]
    assert pimler[-1].dinamik  # 'latest' sürüm değildir


def test_mise():
    icerik = ('[tools]\nnode = "22.11.0"\npython = ["3.11", "${{ env.PY }}"]\n'
              'golang = "latest"\ndeneme = "1.2.3"\n')
    pimler = araclar.mise("mise.toml", icerik)
    assert any(p.ham == "22.11.0" and p.kullanilabilir for p in pimler)
    assert sum(1 for p in pimler if p.calisma_zamani == "python"
               and p.kullanilabilir) == 1  # yalnız "3.11" somut
    assert any(p.ham == "3.11" and p.satir == 3 for p in pimler)
    assert any(p.ham == "${{ env.PY }}" and p.dinamik for p in pimler)
    assert any(p.ham == "latest" and p.dinamik for p in pimler)
    assert all(p.calisma_zamani != "deneme" for p in pimler)  # bilinmeyen araç yok


def test_mise_bozuk_ve_araçsız():
    (p,) = araclar.mise("mise.toml", "x = = = 3\n")
    assert p.durum == "okunamadı"
    assert araclar.mise("mise.toml", '[settings]\nquiet = true\n') == []
    assert araclar.mise("mise.toml", '[tools]\nnode = ""\n') == []
