
import heapq

from graph import Graph


def jaccard_heuristic(current: int, target: int, categories: dict[int, set[str]]) -> float:
    """
    Return the Jaccard similarity between two sets of vertices based on the intersection and union of their
    associated sets of categories.
    """
    current_cats = categories[current]
    target_cats = categories[target]

    if not current_cats or not target_cats:
        return 1.0

    # Jaccard similarity: size of intersection / size of union
    overlap = len(current_cats & target_cats) / len(current_cats | target_cats)
    return 1.0 - overlap  # invert so that closer = lower cost


def astar(graph: Graph, source: str, target: str, categories: dict[int, set[str]]) -> list[str] | None:
    """Return the shortest path from source to target using A*.

    f(n) = the estimated total cost of a path through node n
    g(n) = the exact cost to get from the start node to node n (number of hops taken so far)
    h(n) = the heuristic estimate of the cost from node n to the goal, provided by jaccard_heuristic()
    with f(n) = g(n) + h(n)

    Returns a list of article names from source to target (inclusive), or None if no path exists.

    Preconditions:
        - source in graph._vertices
        - target in graph._vertices
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
    """Return up to max_paths optimal paths from source to target using A*.

    Returns a list of paths, where each path is a list of article names
    from source to target (inclusive). Returns None if no path exists.
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
    """Reconstruct the path from source to target using the came_from map."""
    path = []
    current = target
    while current != source:
        path.append(current)
        current = came_from[current]
    path.append(source)
    path.reverse()
    return path


def _reconstruct_all_paths(came_from: dict[str, set[str]], source: str, target: str, max_paths: int) -> list[list[str]]:
    """Recursively reconstruct up to max_paths optimal paths from source to target."""
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

# Note: examine potential of using f = h, eliminating depth -- only caring about Jaccard similarity. When similarity
# patterns are good, it provides immediate answer.
