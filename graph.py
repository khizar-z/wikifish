"""graph.py

A module containing the Graph and _Vertex classes used to represent
the Wikipedia hyperlink network as a directed graph.

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""
from __future__ import annotations


class _Vertex:
    """A vertex representing a Wikipedia article.

    Each vertex holds the name of the article and its ID. The article name is a string and the id is an int.
    forward_link is a set containing all the articles accessible from the current one and reverse_links is a
    set containing all the vertices that can access the current one.

    Instance Attributes:
        - article_name: The name of the wikipedia page article.
        - article_id: The id of the wikipedia page, assigned during data collection.
        - forward_links: The vertices that are accessible via links from the current one.
        - reverse_links: The set of vertices that are pointing to this vertex via links.

    Representation Invariants:
        - self not in self.forward_links
        - self not in self.reverse_links
    """
    article_name: str
    article_id: int
    forward_links: set[_Vertex]
    reverse_links: set[_Vertex]

    def __init__(self, article_name: str, article_id: int) -> None:
        """Initialize a new vertex with the given article name and ID.

        This vertex is initialized with no links.
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
    #         Maps article_name to _Vertex object.
    _vertices: dict[str, _Vertex]

    def __init__(self) -> None:
        """Initialize an empty graph (no vertices or edges)."""
        self._vertices = {}

    def add_vertex(self, article_name: str, article_id: int) -> None:
        """Add a vertex with the given article name and article id.

        The new vertex is not adjacent to any other vertices.
        Do nothing if the given article is already in this graph.
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

    def get_forward_links(self, article_name: str) -> set:
        """Return a set of the forward links of the given article.

        Note that the *article_name* are returned, not the _Vertex objects themselves.

        Raise a ValueError if article does not appear as a vertex in this graph.
        """
        if article_name in self._vertices:
            v = self._vertices[article_name]
            return {links.article_name for links in v.forward_links}
        else:
            raise ValueError

    def get_all_vertices(self) -> set:
        """Return a set of all vertex items in this graph.
        """
        return set(self._vertices.keys())

    def get_vertex_by_name(self, article_name: str) -> _Vertex:
        """Return a vertex from the given article name."""
        return self._vertices[article_name]

    def contains_vertex(self, article_name: str) -> bool:
        """Return whether a vertex with the given article name exists in this graph."""
        return article_name in self._vertices


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    import python_ta
    python_ta.check_all(config={
        'extra-imports': ['graph', 'heapq', 'collections', 'networkx', 'dash', 'plotly', ],
        'allowed-io': ['load_graph', 'run_analysis'],
        'max-line-length': 120
    })
