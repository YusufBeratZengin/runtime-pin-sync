"""Komut satırı arayüzü.

    runtime-pin-sync [yol] [--json] [--kaynak DOSYA] [--degisken AD=DEĞER] [--lang tr|en]
    runtime-pin-sync sync [yol] --kaynak DOSYA [--dry-run] [--lang tr|en]

Çıkış kodları: 0 = uyumlu; 1 = çelişki (ya da elle düzeltme gerekti);
2 = kullanım/yol hatası.

``--help`` metni de seçilen dilde basılır: ``--lang en`` (ya da
``RUNTIME_PIN_SYNC_LANG=en``) hem tabloyu hem yardımı çevirir.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from collections.abc import Sequence

from . import __version__
from .dil import m
from .karsilastir import celiski
from .rapor import json_sözlüğü, tablo
from .tara import kaynak_kontrol, tara, tarama_hatalari
from .yaz import norm_yol, senkronla

__all__ = ["main"]

# argparse'in sabit İngilizce iskelet etiketleri; ``tr`` yardımında çevrilir.
_YARDIM_BASLIKLARI = {
    "positional arguments": "konumsal argümanlar",
    "options": "seçenekler",
}


class _DilliParser(argparse.ArgumentParser):
    """argparse'in sabit etiketlerini (``usage:``, bölüm başlıkları) dile uydurur.

    Açıklama ve seçenek metinleri katalogdan gelir; argparse'ın kendi ürettiği
    iskelet ise İngilizcedir. Yalnız bu iskelet çevrilir — kullanıcı metinlerine
    dokunulmaz (metinlerde bu etiketler geçmez, testle sabitlenmiştir).
    """

    dil: str = "tr"

    def format_help(self) -> str:
        metin = super().format_help()
        if self.dil == "en":
            return metin
        metin = _kullanim_onekini_cevir(metin)
        for ingilizce, turkce in _YARDIM_BASLIKLARI.items():
            metin = metin.replace(f"\n{ingilizce}:", f"\n{turkce}:")
        return metin


def _kullanim_onekini_cevir(metin: str) -> str:
    """``usage:`` -> ``kullanım:``; sarmalanmış satırların girintisini korur.

    argparse sürekli satırları ön ek genişliğine göre hizalar; ön ek
    uzadığında hiza kaymasın diye usage bloğunun devam satırları kaydırılır.
    """
    eski, yeni = "usage: ", "kullanım: "
    if not metin.startswith(eski):
        return metin
    fark = len(yeni) - len(eski)
    satirlar = metin.split("\n")
    satirlar[0] = yeni + satirlar[0][len(eski):]
    i = 1
    while i < len(satirlar) and satirlar[i].strip():
        satirlar[i] = " " * fark + satirlar[i]
        i += 1
    return "\n".join(satirlar)


def _dil_belirle(lang: str | None) -> str:
    """Geçerli dili seçer: açık bayrak > ortam değişkeni > ``tr``.

    Tanınmayan değer sessizce ``tr``'ye düşer (parçalanmış çıktı üretmemek
    için); ``--lang`` zaten ``choices`` ile sınırlıdır.
    """
    secili = (lang or os.environ.get("RUNTIME_PIN_SYNC_LANG") or "tr").lower()
    return secili if secili in ("tr", "en") else "tr"


def _lang_on_tarama(girdi: list[str]) -> str | None:
    """``parse_args``'tan ÖNCE ``--lang`` değerini bulur.

    Yardım metni argparse tarafından, yani dil bilinmeden üretilir; bu ön
    tarama olmadan ``--lang en --help`` İngilizce çıktı vaat edip Türkçe
    yardım basardı. ``--lang=en`` biçimi de desteklenir.
    """
    for i, a in enumerate(girdi):
        if a == "--lang":
            return girdi[i + 1] if i + 1 < len(girdi) else None
        if a.startswith("--lang="):
            return a.split("=", 1)[1]
    return None


def _parser(sync_kipi: bool, lang: str = "tr") -> argparse.ArgumentParser:
    def y(anahtar: str) -> str:
        return m(lang, anahtar)

    p = _DilliParser(
        prog="runtime-pin-sync",
        description=y("cli_description"),
        add_help=False,  # kendi -h metnimiz dil seçimini izlesin
    )
    p.dil = lang
    p.add_argument("-h", "--help", action="help", help=y("cli_help_flag"))
    p.add_argument("--version", "-V", action="version",
                   version=f"runtime-pin-sync {__version__}",
                   help=y("cli_version_flag"))
    p.add_argument("yol", nargs="?", default=".",
                   help=y("cli_path"))
    p.add_argument("--json", action="store_true", dest="json",
                   help=y("cli_json"))
    p.add_argument("--kaynak", "--source", dest="kaynak", metavar="DOSYA",
                   help=y("cli_source"))
    p.add_argument("--degisken", "--variable", dest="degiskenler",
                   action="append", default=[], metavar="AD=DEĞER",
                   help=y("cli_variable"))
    p.add_argument("--lang", choices=["tr", "en"], default=None,
                   help=y("cli_lang"))
    if sync_kipi:
        p.add_argument("--dry-run", "--kuru", action="store_true", dest="dry_run",
                       help=y("cli_dry_run"))
    else:
        p.set_defaults(dry_run=False)
    return p


def _degisken_çöz(girdiler: list[str], lang: str = "tr") -> dict[str, str]:
    sonuc: dict[str, str] = {}
    for g in girdiler:
        ad, sep, deger = g.partition("=")
        if not sep or not ad.strip():
            msg = (
                f"--variable must be in 'NAME=VALUE' format: {g!r}"
                if lang == "en"
                else f"--degisken 'AD=DEĞER' biçiminde olmalı: {g!r}"
            )
            raise ValueError(msg)
        sonuc[ad.strip()] = deger.strip()
    return sonuc


def main(argv: Sequence[str] | None = None) -> int:
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            with contextlib.suppress(Exception):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            with contextlib.suppress(Exception):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    girdi = list(sys.argv[1:] if argv is None else argv)
    komut = "check"
    if girdi and girdi[0] in ("sync", "check"):
        komut = girdi.pop(0)
    # yardım metni --lang'ı görmeden üretilir: dile göre parser kurulmadan önce
    # bayrağı ön taramayla oku (ortam değişkeni de aynı önceliği izler)
    lang = _dil_belirle(_lang_on_tarama(girdi))
    args = _parser(komut == "sync", lang).parse_args(girdi)
    lang = _dil_belirle(args.lang)
    err_prefix = "error" if lang == "en" else "hata"

    try:
        degiskenler = _degisken_çöz(list(args.degiskenler), lang=lang)
    except ValueError as exc:
        print(f"{err_prefix}: {exc}", file=sys.stderr)
        return 2

    norm_kaynak = norm_yol(args.kaynak) if args.kaynak else None
    try:
        pimler = tara(args.yol, degiskenler, lang=lang)
    except (ValueError, OSError) as exc:
        print(f"{err_prefix}: {exc}", file=sys.stderr)
        return 2

    # Eksik tarama "uyumlu" diye sunulamaz: görülmeyen dizin çelişki saklıyor
    # olabilir. check ve sync aynı sözleşmeyi uygular (exit 2).
    eksik = tarama_hatalari(pimler)
    if eksik:
        print(f"{err_prefix}: {m(lang, 'scan_incomplete', dizinler=', '.join(p.dosya for p in eksik))}",
              file=sys.stderr)
        return 2

    if norm_kaynak is not None and not kaynak_kontrol(pimler, norm_kaynak):
        msg = m(lang, "source_unusable", kaynak=args.kaynak)
        print(f"{err_prefix}: {msg}", file=sys.stderr)
        return 2

    celiskiler = celiski(pimler, kaynak=norm_kaynak)

    if komut == "sync":
        if not args.kaynak:
            msg = (
                "sync requires --source (single source of truth file)"
                if lang == "en"
                else "sync için --kaynak gerekli (tek gerçek kaynak dosya)"
            )
            print(f"{err_prefix}: {msg}", file=sys.stderr)
            return 2
        return _sync(args, degiskenler, lang=lang)

    if args.json:
        print(json.dumps(json_sözlüğü(pimler, celiskiler, norm_kaynak, lang=lang),
                         ensure_ascii=False, indent=2))
    else:
        print(tablo(pimler, celiskiler, norm_kaynak, lang=lang))
    return 1 if celiskiler else 0


def _sync(args: argparse.Namespace, degiskenler: dict[str, str], lang: str = "tr") -> int:
    err_prefix = "error" if lang == "en" else "hata"
    try:
        otomatik, elle = senkronla(args.yol, args.kaynak, args.dry_run,
                                  degiskenler, lang=lang)
    except (ValueError, OSError) as exc:
        print(f"{err_prefix}: {exc}", file=sys.stderr)
        return 2

    etiket = (
        ("to be changed" if args.dry_run else "changed")
        if lang == "en"
        else ("değiştirilecek" if args.dry_run else "değiştirildi")
    )

    if args.json:
        cikti = {
            "kuru_calis": args.dry_run,
            "dry_run": args.dry_run,
            "degisiklikler": [vars(d) for d in otomatik],
            "elle": [vars(d) for d in elle],
        }
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
    else:
        if otomatik:
            for d in otomatik:
                print(f"{d.dosya}:{d.satir}  {d.eski!r} → {d.yeni!r} ({etiket})")
        if elle:
            baslik = "\nMUST BE FIXED MANUALLY:" if lang == "en" else "\nELLE DÜZELTİLMELİ:"
            print(baslik)
            for d in elle:
                print(f"  {d.dosya}:{d.satir}  ({d.eski!r} → {d.yeni!r}) {d.gerekce}")
        if not otomatik and not elle:
            bos_msg = (
                "nothing to sync - all pins already match the source."
                if lang == "en"
                else "senkronlanacak bir şey yok — her şey zaten kaynakla uyumlu."
            )
            print(bos_msg)
    return 1 if elle else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
