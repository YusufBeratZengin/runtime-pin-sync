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
$ runtime-pin-sync .
ÇALIŞMA ZAMANI  KAYNAK                    TÜR              SABİTLEME  DURUM
--------------  ------------------------  ---------------  ---------  --------
node            .github/workflows/ci.yml  ci-adim          20         referans
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

(Bu depo içindeki `ornek-depolar/uyumsuz` deposunun GERÇEK çıktısıdır.)

Çelişkiyi tek kaynaktan gider:

```console
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
| Java | `.java-version`, `pom.xml` (`maven.compiler.release` vb.), Dockerfile `FROM eclipse-temurin:…` vb., `actions/setup-java` + matris |

## Çelişki ne demek?

Her sabitleme bir **sürüm kümesine** dönüşür; iki küme kesişmiyorsa çelişki
vardır:

- `engines.node: ">=18"` ile `.nvmrc: 20` → **uyumlu** (aralık sabitle ile
  kavga etmez).
- `requires-python: ">=3.10"` ile `.python-version: 3.9` → **çelişki**.
- `.nvmrc: 20` ile `FROM node:22` → **çelişki** (iki ayrı somut sürüm).
- `3.12` ile `3.12.*` ile `3.12.1`: ön ek semantiği — `3.12`, `3.12.1`'i kapsar.
- CI **matrisi** (`[20, 22]`) bir test ızgarasıdır: üyelerinin BİRLEŞİMİ olarak
  karşılaştırılır; ızgaradaki herhangi bir değere eşit sabitleme çelişmez.
- Desteklenen sözdizimi: düz/ön ek (`20`, `20.x`), aralıklar (`>= > <= < ==`),
  `||` birleşimleri, virgülle VE listeleri (`>=3.10,<4.0`), semver `^`/`~`,
  PEP 440 `~=`.
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
- aralıklar (`>=18`), test ızgaraları, şablonlu etiketler (`ARG TAG`) ve tek
  anlamlı olmayan her satır **ELLE DÜZELTİLMELİ** listesine yazılır — asla
  sessizce değiştirilmez;
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
  satırlık ayrıştırıcı (`miniyaml.py`) o alt kümeyi tanır, gerisini
  "okunamadı" uyarısıyla dürüstçe eler — PyYAML gerekmez.
- JSON/JSONC: stdlib `json` + `devcontainer.json` için yorum/son-virgül
  tolere eden ince bir katman.

Her CI işinde çalışacak bir geliştirme aracı bir saniyede kurulmalı ve tedarik
zinciri sürprizi çıkarmamalıdır.

## Sınırlar (dürüst liste)

- Komut satırı iletileri Türkçedir (bayrakların İngilizce takma adları vardır);
  `--lang en` çıktı modu planlanmıştır (issue'lara bakın).
- İş akışı dosyaları mini YAML alt kümesiyle okunur; alışıldık dışı YAML,
  yanlış rapor yerine "okunamadı" uyarısı üretir.
- Paket/bağımlılık sürümleri kapsam dışıdır (`renovate`/`syncpack` işi);
  derleyici/ABI sapması ve araç kurulumu da kapsam dışıdır.
- Node `lts/*` ve `lts/<ad>` takma adları elle tutulan yerleşik bir tablodan
  çözülür (şimdilik hydrogen→16 … krypton→24); bilinmeyen takma ad tahmin
  edilmez, atlanır.
- Ön sürüm sonekleri (`1.85.0-rc1`) ve `!=` dışlama aralıkları yanlış
  karşılaştırmak yerine "okunamadı" olarak raporlanır.

## Geliştirme

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
bash scripts/check.sh    # ruff + mypy --strict + pytest --cov-fail-under=85
```

## Lisans

MIT © 2026 YusufBeratZengin
