#!/usr/bin/env python3
"""CLI entry point for downloading mugshot images.

Examples:
    python download.py --county jefferson --mode recent
    python download.py --county midlands --mode all
    python download.py --county orange --mode recent --output /path/to/dir
    python download.py --county orange --mode all --workers 4
"""
import argparse
import os
from config import IMAGES_DIR, NEW_IMAGES_DIR

COUNTIES = ('jefferson', 'midlands', 'orange', 'all')
MODES = ('recent', 'all')


def _download_county(county, output_dir, mode, workers):
    county_dir = os.path.join(output_dir, county.capitalize()) if mode == 'all' else output_dir
    if county == 'jefferson':
        from scrapers.jefferson import download
        download(county_dir, mode=mode)
    elif county == 'midlands':
        from scrapers.midlands import download
        download(county_dir, mode=mode)
    elif county == 'orange':
        from scrapers.orange_county import download
        download(county_dir, mode=mode, workers=workers)


def main():
    parser = argparse.ArgumentParser(description='Download mugshot images by county.')
    parser.add_argument('--county', choices=COUNTIES, required=True,
                        help='County to download from, or "all" for every county')
    parser.add_argument('--mode', choices=MODES, default='recent',
                        help='recent = new bookings only; all = bulk historical download')
    parser.add_argument('--output', default=None,
                        help='Output directory (default: newImages for recent, BlankSlate for all)')
    parser.add_argument('--workers', type=int, default=3,
                        help='Parallel browser instances for Orange County (default: 3)')
    args = parser.parse_args()

    output_dir = args.output or (NEW_IMAGES_DIR if args.mode == 'recent' else IMAGES_DIR)

    targets = ['jefferson', 'midlands', 'orange'] if args.county == 'all' else [args.county]

    for county in targets:
        print(f"\n--- Starting {county} ---")
        _download_county(county, output_dir, args.mode, args.workers)
        print(f"Done: {county} [{args.mode}] -> {output_dir}")


if __name__ == "__main__":
    main()
