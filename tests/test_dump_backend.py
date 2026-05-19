"""Tests for the compiled dump backend."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest

from analysis import find_paths, run_analysis
from dump_compiler import compile_dump_snapshot
from pathfinding import build_path_from_next_hops, reverse_distances, reverse_distances_for_sources
from wiki_backend import DumpBackend
from tests.test_support import write_fixture_dump_dir


class DumpBackendTests(unittest.TestCase):
    """Fixture-driven tests for the dump compiler and runtime backend."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        dump_dir = write_fixture_dump_dir(self.temp_dir.name)
        self.output_dir = os.path.join(self.temp_dir.name, 'compiled')
        compile_dump_snapshot(dump_dir, self.output_dir)
        self.backend = DumpBackend(self.output_dir)

    def tearDown(self) -> None:
        self.backend.close()
        self.temp_dir.cleanup()

    def test_resolve_title_handles_redirects_and_underscores(self) -> None:
        resolved = self.backend.resolve_title('Redirect_Alpha')
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.canonical_title, 'Alpha')
        self.assertEqual(resolved.redirected_from, 'Redirect Alpha')

    def test_snapshot_metadata_is_loaded(self) -> None:
        snapshot = self.backend.snapshot_info()
        self.assertEqual(snapshot.wiki, 'enwiki')
        self.assertEqual(snapshot.snapshot_date, '2026-05-01')
        self.assertEqual(snapshot.article_count, 4)

    def test_compiled_graph_collapses_redirect_targets(self) -> None:
        alpha = self.backend.resolve_title('Alpha')
        bravo = self.backend.resolve_title('Bravo')
        charlie = self.backend.resolve_title('Charlie')
        delta = self.backend.resolve_title('Delta')
        self.assertIsNotNone(alpha)
        self.assertIsNotNone(bravo)
        self.assertIsNotNone(charlie)
        self.assertIsNotNone(delta)

        alpha_neighbors = [self.backend.canonical_title(node_id) for node_id in self.backend.out_neighbors(alpha.node_id)]
        delta_neighbors = [self.backend.canonical_title(node_id) for node_id in self.backend.out_neighbors(delta.node_id)]

        self.assertEqual(alpha_neighbors, ['Bravo'])
        self.assertEqual(delta_neighbors, ['Alpha', 'Charlie'])
        self.assertEqual(set(self.backend.categories(delta.node_id)), {3, 2})

    def test_bfs_and_astar_return_same_shortest_length(self) -> None:
        delta = self.backend.resolve_title('Delta')
        bravo = self.backend.resolve_title('Bravo')
        assert delta is not None and bravo is not None

        bfs_paths = find_paths(self.backend, delta.node_id, bravo.node_id, 'bfs', 5)
        astar_paths = find_paths(self.backend, delta.node_id, bravo.node_id, 'astar', 1)

        self.assertEqual(len(bfs_paths[0]) - 1, len(astar_paths[0]) - 1)
        self.assertEqual(
            {tuple(self.backend.canonical_title(node_id) for node_id in path) for path in bfs_paths},
            {
                ('Delta', 'Alpha', 'Bravo'),
                ('Delta', 'Charlie', 'Bravo'),
            },
        )

    def test_reverse_distance_scoring_produces_expected_analysis(self) -> None:
        delta = self.backend.resolve_title('Delta')
        alpha = self.backend.resolve_title('Alpha')
        bravo = self.backend.resolve_title('Bravo')
        charlie = self.backend.resolve_title('Charlie')
        assert delta is not None and alpha is not None and bravo is not None and charlie is not None

        results = run_analysis(
            self.backend,
            [delta.node_id, alpha.node_id, bravo.node_id, charlie.node_id],
            'bfs',
            3,
        )

        self.assertEqual(results['hop_counts'], [1, 2, 1, 0])
        self.assertEqual(results['move_quality'], ['BLUNDER', 'OPTIMAL', 'OPTIMAL'])
        self.assertEqual(results['per_move_optimal'][0], ['Delta', 'Charlie'])

    def test_targeted_reverse_search_matches_global_for_requested_nodes(self) -> None:
        delta = self.backend.resolve_title('Delta')
        alpha = self.backend.resolve_title('Alpha')
        bravo = self.backend.resolve_title('Bravo')
        charlie = self.backend.resolve_title('Charlie')
        assert delta is not None and alpha is not None and bravo is not None and charlie is not None

        requested = [delta.node_id, alpha.node_id, bravo.node_id, charlie.node_id]
        full_distances = reverse_distances(self.backend, charlie.node_id)
        distances, next_hops = reverse_distances_for_sources(self.backend, charlie.node_id, requested)

        for node_id in requested:
            self.assertEqual(distances[node_id], full_distances[node_id])

        self.assertEqual(
            build_path_from_next_hops(delta.node_id, charlie.node_id, next_hops),
            [delta.node_id, charlie.node_id],
        )

    def test_resolve_title_works_from_another_thread(self) -> None:
        result: dict[str, str | None] = {'title': None}
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                resolved = self.backend.resolve_title('Redirect_Alpha')
                result['title'] = None if resolved is None else resolved.canonical_title
            except BaseException as error:  # pragma: no cover - surfaced in assertion
                errors.append(error)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(result['title'], 'Alpha')

    def test_targeted_reverse_search_stops_after_all_sources_found(self) -> None:
        backend = _TinyCountingBackend()
        distances, next_hops = reverse_distances_for_sources(backend, 0, [1])

        self.assertEqual(distances, {0: 0, 1: 1})
        self.assertEqual(next_hops, {1: 0})
        self.assertEqual(backend.in_neighbor_calls, [0])


class _TinyCountingBackend:
    """Minimal backend used to verify bounded reverse search behaviour."""

    def __init__(self) -> None:
        self.in_neighbor_calls: list[int] = []

    def resolve_title(self, raw_title: str):
        raise NotImplementedError

    def canonical_title(self, node_id: int) -> str:
        return str(node_id)

    def out_neighbors(self, node_id: int):
        return ()

    def in_neighbors(self, node_id: int):
        self.in_neighbor_calls.append(node_id)
        if node_id == 0:
            return (1, 2)
        return ()

    def categories(self, node_id: int):
        return ()

    def snapshot_info(self):
        raise NotImplementedError


if __name__ == '__main__':
    unittest.main()
