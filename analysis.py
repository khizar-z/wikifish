"""analysis.py

A module containing two functions (find_paths and run_analysis)
that generate comprehensive post-game analysis data to be displayed.

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""
from __future__ import annotations
from graph import Graph
from pathfinding import astar_all, astar, bi_bfs_all


def find_paths(
        graph: Graph,
        categories: dict[int, set[str]],
        source: str,
        target: str,
        algorithm: str,
        max_paths: int
) -> list[list[str]] | None:
    """Return up to max_paths shortest paths from source to target.

    Routes to the appropriate pathfinding function based on algorithm and
    max_paths. When max_paths is 1, uses the leaner single-path functions
    (bfs() or astar()) to avoid the overhead of multi-predecessor tracking.

    Returns a list of paths (each a list of article names from source to target
    inclusive), or None if no path exists.

    Preconditions:
        - graph.contains_vertex(source)
        - graph.contains_vertex(target)
        - algorithm in {'bfs', 'astar'}
        - max_paths >= 1
    """
    if max_paths == 1:
        result = None
        if algorithm == "bfs":
            result = bi_bfs_all(graph, source, target, 1)
        else:
            result = astar(graph, source, target, categories)
        return [result] if result is not None else None
    if algorithm == "bfs":
        return bi_bfs_all(graph, source, target, max_paths)
    else:
        return astar_all(graph, source, target, categories, max_paths)


def run_analysis(
        graph: Graph,
        categories: dict[int, set[str]],
        player_path: list[str],
        algorithm: str,
        max_paths: int
) -> dict:
    """Run full post-game analysis on a player's WikiRace path and return structured results.

    For each article in player_path, computes the exact hop-count to the target
    and classifies the transition to the next article as GREAT, OPTIMAL, NEUTRAL,
    BLUNDER, or UNKNOWN. Also finds up to max_paths globally optimal paths from
    the start to the target for comparison.

    Returns a dict with the following keys:
        - player_path:     list[str] — the original input path
        - optimal_paths:   list[list[str]] | None — up to max_paths optimal routes
        - optimal_length:  int | None — hop-count of the shortest optimal path
        - hop_counts:      list[int] — hop-count to target at each step of player_path
        - move_quality:    list[str] — quality label for each move (len = len(player_path) - 1)
        - per_move_optimal: list[list[str] | None] — optimal path onward from each article

    Preconditions:
        - len(player_path) >= 2
        - all articles in player_path exist in graph
        - algorithm in {'bfs', 'astar'}
        - max_paths >= 1
    """
    print(f"\nAnalysing: {player_path[0]} → {player_path[-1]}")
    print(f"Finding optimal path(s) with max_paths={max_paths}...")
    source = player_path[0]
    target = player_path[-1]

    optimal_paths = find_paths(graph, categories, source, target, algorithm, max_paths)
    optimal_length = len(optimal_paths[0]) - 1 if optimal_paths else None
    print(f"  Optimal: {len(optimal_paths[0]) - 1} hops" if optimal_paths else "  No path found.")

    hop_counts = []
    move_quality = []
    per_move_optimal = []

    for i, article in enumerate(player_path):
        print(f"  Evaluating move {i + 1}/{len(player_path)}: {article}...")
        paths_from_here = find_paths(graph, categories, article, target, algorithm, 1)
        dist = len(paths_from_here[0]) - 1 if paths_from_here else None
        hop_counts.append(dist if dist is not None else 0)
        per_move_optimal.append(paths_from_here[0] if paths_from_here else None)

        if i < len(player_path) - 1:
            next_article = player_path[i + 1]
            paths_from_next = find_paths(graph, categories, next_article, target, algorithm, 1)
            dist_next = len(paths_from_next[0]) - 1 if paths_from_next else None

            if dist is None or dist_next is None:
                quality = "UNKNOWN"
            elif dist_next < dist - 1:
                quality = "GREAT"
            elif dist_next == dist - 1:
                quality = "OPTIMAL"
            elif dist_next == dist:
                quality = "NEUTRAL"
            else:
                quality = "BLUNDER"

            move_quality.append(quality)

    return {
        "player_path": player_path,
        "optimal_paths": optimal_paths,
        "optimal_length": optimal_length,
        "hop_counts": hop_counts,
        "move_quality": move_quality,
        "per_move_optimal": per_move_optimal,
    }


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    import python_ta
    python_ta.check_all(config={
        'extra-imports': ['graph', 'heapq', 'collections', 'networkx', 'dash', 'plotly', 'pathfinding'],
        'allowed-io': ['load_graph', 'run_analysis'],
        'max-line-length': 120
    })
