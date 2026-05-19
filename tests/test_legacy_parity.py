"""Parity tests between the refactor and the legacy SNAP behaviour."""
from __future__ import annotations

from collections import deque
import heapq
import unittest

from analysis import find_paths, run_analysis
from tests.test_support import build_snap_fixture
from wiki_backend import SnapBackend


class LegacyParityTests(unittest.TestCase):
    """Regression coverage for the legacy SNAP-backed workflow."""

    def setUp(self) -> None:
        graph, categories = build_snap_fixture()
        self.graph = graph
        self.categories = categories
        self.backend = SnapBackend(graph, categories)

    def test_shortest_path_matches_legacy_bfs(self) -> None:
        source = self.backend.resolve_title('Alpha')
        target = self.backend.resolve_title('Delta')
        assert source is not None and target is not None

        legacy_paths = legacy_bi_bfs_all(self.graph, 'Alpha', 'Delta', 1)
        modern_paths = find_paths(self.backend, source.node_id, target.node_id, 'bfs', 1)

        self.assertEqual(
            [[self.backend.canonical_title(node_id) for node_id in path] for path in modern_paths or []],
            legacy_paths,
        )

    def test_shortest_path_matches_legacy_astar(self) -> None:
        source = self.backend.resolve_title('Alpha')
        target = self.backend.resolve_title('Delta')
        assert source is not None and target is not None

        legacy_path = legacy_astar(self.graph, 'Alpha', 'Delta', self.categories)
        modern_path = find_paths(self.backend, source.node_id, target.node_id, 'astar', 1)

        self.assertEqual(
            [self.backend.canonical_title(node_id) for node_id in modern_path[0]],
            legacy_path,
        )

    def test_analysis_matches_legacy_results(self) -> None:
        player_path = ['Alpha', 'Echo', 'Foxtrot', 'Golf', 'Delta']
        player_ids = [self.backend.resolve_title(title).node_id for title in player_path]

        modern = run_analysis(self.backend, player_ids, 'bfs', 1)
        legacy = legacy_run_analysis(self.graph, self.categories, player_path, 'bfs', 1)

        self.assertEqual(modern['player_path'], legacy['player_path'])
        self.assertEqual(modern['optimal_length'], legacy['optimal_length'])
        self.assertEqual(modern['hop_counts'], legacy['hop_counts'])
        self.assertEqual(modern['move_quality'], legacy['move_quality'])
        self.assertEqual(modern['per_move_optimal'], legacy['per_move_optimal'])


def legacy_jaccard_heuristic(current: int, target: int, categories: dict[int, set[str]]) -> float:
    """Copied from the legacy code for regression comparison."""
    current_cats = categories[current]
    target_cats = categories[target]

    if not current_cats or not target_cats:
        return 1.0

    overlap = len(current_cats & target_cats) / len(current_cats | target_cats)
    return 1.0 - overlap


def legacy_astar(graph, source: str, target: str, categories: dict[int, set[str]]) -> list[str] | None:
    """Legacy A* implementation."""
    source_vertex = graph.get_vertex_by_name(source)
    target_vertex = graph.get_vertex_by_name(target)

    start_h = legacy_jaccard_heuristic(source_vertex.article_id, target_vertex.article_id, categories)
    heap = [(start_h, 0, source)]
    best_g: dict[str, float] = {source: 0}
    came_from: dict[str, str] = {}

    while heap:
        _, g, current_name = heapq.heappop(heap)

        if current_name == target:
            return legacy_reconstruct_path(came_from, source, target)

        if g > best_g.get(current_name, float('inf')):
            continue

        current_vertex = graph.get_vertex_by_name(current_name)

        for neighbour in current_vertex.forward_links:
            new_g = g + 1
            neighbour_name = neighbour.article_name

            if new_g < best_g.get(neighbour_name, float('inf')):
                best_g[neighbour_name] = new_g
                h = legacy_jaccard_heuristic(neighbour.article_id, target_vertex.article_id, categories)
                came_from[neighbour_name] = current_name
                heapq.heappush(heap, (new_g + h, new_g, neighbour_name))
    return None


def legacy_bi_bfs_all(graph, start: str, end: str, max_path: int) -> list[list[str]] | None:
    """Legacy bidirectional BFS implementation."""
    if start == end:
        return [[start]]
    all_path = []
    size_of_shortest_path = float('inf')

    queue = deque([start])
    visited = {start}
    parent = {start: None}

    queue_rev = deque([end])
    visited_rev = {end}
    parent_rev = {end: None}

    while queue and queue_rev:
        found_this_round = False

        for _ in range(len(queue)):
            node = queue.popleft()
            for neighbor in graph.get_vertex_by_name(node).forward_links:
                if neighbor.article_name not in visited:
                    visited.add(neighbor.article_name)
                    parent[neighbor.article_name] = node
                    queue.append(neighbor.article_name)

                    if neighbor.article_name in visited_rev:
                        path = legacy_build_path(neighbor.article_name, parent, parent_rev)
                        if len(path) < size_of_shortest_path:
                            size_of_shortest_path = len(path)
                            all_path = [path]
                        elif len(path) == size_of_shortest_path and path not in all_path:
                            all_path.append(path)
                        found_this_round = True

        for _ in range(len(queue_rev)):
            node_rev = queue_rev.popleft()
            for neighbor in graph.get_vertex_by_name(node_rev).reverse_links:
                if neighbor.article_name not in visited_rev:
                    visited_rev.add(neighbor.article_name)
                    parent_rev[neighbor.article_name] = node_rev
                    queue_rev.append(neighbor.article_name)

                    if neighbor.article_name in visited:
                        path = legacy_build_path(neighbor.article_name, parent, parent_rev)
                        if len(path) < size_of_shortest_path:
                            size_of_shortest_path = len(path)
                            all_path = [path]
                        elif len(path) == size_of_shortest_path and path not in all_path:
                            all_path.append(path)
                        found_this_round = True

        if found_this_round:
            return all_path[:max_path]
    return None


def legacy_reconstruct_path(came_from: dict[str, str], source: str, target: str) -> list[str]:
    """Legacy path reconstruction helper."""
    path = []
    current = target
    while current != source:
        path.append(current)
        current = came_from[current]
    path.append(source)
    path.reverse()
    return path


def legacy_build_path(meeting_node: str, parent_dict: dict[str, str | None], parent_rev_dict: dict[str, str | None]) -> list[str]:
    """Legacy bidirectional path reconstruction helper."""
    path_forward = []
    node = meeting_node
    while node is not None:
        path_forward.append(node)
        node = parent_dict[node]
    path_forward.reverse()

    path_backward = []
    node = parent_rev_dict[meeting_node]
    while node is not None:
        path_backward.append(node)
        node = parent_rev_dict[node]

    return path_forward + path_backward


def legacy_find_paths(graph, categories, source: str, target: str, algorithm: str, max_paths: int):
    """Legacy dispatcher used by the regression test."""
    if max_paths == 1:
        if algorithm == 'bfs':
            return legacy_bi_bfs_all(graph, source, target, 1)
        result = legacy_astar(graph, source, target, categories)
        return [result] if result is not None else None
    raise NotImplementedError


def legacy_run_analysis(graph, categories, player_path: list[str], algorithm: str, max_paths: int) -> dict:
    """Legacy analysis loop copied for regression comparison."""
    source = player_path[0]
    target = player_path[-1]
    optimal_paths = legacy_find_paths(graph, categories, source, target, algorithm, max_paths)
    optimal_length = len(optimal_paths[0]) - 1 if optimal_paths else None

    hop_counts = []
    move_quality = []
    per_move_optimal = []

    for i, article in enumerate(player_path):
        paths_from_here = legacy_find_paths(graph, categories, article, target, algorithm, 1)
        dist = len(paths_from_here[0]) - 1 if paths_from_here else None
        hop_counts.append(dist if dist is not None else 0)
        per_move_optimal.append(paths_from_here[0] if paths_from_here else None)

        if i < len(player_path) - 1:
            next_article = player_path[i + 1]
            paths_from_next = legacy_find_paths(graph, categories, next_article, target, algorithm, 1)
            dist_next = len(paths_from_next[0]) - 1 if paths_from_next else None

            if dist is None or dist_next is None:
                quality = 'UNKNOWN'
            elif dist_next < dist - 1:
                quality = 'GREAT'
            elif dist_next == dist - 1:
                quality = 'OPTIMAL'
            elif dist_next == dist:
                quality = 'NEUTRAL'
            else:
                quality = 'BLUNDER'

            move_quality.append(quality)

    return {
        'player_path': player_path,
        'optimal_paths': optimal_paths,
        'optimal_length': optimal_length,
        'hop_counts': hop_counts,
        'move_quality': move_quality,
        'per_move_optimal': per_move_optimal,
    }


if __name__ == '__main__':
    unittest.main()
