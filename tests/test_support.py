"""Shared test helpers for WikiFish."""
from __future__ import annotations

import gzip
import os

from graph import Graph


def build_snap_fixture() -> tuple[Graph, dict[int, set[str]]]:
    """Return a small deterministic legacy graph fixture."""
    graph = Graph()
    pages = {
        1: 'Alpha',
        2: 'Bravo',
        3: 'Charlie',
        4: 'Delta',
        5: 'Echo',
        6: 'Foxtrot',
        7: 'Golf',
    }
    for page_id, title in pages.items():
        graph.add_vertex(title, page_id)

    for source, target in [
        ('Alpha', 'Bravo'),
        ('Bravo', 'Charlie'),
        ('Charlie', 'Delta'),
        ('Alpha', 'Echo'),
        ('Echo', 'Foxtrot'),
        ('Foxtrot', 'Golf'),
        ('Golf', 'Delta'),
    ]:
        graph.add_edge(source, target)

    categories = {
        1: {'Start', 'RouteA'},
        2: {'RouteA'},
        3: {'RouteA', 'Targetish'},
        4: {'Targetish'},
        5: {'RouteB'},
        6: {'RouteB'},
        7: {'RouteB', 'Targetish'},
    }
    return graph, categories


def write_fixture_dump_dir(base_dir: str) -> str:
    """Write a tiny Wikimedia-style SQL dump fixture and return its directory."""
    dump_dir = os.path.join(base_dir, 'dumps')
    os.makedirs(dump_dir, exist_ok=True)

    _write_sql_dump(
        os.path.join(dump_dir, 'enwiki-20260501-page.sql.gz'),
        'page',
        [
            (1, 0, 'Alpha', 0),
            (2, 0, 'Bravo', 0),
            (3, 0, 'Charlie', 0),
            (4, 0, 'Redirect_Alpha', 1),
            (5, 0, 'Delta', 0),
            (6, 0, 'Echo', 1),
            (7, 0, 'Foxtrot', 1),
        ]
    )
    _write_sql_dump(
        os.path.join(dump_dir, 'enwiki-20260501-redirect.sql.gz'),
        'redirect',
        [
            (4, 0, 'Alpha'),
            (6, 0, 'Charlie'),
            (7, 0, 'Echo'),
        ]
    )
    _write_sql_dump(
        os.path.join(dump_dir, 'enwiki-20260501-linktarget.sql.gz'),
        'linktarget',
        [
            (1, 0, 'Bravo'),
            (2, 0, 'Charlie'),
            (3, 0, 'Echo'),
            (4, 0, 'Redirect_Alpha'),
            (5, 0, 'Alpha'),
        ]
    )
    _write_sql_dump(
        os.path.join(dump_dir, 'enwiki-20260501-pagelinks.sql.gz'),
        'pagelinks',
        [
            (1, 0, 1),
            (2, 0, 2),
            (3, 0, 1),
            (5, 0, 4),
            (5, 0, 3),
        ]
    )
    _write_sql_dump(
        os.path.join(dump_dir, 'enwiki-20260501-categorylinks.sql.gz'),
        'categorylinks',
        [
            (1, 'Start'),
            (2, 'Middle'),
            (3, 'Target'),
            (5, 'Branch'),
            (5, 'Target'),
        ]
    )

    return dump_dir


def _write_sql_dump(path: str, table: str, rows: list[tuple]) -> None:
    """Write a minimal INSERT-only SQL dump."""
    encoded_rows = ','.join(f"({','.join(_sql_literal(value) for value in row)})" for row in rows)
    statement = f"INSERT INTO `{table}` VALUES {encoded_rows};\n"
    with gzip.open(path, 'wt', encoding='utf-8') as file:
        file.write(statement)


def _sql_literal(value: object) -> str:
    """Return a SQL literal for the test dump generator."""
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        escaped = value.replace('\\', '\\\\').replace("'", "\\'")
        return f"'{escaped}'"
    return str(value)
