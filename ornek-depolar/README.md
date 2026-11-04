# Örnek depolar (UYDURMA)

Bu klasördeki her şey **sahte demo verisidir**: şirket, paket ve sürüm
adları uydurmadır ("örnek", "fake", xxxxxx). Gerçek bir projeye ait
hiçbir bilgi içermez; yalnız `runtime-pin-sync`'in davranışını göstermek
ve test edilmek için vardır.

- `uyumsuz/` — Node 20 (nvmrc, CI, .tool-versions) ama Dockerfile 22 +
  Python 3.9 vs requires-python >=3.10. Beklenen: `runtime-pin-sync uyumsuz`
  → exit 1, iki çelişki.
- `tutarli/` — her kaynak aynı sürümü gösterir (`.sdkmanrc` içinde
  `java=21.0.1+12`). Beklenen: exit 0.
- `bozuk/` — geçersiz JSON, `${{ }}` matrisi ve `ARG` ile parametreli
  FROM içerir. Beklenen: hata VERMEZ, "okunamadı"/"dinamik, atlandı"
  uyarılarıyla exit 0.
