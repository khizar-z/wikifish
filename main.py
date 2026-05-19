"""main.py

CLI entry point for compiling or serving WikiFish datasets.
"""
from __future__ import annotations

import argparse
import os

import app as wikifish_app
from dump_compiler import compile_dump_snapshot
from load_graph import load_snap_backend
from wiki_backend import DumpBackend, WikiBackend


DEFAULT_SNAPSHOT_DIR = os.path.join('data', 'enwiki_snapshot')
LEGACY_FILES = (
    'wiki-topcats.txt',
    'wiki-topcats-page-names.txt',
    'wiki-topcats-categories.txt',
)


def parse_args() -> argparse.Namespace:
    """Return parsed CLI arguments."""
    parser = argparse.ArgumentParser(description='Run or compile WikiFish datasets.')
    subparsers = parser.add_subparsers(dest='command')

    compile_parser = subparsers.add_parser('compile', help='Compile Wikimedia SQL dumps into WikiFish artifacts.')
    compile_parser.add_argument('--dump-dir', required=True, help='Directory containing Wikimedia SQL dump files.')
    compile_parser.add_argument('--output-dir', default=DEFAULT_SNAPSHOT_DIR, help='Destination for compiled artifacts.')
    compile_parser.add_argument('--wiki', default='enwiki', help='Wiki identifier to record in the manifest.')
    compile_parser.add_argument('--snapshot-date', default=None, help='Override the snapshot date stored in the manifest.')

    serve_parser = subparsers.add_parser('serve', help='Start the Dash application.')
    serve_parser.add_argument('--data-dir', default=DEFAULT_SNAPSHOT_DIR, help='Compiled snapshot artifact directory.')

    parser.set_defaults(command='serve')
    return parser.parse_args()


def load_backend(data_dir: str = DEFAULT_SNAPSHOT_DIR) -> WikiBackend:
    """Load the best available backend for the current environment."""
    manifest_path = os.path.join(data_dir, 'manifest.json')
    if os.path.exists(manifest_path):
        print(f'Loading compiled snapshot from {data_dir} ...')
        return DumpBackend(data_dir)

    if all(os.path.exists(path) for path in LEGACY_FILES):
        print('Loading legacy SNAP graph (this will take 30-60 seconds)...')
        return load_snap_backend(*LEGACY_FILES)

    raise FileNotFoundError(
        'No compiled snapshot found and legacy wiki-topcats files are missing. '
        'Run `python main.py compile --dump-dir <path>` first.'
    )


def main() -> None:
    """Run the requested CLI action."""
    args = parse_args()

    if args.command == 'compile':
        print(f'Compiling Wikimedia dump from {args.dump_dir} into {args.output_dir} ...')
        compile_dump_snapshot(
            dump_dir=args.dump_dir,
            output_dir=args.output_dir,
            wiki=args.wiki,
            snapshot_date=args.snapshot_date,
        )
        print('Compilation complete.')
        return

    loaded_backend = load_backend(args.data_dir)
    print('Starting server at http://127.0.0.1:8050 ...')
    wikifish_app.init(loaded_backend)


if __name__ == '__main__':
    main()
