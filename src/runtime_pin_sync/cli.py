"""Komut satırı arayüzü.

    runtime-pin-sync [yol] [--json] [--kaynak DOSYA] [--degisken AD=DEĞER] [--lang tr|en]
    runtime-pin-sync sync [yol] --kaynak DOSYA [--dry-run] [--lang tr|en]

Çıkış kodları: 0 = uyumlu; 1 = çelişki (ya da elle düzeltme gerekti);
2 = kullanım/yol hatası.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from collections.abc import Sequence

from . import __version__
from .karsilastir import celiski
from .rapor import json_sözlüğü, tablo
from .tara import kaynak_kontrol, tara
from .yaz import norm_yol, senkronla

__all__ = ["main"]


def _parser(sync_kipi: bool) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="runtime-pin-sync",
        description="Dağılmış sürüm sabitlemelerini denetle ve senkronla / Check and sync runtime pins.",
    )
    p.add_argument("--version", "-V", action="version",
                   version=f"runtime-pin-sync {__version__}")
    p.add_argument("yol", nargs="?", default=".",
                   help="depo kökü (varsayılan: .) / repository root (default: .)")
    p.add_argument("--json", action="store_true", dest="json",
                   help="makine okuyabilir JSON çıktı / machine-readable JSON output")
    p.add_argument("--kaynak", "--source", dest="kaynak", metavar="DOSYA",
                   help="tek gerçek kaynak dosya (ör. .tool-versions) / single source of truth")
    p.add_argument("--degisken", "--variable", dest="degiskenler",
                   action="append", default=[], metavar="AD=DEĞER",
                   help="çözülemeyen CI ifadeleri için değer ver / provide value for CI expression")
    p.add_argument("--lang", choices=["tr", "en"], default=None,
                   help="çıktı dili / output language (tr|en, varsayılan: tr)")
    if sync_kipi:
        p.add_argument("--dry-run", "--kuru", action="store_true", dest="dry_run",
                       help="dosyaları değiştirmeden göster / show changes without modifying files")
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


def _gerekce_cevir(gerekce: str, lang: str) -> str:
    if lang != "en":
        return gerekce
    if "aynı satırda birden fazla hedef" in gerekce:
        return "multiple targets on the same line"
    if "senkron sonrası çelişki giderilmedi" in gerekce:
        return "conflict remains unresolved after sync"
    if "sabit sürüm değil" in gerekce:
        return (
            gerekce.replace("referans", "reference")
            .replace("sabit sürüm değil (aralık/ızgara); yazılmaz",
                     "is not a pinned version (range/matrix); will not rewrite")
        )
    if "uygulanamadı:" in gerekce:
        return gerekce.replace("uygulanamadı:", "failed to apply:")
    return gerekce


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
    args = _parser(komut == "sync").parse_args(girdi)
    lang = (args.lang or os.environ.get("RUNTIME_PIN_SYNC_LANG", "tr")).lower()
    if lang not in ("tr", "en"):
        lang = "tr"
    err_prefix = "error" if lang == "en" else "hata"

    try:
        degiskenler = _degisken_çöz(list(args.degiskenler), lang=lang)
    except ValueError as exc:
        print(f"{err_prefix}: {exc}", file=sys.stderr)
        return 2

    norm_kaynak = norm_yol(args.kaynak) if args.kaynak else None
    try:
        pimler = tara(args.yol, degiskenler)
    except (ValueError, OSError) as exc:
        print(f"{err_prefix}: {exc}", file=sys.stderr)
        return 2

    if norm_kaynak is not None and not kaynak_kontrol(pimler, norm_kaynak):
        msg = (
            f"source not found or yields no versions: {args.kaynak}"
            if lang == "en"
            else f"kaynak bulunamadı ya da sürüm üretmiyor: {args.kaynak}"
        )
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
        otomatik, elle = senkronla(args.yol, args.kaynak, args.dry_run, degiskenler)
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
                gerekce = _gerekce_cevir(d.gerekce, lang)
                print(f"  {d.dosya}:{d.satir}  ({d.eski!r} → {d.yeni!r}) {gerekce}")
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
