"""pathfinding.py

Pathfinding algorithms and helper functions for WikiFish backends.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Sequence
import heapq

from wiki_backend import WikiBackend


def jaccard_heuristic(backend: WikiBackend, current: int, target: int) -> float:
    """Return an estimated distance between two nodes based on category overlap."""
    current_cats = backend.categories(current)
    target_cats = backend.categories(target)

    if not current_cats or not target_cats:
        return 1.0

    current_set = set(current_cats)
    target_set = set(target_cats)
    overlap = len(current_set & target_set) / len(current_set | target_set)
    return 1.0 - overlap


def astar(backend: WikiBackend, source: int, target: int) -> list[int] | None:
    """Return a shortest path from source to target using A* search."""
    start_h = jaccard_heuristic(backend, source, target)
    heap = [(start_h, 0, source)]
    best_g: dict[int, int] = {source: 0}
    came_from: dict[int, int] = {}

    while heap:
        _, g, current = heapq.heappop(heap)

        if current == target:
            return _reconstruct_path(came_from, source, target)

        if g > best_g.get(current, 10 ** 18):
            continue

        for neighbour in backend.out_neighbors(current):
            next_node = int(neighbour)
            new_g = g + 1
            if new_g < best_g.get(next_node, 10 ** 18):
                best_g[next_node] = new_g
                came_from[next_node] = current
                new_f = new_g + jaccard_heuristic(backend, next_node, target)
                heapq.heappush(heap, (new_f, new_g, next_node))

    return None


def astar_all(backend: WikiBackend, source: int, target: int, max_paths: int = 5) -> list[list[int]] | None:
    """Return up to max_paths shortest paths from source to target using A*."""
    start_h = jaccard_heuristic(backend, source, target)
    heap = [(start_h, 0, source)]
    best_g: dict[int, int] = {source: 0}
    came_from: dict[int, set[int]] = {source: set()}
    optimal_target_g: int | None = None

    while heap:
        _, g, current = heapq.heappop(heap)

        if optimal_target_g is not None and g > optimal_target_g:
            break

        if current == target:
            optimal_target_g = g
            continue

        if g > best_g.get(current, 10 ** 18):
            continue

        for neighbour in backend.out_neighbors(current):
            next_node = int(neighbour)
            new_g = g + 1
            current_best = best_g.get(next_node, 10 ** 18)

            if new_g < current_best:
                best_g[next_node] = new_g
                came_from[next_node] = {current}
                score = new_g + jaccard_heuristic(backend, next_node, target)
                heapq.heappush(heap, (score, new_g, next_node))
            elif new_g == current_best:
                came_from.setdefault(next_node, set()).add(current)

    if target not in came_from:
        return None

    return _reconstruct_all_paths(came_from, source, target, max_paths, backend)


def bi_bfs_all(backend: WikiBackend, start: int, end: int, max_paths: int) -> list[list[int]] | None:
    """Return up to max_paths shortest paths from start to end."""
    if start == end:
        return [[start]]

    frontier_f = {start}
    frontier_b = {end}
    depth_f = {start: 0}
    depth_b = {end: 0}
    parents_f: dict[int, set[int]] = {start: set()}
    parents_b: dict[int, set[int]] = {end: set()}
    meetings: set[int] = set()

    while frontier_f and frontier_b and not meetings:
        if len(frontier_f) <= len(frontier_b):
            frontier_f, meetings = _expand_frontier(
                frontier=frontier_f,
                current_depths=depth_f,
                current_parents=parents_f,
                other_depths=depth_b,
                backend=backend,
                forward=True
            )
        else:
            frontier_b, meetings = _expand_frontier(
                frontier=frontier_b,
                current_depths=depth_b,
                current_parents=parents_b,
                other_depths=depth_f,
                backend=backend,
                forward=False
            )

    if not meetings:
        return None

    results: list[list[int]] = []
    for meeting in sorted(meetings, key=backend.canonical_title):
        forward_paths = _reconstruct_all_paths(parents_f, start, meeting, max_paths, backend)
        backward_paths = _reconstruct_all_paths(parents_b, end, meeting, max_paths, backend)

        for forward_path in forward_paths:
            if len(results) >= max_paths:
                break
            for backward_path in backward_paths:
                if len(results) >= max_paths:
                    break
                path = forward_path + list(reversed(backward_path[:-1]))
                if path not in results:
                    results.append(path)

        if len(results) >= max_paths:
            break

    return results[:max_paths]


def reverse_distances(backend: WikiBackend, target: int) -> dict[int, int]:
    """Return exact shortest-path distances to target for all reachable nodes."""
    distances = {target: 0}
    queue = deque([target])

    while queue:
        current = queue.popleft()
        next_distance = distances[current] + 1

        for neighbour in backend.in_neighbors(current):
            node = int(neighbour)
            if node not in distances:
                distances[node] = next_distance
                queue.append(node)

    return distances


def reverse_distances_for_sources(
    backend: WikiBackend,
    target: int,
    sources: Sequence[int]
) -> tuple[dict[int, int], dict[int, int]]:
    """Return exact target distances for the requested sources plus one shortest-path tree.

    Runs a reverse BFS from target and stops as soon as every node in sources has
    been discovered. The returned next_hops map stores one successor on a
    shortest path toward target for each discovered non-target node.
    """
    distances = {target: 0}
    next_hops: dict[int, int] = {}
    requested = set(int(source) for source in sources)
    unresolved = requested - {target}

    if not unresolved:
        return distances, next_hops

    queue = deque([target])
    while queue and unresolved:
        current = queue.popleft()
        next_distance = distances[current] + 1

        for neighbour in backend.in_neighbors(current):
            node = int(neighbour)
            if node in distances:
                continue

            distances[node] = next_distance
            next_hops[node] = current
            unresolved.discard(node)

            if not unresolved:
                return distances, next_hops

            queue.append(node)

    return distances, next_hops


def build_path_from_distances(
    backend: WikiBackend,
    start: int,
    target: int,
    distances: dict[int, int]
) -> list[int] | None:
    """Return one deterministic shortest path using a reverse-distance map."""
    if start not in distances:
        return None
    if start == target:
        return [start]

    path = [start]
    current = start

    while current != target:
        current_distance = distances[current]
        candidates = [
            int(neighbour)
            for neighbour in backend.out_neighbors(current)
            if distances.get(int(neighbour)) == current_distance - 1
        ]
        if not candidates:
            return None

        current = min(candidates, key=backend.canonical_title)
        path.append(current)

    return path


def build_path_from_next_hops(start: int, target: int, next_hops: dict[int, int]) -> list[int] | None:
    """Return one shortest path from start to target using a reverse-BFS tree."""
    if start == target:
        return [target]
    if start not in next_hops:
        return None

    path = [start]
    current = start
    while current != target:
        current = next_hops.get(current)
        if current is None:
            return None
        path.append(current)

    return path


def _expand_frontier(
    frontier: set[int],
    current_depths: dict[int, int],
    current_parents: dict[int, set[int]],
    other_depths: dict[int, int],
    backend: WikiBackend,
    forward: bool
) -> tuple[set[int], set[int]]:
    """Expand one BFS frontier layer and return the next frontier plus meeting nodes."""
    next_frontier: set[int] = set()
    meetings: set[int] = set()

    for node in frontier:
        next_depth = current_depths[node] + 1
        neighbours: Sequence[int] = (
            backend.out_neighbors(node) if forward else backend.in_neighbors(node)
        )

        for neighbour in neighbours:
            next_node = int(neighbour)

            if next_node not in current_depths:
                current_depths[next_node] = next_depth
                current_parents[next_node] = {node}
                next_frontier.add(next_node)
            elif current_depths[next_node] == next_depth:
                current_parents.setdefault(next_node, set()).add(node)

            if next_node in other_depths:
                meetings.add(next_node)

    return next_frontier, meetings


def _reconstruct_path(came_from: dict[int, int], source: int, target: int) -> list[int]:
    """Return the path from source to target by following the came_from map."""
    path = []
    current = target
    while current != source:
        path.append(current)
        current = came_from[current]
    path.append(source)
    path.reverse()
    return path


def _reconstruct_all_paths(
    came_from: dict[int, set[int]],
    source: int,
    target: int,
    max_paths: int,
    backend: WikiBackend
) -> list[list[int]]:
    """Return up to max_paths paths from source to target by following predecessor sets."""
    if target == source:
        return [[source]]

    all_paths = []
    for predecessor in sorted(came_from.get(target, set()), key=backend.canonical_title):
        if len(all_paths) >= max_paths:
            break
        for path in _reconstruct_all_paths(came_from, source, predecessor, max_paths, backend):
            if len(all_paths) >= max_paths:
                break
            all_paths.append(path + [target])

    return all_paths
