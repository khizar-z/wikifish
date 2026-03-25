
from __future__ import annotations
import csv
from typing import Any


class _Vertex:
    """A vertex is used to represent a wikipedia article.

    Each vertex is represented using the name of the article and its id, which was assigned during the data collection
    phase. The article name is a string and the id is an int. Forward_link is a set containing all the articles
    accessible from the current one. We call the link between two articles to be bidirectional, when article A can
    be accessed from article B and vice versa

    Instance Attributes:
        - article_name: The name of the wikipedia page article.
        - article_id: The id of the wikipedia page, assigned during data collection.
        - forward_link: The vertices that are accessible from this wikipedia page, ie the wikipedia articles that
        the different hyperlinks redirect to.
        - bidirectional_link: The vertices that are accessible from this wikipedia page, whose forward link's can
        access this article as well.

    Representation Invariants:
        - self not in self.forward_link
        - self not in self.bidirectional_link
        - all(self in u.neighbours for u in self.neighbours)
        - IF IN OMIDIRECTIONAL THEN FORWARD DIRECTIN FOR BOTH
    """
    article_name: str
    article_id: int
    forward_link: set[_Vertex]
    bidirectional_link: set[_Vertex]

    def __init__(self, article_name: str,
                 article_id: int,) -> None:
        """Initialize a new vertex with the given item and kind.

        This vertex is initialized with no neighbours.

        Preconditions:
            -
        """
        self.article_name = article_name
        self.article_id = article_id

    def degree_fl(self) -> int:
        """Return the degree of the forward links."""
        return len(self.forward_link)

    def degree_om(self) -> int:
        """Return the degree of the bidirectional links."""
        return len(self.bidirectional_link)


class Graph:
    """A graph used to represent a wikipedia article network.
    """
    # Private Instance Attributes:
    #     - _vertices:
    #         A collection of the vertices contained in this graph.
    #         Maps item to _Vertex object.
    _vertices: dict[Any, _Vertex]

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
        """Add a one directional edge pointing from article 1 to article 2 in this graph.

        Raise a ValueError if item1 or item2 do not appear as vertices in this graph.

        Preconditions:
            - item1 != item2
        """
        if article_name1 in self._vertices and article_name2 in self._vertices:
            v1 = self._vertices[article_name1]
            v2 = self._vertices[article_name2]

            v1.forward_link.add(v2)
        else:
            raise ValueError

    def add_bidirectional_edge(self, article_name1: str, article_name2: str) -> None:
        """Add a bidirectional edge between the two articles in this graph.

        Raise a ValueError if item1 or item2 do not appear as vertices in this graph.

        Preconditions:
            - item1 != item2
        """
        if article_name1 in self._vertices and article_name2 in self._vertices:
            v1 = self._vertices[article_name1]
            v2 = self._vertices[article_name2]

            v1.bidirectional_link.add(v2)
            v2.bidirectional_link.add(v1)
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
            return {links.article_name for links in v.forward_link}
        else:
            raise ValueError

    def get_all_vertices(self, kind: str = '') -> set:
        """Return a set of all vertex items in this graph.

        Preconditions:
            -
        """
        return set(self._vertices.keys())



