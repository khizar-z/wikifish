
from __future__ import annotations
from typing import Any


class _Vertex:
    """A vertex representing a Wikipedia article.

    Each vertex holds the name of the article and its ID. The article name is a string and the id is an int.
    forward_link is a set containing all the articles accessible from the current one. The link between two
    articles is bidirectional iff article A can be accessed from article B and vice versa.

    Instance Attributes:
        - article_name: The name of the wikipedia page article.
        - article_id: The id of the wikipedia page, assigned during data collection.
        - forward_links: The vertices that are accessible via links from the current one.
        - reverse_links: The set of vertices that are pointing to this vertex via links.

    Representation Invariants:
        - self not in self.forward_links
        - self not in self.reverse_links
        -
        -
    """
    article_name: str
    article_id: int
    forward_links: set[_Vertex]
    reverse_links: set[_Vertex]

    def __init__(self, article_name: str, article_id: int) -> None:
        """Initialize a new vertex with the given article name and ID.

        This vertex is initialized with no links.

        Preconditions:
            -
        """
        self.article_name = article_name
        self.article_id = article_id
        self.forward_links = set()
        self.reverse_links = set()

    def degree_fl(self) -> int:
        """Return the degree of the forward links."""
        return len(self.forward_links)

    def degree_rl(self) -> int:
        """Return the degree of the reverse links."""
        return len(self.reverse_links)


class Graph:
    """A graph used to represent a Wikipedia article network.
    """
    # Private Instance Attributes:
    #     - _vertices:
    #         A collection of the vertices contained in this graph.
    #         Maps item to _Vertex object.
    _vertices: dict[str, _Vertex]

    def __init__(self) -> None:
        """Initialize an empty graph (no vertices or edges)."""
        self._vertices = {}

    def add_vertex(self, article_name: str, article_id: int) -> None:
        """Add a vertex with the given article name and article id.

        The new vertex is not adjacent to any other vertices.
        Do nothing if the given item is already in this graph.

        Preconditions:
            -
        """
        if article_name not in self._vertices:
            self._vertices[article_name] = _Vertex(article_name, article_id)

    def add_forward_edge(self, article_name1: str, article_name2: str) -> None:
        """Add a directed edge from article 1 to article 2 in this graph.

        Raise a ValueError if article_name1 or article_name2 do not appear as vertices in this graph.

        Preconditions:
            - article_name1 != article_name2
        """
        if article_name1 in self._vertices and article_name2 in self._vertices:
            v1 = self._vertices[article_name1]
            v2 = self._vertices[article_name2]

            v1.forward_links.add(v2)
            v2.reverse_links.add(v1)
        else:
            raise ValueError


    # def adjacent(self, item1: Any, item2: Any) -> bool:
    #     """Return whether item1 and item2 are adjacent vertices in this graph.
    #
    #     Return False if item1 or item2 do not appear as vertices in this graph.
    #     """
    #     if item1 in self._vertices and item2 in self._vertices:
    #         v1 = self._vertices[item1]
    #         return any(v2.item == item2 for v2 in v1.bidirectional)
    #     else:
    #         return False

    def get_forward_links(self, item: Any) -> set:
        """Return a set of the forward links of the given article.

        Note that the *items* are returned, not the _Vertex objects themselves.

        Raise a ValueError if item does not appear as a vertex in this graph.
        """
        if item in self._vertices:
            v = self._vertices[item]
            return {links.article_name for links in v.forward_links}
        else:
            raise ValueError

    def get_all_vertices(self, kind: str = '') -> set:
        """Return a set of all vertex items in this graph.

        Preconditions:
            -
        """
        return set(self._vertices.keys())
