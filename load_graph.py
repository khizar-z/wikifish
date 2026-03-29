"""load_graph.py

A module containing the code that loads the three dataset
files into a Graph and categories dictionary.

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""
from __future__ import annotations
import sys
import csv

from graph import Graph

csv.field_size_limit(sys.maxsize)  # We are working with ridiculous files.


def load_graph(hyperlinks_file: str, page_name_file: str, categories_file: str) -> tuple[Graph, dict[int, set[str]]]:
    """Return a Wikipedia graph corresponding to the given datasets.

    Precondition:
        - hyperlinks_file must be a valid text file with each line representing the link between two article ID
        - page_name_file must be a valid text file with each line containing the article id followed by its name
        - categories_file must be a valid text file with each line containing a category followed by the IDs of every
        article contained in it
    """
    graph = Graph()
    articles: dict[int, str] = {}  # { id: name }

    with open(page_name_file) as file:
        new_page_name = csv.reader(file)
        for row in new_page_name:
            cleaned_line = row[0].split(' ', maxsplit=1)
            articles[int(cleaned_line[0])] = cleaned_line[1]
            graph.add_vertex(cleaned_line[1], int(cleaned_line[0]))
    print(f"  Loaded articles.")

    with open(hyperlinks_file) as file:
        new_hyperlinks_file = csv.reader(file)
        for row in new_hyperlinks_file:
            cleaned_line = row[0].split(' ', maxsplit=1)
            article1, article2 = cleaned_line[0], cleaned_line[1]
            if article1 != article2:
                graph.add_forward_edge(articles[int(cleaned_line[0])], articles[int(cleaned_line[1])])
    print(f"  Loaded edges.")

    categories: dict[int, set[str]] = {aid: set() for aid in articles}  # { id: set(categories) }

    with open(categories_file) as file:
        for row in csv.reader(file):
            parts = row[0].split()
            category_name = parts[0].rstrip(';')
            for aid in parts[1:]:
                if int(aid) in articles:
                    categories[int(aid)].add(category_name)
    print("  Loaded categories.")
    return graph, categories


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    import python_ta
    python_ta.check_all(config={
        'extra-imports': ['graph', 'heapq', 'collections', 'networkx', 'dash', 'plotly', ],
        'allowed-io': ['load_graph', 'run_analysis'],
        'max-line-length': 120
    })
