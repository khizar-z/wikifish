"""dump_compiler.py

Compiler for turning Wikimedia SQL dump snapshots into WikiFish artifacts.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
import glob
import gzip
import json
import os
import sqlite3
import time

from wiki_backend import INVALID_U32, write_numeric_array


@dataclass(frozen=True)
class _PageRecord:
    """Metadata about a page row in the source dump."""
    page_id: int
    title: str
    is_redirect: bool


class _ProgressLogger:
    """Simple stage-based logger for long-running compile jobs."""

    _compile_start: float
    _stage_start: float | None

    def __init__(self) -> None:
        self._compile_start = time.perf_counter()
        self._stage_start = None

    def log(self, message: str) -> None:
        """Print a progress message with elapsed compile time."""
        elapsed = time.perf_counter() - self._compile_start
        print(f'[{elapsed:8.1f}s] {message}', flush=True)

    def begin_stage(self, name: str) -> None:
        """Mark the start of a stage."""
        self._stage_start = time.perf_counter()
        self.log(f'START  {name}')

    def end_stage(self, name: str, extra: str = '') -> None:
        """Mark the end of a stage."""
        stage_elapsed = 0.0 if self._stage_start is None else time.perf_counter() - self._stage_start
        suffix = f' | {extra}' if extra else ''
        self.log(f'END    {name} ({stage_elapsed:.1f}s){suffix}')
        self._stage_start = None

    def heartbeat(self, stage_name: str, row_count: int) -> None:
        """Print an in-stage heartbeat for large dump scans."""
        stage_elapsed = 0.0 if self._stage_start is None else time.perf_counter() - self._stage_start
        self.log(f'... {stage_name}: processed {row_count:,} rows ({stage_elapsed:.1f}s in stage)')


def compile_dump_snapshot(
    dump_dir: str,
    output_dir: str,
    wiki: str = 'enwiki',
    snapshot_date: str | None = None
) -> None:
    """Compile a Wikimedia SQL dump directory into WikiFish runtime artifacts."""
    logger = _ProgressLogger()
    page_path = _locate_dump_file(dump_dir, 'page.sql.gz')
    redirect_path = _locate_dump_file(dump_dir, 'redirect.sql.gz')
    linktarget_path = _locate_dump_file(dump_dir, 'linktarget.sql.gz')
    pagelinks_path = _locate_dump_file(dump_dir, 'pagelinks.sql.gz')
    categorylinks_path = _locate_dump_file(dump_dir, 'categorylinks.sql.gz')

    snapshot_date = snapshot_date or _derive_snapshot_date(page_path)
    os.makedirs(output_dir, exist_ok=True)

    logger.log(f'Output directory: {output_dir}')
    logger.log(f'Snapshot date: {snapshot_date}')
    logger.log(f'Input file: {os.path.basename(page_path)} ({_format_bytes(os.path.getsize(page_path))})')
    logger.log(f'Input file: {os.path.basename(redirect_path)} ({_format_bytes(os.path.getsize(redirect_path))})')
    logger.log(f'Input file: {os.path.basename(linktarget_path)} ({_format_bytes(os.path.getsize(linktarget_path))})')
    logger.log(f'Input file: {os.path.basename(pagelinks_path)} ({_format_bytes(os.path.getsize(pagelinks_path))})')
    logger.log(f'Input file: {os.path.basename(categorylinks_path)} ({_format_bytes(os.path.getsize(categorylinks_path))})')

    logger.begin_stage('load page table')
    pages, title_to_page_id = _load_pages(page_path, logger)
    logger.end_stage('load page table', f'{len(pages):,} namespace-0 pages')

    logger.begin_stage('load redirect table')
    redirect_targets = _load_redirects(redirect_path, pages, logger)
    logger.end_stage('load redirect table', f'{len(redirect_targets):,} redirects')

    logger.begin_stage('resolve redirect chains')
    resolved_redirects = _resolve_redirects(pages, title_to_page_id, redirect_targets)
    logger.end_stage('resolve redirect chains', f'{len(resolved_redirects):,} canonicalized redirects')

    canonical_page_ids = sorted(
        page_id
        for page_id, page in pages.items()
        if not page.is_redirect
    )
    dense_id_by_page_id = {page_id: index for index, page_id in enumerate(canonical_page_ids)}
    article_count = len(canonical_page_ids)
    logger.log(f'Canonical article count: {article_count:,}')

    logger.begin_stage('load linktarget table')
    linktarget_dense = _load_linktargets(
        linktarget_path,
        title_to_page_id,
        resolved_redirects,
        dense_id_by_page_id,
        logger
    )
    logger.end_stage('load linktarget table', f'{len(linktarget_dense):,} linktarget slots')

    logger.begin_stage('count pagelinks edges')
    out_counts, in_counts = _count_edges(
        pagelinks_path,
        dense_id_by_page_id,
        linktarget_dense,
        logger
    )
    total_edges = sum(out_counts)
    logger.end_stage('count pagelinks edges', f'{total_edges:,} edges kept')

    logger.begin_stage('build adjacency offsets')
    forward_offsets = _prefix_sum_offsets(out_counts)
    reverse_offsets = _prefix_sum_offsets(in_counts)
    logger.end_stage('build adjacency offsets')

    logger.begin_stage('fill adjacency arrays')
    forward_neighbors, reverse_neighbors = _fill_edges(
        pagelinks_path,
        dense_id_by_page_id,
        linktarget_dense,
        forward_offsets,
        reverse_offsets,
        logger
    )
    logger.end_stage(
        'fill adjacency arrays',
        f'forward={len(forward_neighbors):,} reverse={len(reverse_neighbors):,}'
    )

    logger.begin_stage('count categorylinks')
    category_counts = _count_categories(categorylinks_path, dense_id_by_page_id, logger)
    logger.end_stage('count categorylinks', f'{sum(category_counts):,} category memberships')

    logger.begin_stage('build category offsets')
    category_offsets = _prefix_sum_offsets(category_counts)
    logger.end_stage('build category offsets')

    logger.begin_stage('fill category arrays')
    category_ids = _fill_categories(categorylinks_path, dense_id_by_page_id, category_offsets, logger)
    logger.end_stage('fill category arrays', f'{len(category_ids):,} stored category ids')

    logger.begin_stage('write sqlite catalog')
    _write_catalog(
        os.path.join(output_dir, 'catalog.db'),
        pages,
        canonical_page_ids,
        dense_id_by_page_id,
        resolved_redirects
    )
    logger.end_stage('write sqlite catalog')

    logger.begin_stage('write binary artifacts')
    write_numeric_array(os.path.join(output_dir, 'forward_offsets.bin'), forward_offsets, 'Q')
    write_numeric_array(os.path.join(output_dir, 'forward_neighbors.bin'), forward_neighbors, 'I')
    write_numeric_array(os.path.join(output_dir, 'reverse_offsets.bin'), reverse_offsets, 'Q')
    write_numeric_array(os.path.join(output_dir, 'reverse_neighbors.bin'), reverse_neighbors, 'I')
    write_numeric_array(os.path.join(output_dir, 'category_offsets.bin'), category_offsets, 'Q')
    write_numeric_array(os.path.join(output_dir, 'category_ids.bin'), category_ids, 'I')
    logger.end_stage('write binary artifacts')

    manifest = {
        'wiki': wiki,
        'snapshot_date': snapshot_date,
        'article_count': article_count,
        'format_version': 1,
        'catalog': 'catalog.db',
        'forward_offsets': 'forward_offsets.bin',
        'forward_neighbors': 'forward_neighbors.bin',
        'reverse_offsets': 'reverse_offsets.bin',
        'reverse_neighbors': 'reverse_neighbors.bin',
        'category_offsets': 'category_offsets.bin',
        'category_ids': 'category_ids.bin',
    }
    logger.begin_stage('write manifest')
    with open(os.path.join(output_dir, 'manifest.json'), 'w') as file:
        json.dump(manifest, file, indent=2)
    logger.end_stage('write manifest')
    logger.log('Compilation finished successfully.')


def _locate_dump_file(dump_dir: str, suffix: str) -> str:
    matches = sorted(glob.glob(os.path.join(dump_dir, f'*-{suffix}')))
    if not matches:
        raise FileNotFoundError(f'Could not find *-{suffix} in {dump_dir}')
    return matches[0]


def _derive_snapshot_date(page_path: str) -> str:
    filename = os.path.basename(page_path)
    parts = filename.split('-')
    if len(parts) >= 3 and parts[1].isdigit() and len(parts[1]) == 8:
        return f'{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}'
    return 'latest'


def _load_pages(page_path: str, logger: _ProgressLogger) -> tuple[dict[int, _PageRecord], dict[str, int]]:
    pages = {}
    title_to_page_id = {}
    for row in iter_sql_rows(page_path, logger, 'page rows'):
        page_id = int(row[0])
        namespace = int(row[1])
        if namespace != 0:
            continue

        title = _canonicalise_db_title(str(row[2]))
        is_redirect = bool(int(row[3]))
        pages[page_id] = _PageRecord(page_id=page_id, title=title, is_redirect=is_redirect)
        title_to_page_id[title] = page_id
    return pages, title_to_page_id


def _load_redirects(
    redirect_path: str,
    pages: dict[int, _PageRecord],
    logger: _ProgressLogger
) -> dict[int, str]:
    redirect_targets = {}
    for row in iter_sql_rows(redirect_path, logger, 'redirect rows'):
        source_page_id = int(row[0])
        namespace = int(row[1])
        if namespace != 0 or source_page_id not in pages:
            continue
        redirect_targets[source_page_id] = _canonicalise_db_title(str(row[2]))
    return redirect_targets


def _resolve_redirects(
    pages: dict[int, _PageRecord],
    title_to_page_id: dict[str, int],
    redirect_targets: dict[int, str]
) -> dict[int, int]:
    resolved = {}
    resolution_cache: dict[int, int | None] = {}

    def resolve_page(page_id: int, seen: set[int]) -> int | None:
        if page_id in resolution_cache:
            return resolution_cache[page_id]
        if page_id in seen:
            resolution_cache[page_id] = None
            return None

        seen.add(page_id)
        page = pages[page_id]
        if not page.is_redirect:
            resolution_cache[page_id] = page_id
            seen.remove(page_id)
            return page_id

        target_title = redirect_targets.get(page_id)
        target_page_id = title_to_page_id.get(target_title or '')
        if target_page_id is None:
            resolution_cache[page_id] = None
            seen.remove(page_id)
            return None

        resolved_target = resolve_page(target_page_id, seen)
        resolution_cache[page_id] = resolved_target
        seen.remove(page_id)
        return resolved_target

    for page_id, page in pages.items():
        if page.is_redirect:
            resolved_page_id = resolve_page(page_id, set())
            if resolved_page_id is not None and resolved_page_id != page_id:
                resolved[page_id] = resolved_page_id

    return resolved


def _load_linktargets(
    linktarget_path: str,
    title_to_page_id: dict[str, int],
    resolved_redirects: dict[int, int],
    dense_id_by_page_id: dict[int, int],
    logger: _ProgressLogger
) -> array:
    lookup = array('I', [INVALID_U32])

    for row in iter_sql_rows(linktarget_path, logger, 'linktarget rows'):
        linktarget_id = int(row[0])
        namespace = int(row[1])
        if namespace != 0:
            continue

        title = _canonicalise_db_title(str(row[2]))
        page_id = title_to_page_id.get(title)
        if page_id is None:
            continue

        canonical_page_id = resolved_redirects.get(page_id, page_id)
        dense_id = dense_id_by_page_id.get(canonical_page_id)
        if dense_id is None:
            continue

        _ensure_array_length(lookup, linktarget_id + 1, INVALID_U32)
        lookup[linktarget_id] = dense_id

    return lookup


def _count_edges(
    pagelinks_path: str,
    dense_id_by_page_id: dict[int, int],
    linktarget_dense: array,
    logger: _ProgressLogger
) -> tuple[list[int], list[int]]:
    article_count = len(dense_id_by_page_id)
    out_counts = [0] * article_count
    in_counts = [0] * article_count

    for row in iter_sql_rows(pagelinks_path, logger, 'pagelinks rows (count pass)'):
        source_page_id = int(row[0])
        source_namespace = int(row[1])
        linktarget_id = int(row[2])

        if source_namespace != 0:
            continue

        source_dense = dense_id_by_page_id.get(source_page_id)
        if source_dense is None:
            continue
        if linktarget_id >= len(linktarget_dense):
            continue

        target_dense = int(linktarget_dense[linktarget_id])
        if target_dense == INVALID_U32 or target_dense == source_dense:
            continue

        out_counts[source_dense] += 1
        in_counts[target_dense] += 1

    return out_counts, in_counts


def _fill_edges(
    pagelinks_path: str,
    dense_id_by_page_id: dict[int, int],
    linktarget_dense: array,
    forward_offsets: array,
    reverse_offsets: array,
    logger: _ProgressLogger
) -> tuple[array, array]:
    total_edges = int(forward_offsets[-1])
    forward_neighbors = array('I', [0]) * total_edges
    reverse_neighbors = array('I', [0]) * int(reverse_offsets[-1])
    forward_positions = [int(offset) for offset in forward_offsets[:-1]]
    reverse_positions = [int(offset) for offset in reverse_offsets[:-1]]

    for row in iter_sql_rows(pagelinks_path, logger, 'pagelinks rows (fill pass)'):
        source_page_id = int(row[0])
        source_namespace = int(row[1])
        linktarget_id = int(row[2])

        if source_namespace != 0:
            continue

        source_dense = dense_id_by_page_id.get(source_page_id)
        if source_dense is None:
            continue
        if linktarget_id >= len(linktarget_dense):
            continue

        target_dense = int(linktarget_dense[linktarget_id])
        if target_dense == INVALID_U32 or target_dense == source_dense:
            continue

        forward_neighbors[forward_positions[source_dense]] = target_dense
        forward_positions[source_dense] += 1
        reverse_neighbors[reverse_positions[target_dense]] = source_dense
        reverse_positions[target_dense] += 1

    return forward_neighbors, reverse_neighbors


def _count_categories(
    categorylinks_path: str,
    dense_id_by_page_id: dict[int, int],
    logger: _ProgressLogger
) -> list[int]:
    category_counts = [0] * len(dense_id_by_page_id)
    for row in iter_sql_rows(categorylinks_path, logger, 'categorylinks rows (count pass)'):
        page_id = int(row[0])
        dense_id = dense_id_by_page_id.get(page_id)
        if dense_id is None:
            continue
        category_counts[dense_id] += 1
    return category_counts


def _fill_categories(
    categorylinks_path: str,
    dense_id_by_page_id: dict[int, int],
    category_offsets: array,
    logger: _ProgressLogger
) -> array:
    category_ids = array('I', [0]) * int(category_offsets[-1])
    positions = [int(offset) for offset in category_offsets[:-1]]
    category_name_to_id: dict[str, int] = {}

    for row in iter_sql_rows(categorylinks_path, logger, 'categorylinks rows (fill pass)'):
        page_id = int(row[0])
        dense_id = dense_id_by_page_id.get(page_id)
        if dense_id is None:
            continue

        category_name = str(row[1])
        if category_name not in category_name_to_id:
            category_name_to_id[category_name] = len(category_name_to_id)

        category_ids[positions[dense_id]] = category_name_to_id[category_name]
        positions[dense_id] += 1

    return category_ids


def _write_catalog(
    catalog_path: str,
    pages: dict[int, _PageRecord],
    canonical_page_ids: list[int],
    dense_id_by_page_id: dict[int, int],
    resolved_redirects: dict[int, int]
) -> None:
    if os.path.exists(catalog_path):
        os.remove(catalog_path)

    connection = sqlite3.connect(catalog_path)
    cursor = connection.cursor()
    cursor.executescript(
        """
        CREATE TABLE pages (
            dense_id INTEGER PRIMARY KEY,
            page_id INTEGER NOT NULL UNIQUE,
            title TEXT NOT NULL UNIQUE
        );

        CREATE TABLE aliases (
            alias TEXT PRIMARY KEY,
            dense_id INTEGER NOT NULL,
            canonical_title TEXT NOT NULL,
            redirected_from TEXT
        );
        """
    )

    for page_id in canonical_page_ids:
        dense_id = dense_id_by_page_id[page_id]
        title = pages[page_id].title
        cursor.execute(
            "INSERT INTO pages (dense_id, page_id, title) VALUES (?, ?, ?)",
            (dense_id, page_id, title)
        )
        cursor.execute(
            "INSERT INTO aliases (alias, dense_id, canonical_title, redirected_from) VALUES (?, ?, ?, ?)",
            (title, dense_id, title, None)
        )

    for redirect_page_id, canonical_page_id in resolved_redirects.items():
        alias = pages[redirect_page_id].title
        dense_id = dense_id_by_page_id[canonical_page_id]
        canonical_title = pages[canonical_page_id].title
        cursor.execute(
            "INSERT OR REPLACE INTO aliases (alias, dense_id, canonical_title, redirected_from) VALUES (?, ?, ?, ?)",
            (alias, dense_id, canonical_title, alias)
        )

    connection.commit()
    connection.close()


def _prefix_sum_offsets(counts: list[int]) -> array:
    offsets = array('Q', [0])
    running_total = 0
    for count in counts:
        running_total += count
        offsets.append(running_total)
    return offsets


def _ensure_array_length(values: array, required_length: int, fill_value: int) -> None:
    if required_length <= len(values):
        return
    values.extend([fill_value] * (required_length - len(values)))


def _canonicalise_db_title(title: str) -> str:
    return title.replace('_', ' ')


def iter_sql_rows(
    path: str,
    logger: _ProgressLogger | None = None,
    stage_name: str | None = None,
    log_every_rows: int = 1_000_000
):
    """Yield parsed rows from a Wikimedia SQL dump."""
    row_count = 0
    with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as file:
        buffer = ''
        for line in file:
            if buffer:
                buffer += line
                if line.rstrip().endswith(';'):
                    for row in _rows_from_insert(buffer):
                        row_count += 1
                        if logger is not None and stage_name is not None and row_count % log_every_rows == 0:
                            logger.heartbeat(stage_name, row_count)
                        yield row
                    buffer = ''
                continue

            if not line.startswith('INSERT INTO'):
                continue
            if line.rstrip().endswith(';'):
                for row in _rows_from_insert(line):
                    row_count += 1
                    if logger is not None and stage_name is not None and row_count % log_every_rows == 0:
                        logger.heartbeat(stage_name, row_count)
                    yield row
            else:
                buffer = line

    if logger is not None and stage_name is not None:
        logger.log(f'Completed {stage_name}: {row_count:,} rows total')


def _rows_from_insert(statement: str):
    values_index = statement.index('VALUES') + len('VALUES')
    values_blob = statement[values_index:].strip()
    yield from _parse_values_blob(values_blob)


def _parse_values_blob(values_blob: str):
    row = None
    token = []
    token_was_quoted = False
    in_string = False
    escape = False

    def flush_token() -> str | None:
        nonlocal token, token_was_quoted
        value = _finish_token(token, token_was_quoted)
        token = []
        token_was_quoted = False
        return value

    for char in values_blob:
        if in_string:
            if escape:
                token.append(_decode_escape(char))
                escape = False
            elif char == '\\':
                escape = True
            elif char == "'":
                in_string = False
            else:
                token.append(char)
            continue

        if char == '(':
            row = []
            token = []
            token_was_quoted = False
        elif char == ')':
            if row is not None:
                row.append(flush_token())
                yield row
                row = None
        elif char == ',':
            if row is not None:
                row.append(flush_token())
        elif char == "'":
            in_string = True
            token_was_quoted = True
        elif char == ';':
            break
        else:
            if row is not None:
                token.append(char)


def _finish_token(token: list[str], token_was_quoted: bool) -> str | None:
    if token_was_quoted:
        return ''.join(token)

    raw = ''.join(token).strip()
    if raw == '' or raw.upper() == 'NULL':
        return None
    return raw


def _decode_escape(char: str) -> str:
    escapes = {
        '0': '\0',
        'b': '\b',
        'n': '\n',
        'r': '\r',
        't': '\t',
        'Z': '\x1a',
        '\\': '\\',
        "'": "'",
    }
    return escapes.get(char, char)


def _format_bytes(size: int) -> str:
    """Return a short human-readable byte count."""
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    value = float(size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f'{value:.1f} {unit}'
        value /= 1024.0
    return f'{size} B'
