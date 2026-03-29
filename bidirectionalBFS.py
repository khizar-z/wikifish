
import math
from collections import deque
import graph


def bi_bfs_all(graph1: graph.Graph, start: str, end: str, max_path: int) -> list[list[str]] | bool:
    """Return up to 5 (specified by max_path) of the shortest paths from start to end using bidirectional BFS.

    Expands both directions level-by-level and returns paths found in the first meeting layer. Returns False
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
        return False

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
    return False


def _build_path_bi_bfs_all(meeting_node: str, parent: dict[str, str], parent_rev: dict[str, str]):
    """
    Helper function for bidirectional_bfs_all which reconstruct a path from start to end through a meeting node.
    """
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
