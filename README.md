# WikiFish

**A post-game analysis engine for WikiRace, inspired by Stockfish.**

<img width="1337" height="688" alt="image" src="https://github.com/user-attachments/assets/edf7f272-fc1e-4026-b0b5-3975d6b365e9" />


WikiRace is a game where players navigate from one Wikipedia article to another using only hyperlinks, as fast as possible. WikiFish analyses your completed game — showing you the optimal path, scoring every move you made, and visualising exactly where you went wrong.

---

## Demo

<img width="1230" height="511" alt="image" src="https://github.com/user-attachments/assets/207a7361-1e18-4aaa-8634-6a4597df00dc" />

<img width="1279" height="485" alt="image" src="https://github.com/user-attachments/assets/0ffa97da-67ce-48e0-adab-1b911655c9f3" />


---

## Features

- **Optimal pathfinding** — finds the shortest route between any two articles in the Wikipedia hyperlink graph using Bidirectional BFS or A* with a Jaccard category heuristic
- **Multi-path support** — returns up to 5 equally-optimal paths of the same minimum hop-count
- **Move evaluation** — computes the exact hop-count to the target from every article in your path and classifies each move as GREAT / OPTIMAL / NEUTRAL / BLUNDER
- **Position evaluation chart** — a Plotly line chart plotting your hop-count over each move with an optimal reference line overlaid, styled after Chess.com's accuracy graph
- **Interactive path network** — a NetworkX/Plotly graph showing your path vs the optimal path with nodes colour-coded by role; click any move to zoom into that step
- **Move inspection** — click any point on the chart to see the best available move, your move quality, and the full optimal path from that position
- **Web interface** — fully browser-based, built with Dash; no frontend code required

---

## How it works

Wikipedia's hyperlink network is modelled as a **directed graph** with 1.79 million nodes and 28.5 million edges, loaded from the [SNAP wiki-topcats dataset](https://snap.stanford.edu/data/wiki-topcats.html). The graph is loaded into memory at startup and all pathfinding runs in-memory with zero HTTP requests.

The **A\* heuristic** uses Jaccard overlap of Wikipedia category sets: $h(n) = 1 - |C_n \cap C_t| / |C_n \cup C_t|$, where $C_n$ and $C_t$ are the category memberships of the current article and the target. This steers the search toward topically related articles without requiring any live network requests.

---

## Installation

**Requirements**: Python 3.11+

```bash
git clone https://github.com/khizar-z/wikifish.git
cd wikifish
pip install -r requirements.txt
```

### Dataset

Download the three wiki-topcats files from [SNAP](https://snap.stanford.edu/data/wiki-topcats.html) and place them in the project root:

- `wiki-topcats.txt`
- `wiki-topcats-page-names.txt`
- `wiki-topcats-categories.txt`

> **Note**: The uncompressed files are ~400 MB total. Graph loading takes 30–60 seconds on first run.

---

## Usage

```bash
python main.py
```

Once you see `Starting server at http://127.0.0.1:8050`, open that URL in your browser.

1. Paste your WikiRace path into the text area, one article per line (names must match Wikipedia exactly, case-sensitive)
2. Choose an algorithm: **Bidirectional BFS** or **A\* (category heuristic)**
3. Select how many optimal paths to show (1–5)
4. Click **Analyse**

**Interacting with results:**
- Click any point on the evaluation chart to inspect that move — the path graph zooms in and a detail panel appears
- Click **Reset view** to return to the full path overview

---

## Project structure

```
wikifish/
├── main.py          # Entry point — loads graph and starts Dash server
├── app.py           # Dash web application, layout and callbacks
├── graph.py         # Graph and _Vertex classes
├── load_graph.py    # Dataset loading into Graph + categories dict
├── pathfinding.py   # Bidirectional BFS, A*, Jaccard heuristic
├── analysis.py      # Post-game analysis logic, move quality classification
├── graph_viz.py     # Plotly/NetworkX chart and subgraph figure builders
└── requirements.txt
```

---

## Algorithms

| Algorithm | Completeness | Optimality | Notes |
|---|---|---|---|
| Bidirectional BFS | ✓ | ✓ | Expands from both ends; finds all shortest paths |
| A\* (Jaccard) | ✓ | ✓ | Faster on topically adjacent pairs; degrades to BFS when categories don't overlap |

Both algorithms support multi-path mode, tracking all equally-optimal predecessors per node and reconstructing up to `max_paths` shortest routes.

---

## Built with

- [Dash](https://dash.plotly.com/) — web interface
- [Plotly](https://plotly.com/python/) — interactive charts
- [NetworkX](https://networkx.org/) — graph layout for the path visualisation
- [SNAP wiki-topcats](https://snap.stanford.edu/data/wiki-topcats.html) — Wikipedia hyperlink dataset (Yin et al., KDD 2017)

---

## Authors

Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick — University of Toronto, CSC111, 2026
