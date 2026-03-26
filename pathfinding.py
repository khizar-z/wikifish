
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

    Returns a list of article names from source to target (inclusive),
    or None if no path exists.

    Preconditions:
        - source in graph._vertices
        - target in graph._vertices
    """
    source_vertex = graph.get_vertex_by_name(source)
    target_vertex = graph.get_vertex_by_name(target)

    start_h = jaccard_heuristic(source_vertex.article_id, target_vertex.article_id, categories)
    heap = [(start_h, 0, source)] # f, g, article_name

    # Maps article_name to best g_score seen so far
    best_g: dict[str, float] = {source: 0}

    # Maps article_name to previous article_name
    came_from: dict[str, str] = {}

    while heap:
        f, g, current_name = heapq.heappop(heap)

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
