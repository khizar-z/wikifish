
import math
import load_graph
from collections import deque
import graph


# def bfs(graph1: graph.Graph, start: str, end: str) -> list | bool:
#     """
#
#     Preconditions:
#         - start in graph1.get_all_vertices()
#         - end in graph1.get_all_vertices()
#     """
#     start_v = graph1.get_vertex(start)
#     end_v = graph1.get_vertex(end)
#     if start_v is None or end_v is None:
#         return False
#
#     queue = deque([start_v])
#     visited = {start_v}
#     parent = {}
#     parent[start_v] = None
#
#     while queue:
#         node = queue.popleft()
#
#         for neighbor in node.forward_links:
#             if neighbor not in visited:
#                 visited.add(neighbor)
#                 parent[neighbor] = node
#                 queue.append(neighbor)
#
#                 if neighbor.article_name == end:
#                     return build_path(neighbor, parent)
#     return False
#
#
# def build_path(meeting_node, parent):
#     path_forward = []
#     node = meeting_node
#
#     while node is not None:
#         path_forward.append(node.article_name)
#         node = parent[node]
#
#     path_forward.reverse()
#     return path_forward


# def bi_bfs(graph1: graph.Graph, start: str, end: str) -> list | bool:
#     """
#
#     Preconditions:
#         - start in graph1.get_all_vertices()
#         - end in graph1.get_all_vertices()
#     """
#     start_v = graph1.get_vertex(start)
#     end_v = graph1.get_vertex(end)
#     if start_v is None or end_v is None:
#         return False
#
#     queue = deque([start_v])
#     visited = {start_v}
#     parent = {}
#     parent[start_v] = None
#
#     queue_rev = deque([end_v])
#     visited_rev = {end_v}
#     parent_rev = {}
#     parent_rev[end_v] = None
#
#     while queue and queue_rev:
#         node = queue.popleft()
#
#         for neighbor in node.forward_links:
#             if neighbor not in visited:
#                 visited.add(neighbor)
#                 parent[neighbor] = node
#                 queue.append(neighbor)
#
#                 if neighbor in visited_rev:
#                     return build_path(neighbor, parent, parent_rev)
#
#         node_rev = queue_rev.popleft()
#
#         for neighbor in node_rev.reverse_links:
#             if neighbor not in visited_rev:
#                 visited_rev.add(neighbor)
#                 parent_rev[neighbor] = node_rev
#                 queue_rev.append(neighbor)
#
#                 if neighbor in visited:
#                     return build_path(neighbor, parent, parent_rev)
#     return False


# def bi_bfs_all(graph1: graph.Graph, start: str, end: str, max_path: int) -> list | bool:
#     """
#
#     Preconditions:
#         - start in graph1.get_all_vertices()
#         - end in graph1.get_all_vertices()
#     """
#     start_v = graph1.get_vertex(start)
#     end_v = graph1.get_vertex(end)
#     all_path: list[list[str]] = []
#     size_of_shortest_path = math.inf
#
#     if start_v is None or end_v is None:
#         return False
#
#     # Sets up variables for the forward direction
#     queue = deque([start_v])
#     visited: set = {start_v}
#     parent: dict = {start_v: None}
#
#     # Sets up variables for the reverse direction
#     queue_rev = deque([end_v])
#     visited_rev: set = {end_v}
#     parent_rev: dict = {end_v: None}
#
#     while (queue and queue_rev) and len(all_path) < max_path:
#         node = queue.popleft()
#
#         for neighbor in node.forward_links:
#             if neighbor not in visited:
#                 visited.add(neighbor)
#                 parent[neighbor] = node
#                 queue.append(neighbor)
#
#                 if neighbor in visited_rev:
#                     path = _build_path(neighbor, parent, parent_rev)
#                     _path_handling(path, size_of_shortest_path, all_path)
#         node_rev = queue_rev.popleft()
#
#         for neighbor in node_rev.reverse_links:
#             if neighbor not in visited_rev:
#                 visited_rev.add(neighbor)
#                 parent_rev[neighbor] = node_rev
#                 queue_rev.append(neighbor)
#
#                 if neighbor in visited:
#                     path = _build_path(neighbor, parent, parent_rev)
#                     _path_handling(path, size_of_shortest_path, all_path)
#
#     if all_path:
#         return all_path, len(all_path)
#     return False
#
#
# def _path_handling(current_path, size, all_path):
#     if len(current_path) < size:  # make another since its the same below too
#         all_path.append(current_path)
#         size = len(current_path)
#         _check_current_list(all_path, size)  # will check if there are any path bigger than size of shortest
#     elif len(current_path) == size:
#         all_path.append(current_path)
#         _check_current_list(all_path, size)
#
#
# def _build_path(meeting_node, parent, parent_rev):
#     path_forward = []
#     node = meeting_node
#
#     while node is not None:
#         path_forward.append(node.article_name)
#         node = parent[node]
#
#     path_forward.reverse()
#
#     path_backward = []
#     node = parent_rev[meeting_node]
#
#     while node is not None:
#         path_backward.append(node.article_name)
#         node = parent_rev[node]
#
#     return path_forward + path_backward
#
#
# def _check_current_list(list_of_path, size) -> None:
#     for path in list_of_path:
#         if len(path) > size:
#             list_of_path.remove(path)



def bi_bfs_all(graph1: graph.Graph, start: str, end: str, max_path: int) -> list[list[str]] | bool:
    """Returns the least amount of steps required to get from start to finish.

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
                if neighbor.article_name not in visited:
                    visited.add(neighbor.article_name)
                    parent[neighbor.article_name] = node
                    queue.append(neighbor.article_name)

                    if neighbor.article_name in visited_rev:
                        path = _build_path(neighbor.article_name, parent, parent_rev)

                        if len(path) < size_of_shortest_path:
                            size_of_shortest_path = len(path)
                            all_path = [path]
                        elif len(path) == size_of_shortest_path and path not in all_path:
                            all_path.append(path)
                        found_this_round = True

        # Expands a full layer of the tree in the reverse direction
        backward_layer_size = len(queue_rev)
        for _ in range(backward_layer_size):
            node_rev = queue_rev.popleft()

            for neighbor in graph1.get_vertex_by_name(node_rev).reverse_links:
                if neighbor.article_name not in visited_rev:
                    visited_rev.add(neighbor.article_name)
                    parent_rev[neighbor.article_name] = node_rev
                    queue_rev.append(neighbor.article_name)

                    if neighbor.article_name in visited:
                        path = _build_path(neighbor.article_name, parent, parent_rev)

                        if len(path) < size_of_shortest_path:
                            size_of_shortest_path = len(path)
                            all_path = [path]
                        elif len(path) == size_of_shortest_path and path not in all_path:
                            all_path.append(path)
                        found_this_round = True

        if found_this_round:
            return all_path[:max_path]
    return False


def _build_path(meeting_node, parent, parent_rev):
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
