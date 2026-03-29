"""pathfinding.py

A module containing the functions responsible for the pathfinding
algorithms used by the program. Contains functions for bidirectional
BFS and A* as well as relevant helper functions.

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""
import heapq

from graph import Graph
from collections import deque
import math

def jaccard_heuristic(current: int, target: int, categories: dict[int, set[str]]) -> float:
    """Return an estimated distance between two articles based on category overlap.

    Computes one minus the Jaccard similarity of the two articles' category sets.
    The result is in [0.0, 1.0], where 0.0 means identical categories (very close)
    and 1.0 means no shared categories (very far). Returns 1.0 if either article
    has no category data.

    Used as the h(n) heuristic in A* search.

    Preconditions:
        - current in categories
        - target in categories
    """
    current_cats = categories[current]
    target_cats = categories[target]

    if not current_cats or not target_cats:
        return 1.0

    # Jaccard similarity: size of intersection / size of union
    overlap = len(current_cats & target_cats) / len(current_cats | target_cats)
    return 1.0 - overlap  # invert so that closer = lower cost


def astar(graph: Graph, source: str, target: str, categories: dict[int, set[str]]) -> list[str] | None:
    """Return a shortest path from source to target using A* search.

    Uses a priority queue ordered by f(n) = g(n) + h(n), where g(n) is the
    exact hop-count from source to n, and h(n) is the Jaccard category heuristic.
    The heuristic directs the search toward articles that share more categories
    with the target, potentially expanding far fewer nodes than BFS.

    Returns a list of article names from source to target (inclusive),
    or None if no path exists.

    Preconditions:
        - graph.contains_vertex(source)
        - graph.contains_vertex(target)
    """
    source_vertex = graph.get_vertex_by_name(source)
    target_vertex = graph.get_vertex_by_name(target)

    start_h = jaccard_heuristic(source_vertex.article_id, target_vertex.article_id, categories)
    heap = [(start_h, 0, source)]  # f, g, article_name

    # Maps article_name to best g score seen so far
    best_g: dict[str, float] = {source: 0}

    # Maps article_name to previous article_name
    came_from: dict[str, str] = {}

    while heap:
        _, g, current_name = heapq.heappop(heap)

        if current_name == target:
            return _reconstruct_path(came_from, source, target)

        # Skip if already found a better path to this node
        if g > best_g.get(current_name, float('inf')):
            continue

        current_vertex = graph.get_vertex_by_name(current_name)

        for neighbour in current_vertex.forward_links:
            new_g = g + 1
            neighbour_name = neighbour.article_name

            if new_g < best_g.get(neighbour_name, float('inf')):
                best_g[neighbour_name] = new_g
                h = jaccard_heuristic(neighbour.article_id, target_vertex.article_id, categories)
                new_f = new_g + h
                came_from[neighbour_name] = current_name
                heapq.heappush(heap, (new_f, new_g, neighbour_name))
    return None


def astar_all(graph: Graph, source: str, target: str, categories: dict[int, set[str]], max_paths: int = 5) -> list[list[str]] | None:
    """Return up to max_paths shortest paths from source to target using A* search.

    Extends astar() to track multiple equally-optimal predecessors per node.
    Continues processing the heap after first reaching the target until all
    nodes at the optimal depth have been examined, ensuring no equally-short
    paths are missed. Stops early once max_paths have been reconstructed.

    Returns a list of paths, where each path is a list of article names from
    source to target (inclusive). Returns None if no path exists.

    Preconditions:
        - graph.contains_vertex(source)
        - graph.contains_vertex(target)
        - max_paths >= 1
    """
    source_vertex = graph.get_vertex_by_name(source)
    target_vertex = graph.get_vertex_by_name(target)

    start_h = jaccard_heuristic(source_vertex.article_id, target_vertex.article_id, categories)
    heap = [(start_h, 0, source)]

    best_g: dict[str, float] = {source: 0}
    came_from: dict[str, set[str]] = {source: set()}
    optimal_target_g: float | None = None

    while heap:
        _, g, current_name = heapq.heappop(heap)

        if optimal_target_g is not None and g > optimal_target_g:
            break

        if current_name == target:
            optimal_target_g = g
            continue

        if g > best_g.get(current_name, float('inf')):
            continue

        current_vertex = graph.get_vertex_by_name(current_name)

        for neighbour in current_vertex.forward_links:
            new_g = g + 1
            neighbour_name = neighbour.article_name
            current_best = best_g.get(neighbour_name, float('inf'))

            if new_g < current_best:
                best_g[neighbour_name] = new_g
                came_from[neighbour_name] = {current_name}
                h = jaccard_heuristic(neighbour.article_id, target_vertex.article_id, categories)
                heapq.heappush(heap, (new_g + h, new_g, neighbour_name))

            elif new_g == current_best:
                came_from.setdefault(neighbour_name, set()).add(current_name)

    if target not in came_from:
        return None

    return _reconstruct_all_paths(came_from, source, target, max_paths)


def bi_bfs_all(graph1: Graph, start: str, end: str, max_path: int) -> list[list[str]] | None:
    """Return up to 5 (specified by max_path) of the shortest paths from start to end using bidirectional BFS.

    Expands both directions level-by-level and returns paths found in the first meeting layer. Returns None
    if no path exists.

    Preconditions:
        - start in graph1.get_all_vertices()
        - end in graph1.get_all_vertices()
    """
    start_v = graph1.get_vertex_by_name(start)
    end_v = graph1.get_vertex_by_name(end)
    all_path: list[list[str]] = []
    size_of_shortest_path = math.inf

    if start_v is None or end_v is None:
        return None

    # Sets up variables for the forward direction
    queue = deque([start])
    visited: set[str] = {start}
    parent: dict[str, str | None] = {start: None}

    # Sets up variables for the reverse direction
    queue_rev = deque([end])
    visited_rev: set[str] = {end}
    parent_rev: dict[str, str | None] = {end: None}

    while queue and queue_rev:
        found_this_round = False

        # Expands a full layer of the tree
        level_size = len(queue)
        for _ in range(level_size):
            node = queue.popleft()

            for neighbor in graph1.get_vertex_by_name(node).forward_links:
                if neighbor.article_name not in visited:  # To avoid looping
                    visited.add(neighbor.article_name)
                    parent[neighbor.article_name] = node
                    queue.append(neighbor.article_name)

                    if neighbor.article_name in visited_rev:
                        path = _build_path_bi_bfs_all(neighbor.article_name, parent, parent_rev)

                        if len(path) < size_of_shortest_path:
                            size_of_shortest_path = len(path)
                            all_path = [path]  # If a shorter path is found, the list is reset
                        elif len(path) == size_of_shortest_path and path not in all_path:
                            all_path.append(path)
                        found_this_round = True

        # Expands a full layer of the tree in the reverse direction
        backward_layer_size = len(queue_rev)
        for _ in range(backward_layer_size):
            node_rev = queue_rev.popleft()

            for neighbor in graph1.get_vertex_by_name(node_rev).reverse_links:
                if neighbor.article_name not in visited_rev:  # To avoid looping
                    visited_rev.add(neighbor.article_name)
                    parent_rev[neighbor.article_name] = node_rev
                    queue_rev.append(neighbor.article_name)

                    if neighbor.article_name in visited:
                        path = _build_path_bi_bfs_all(neighbor.article_name, parent, parent_rev)

                        if len(path) < size_of_shortest_path:
                            size_of_shortest_path = len(path)
                            all_path = [path]  # If a shorter path is found, the list is reset
                        elif len(path) == size_of_shortest_path and path not in all_path:
                            all_path.append(path)
                        found_this_round = True

        if found_this_round:
            return all_path[:max_path]
    return None


def _reconstruct_path(came_from: dict[str, str], source: str, target: str) -> list[str]:
    """Return the path from source to target by following the came_from map.

    Walks backwards from target to source using came_from, then reverses the
    result to produce a forward-ordered list of article names.

    Preconditions:
        - target is reachable from source via came_from
    """
    path = []
    current = target
    while current != source:
        path.append(current)
        current = came_from[current]
    path.append(source)
    path.reverse()
    return path


def _reconstruct_all_paths(came_from: dict[str, set[str]], source: str, target: str, max_paths: int) -> list[list[str]]:
    """Return up to max_paths paths from source to target by recursively following came_from.

    At each node, iterates over all recorded predecessors to branch into every
    equally-optimal route. Stops as soon as max_paths complete paths have been
    collected to avoid explosion on densely connected graphs.

    Preconditions:
        - target is reachable from source via came_from
        - max_paths >= 1
    """
    if target == source:
        return [[source]]

    all_paths = []
    for predecessor in came_from.get(target, set()):
        if len(all_paths) >= max_paths:
            break
        for path in _reconstruct_all_paths(came_from, source, predecessor, max_paths):
            if len(all_paths) >= max_paths:
                break
            all_paths.append(path + [target])

    return all_paths


def _build_path_bi_bfs_all(meeting_node: str, parent: dict[str, str], parent_rev: dict[str, str]):
    """Helper function for bidirectional_bfs_all which reconstruct a path from start to end through a meeting node."""
    path_forward = []
    node = meeting_node
    while node is not None:
        path_forward.append(node)
        node = parent[node]
    path_forward.reverse()

    path_backward = []
    node = parent_rev[meeting_node]
    while node is not None:
        path_backward.append(node)
        node = parent_rev[node]

    return path_forward + path_backward


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    import python_ta
    python_ta.check_all(config={
        'extra-imports': ['graph', 'heapq', 'collections', 'networkx', 'dash', 'plotly', 'collections', 'math'],
        'allowed-io': ['load_graph', 'run_analysis'],
        'max-line-length': 120
    })
