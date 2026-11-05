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
    "dir_unreadable": (
        "okunamadı: dizin taranamadı ({hata})",
        "could not read: directory not scanned ({hata})",
    ),
    "scan_incomplete": (
        "tarama eksik — okunamayan dizin(ler): {dizinler}; sonuç 'temiz' sayılmaz",
        "scan incomplete — unreadable director(y/ies): {dizinler}; the result "
        "is not a clean pass",
    ),
    # --- tarama/bulucu uyarıları ---------------------------------------------
    # Uyarılar ÜRETİLDİKLERİ yerde bu katalogdan seçilir. Rapor katmanında
    # metin değiştirme (string replace) ile çeviri yapılmaz: eksik bir eşleme
    # ``--lang en`` çıktısında Türkçe artık bırakıyordu.
    "w_unreadable_file": (
        "okunamadı: {hata}",
        "could not read: {hata}",
    ),
    "w_symlink_outside": (
        "okunamadı: bağlantı depo dışına işaret ediyor (okuma reddedildi)",
        "could not read: link points outside the repository (read refused)",
    ),
    "w_empty_file": (
        "okunamadı: boş dosya",
        "could not read: empty file",
    ),
    "w_empty_token": (
        "okunamadı: boş belirteç",
        "could not read: empty token",
    ),
    "w_token_unparsable": (
        "okunamadı: {ham!r} sürüm belirteçi çözümlenemedi",
        "could not read: could not parse version token {ham!r}",
    ),
    "w_invalid_json": (
        "okunamadı: geçersiz JSON ({hata})",
        "could not read: invalid JSON ({hata})",
    ),
    "w_json_not_object": (
        "okunamadı: JSON bir nesne değil",
        "could not read: JSON is not an object",
    ),
    "w_engines_not_text": (
        "okunamadı: engines.node bir metin değil",
        "could not read: engines.node is not a string",
    ),
    "w_invalid_jsonc": (
        "okunamadı: geçersiz JSONC ({hata})",
        "could not read: invalid JSONC ({hata})",
    ),
    "w_invalid_toml": (
        "okunamadı: geçersiz TOML ({hata})",
        "could not read: invalid TOML ({hata})",
    ),
    "w_requires_python_not_text": (
        "okunamadı: requires-python bir metin değil",
        "could not read: requires-python is not a string",
    ),
    "w_channel_not_text": (
        "okunamadı: channel bir metin değil",
        "could not read: channel is not a string",
    ),
    "w_gomod_no_go": (
        "okunamadı: go.mod içinde 'go' satırı yok",
        "could not read: no 'go' directive in go.mod",
    ),
    "w_prerelease": (
        "okunamadı: ön sürüm karşılaştırmaya girmez ({ham})",
        "could not read: prerelease excluded from comparison ({ham})",
    ),
    #: Dockerfile/devcontainer etiketi yokken SABİTLEME sütununda görünen yer tutucu
    "untagged": ("(etiketsiz)", "(untagged)"),
    #: devcontainer feature sürümü belirtilmemişken görünen yer tutucu
    "default_feature": ("(varsayılan)", "(default)"),
    "w_from_line": (
        "okunamadı: FROM satırı çözümlenemedi",
        "could not read: could not parse the FROM line",
    ),
    "w_tag_unparsable": (
        "okunamadı: çözümlenemeyen etiket {etiket!r}",
        "could not read: unresolvable tag {etiket!r}",
    ),
    "w_tag_prerelease": (
        "okunamadı: ön sürüm etiketi karşılaştırmaya girmez ({etiket})",
        "could not read: prerelease tag excluded from comparison ({etiket})",
    ),
    "w_tag_suffix": (
        "okunamadı: desteklenmeyen etiket soneki ({etiket})",
        "could not read: unsupported tag suffix ({etiket})",
    ),
    "w_unsupported_yaml": (
        "okunamadı: desteklenmeyen YAML ({hata})",
        "could not read: unsupported YAML ({hata})",
    ),
    "w_workflow_not_mapping": (
        "okunamadı: iş akışı bir eşleme değil",
        "could not read: workflow is not a mapping",
    ),
    "w_version_file_outside": (
        "okunamadı: version-file {hedef!r} depo sınırını aşıyor ya da dosya "
        "bağlantısı (reddedildi)",
        "could not read: version-file {hedef!r} points outside the repository "
        "or is a symlink (refused)",
    ),
    "w_version_file_missing": (
        "okunamadı: version-file {hedef!r} bulunamadı",
        "could not read: version-file {hedef!r} not found",
    ),
    "w_version_file_error": (
        "okunamadı: version-file {hedef!r} ({hata})",
        "could not read: version-file {hedef!r} ({hata})",
    ),
    # --- alt ayrıştırıcıların kendi hata metinleri ----------------------------
    "yaml_tab_indent": (
        "girinti için sekme kullanılamaz",
        "tabs cannot be used for indentation",
    ),
    "yaml_unexpected_indent": (
        "beklenmeyen girinti: {govde!r}",
        "unexpected indentation: {govde!r}",
    ),
    "yaml_expected_mapping": (
        "eşleme beklenirken: {govde!r}",
        "expected a mapping: {govde!r}",
    ),
    "toml_unsupported_header": (
        "mini TOML: desteklenmeyen tablo başlığı (satır {no})",
        "mini TOML: unsupported table header (line {no})",
    ),
    "toml_conflicting_key": (
        "mini TOML: çakışan anahtar (satır {no})",
        "mini TOML: conflicting key (line {no})",
    ),
    "toml_unparsable_line": (
        "mini TOML: çözülemeyen satır {no}: {govde!r}",
        "mini TOML: could not parse line {no}: {govde!r}",
    ),
    "toml_unclosed": (
        "mini TOML: kapanmamış dizi/tablo (satır {no})",
        "mini TOML: unclosed array/table (line {no})",
    ),
    # --- CLI yardım metinleri (``--help`` de seçilen dilde basılır) -----------
    "cli_description": (
        "Dağılmış çalışma zamanı sürüm sabitlemelerini denetle ve senkronla.",
        "Check and sync scattered runtime version pins.",
    ),
    "cli_help_flag": (
        "bu yardımı göster ve çık",
        "show this help message and exit",
    ),
    "cli_version_flag": (
        "program sürümünü göster ve çık",
        "show program's version number and exit",
    ),
    "cli_path": (
        "depo kökü (varsayılan: .)",
        "repository root (default: .)",
    ),
    "cli_json": (
        "makine okuyabilir JSON çıktı",
        "machine-readable JSON output",
    ),
    "cli_source": (
        "tek gerçek kaynak dosya (ör. .tool-versions)",
        "single source of truth file (e.g. .tool-versions)",
    ),
    "cli_variable": (
        "çözülemeyen CI ifadesi için değer ver (AD=DEĞER)",
        "value for an unresolved CI expression (NAME=VALUE)",
    ),
    "cli_lang": (
        "çıktının ve bu yardımın dili (varsayılan: tr; RUNTIME_PIN_SYNC_LANG)",
        "language of the output and of this help (default: tr; RUNTIME_PIN_SYNC_LANG)",
    ),
    "cli_dry_run": (
        "dosyaları değiştirmeden göster",
        "show changes without modifying files",
    ),
}


def m(lang: str, anahtar: str, **kw: object) -> str:
    """Katalogdan istenen dildeki mesajı biçimlendirir."""
    tr, en = MESAJLAR[anahtar]
    return (en if lang == "en" else tr).format(**kw)
