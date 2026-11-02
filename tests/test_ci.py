"""GitHub Actions okuma testleri: setup-*, matris, ${{ }} tuzakları."""

from runtime_pin_sync.ci import is_aksi

AKIS = """
name: ci
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
"""


def hamlar(pimler):
    return sorted((p.calisma_zamani, p.ham) for p in pimler)


def test_setup_adimlari():
    pimler = is_aksi("w/ci.yml", AKIS)
    assert hamlar(pimler) == [("node", "20"), ("python", "3.12")]
    assert all(p.satir for p in pimler)  # sync için satır bilgisi var


def test_matris_ızgarası_birleşim_olarak_tek_sabitlemedir():
    icerik = """
jobs:
  t:
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
"""
    pimler = is_aksi("w/ci.yml", icerik)
    assert len(pimler) == 1  # adım matristen çözüldü, matriks yinelenmedi
    (p,) = pimler
    assert p.ham == "3.11, 3.12"
    assert p.kullanilabilir
    assert not p.aralik.sabit  # ızgara referans adayı değildir
    from runtime_pin_sync.versiyon import AralikKumesi, spek_ayristir, kümeler_kesisir
    assert kümeler_kesisir(p.aralik, spek_ayristir("3.11"))
    assert kümeler_kesisir(p.aralik, spek_ayristir("3.12"))
    assert not kümeler_kesisir(p.aralik, AralikKumesi(()))  # boş kümeyle kesişmez


def test_matris_somut_listele_adimsiz():
    icerik = """
jobs:
  t:
    strategy:
      matrix:
        node-version: [20, 22]
    steps:
      - run: echo hi
"""
    pimler = is_aksi("w/ci.yml", icerik)
    assert [(p.tur, p.ham) for p in pimler] == [("ci-matriks", "20, 22")]


def test_çözülemeyen_ifade_hata_degil_dinamik():
    icerik = """
jobs:
  t:
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ fromJSON(inputs.versions) }}
"""
    pimler = is_aksi("w/ci.yml", icerik)
    assert len(pimler) == 1 and pimler[0].dinamik and not pimler[0].uyari


def test_degisken_verilirse_cozulur():
    icerik = """
jobs:
  t:
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node }}
"""
    pimler = is_aksi("w/ci.yml", icerik, {"node": "20"})
    assert pimler[0].ham == "20" and pimler[0].kullanilabilir


def test_version_file_mevcutsa_yinelenmez(tmp_path):
    (tmp_path / ".nvmrc").write_text("20\n")
    icerik = """
jobs:
  t:
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
"""
    assert is_aksi("w/ci.yml", icerik, {}, str(tmp_path)) == []


def test_version_file_yoksa_uyari(tmp_path):
    icerik = """
jobs:
  t:
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version-file: .python-version
"""
    (p,) = is_aksi("w/ci.yml", icerik, {}, str(tmp_path))
    assert p.durum == "okunamadı" and "version-file" in p.uyari


def test_sürüm_dışı_matris_yoksayar():
    icerik = """
jobs:
  t:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps: [run: x]
"""
    assert is_aksi("w/ci.yml", icerik) == []


def test_bozuk_akis_hata_vermez():
    (p,) = is_aksi("w/ci.yml", "bu: :bir: akış değil\n\tkotu: 1\n")
    assert p.durum == "okunamadı"
    (d,) = is_aksi("w/ci.yml", "- düz dizi\n")
    assert d.durum == "okunamadı"
    assert is_aksi("w/ci.yml", "name: x\non: push\n") == []  # jobs yok
    assert is_aksi("w/ci.yml", "jobs:\n  bozuk: 5\n") == []


def test_adim_dizisi_bozuksa_atlanır():
    assert is_aksi("w/c.yml", "jobs:\n  t:\n    steps: 5\n") == []


def test_rust_toolchain_eylemi():
    icerik = """
jobs:
  t:
    steps:
      - uses: dtolnay/rust-toolchain@1.85.0
        with:
          toolchain: "1.85.0"
"""
    pimler = is_aksi("w/c.yml", icerik)
    assert pimler[0].calisma_zamani == "rust" and pimler[0].ham == "1.85.0"


def test_step_listesi_ve_sablon_listesi():
    icerik = """
jobs:
  t:
    strategy:
      matrix:
        node: [20, 22]
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version:
            - ${{ matrix.node }}
            - ${{ env.BELLI_DEGIL }}
"""
    pimler = is_aksi("w/c.yml", icerik)
    assert len(pimler) == 2
    somut = [p for p in pimler if p.kullanilabilir]
    dinamik = [p for p in pimler if p.dinamik]
    assert len(somut) == 1 and somut[0].ham == "20, 22"
    assert len(dinamik) == 1
