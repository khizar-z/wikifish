"""main.py

The starting point for the program. Loads the graph through load_graph()
and initiates the website through wikifish_app.init().

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""
from load_graph import load_graph
import app as wikifish_app

if __name__ == '__main__':
    print("Loading graph (this will take 30-60 seconds)...")
    graph, categories = load_graph(
        'wiki-topcats.txt',
        'wiki-topcats-page-names.txt',
        'wiki-topcats-categories.txt'
    )
    print("Graph loaded. Starting server at http://127.0.0.1:8050 ...")
    wikifish_app.init(graph, categories)
