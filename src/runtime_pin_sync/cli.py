"""Komut satırı arayüzü.

    runtime-pin-sync [yol] [--json] [--kaynak DOSYA] [--degisken AD=DEĞER]
    runtime-pin-sync sync [yol] --kaynak DOSYA [--dry-run]

Çıkış kodları: 0 = uyumlu; 1 = çelişki (ya da elle düzeltme gerekti);
2 = kullanım/yol hatası.
"""

from __future__ import annotations

import argparse
import json
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
        description="Dağılmış sürüm sabitlemelerini denetle ve senkronla.",
    )
    p.add_argument("--version", "-V", action="version",
                   version=f"runtime-pin-sync {__version__}")
    p.add_argument("yol", nargs="?", default=".",
                   help="depo kökü (varsayılan: .)")
    p.add_argument("--json", action="store_true", dest="json",
                   help="makine okuyabilir JSON çıktı")
    p.add_argument("--kaynak", "--source", dest="kaynak", metavar="DOSYA",
                   help="tek gerçek kaynak dosya (ör. .tool-versions)")
    p.add_argument("--degisken", "--variable", dest="degiskenler",
                   action="append", default=[], metavar="AD=DEĞER",
                   help="çözülemeyen CI ifadeleri için değer ver (tekrarlanabilir)")
    if sync_kipi:
        p.add_argument("--dry-run", "--kuru", action="store_true", dest="dry_run",
                       help="dosyaları değiştirmeden göster")
    else:
        p.set_defaults(dry_run=False)
    return p


def _degisken_çöz(girdiler: list[str]) -> dict[str, str]:
    sonuc: dict[str, str] = {}
    for g in girdiler:
        ad, sep, deger = g.partition("=")
        if not sep or not ad.strip():
            raise ValueError(f"--degisken 'AD=DEĞER' biçiminde olmalı: {g!r}")
        sonuc[ad.strip()] = deger.strip()
    return sonuc


def main(argv: Sequence[str] | None = None) -> int:
    girdi = list(sys.argv[1:] if argv is None else argv)
    komut = "check"
    if girdi and girdi[0] in ("sync", "check"):
        komut = girdi.pop(0)
    args = _parser(komut == "sync").parse_args(girdi)
    try:
        degiskenler = _degisken_çöz(list(args.degiskenler))
    except ValueError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2
    norm_kaynak = norm_yol(args.kaynak) if args.kaynak else None
    try:
        pimler = tara(args.yol, degiskenler)
    except (ValueError, OSError) as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2
    if norm_kaynak is not None and not kaynak_kontrol(pimler, norm_kaynak):
        print(f"hata: kaynak bulunamadı ya da sürüm üretmiyor: {args.kaynak}",
              file=sys.stderr)
        return 2
    celiskiler = celiski(pimler, kaynak=norm_kaynak)

    if komut == "sync":
        if not args.kaynak:
            print("hata: sync için --kaynak gerekli (tek gerçek kaynak dosya)",
                  file=sys.stderr)
            return 2
        return _sync(args, degiskenler)

    if args.json:
        print(json.dumps(json_sözlüğü(pimler, celiskiler, norm_kaynak),
                         ensure_ascii=False, indent=2))
    else:
        print(tablo(pimler, celiskiler, norm_kaynak))
    return 1 if celiskiler else 0


def _sync(args: argparse.Namespace, degiskenler: dict[str, str]) -> int:
    try:
        otomatik, elle = senkronla(args.yol, args.kaynak, args.dry_run, degiskenler)
    except (ValueError, OSError) as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 2
    etiket = "değiştirilecek" if args.dry_run else "değiştirildi"
    if args.json:
        cikti = {
            "kuru_calis": args.dry_run,
            "degisiklikler": [vars(d) for d in otomatik],
            "elle": [vars(d) for d in elle],
        }
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
    else:
        if otomatik:
            for d in otomatik:
                print(f"{d.dosya}:{d.satir}  {d.eski!r} → {d.yeni!r} ({etiket})")
        if elle:
            print("\nELLE DÜZELTİLMELİ:")
            for d in elle:
                print(f"  {d.dosya}:{d.satir}  ({d.eski!r} → {d.yeni!r}) {d.gerekce}")
        if not otomatik and not elle:
            print("senkronlanacak bir şey yok — her şey zaten kaynakla uyumlu.")
    return 1 if elle else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
