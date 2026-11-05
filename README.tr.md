# runtime-pin-sync (Türkçe)

**Sürüm sabitlemelerini; `.nvmrc`, `.python-version`, `.tool-versions`,
`mise.toml`, `package.json` engines, `pyproject.toml` requires-python,
Dockerfile `FROM`, devcontainer ve CI `setup-*`/matris satırları arasında
bulur ve düzeltir — hiçbir araç yöneticisine geçmeye zorlamadan.**

"Bende çalışıyor, CI'da patlıyor" cümlesinin en sık nedeni basittir: aynı
çalışma zamanı altı yere sabitlenmiştir ve birileri yalnız üçünü güncellemiştir.
`runtime-pin-sync` mevcut tüm sabitlemeleri okur, bunları **sürüm kümeleri**
olarak karşılaştırır (`>=18` gibi bir aralık `20` ile asla çelişmez; `20` ile
`22` çelişir) ve tek bir yetkili kaynak dosyadan sapmaları yeniden yazar.

[English README](README.md) · [Değişiklikler](CHANGELOG.md) ·
[Katkı](CONTRIBUTING.md) · [Güvenlik](SECURITY.md)

## Kurulum

```bash
pip install runtime-pin-sync
```

Python ≥ 3.10. **Sıfır çalışma zamanı bağımlılığı** (nedeni aşağıda).

## 30 saniyelik örnek

```console
$ cd ornek-depolar/uyumsuz
$ runtime-pin-sync .
ÇALIŞMA ZAMANI  KAYNAK                    TÜR              SABİTLEME  DURUM
--------------  ------------------------  ---------------  ---------  --------
node            .github/workflows/ci.yml  ci-adım          20         referans
node            .nvmrc                    nvmrc            20         uyumlu
node            .tool-versions            tool-versions    20.11.0    uyumlu
node            Dockerfile                dockerfile       22         ÇELİŞKİ
node            package.json              engines          >=18       uyumlu
python          .python-version           python-version   3.9        ÇELİŞKİ
python          .tool-versions            tool-versions    3.12.1     referans
python          Dockerfile                dockerfile       3.12       uyumlu
python          pyproject.toml            requires-python  >=3.10     uyumlu

node: ci.yml=20 | .nvmrc=20 | .tool-versions=20.11.0 | Dockerfile=22 | package.json=>=18 → ÇELİŞKİ: Dockerfile
python: .python-version=3.9 | .tool-versions=3.12.1 | Dockerfile=3.12 | pyproject.toml=>=3.10 → ÇELİŞKİ: .python-version
SONUÇ: 2 çalışma zamanında çelişki bulundu.
$ echo $?
1
```

(Bu depo içindeki `ornek-depolar/uyumsuz` deposunun GERÇEK çıktısıdır; komut o
dizinde çalıştırılmıştır. Aşağıdaki her örnekte komutun hangi dizinde
çalıştığı yazılıdır. Varsayılan dil Türkçedir; insan tarafından okunan yüzey —
tablolar, çelişki özetleri, sync planı ve tüm elle-düzeltme gerekçeleri, hata
ve uyarı metinleri — `--lang en` veya `RUNTIME_PIN_SYNC_LANG=en` ile
İngilizce üretilir. JSON alan adları API kararlılığı için iki kipte de
Türkçedir.)

İngilizce kipte çalıştırma:

```console
$ cd ornek-depolar/uyumsuz
$ runtime-pin-sync . --lang en
RUNTIME  SOURCE                    TYPE             PIN      STATUS
-------  ------------------------  ---------------  -------  ----------
node     .github/workflows/ci.yml  ci-step          20       reference
node     .nvmrc                    nvmrc            20       consistent
node     .tool-versions            tool-versions    20.11.0  consistent
node     Dockerfile                dockerfile       22       CONFLICT
node     package.json              engines          >=18     consistent
python   .python-version           python-version   3.9      CONFLICT
python   .tool-versions            tool-versions    3.12.1   reference
python   Dockerfile                dockerfile       3.12     consistent
python   pyproject.toml            requires-python  >=3.10   consistent

node: ci.yml=20 | .nvmrc=20 | .tool-versions=20.11.0 | Dockerfile=22 | package.json=>=18 → CONFLICT: Dockerfile
python: .python-version=3.9 | .tool-versions=3.12.1 | Dockerfile=3.12 | pyproject.toml=>=3.10 → CONFLICT: .python-version
RESULT: 2 runtimes have conflicts.
```

Çelişkiyi tek kaynaktan gider (Türkçe ve İngilizce destekler):

```console
$ cd ornek-depolar/uyumsuz
$ runtime-pin-sync sync --kaynak .tool-versions --dry-run
.python-version:1  '3.9' → '3.12.1' (değiştirilecek)
Dockerfile:2  '22' → '20.11.0' (değiştirilecek)
$ runtime-pin-sync sync --kaynak .tool-versions   # yalnız hedef satırlar değişir
$ runtime-pin-sync . && echo temiz
SONUÇ: tüm sabitlemeler uyumlu ✓
temiz
```

## Hangi dosyaları okur?

| Çalışma zamanı | Kaynaklar |
| --- | --- |
| Node | `.nvmrc`, `.node-version`, `package.json` → `engines.node`, `.tool-versions`, `mise.toml`, Dockerfile `FROM node:…`, devcontainer `image`/`features`, `actions/setup-node` + matris |
| Python | `.python-version`, `pyproject.toml` → `requires-python`, `.tool-versions`, `mise.toml`, Dockerfile `FROM python:…`, devcontainer, `actions/setup-python` + matris |
| Go | `go.mod` (`go`, `toolchain`), `.go-version`, Dockerfile `FROM golang:…`, `actions/setup-go` + matris |
| Rust | `rust-toolchain`, `rust-toolchain.toml`, Dockerfile `FROM rust:…`, `dtolnay/rust-toolchain` |
| Java | `.java-version`, `.sdkmanrc` (`java=…`), `pom.xml` (`maven.compiler.release` vb.), Dockerfile `FROM eclipse-temurin:…` vb., `actions/setup-java` + matris |

### Ayrıştırıcı sınırları: Go ve Java

İki okuyucu da bilinçli olarak satır odaklıdır; nerede durduklarını bilmek
yanlış güvene engel olur.

**Go** — `go.mod` ve `.go-version`:

```text
go 1.22               → >=1.22    (MİNİMUM gereksinim, sabitleme DEĞİL)
toolchain go1.23.1    → 1.23.1    (tam araç zinciri; go 1.22 ile birlikte geçerli)
```

Bu yüzden `go 1.22` ile `toolchain go1.23.1` çelişmez: ilki "en az 1.22" der,
ikincisi 1.23.1'i seçer. `.go-version` tek ve tam bir belirteç olarak okunur.
Desteklenen: satır başına bir `go`/`toolchain` direktifi, her girintide,
`toolchain` `go` ön ekiyle ya da öneksiz. Okunmayan: `toolchain default`,
çok satırlı direktifler, ortamdaki `GOTOOLCHAIN` ve yorum/`replace` bloğu
içine gizlenmiş sürümler.

**Java** — `pom.xml` ve `.java-version`:

```xml
<properties>
  <maven.compiler.release>21</maven.compiler.release>
  <java.version>21</java.version>
</properties>
```

`maven.compiler.release`, `maven.compiler.source`, `java.version`, `release`
anahtarlarının her biri (bu sırayla) okunur, ama yalnız ilk tek satırlık
birebir öğesi — üst öğe doğrulanmadığı için eklenti yapılandırmasındaki bir
`<release>` de eşleşir. `${...}` değerleri dinamik sayılıp atlanır. Okunmayan: çok satırlı ya da ad
alanı önekli öğeler; XML varlıkları çözülmez (böyle değerler çözümlenemedi
olarak raporlanır). Maven profiline göre değişen değerler, `toolchains.xml` ve
`.mvn/jvm.config` kapsam dışıdır. `.java-version` tek ve tam bir belirteçtir.

`.sdkmanrc` (SDKMAN!) `anahtar=değer` satırları olarak okunur; yalnız `java`
anahtarı Java kaynağıdır, diğer araçlar (`maven`, `gradle`) yok sayılır.
`java=17.0.2+8` yapı bilgisini korur; dağıtım eki (`java=21.0.1-tem`) sürümün
parçası değildir ve `sync` satırı yeniden yazarken korunur. `latest` ya da
tanınmayan bir değer dinamik, boş değer okunamadı olarak raporlanır.

## Çelişki ne demek?

Her sabitleme bir **sürüm kümesine** dönüşür; iki küme kesişmiyorsa çelişki
vardır:

- `engines.node: ">=18"` ile `.nvmrc: 20` → **uyumlu** (aralık sabitle ile
  kavga etmez).
- `requires-python: ">=3.10"` ile `.python-version: 3.9` → **çelişki**.
- `.nvmrc: 20` ile `FROM node:22` → **çelişki** (iki ayrı somut sürüm).
- `3.12` ile `3.12.*` ile `3.12.1`: ön ek semantiği — `3.12`, `3.12.1`'i kapsar;
  ancak tam belirtilmiş sürüm NOKTADIR: `20.1.0`, `>20.1.0` ile kesişmez.
- CI **matrisi** (`[20, 22]`), `mise.toml` listeleri
  (`node = ["22", "24"]`) ve çok değerli `.tool-versions` satırları
  (`python 3.12.1 3.11.8`) kurulu sürümlerin BİRLEŞİMİDİR; ayrı ve çelişen
  sabitlemeler değildir. Herhangi bir üyeye eşit sabitleme çelişmez ve tek bir
  üye "asıl" referans ilan edilmez.
- Desteklenen sözdizimi: düz/ön ek (`20`, `20.x`), aralıklar (`>= > <= < ==`),
  `||` birleşimleri, virgülle VE listeleri (`>=3.10,<4.0`), semver `^`/`~`,
  PEP 440 `~=`.
- Desteklenmeyen sözdizimi TAHMİN EDİLMEZ: `!=`, `===`, npm tire aralığı
  (`1.2.3 - 1.4.0`), ön sürüm soneki (`1.2.3-beta.1`), Ruby'nin `~>`
  operatörü ve Node takma adları (`lts/iron`) "çözümlenemedi/atlandı" olarak
  raporlanır; başka bir aralık gibi yorumlanmaz. `~=` en az iki bileşen
  ister (PEP 440): `~=3` sessizce `>=3,<4` sayılmaz, çözümlenemez kalır.
- **Dinamik ifade hata değildir.** `${{ matrix.x }}`, çözülemeyen Dockerfile
  `ARG` etiketleri ve bilinmeyen `lts/…` takma adları "atlandı" olarak rapor
  edilir; denetlenmesini istiyorsanız `--degisken node=20` ile değer verin.

## Tek kaynak ve `sync`

`--kaynak DOSYA` (İngilizce takma adı `--source`) yetkili dosyayı seçer.

```bash
runtime-pin-sync sync --kaynak .tool-versions --dry-run   # planla, dosyaya dokunma
runtime-pin-sync sync --kaynak .tool-versions             # sapmaları yeniden yaz
```

`sync` bilinçli olarak muhafazakârdır:

- otomatik değişiklik yalnız tek belirteçli, satırı belirli hedeflerde olur;
  bu ancak SAPILAN ile referans değerin ikisi de düz sabit sürümse yapılır —
  `>=`, `^`, `~`, `||` veya matris listesi içeren belirteç yazılmaz;
  referansın kendisi sabit değilse hiçbir şey yazılmaz;
- aralıklar (`>=18`), test ızgaraları, şablonlu etiketler (`ARG TAG`) ve tek
  anlamlı olmayan her satır **ELLE DÜZELTİLMELİ** listesine yazılır — asla
  sessizce değiştirilmez;
- yazım hedefleri denetlenir: symlink'li dosyalara ve depo dışına çözülen
  yollara asla yazılmaz. Sınır OKUMALARI da korur: depo **dışına** çıkan
  symlink'li sürüm dosyası ya da `*-version-file: ../..` hedefi, içeriği
  rapora sızmadan okunmadan reddedilir. Depo **içinde** kalan dosya bağlantısı
  depo içeriğidir — karşılaştırma için okunur, ama üzerinden asla yazılmaz
  (her zaman elle düzeltilmeli listesine düşer); dosyalar bayt düzeyinde
  okunup yazılır, CRLF ve karışık satır sonları hedef satır dışında aynen kalır;
- yazım atomiktir: yeni içerik aynı dizindeki geçici dosyaya yazılıp
  `fsync` edilir, sonra `os.replace` ile yerine konur. Kesilen ya da hata
  veren bir yazım hedef dosyayı bayt bayt eski hâlinde bırakır, geride
  geçici dosya kalmaz; dosyanın izinleri korunur;
- aynı sabitleme birden çok satırda geçiyorsa TÜM satırlar yazılır; yazımdan
  sonra depo yeniden taranır, kalan çelişki başarı sayılmaz (exit 1);
- `--dry-run` dosyaların bit bit değişmediğini garanti eder (testli).

## Kütüphane arayüzü

```python
from runtime_pin_sync import tara, celiski   # takma adlar: scan, conflicts

pimler = tara(".")          # list[Sabitleme]
for c in celiski(pimler):   # list[Celiski]
    print(c.mesaj)          # "node: … → ÇELİŞKİ: Dockerfile"
```

## CI kapısı

```yaml
- uses: actions/setup-python@v5
- run: pipx run runtime-pin-sync . --json   # çelişkide exit 1
```

## Neden sıfır bağımlılık?

- TOML: stdlib `tomllib` (Python ≥ 3.11); 3.10 için yerleşik mini yedek
  ayrıştırıcı (`minitoml.py`).
- YAML: iş akışı dosyaları YAML'ın küçük bir alt kümesini kullanır; ~170
  satırlık ayrıştırıcı (`miniyaml.py`) o alt kümeyi tanır, harici kütüphane gerektirmez.
- JSON/JSONC: stdlib `json` + `devcontainer.json` için yorum/son-virgül
  tolere eden ince bir katman.

Her CI işinde çalışacak bir geliştirme aracı bir saniyede kurulmalı ve
*çalışma zamanına* üçüncü taraf kod sokmamalıdır: `pip install runtime-pin-sync`
hiçbir paket çekmez. (Paketleme `hatchling` kullanır; test, lint ve tip
kontrolü `[dev]` ekstrasındaki araçları ister — bunların hiçbiri kullanıcının
çalışma zamanına girmez.)

### Desteklenen YAML alt kümesi ve PyYAML / ruamel.yaml ile farkı

İş akışı ayrıştırıcımız (`src/runtime_pin_sync/miniyaml.py`) kasıtlı olarak GitHub Actions (`.github/workflows/*.yml`) dosyalarının kullandığı alt kümeyi hedefler:

- **Desteklenen söz dizimi**:
  - Eşlemeler: anahtar-değer çiftleri (`name: test`, `with:`) ve girintili iç eşlemeler.
  - Blok diziler (`- uses: actions/setup-node@v4`, `- run: ...`).
  - Akış dizileri (`node-version: [20, 22]`, `[3.10, 3.12]`).
  - Skalerler: tırnaksız metinler ve sayılar, tek tırnaklı (`'20'`) ve çift tırnaklı (`"3.12"`) dizgiler.
  - Çok satırlı blok metinler: birebir (`|`, `|-`) ve katlanmış (`>`, `>-`).
  - Yorumlar: satır başı veya satır içi `# ...`.

- **Kapsam dışı bırakılan yapılar**:
  - Çıpalar ve takma adlar (`&ref`, `*ref`)
  - Birleştirme anahtarları (`<<: *defaults`)
  - Özel veri tipi etiketleri (`!!str`, `!custom`)
  - Karmaşık / çok satırlı anahtarlar (`? [anahtar]`)
  - Girintide sekme (TAB) karakteri kullanımı (girinti belirsizliğini önlemek için hata fırlatır)

- **Alışılmadık YAML durumunda davranış**:
  Desteklenmeyen veya bozuk bir YAML ile karşılaşıldığında araç çökmez; o dosyayı açık bir uyarıyla (`okunamadı: desteklenmeyen YAML (...)` / `could not read: unsupported YAML (...)`) işaretler ve deponun kalanını denetlemeyi sürdürür.

- **Neden PyYAML veya ruamel.yaml değil?**:
  - *C-derleme / sistem bağımlılığı yok:* Linux, macOS ve Windows'ta Python 3.10+ kurulu her makinede derleyicisiz çalışır.
  - *Çalışma zamanında üçüncü taraf YAML ayrıştırıcısı yok:* PyYAML/ruamel.yaml
    kullanıcının bağımlılık grafiğinden çıkar; onların güvenlik duyuruları ve
    sürüm koşuşturması size ulaşmaz. Bu, "projenin hiç bağımlılığı yok"
    iddiası **değildir**: derleme `hatchling`, test/lint ise `[dev]` ekstrası
    ister.
  - *Kontrollü hata sınırları:* Ayrıştırma hataları yakalanıp yerelleştirilmiş uyarılara dönüştürülür.

## Sınırlar (dürüst liste)

- Komut satırı varsayılan olarak Türkçedir; `--lang en` veya
  `RUNTIME_PIN_SYNC_LANG=en` insan tarafından okunan yüzeyi çevirir: durum
  tablosu, çelişki özeti, sync değişiklik listesi ve TÜM elle-düzeltme
  gerekçeleri, hata iletileri ve ayrıştırıcı uyarıları — ayrıca `--help`
  metninin kendisi (açıklama, seçenekler ve argparse'ın `usage:`/bölüm
  etiketleri). JSON anahtarları çevrilmez (kararlı API). Tablodaki `TÜR`
  sütunu çevrilen bir etikettir (`ci-adim` → `ci-adım`); JSON'daki `tur`
  alanı her zaman kararlı kimliği taşır.
- Okunamayan bir dizin sessizce atlanmaz: tarama, kısmi sonucu "temiz" diye
  sunmak yerine çıkış kodu 2 ile durur
  (`tarama eksik — okunamayan dizin(ler): …`).
- İş akışı dosyaları mini YAML alt kümesiyle okunur; alışıldık dışı YAML,
  yanlış rapor veya çökme yerine "okunamadı" uyarısı üretir.
- Paket/bağımlılık sürümleri kapsam dışıdır (`renovate`/`syncpack` işi);
  derleyici/ABI sapması ve araç kurulumu da kapsam dışıdır.
- Node `lts/<ad>` takma adları elle tutulan yerleşik tablodan çözülür
  (gallium→16, hydrogen→18, iron→20, jod→22, krypton→24; kaynak resmî
  nodejs/Release takvimi); bilinmeyen takma ad tahmin edilmez, atlanır.
  Hareketli `lts/*` takma adı dinamik sayılır — tablonun en yeni sayısı güncel
  gerçek gibi sunulmaz.
- Ön sürüm sonekleri (`1.85.0-rc1`) ve `!=` dışlama aralıkları yanlış
  karşılaştırmak yerine "okunamadı" olarak raporlanır.

## Geliştirme

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
bash scripts/check.sh    # ruff + mypy --strict + pytest --cov-fail-under=85

# paketleme kontrolü (CI'daki `paket` işiyle aynı fikir: yalnız wheel, PyPI yok)
python -m build --outdir dist
python -m venv .venv-wheel && .venv-wheel/bin/pip install --no-index \
    --find-links dist runtime-pin-sync
```

## Lisans

MIT © 2026 Yusuf Berat Zengin
