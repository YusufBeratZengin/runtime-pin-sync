"""senkronla testleri — kabul ölçütü 3: diff yalnız hedef satırı gösterir."""

from conftest import yaz
from runtime_pin_sync import celiski, senkronla, tara


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


def test_aynı_satıra_iki_hedef_elle_gider(tmp_path, monkeypatch):
    # Savunma kuralı: iki ayrı sabitleme aynı satırı hedefliyorsa hiçbiri
    # otomatik yazılmaz (hangi değerin kalacağı belirsiz).
    from runtime_pin_sync import yaz as yaz_modul
    from runtime_pin_sync.bulucular import pin
    from runtime_pin_sync.sabitleme import Celiski

    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    # iki farklı belirteç AYNI satırda dursun ki ikisi de yazılabilir görünsün
    yaz(tmp_path, "surumler.txt", "22 24\n")
    p1 = pin("node", "surumler.txt", "tool-versions", "22", satir=1)
    p2 = pin("node", "surumler.txt", "tool-versions", "24", satir=1)
    monkeypatch.setattr(
        yaz_modul, "celiski",
        lambda *a, **k: [Celiski("node", "surumler.txt", "20.11.0", [p1, p2])])
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []
    assert len(elle) == 2
    assert all("aynı satırda birden fazla hedef" in d.gerekce for d in elle)


def test_mise_listesi_tek_elle_kaydı_üretir(tmp_path):
    # Liste birleşim olarak TEK pimdir: iki üye için iki ayrı hedef uydurulmaz.
    yaz(tmp_path, ".tool-versions", "python 3.12.1\n")
    yaz(tmp_path, "mise.toml", """[tools]
python = ["3.9", "3.10"]
""")
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []
    (kayit,) = elle
    assert kayit.dosya == "mise.toml" and kayit.satir == 2
    assert "ızgara" in kayit.gerekce
    assert (tmp_path / "mise.toml").read_text(encoding="utf-8") == """[tools]
python = ["3.9", "3.10"]
"""


def test_uygulanamayan_değişiklik_elle_düşer(tmp_path, monkeypatch):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, ".nvmrc", "22\n")
    from runtime_pin_sync import yaz as yaz_modul

    def patlayan(*_args, **_kwargs):
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


# --- regresyon: yanlış alanı yazma (node.py / ci.py konum tuzakları) ----------

def test_engines_karıştıran_package_json_doğru_satırı_yazar(tmp_path):
    # dependencies.node da "22": eskiden ilk eşleşme (dependencies) seçilirdi.
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "package.json",
        '{\n  "dependencies": {"node": "22"},\n  "engines": {"node": "22"}\n}\n')
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle == []
    assert {d.satir for d in otomatik} == {3}       # engines satırı
    icerik = (tmp_path / "package.json").read_text(encoding="utf-8")
    assert '"dependencies": {"node": "22"}' in icerik   # BAĞIMLILIK DOKUNULMADI
    assert '"engines": {"node": "20.11.0"}' in icerik


def test_ci_ad_satırı_yanılır_sync_gerçek_girdiyi_yazar(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, ".github/workflows/ci.yml",
        "jobs:\n  t:\n    steps:\n"
        "      - name: node-version 22 installation\n"
        "      - uses: actions/setup-node@v4\n"
        "        with:\n          node-version: 22\n")
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle == []
    assert otomatik and {d.satir for d in otomatik if d.dosya.endswith("ci.yml")} == {7}
    satirlar = (tmp_path / ".github/workflows/ci.yml").read_text(
        encoding="utf-8").splitlines()
    assert satirlar[3] == "      - name: node-version 22 installation"
    assert satirlar[6] == "          node-version: 20.11.0"


# --- regresyon: depo dışına yazma / symlink -----------------------------------

def test_symlink_hedef_depo_dışına_yazılmaz(tmp_path):
    # Yeni sınır: okuma DA reddedilir — depo dışına çıkan symlink depoya
    # içerik taşımaz (tara.py) ve yazılamaz (yaz.py). Uyarı yalnız yolu
    # tekrarlar; dışarıdaki içerik hiçbir yere sızmaz.
    try:
        (tmp_path / "harici.txt").write_text("22\n", encoding="utf-8")
        depo = tmp_path / "depo"
        depo.mkdir()
        (depo / ".tool-versions").write_text("node 20.11.0\n", encoding="utf-8")
        (depo / ".nvmrc").symlink_to(tmp_path / "harici.txt")
    except OSError:  # Windows: symlink hakkı yoksa atla
        import pytest
        pytest.skip("symlink desteklenmiyor")
    pimler = tara(depo)
    red = [p for p in pimler if p.uyari and "depo dışına" in p.uyari]
    assert red and red[0].dosya == ".nvmrc"
    assert not any(p.dosya == ".nvmrc" and p.kullanilabilir for p in pimler)
    assert "22" not in " ".join(p.ham for p in pimler)  # içerik sızmadı
    otomatik, elle = senkronla(depo, ".tool-versions", False)
    assert otomatik == [] and elle == []
    assert (tmp_path / "harici.txt").read_text(encoding="utf-8") == "22\n"


# --- regresyon: aralık/matris güvenliği ---------------------------------------

def test_hedef_carret_22_sabit_sayılıp_yazılmaz(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "package.json", '{"engines": {"node": "^22"}}\n')
    otomatik, elle = senkronla(tmp_path, ".tool-versions", True)
    assert otomatik == []
    assert elle[0].dosya == "package.json"
    assert "aralık" in elle[0].gerekce


def test_kaynak_aralık_ise_hiçbir_şey_yazılmaz(tmp_path):
    # kaynak >=22; .nvmrc 20 dışlanır — eski kod .nvmrc'ye ">=22" yazıyordu.
    yaz(tmp_path, ".tool-versions", "node >=22\n")
    yaz(tmp_path, ".nvmrc", "20\n")
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert otomatik == []
    assert elle and "aralık" in elle[0].gerekce
    assert (tmp_path / ".nvmrc").read_text(encoding="utf-8") == "20\n"


def test_kaynak_matris_ise_ifade_yazılmaz(tmp_path):
    yaz(tmp_path, ".github/workflows/ci.yml",
        "jobs:\n  t:\n    strategy:\n      matrix:\n"
        "        node-version: [22, 24]\n")
    yaz(tmp_path, ".nvmrc", "20\n")
    otomatik, elle = senkronla(tmp_path, ".github/workflows/ci.yml", False)
    assert otomatik == []
    assert elle and "ızgara" in elle[0].gerekce
    assert (tmp_path / ".nvmrc").read_text(encoding="utf-8") == "20\n"


# --- regresyon: tekilleştirme konum kaybedemez --------------------------------

def test_aynı_değer_iki_satır_da_da_değişir(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, "Dockerfile",
        "FROM node:22 AS a\nRUN echo x\nFROM node:22 AS b\n")
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle == []
    satirlar = (tmp_path / "Dockerfile").read_text(encoding="utf-8").splitlines()
    assert satirlar[0] == "FROM node:20.11.0 AS a"
    assert satirlar[2] == "FROM node:20.11.0 AS b"   # İKİNCİ satır da
    from runtime_pin_sync import celiski as _c
    from runtime_pin_sync import tara as _t
    assert _c(_t(tmp_path)) == []


def test_kalan_çelişki_başarı_sunulmaz(tmp_path, monkeypatch):
    # _uygula sessizce hiçbir şey yapmazsa (kurgusal yazıcı hatası) sync
    # "temiz" DÖNMEZ: yeniden tarama kalan çelişkiyi elle listeye ekler.
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, ".nvmrc", "22\n")
    from runtime_pin_sync import yaz as yaz_modul
    monkeypatch.setattr(yaz_modul, "_uygula", lambda *_: None)
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)
    assert elle and any("senkron sonrası" in d.gerekce for d in elle)


# --- regresyon: depo içi symlink okunur, asla yazılmaz ------------------------


def test_depo_içi_symlink_okunur_ama_yazılmaz(tmp_path):
    # README sözleşmesi: depo DIŞINA çıkan bağlantının içeriği okunmadan
    # reddedilir (test_symlink_hedef_depo_dışına_yazılmaz); depo İÇİNDE kalan
    # bağlantı depo içeriğidir → karşılaştırmaya girer, ama yazım yolu her
    # symlink'i reddeder (elle düzeltilmeli), bağlantı dosyası ezilmez.
    import pytest

    depo = tmp_path / "depo"
    (depo / "paket").mkdir(parents=True)
    (depo / ".tool-versions").write_text("node 22\n", encoding="utf-8")
    (depo / ".nvmrc").write_text("20.11.0\n", encoding="utf-8")
    try:
        (depo / "paket" / ".nvmrc").symlink_to(depo / ".nvmrc")
    except OSError:  # Windows: symlink hakkı yoksa atla
        pytest.skip("symlink desteklenmiyor")

    okunan = [p for p in tara(depo) if p.dosya == "paket/.nvmrc"]
    assert okunan and okunan[0].ham == "20.11.0" and okunan[0].uyari is None

    otomatik, elle = senkronla(depo, ".tool-versions", False)
    assert any(d.dosya == ".nvmrc" for d in otomatik)
    baglanti = [d for d in elle if d.dosya == "paket/.nvmrc"]
    assert baglanti and "symlink" in baglanti[0].gerekce
    assert (depo / "paket" / ".nvmrc").is_symlink()          # bağlantı korunur
    assert (depo / ".nvmrc").read_text(encoding="utf-8") == "22\n"


# --- regresyon: yazım atomik — kesinti hedefi bozmaz --------------------------


def test_replace_başarısızsa_hedef_eski_içerikle_kalır(tmp_path, monkeypatch):
    # Doğrudan write_bytes hedefi kesip yeniden yazıyordu: replace aşamasında
    # hata olsa bile dosya çoktan değişmiş olurdu. Geçici dosya + os.replace
    # kuralında hedef ESKİ baytlarıyla kalır, artık .tmp kalmaz.
    from runtime_pin_sync import yaz as yaz_modul

    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    yaz(tmp_path, ".nvmrc", "22\n")
    önce = (tmp_path / ".nvmrc").read_bytes()

    def patlayan(*_args, **_kwargs):
        raise OSError("sahte replace hatası")

    monkeypatch.setattr(yaz_modul.os, "replace", patlayan)
    otomatik, elle = senkronla(tmp_path, ".tool-versions", False)

    assert otomatik == []
    assert any("uygulanamadı" in d.gerekce for d in elle)
    assert (tmp_path / ".nvmrc").read_bytes() == önce        # bozulmadı/boşalmadı
    assert list(tmp_path.glob("*.tmp")) == []                 # geçici dosya temizlendi


def test_atomik_yazma_dosya_izinlerini_korur(tmp_path):
    from runtime_pin_sync.yaz import _atomik_yaz

    hedef = tmp_path / ".nvmrc"
    hedef.write_bytes(b"22\n")
    önce = hedef.stat().st_mode
    _atomik_yaz(hedef, b"20\n")
    assert hedef.read_bytes() == b"20\n"
    assert hedef.stat().st_mode == önce                       # mkstemp 0600'e düşürmez


# --- regresyon: satır sonları bayt düzeyinde korunur ---------------------------

def test_crlf_karışık_satır_sonları_korunur(tmp_path):
    yaz(tmp_path, ".tool-versions", "node 20.11.0\n")
    (tmp_path / ".nvmrc").write_bytes(b"22\r\n")
    (tmp_path / "Dockerfile").write_bytes(
        b"FROM node:22 AS a\r\nWORKDIR /app\nRUN x\r\n")
    senkronla(tmp_path, ".tool-versions", False)
    assert (tmp_path / ".nvmrc").read_bytes() == b"20.11.0\r\n"
    assert (tmp_path / "Dockerfile").read_bytes() == (
        b"FROM node:20.11.0 AS a\r\nWORKDIR /app\nRUN x\r\n")


def test_boş_ya_da_dinamik_kaynak_senkronla_da_hata(tmp_path):
    # Kütüphane yolu da CLI ile aynı sözleşmeyi uygular: kullanılabilir sürüm
    # üretmeyen kaynak "temiz" sayılmaz.
    import pytest

    yaz(tmp_path, ".nvmrc", "")
    yaz(tmp_path, "Dockerfile", "FROM node:22\n")
    with pytest.raises(ValueError, match="sürüm üretmiyor"):
        senkronla(tmp_path, ".nvmrc", True)

    yaz(tmp_path, ".tool-versions", "node latest\n")
    with pytest.raises(ValueError, match="sürüm üretmiyor"):
        senkronla(tmp_path, ".tool-versions", True)
