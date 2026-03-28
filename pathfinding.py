
import heapq

from graph import Graph


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
