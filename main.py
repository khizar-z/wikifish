
from load_graph import load_graph


def init(start, end, graph):
    """
    Docstring unimplemented
    """
    pass


if __name__ == '__main__':
    graph, categories = load_graph(
        'wiki-topcats.txt',
        'wiki-topcats-page-names.txt',
        'wiki-topcats-categories.txt'
    )

