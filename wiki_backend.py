"""wiki_backend.py

Backend abstractions and runtime loaders for WikiFish.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from array import array
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
import json
import mmap
import os
import re
import sqlite3
import threading
from typing import Any

from graph import Graph


_WHITESPACE_RE = re.compile(r"\s+")
INVALID_U32 = (1 << 32) - 1


@dataclass(frozen=True)
class ResolvedPage:
    """A resolved page lookup."""
    node_id: int
    canonical_title: str
    redirected_from: str | None = None


@dataclass(frozen=True)
class SnapshotInfo:
    """Metadata about the snapshot currently loaded."""
    wiki: str
    snapshot_date: str
    article_count: int
    format_version: int


def normalise_title(raw_title: str) -> str:
    """Return a canonical lookup key for a user-supplied title."""
    cleaned = raw_title.strip().replace('_', ' ')
    return _WHITESPACE_RE.sub(' ', cleaned)


def title_lookup_variants(raw_title: str) -> list[str]:
    """Return plausible title lookup variants for a raw input title."""
    cleaned = normalise_title(raw_title)
    if cleaned == '':
        return []

    variants = [cleaned]
    if cleaned[0].isalpha():
        variants.append(cleaned[0].upper() + cleaned[1:])
        variants.append(cleaned[0].lower() + cleaned[1:])

    seen = set()
    ordered = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            ordered.append(variant)
    return ordered


def snapshot_label(snapshot: SnapshotInfo) -> str:
    """Return a short human-readable label for a snapshot."""
    wiki_name = {
        'enwiki': 'English Wikipedia',
    }.get(snapshot.wiki, snapshot.wiki)
    return f'Data: {wiki_name} snapshot {snapshot.snapshot_date}'


class WikiBackend(ABC):
    """Abstract graph backend used by the app and search layer."""

    @abstractmethod
    def resolve_title(self, raw_title: str) -> ResolvedPage | None:
        """Return the resolved page corresponding to raw_title, if any."""

    @abstractmethod
    def canonical_title(self, node_id: int) -> str:
        """Return the canonical title for the given node id."""

    @abstractmethod
    def out_neighbors(self, node_id: int) -> Sequence[int]:
        """Return outgoing neighbours for the given node."""

    @abstractmethod
    def in_neighbors(self, node_id: int) -> Sequence[int]:
        """Return incoming neighbours for the given node."""

    @abstractmethod
    def categories(self, node_id: int) -> Collection[int]:
        """Return category ids associated with the given node."""

    @abstractmethod
    def snapshot_info(self) -> SnapshotInfo:
        """Return metadata for the currently loaded dataset."""


class SnapBackend(WikiBackend):
    """WikiBackend adapter over the original in-memory SNAP graph."""

    _title_to_node: dict[str, int]
    _node_to_title: dict[int, str]
    _forward_neighbors: dict[int, tuple[int, ...]]
    _reverse_neighbors: dict[int, tuple[int, ...]]
    _categories: dict[int, frozenset[int]]
    _snapshot: SnapshotInfo

    def __init__(
        self,
        graph: Graph,
        categories: dict[int, set[str]],
        wiki: str = 'enwiki',
        snapshot_date: str = '2011-snap',
        format_version: int = 1
    ) -> None:
        """Initialise the backend from the legacy SNAP dataset structures."""
        category_name_to_id: dict[str, int] = {}

        self._title_to_node = {}
        self._node_to_title = {}
        self._forward_neighbors = {}
        self._reverse_neighbors = {}
        self._categories = {}

        for title in graph.get_all_vertices():
            vertex = graph.get_vertex_by_name(title)
            self._title_to_node[title] = vertex.article_id
            self._node_to_title[vertex.article_id] = title

        for title in graph.get_all_vertices():
            vertex = graph.get_vertex_by_name(title)
            node_id = vertex.article_id
            forward = sorted(
                (neighbour.article_id for neighbour in vertex.forward_links),
                key=self._node_to_title.__getitem__
            )
            reverse = sorted(
                (neighbour.article_id for neighbour in vertex.reverse_links),
                key=self._node_to_title.__getitem__
            )
            self._forward_neighbors[node_id] = tuple(forward)
            self._reverse_neighbors[node_id] = tuple(reverse)

        for node_id, category_names in categories.items():
            ids = []
            for category_name in sorted(category_names):
                if category_name not in category_name_to_id:
                    category_name_to_id[category_name] = len(category_name_to_id)
                ids.append(category_name_to_id[category_name])
            self._categories[node_id] = frozenset(ids)

        self._snapshot = SnapshotInfo(
            wiki=wiki,
            snapshot_date=snapshot_date,
            article_count=len(self._node_to_title),
            format_version=format_version
        )

    def resolve_title(self, raw_title: str) -> ResolvedPage | None:
        for candidate in title_lookup_variants(raw_title):
            node_id = self._title_to_node.get(candidate)
            if node_id is not None:
                title = self._node_to_title[node_id]
                return ResolvedPage(node_id=node_id, canonical_title=title)
        return None

    def canonical_title(self, node_id: int) -> str:
        return self._node_to_title[node_id]

    def out_neighbors(self, node_id: int) -> Sequence[int]:
        return self._forward_neighbors.get(node_id, ())

    def in_neighbors(self, node_id: int) -> Sequence[int]:
        return self._reverse_neighbors.get(node_id, ())

    def categories(self, node_id: int) -> Collection[int]:
        return self._categories.get(node_id, frozenset())

    def snapshot_info(self) -> SnapshotInfo:
        return self._snapshot


class _MemmapArray:
    """Small wrapper around a read-only memory-mapped numeric array."""

    _file: Any
    _mmap: mmap.mmap | None
    _view: Sequence[int]

    def __init__(self, path: str, format_code: str) -> None:
        self._file = open(path, 'rb')
        size = os.path.getsize(path)
        if size == 0:
            self._mmap = None
            self._view = ()
        else:
            self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            self._view = memoryview(self._mmap).cast(format_code)

    def __getitem__(self, item: int) -> int:
        return self._view[item]

    def slice(self, start: int, end: int) -> Sequence[int]:
        return self._view[start:end]

    def close(self) -> None:
        """Close the underlying file handles."""
        if isinstance(self._view, memoryview):
            self._view.release()
            self._view = ()
        if self._mmap is not None:
            self._mmap.close()
        self._file.close()


class DumpBackend(WikiBackend):
    """WikiBackend backed by compiled Wikimedia snapshot artifacts."""

    _catalog_connections: dict[int, sqlite3.Connection]
    _catalog_lock: threading.Lock
    _catalog_local: threading.local
    _catalog_path: str
    _snapshot: SnapshotInfo
    _forward_offsets: _MemmapArray
    _forward_neighbors: _MemmapArray
    _reverse_offsets: _MemmapArray
    _reverse_neighbors: _MemmapArray
    _category_offsets: _MemmapArray
    _category_ids: _MemmapArray

    def __init__(self, data_dir: str) -> None:
        manifest_path = os.path.join(data_dir, 'manifest.json')
        with open(manifest_path) as manifest_file:
            manifest = json.load(manifest_file)

        self._catalog_path = os.path.join(data_dir, manifest['catalog'])
        self._catalog_connections = {}
        self._catalog_lock = threading.Lock()
        self._catalog_local = threading.local()

        self._snapshot = SnapshotInfo(
            wiki=manifest['wiki'],
            snapshot_date=manifest['snapshot_date'],
            article_count=manifest['article_count'],
            format_version=manifest['format_version']
        )

        self._forward_offsets = _MemmapArray(os.path.join(data_dir, manifest['forward_offsets']), 'Q')
        self._forward_neighbors = _MemmapArray(os.path.join(data_dir, manifest['forward_neighbors']), 'I')
        self._reverse_offsets = _MemmapArray(os.path.join(data_dir, manifest['reverse_offsets']), 'Q')
        self._reverse_neighbors = _MemmapArray(os.path.join(data_dir, manifest['reverse_neighbors']), 'I')
        self._category_offsets = _MemmapArray(os.path.join(data_dir, manifest['category_offsets']), 'Q')
        self._category_ids = _MemmapArray(os.path.join(data_dir, manifest['category_ids']), 'I')

    def close(self) -> None:
        """Close all runtime resources held by this backend."""
        self._forward_offsets.close()
        self._forward_neighbors.close()
        self._reverse_offsets.close()
        self._reverse_neighbors.close()
        self._category_offsets.close()
        self._category_ids.close()
        with self._catalog_lock:
            for connection in self._catalog_connections.values():
                connection.close()
            self._catalog_connections.clear()
        self._catalog_local.connection = None

    @lru_cache(maxsize=2048)
    def resolve_title(self, raw_title: str) -> ResolvedPage | None:
        row = None
        connection = self._catalog_connection()
        for candidate in title_lookup_variants(raw_title):
            row = connection.execute(
                """
                SELECT dense_id, canonical_title, redirected_from
                FROM aliases
                WHERE alias = ?
                """,
                (candidate,)
            ).fetchone()
            if row is not None:
                break

        if row is None:
            return None

        return ResolvedPage(
            node_id=int(row['dense_id']),
            canonical_title=row['canonical_title'],
            redirected_from=row['redirected_from']
        )

    @lru_cache(maxsize=200_000)
    def canonical_title(self, node_id: int) -> str:
        row = self._catalog_connection().execute(
            "SELECT title FROM pages WHERE dense_id = ?",
            (node_id,)
        ).fetchone()
        if row is None:
            raise KeyError(node_id)
        return str(row['title'])

    def out_neighbors(self, node_id: int) -> Sequence[int]:
        start = int(self._forward_offsets[node_id])
        end = int(self._forward_offsets[node_id + 1])
        return self._forward_neighbors.slice(start, end)

    def in_neighbors(self, node_id: int) -> Sequence[int]:
        start = int(self._reverse_offsets[node_id])
        end = int(self._reverse_offsets[node_id + 1])
        return self._reverse_neighbors.slice(start, end)

    @lru_cache(maxsize=200_000)
    def categories(self, node_id: int) -> Collection[int]:
        start = int(self._category_offsets[node_id])
        end = int(self._category_offsets[node_id + 1])
        return frozenset(int(category_id) for category_id in self._category_ids.slice(start, end))

    def snapshot_info(self) -> SnapshotInfo:
        return self._snapshot

    def _catalog_connection(self) -> sqlite3.Connection:
        """Return a read-only SQLite connection for the current thread."""
        connection = getattr(self._catalog_local, 'connection', None)
        if connection is None:
            catalog_uri = f'file:{self._catalog_path}?mode=ro'
            connection = sqlite3.connect(catalog_uri, uri=True, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            self._catalog_local.connection = connection
            with self._catalog_lock:
                self._catalog_connections[threading.get_ident()] = connection
        return connection


def write_numeric_array(path: str, values: Iterable[int], format_code: str) -> None:
    """Write numeric values to a binary array file."""
    output = array(format_code)
    output.extend(values)
    with open(path, 'wb') as file:
        output.tofile(file)
