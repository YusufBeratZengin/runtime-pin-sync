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
