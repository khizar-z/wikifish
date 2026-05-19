"""analysis.py

Post-game analysis logic for WikiFish.
"""
from __future__ import annotations

from wiki_backend import WikiBackend
from pathfinding import (
    astar,
    astar_all,
    bi_bfs_all,
    build_path_from_next_hops,
    reverse_distances_for_sources,
)


def find_paths(
    backend: WikiBackend,
    source: int,
    target: int,
    algorithm: str,
    max_paths: int
) -> list[list[int]] | None:
    """Return up to max_paths shortest paths from source to target."""
    if max_paths == 1:
        if algorithm == 'bfs':
            return bi_bfs_all(backend, source, target, 1)
        result = astar(backend, source, target)
        return [result] if result is not None else None

    if algorithm == 'bfs':
        return bi_bfs_all(backend, source, target, max_paths)
    return astar_all(backend, source, target, max_paths)


def run_analysis(
    backend: WikiBackend,
    player_path_ids: list[int],
    algorithm: str,
    max_paths: int
) -> dict:
    """Run full post-game analysis and return structured results for the UI."""
    source = player_path_ids[0]
    target = player_path_ids[-1]

    print(f"\nAnalysing: {backend.canonical_title(source)} → {backend.canonical_title(target)}")
    print(f"Finding optimal path(s) with max_paths={max_paths}...")

    optimal_paths_ids = find_paths(backend, source, target, algorithm, max_paths)
    optimal_paths = _paths_to_titles(backend, optimal_paths_ids)
    optimal_length = len(optimal_paths_ids[0]) - 1 if optimal_paths_ids else None
    print(f"  Optimal: {optimal_length} hops" if optimal_paths_ids else "  No path found.")

    distances, next_hops = reverse_distances_for_sources(backend, target, player_path_ids)
    player_path = [backend.canonical_title(node_id) for node_id in player_path_ids]
    hop_counts = []
    move_quality = []
    per_move_optimal = []

    for i, node_id in enumerate(player_path_ids):
        article = backend.canonical_title(node_id)
        print(f"  Evaluating move {i + 1}/{len(player_path_ids)}: {article}...")

        distance = distances.get(node_id)
        hop_counts.append(distance if distance is not None else 0)

        optimal_from_here_ids = build_path_from_next_hops(node_id, target, next_hops)
        per_move_optimal.append(
            _path_to_titles(backend, optimal_from_here_ids) if optimal_from_here_ids is not None else None
        )

        if i < len(player_path_ids) - 1:
            next_distance = distances.get(player_path_ids[i + 1])
            quality = _classify_move(distance, next_distance)
            move_quality.append(quality)

    return {
        'player_path': player_path,
        'optimal_paths': optimal_paths,
        'optimal_length': optimal_length,
        'hop_counts': hop_counts,
        'move_quality': move_quality,
        'per_move_optimal': per_move_optimal,
    }


def _classify_move(distance: int | None, next_distance: int | None) -> str:
    """Return a move-quality label based on exact target distances."""
    if distance is None or next_distance is None:
        return 'UNKNOWN'
    if next_distance < distance - 1:
        return 'GREAT'
    if next_distance == distance - 1:
        return 'OPTIMAL'
    if next_distance == distance:
        return 'NEUTRAL'
    return 'BLUNDER'


def _path_to_titles(backend: WikiBackend, path: list[int] | None) -> list[str] | None:
    """Convert a single path of node ids to titles."""
    if path is None:
        return None
    return [backend.canonical_title(node_id) for node_id in path]


def _paths_to_titles(backend: WikiBackend, paths: list[list[int]] | None) -> list[list[str]] | None:
    """Convert a list of paths from node ids to titles."""
    if paths is None:
        return None
    return [[backend.canonical_title(node_id) for node_id in path] for path in paths]
