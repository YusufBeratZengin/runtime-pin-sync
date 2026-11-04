"""TR/EN mesaj kataloğu.

Hata ve gerekçe metinleri üretildikleri yerde bu katalogdan seçilir; böylece
``--lang en`` çıktısında yarım çevrilmiş (Türkçe kalan) gerekçe olmaz. Katalog
dışında serbest metin üretilmez.
"""

from __future__ import annotations

__all__ = ["MESAJLAR", "m"]

# anahtar -> (Türkçe, İngilizce)
MESAJLAR: dict[str, tuple[str, str]] = {
    "not_a_repo": (
        "depo klasörü değil: {yol}",
        "not a repository directory: {yol}",
    ),
    "source_unusable": (
        "kaynak bulunamadı ya da sürüm üretmiyor: {kaynak}",
        "source not found or yields no versions: {kaynak}",
    ),
    "ref_not_fixed": (
        "referans {deger!r} sabit sürüm değil (aralık/ızgara); yazılmaz",
        "reference {deger!r} is not a pinned version (range/matrix); will not rewrite",
    ),
    "same_line": (
        "aynı satırda birden fazla hedef",
        "multiple targets on the same line",
    ),
    "apply_failed": (
        "uygulanamadı: {hata}",
        "failed to apply: {hata}",
    ),
    "conflict_after_sync": (
        "senkron sonrası çelişki giderilmedi",
        "conflict remains unresolved after sync",
    ),
    "type_not_rewritable": (
        "{tur}: otomatik yeniden yazma desteklenmiyor",
        "{tur}: automatic rewrite is not supported",
    ),
    "line_unknown": (
        "satır konumu çözülemedi",
        "could not determine the line position",
    ),
    "target_not_fixed": (
        "{ham!r} bir aralık/ızgara; sabit sürüme zorlanmaz",
        "{ham!r} is a range/matrix; not forced to a pinned version",
    ),
    "file_unreadable": (
        "dosya okunamadı: {hata}",
        "could not read file: {hata}",
    ),
    "line_out_of_range": (
        "satır numarası dosya sınırını aştı",
        "line number exceeds the file length",
    ),
    "token_not_standalone": (
        "{ham!r} satırda tek ve bağımsız değil",
        "{ham!r} is not single and standalone on its line",
    ),
    "docker_template": (
        "Dockerfile etiketi şablonlu; yalnız sürüm bölümü güvenle değişir",
        "Dockerfile tag is templated; only a plain version part can be rewritten safely",
    ),
    "symlink_target": (
        "{dosya}: hedef bir dosya bağlantısı (symlink)",
        "{dosya}: target is a symlink",
    ),
    "outside_target": (
        "{dosya}: hedef depo dışında ({cozum})",
        "{dosya}: target is outside the repository ({cozum})",
    ),
}


def m(lang: str, anahtar: str, **kw: object) -> str:
    """Katalogdan istenen dildeki mesajı biçimlendirir."""
    tr, en = MESAJLAR[anahtar]
    return (en if lang == "en" else tr).format(**kw)
