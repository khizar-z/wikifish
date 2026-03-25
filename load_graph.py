from __future__ import annotations
import csv

from graph import Graph


def load_graph(hyperlinks_file: str, page_name_file: str) -> Graph:
    """Return a Wikipedia graph corresponding to the given datasets.
    """
    graph = Graph()
    articles = {}

    with open(page_name_file) as csvfile:
        new_page_name = csv.reader(csvfile)
        for row in new_page_name:
            cleaned_line = row[0].split(' ', maxsplit=1)
            articles[cleaned_line[0]] = cleaned_line[1]
            graph.add_vertex(cleaned_line[1], int(cleaned_line[0]))
            print(f"Added article ID {cleaned_line[0]} for {cleaned_line[1]}.")

    with open(hyperlinks_file) as csvfile:
        new_hyperlinks_file = csv.reader(csvfile)
        for row in new_hyperlinks_file:
            cleaned_line = row[0].split(' ', maxsplit=1)
            article1, article2 = cleaned_line[0], cleaned_line[1]
            if article1 != article2:
                graph.add_forward_edge(articles[cleaned_line[0]], articles[cleaned_line[1]])
                print(f"Added edge between {article1} and {article2}.")

    return graph


load_graph('wiki-topcats.txt', 'wiki-topcats-page-names.txt')
