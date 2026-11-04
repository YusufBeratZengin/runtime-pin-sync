"""Çelişki motoru testleri (kabul ölçütleri 1 ve 2 dahil)."""

from runtime_pin_sync import celiski, tara
from runtime_pin_sync.bulucular import grid_pin, pin
from runtime_pin_sync.sabitleme import Sabitleme


def p_(cz, dosya, ham, tur="t"):
    return pin(cz, dosya, tur, ham)


def test_kabul2_aralik_celiskisi():
    # >=3.10 ile 3.9 çelişir
    c = celiski([p_("python", "a", ">=3.10"), p_("python", "b", "3.9")])
    assert len(c) == 1 and c[0].calisma_zamani == "python"
    assert [x.dosya for x in c[0].dislananlar] == ["b"]


def test_kabul2_312_ile_ge310_celismez():
    assert celiski([p_("python", "a", "3.12"), p_("python", "b", ">=3.10")]) == []


def test_kabul1_örnek_depo_node_ve_python():
    pimler = tara("ornek-depolar/uyumsuz")
    celiskiler = celiski(pimler)
    rt = {c.calisma_zamani for c in celiskiler}
    assert rt == {"node", "python"}
    node_c = next(c for c in celiskiler if c.calisma_zamani == "node")
    assert [x.dosya for x in node_c.dislananlar] == ["Dockerfile"]
    assert "ÇELİŞKİ: Dockerfile" in node_c.mesaj


def test_referans_konsensüs_çoğunluktur():
    pimler = [p_("node", ".nvmrc", "20"), p_("node", "ci.yml", "20"),
              p_("node", "engines", ">=18"), p_("node", "Dockerfile", "22")]
    (c,) = celiski(pimler)
    assert c.referans_ham == "20"
    assert [x.dosya for x in c.dislananlar] == ["Dockerfile"]


def test_kaynak_referans_olarak_seçilir():
    pimler = [p_("node", ".nvmrc", "20"), p_("node", "Dockerfile", "22")]
    (c,) = celiski(pimler, kaynak="Dockerfile")   # kaynak=22 ise nvmrc hatalı
    assert c.referans_dosya == "Dockerfile"
    assert [x.dosya for x in c.dislananlar] == [".nvmrc"]


def test_kaynak_bulunamazsa_boş():
    pimler = [p_("node", ".nvmrc", "20"), p_("node", "x", "22")]
    assert celiski(pimler, kaynak="olmayan-dosya") == []


def test_ızgara_sabitlemeyi_içeriyorsa_celişmez():
    ızgara = grid_pin("node", "ci.yml", "ci-matriks", ["20", "22"])
    c = celiski([ızgara, p_("node", ".nvmrc", "20")])
    assert c == []


def test_ızgara_dışı_sabitleme_celişir():
    ızgara = grid_pin("node", "ci.yml", "ci-matriks", ["20", "22"])
    c = celiski([ızgara, p_("node", ".nvmrc", "18")])
    assert len(c) == 1 and c[0].dislananlar[0].dosya == ".nvmrc"


def test_ızgara_referans_adayı_değildir():
    # ızgara + tek somut: somut referanstır; ızgara onunla kesişiyor → temiz
    ızgara = grid_pin("node", "ci.yml", "m", ["20", "22"])
    c = celiski([ızgara, p_("node", "a", "20"), p_("node", "b", "21")])
    assert len(c) == 1
    assert [x.dosya for x in c[0].dislananlar] == ["b"]  # 21 konsensüs dışı


def test_uyari_ve_dinamik_celişkiye_girmez():
    pimler = [
        Sabitleme("node", "bozuk.json", "engines", "",
                  uyari="okunamadı"),
        Sabitleme("node", "ci.yml", "ci-adim", "${{ m.x }}", dinamik=True),
        p_("node", ".nvmrc", "20"),
    ]
    assert celiski(pimler) == []


def test_tek_sabitleme_celişkisizdir():
    assert celiski([p_("node", "a", "20")]) == []
    assert celiski([]) == []


def test_farklı_çalışma_zamanları_karışmaz():
    assert celiski([p_("node", "a", "20"), p_("python", "b", "3.12")]) == []


def test_kaynak_ızgarası_somut_uyelerle_kesisir():
    kaynak = grid_pin("node", ".mise", "mise", ["20", "22"])
    pimler = [kaynak, p_("node", "Dockerfile", "22"), p_("node", ".nvmrc", "18")]
    (c,) = celiski(pimler, kaynak=".mise")
    assert c.referans_dosya == ".mise"
    assert [x.dosya for x in c.dislananlar] == [".nvmrc"]


# --- regresyon: referans seçimi gerçek çelişkileri GİZLEYEMEZ -----------------

def test_hub_sabitleme_iki_kardeş_çelişkisini_gizlemez():
    # "20" ikisiyle de kesişen hub; 20.11.0 ile 20.12.0 BİRBİRİYLE çelişir.
    pimler = [p_("node", ".nvmrc", "20"), p_("node", ".tool-versions", "20.11.0"),
              p_("node", "Dockerfile", "20.12.0")]
    (c,) = celiski(pimler)
    assert len(c.dislananlar) == 1
    assert c.dislananlar[0].ham == "20.12.0"


def test_hub_aralık_kardeş_çelişkisini_gizlemez_kaynak_modunda():
    pimler = [p_("node", ".mise", "20"), p_("node", "a", "20.11.0"),
              p_("node", "b", "20.12.0")]
    (c,) = celiski(pimler, kaynak=".mise")
    assert c.dislananlar, "hub kaynak, kardeş çelişkisini silemez"
    assert {p.ham for p in c.dislananlar} == {"20.12.0"}


def test_uyumlu_görünen_hub_aralık_çelişkiyi_gizlemez():
    # >=18 hepsiyle kesişir; ama 20 ile <20 GERÇEKTEN çelişir.
    pimler = [p_("node", "a", ">=18"), p_("node", "b", "20"),
              p_("node", "c", "<20")]
    celiskiler = celiski(pimler)
    assert len(celiskiler) == 1
    (c,) = celiskiler
    assert {p.dosya for p in c.dislananlar} | {c.referans_dosya} == {"b", "c"}


# --- regresyon: mise listesi varsayılan denetimde de BİRLEŞİMDİR --------------

def test_mise_listesi_varsayılan_denetimde_çelişki_üretmez(tmp_path):
    from conftest import yaz
    yaz(tmp_path, "mise.toml", """[tools]
node = ["22", "24"]
""")
    yaz(tmp_path, ".nvmrc", "24\n")
    assert celiski(tara(tmp_path)) == []          # 24 listenin üyesi
    yaz(tmp_path, ".nvmrc", "20\n")
    (c,) = celiski(tara(tmp_path))                # 20 hiçbir üyeyle kesişmez
    assert c.referans_dosya == "mise.toml"
    assert c.referans_ham == "22, 24"
    assert [p.dosya for p in c.dislananlar] == [".nvmrc"]


def test_çok_pimli_kaynak_birleşim_referansı_olur(tmp_path):
    # Aynı kaynak dosya aynı çalışma zamanı için İKİ pim üretirse (iki CI
    # adımı) referans ilk adım değil, ikisinin BİRLEŞİMİDİR; .nvmrc 18 dışlanır.
    from conftest import yaz
    yaz(tmp_path, ".github/workflows/ci.yml",
        "jobs:\n  t:\n    steps:\n"
        "      - uses: actions/setup-node@v4\n"
        "        with:\n          node-version: 20\n"
        "      - uses: actions/setup-node@v4\n"
        "        with:\n          node-version: 22\n")
    yaz(tmp_path, ".nvmrc", "18\n")
    (c,) = celiski(tara(tmp_path), kaynak=".github/workflows/ci.yml")
    assert c.referans_dosya == ".github/workflows/ci.yml"
    assert c.referans_ham == "20, 22"
    assert [p.dosya for p in c.dislananlar] == [".nvmrc"]
