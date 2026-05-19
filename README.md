# WikiFish

**A post-game analysis engine for WikiRace, inspired by Stockfish.**

<img width="1337" height="688" alt="image" src="https://github.com/user-attachments/assets/edf7f272-fc1e-4026-b0b5-3975d6b365e9" />

---

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
- **Snapshot-backed runtime** — compile a current English Wikipedia dump once, then serve analysis from read-only runtime artifacts
- **Title resolution** — accepts canonical article titles, underscore variants, and redirect aliases
- **Web interface** — fully browser-based, built with Dash; no frontend code required

---

## How it works

WikiFish now supports two backends:

- a legacy **SNAP backend** for the original `wiki-topcats` dataset
- a modern **dump backend** compiled from current Wikimedia SQL dumps

The modern runtime compiles current English Wikipedia dumps into:

- a small SQLite catalog for title and redirect resolution
- memory-mapped CSR adjacency arrays for forward and reverse links
- memory-mapped category arrays for the A* heuristic

At runtime, WikiFish opens those artifacts read-only and performs all pathfinding locally with zero HTTP requests.

The **A\* heuristic** uses Jaccard overlap of Wikipedia category sets: $h(n) = 1 - |C_n \cap C_t| / |C_n \cup C_t|$, where $C_n$ and $C_t$ are the category memberships of the current article and the target. This steers the search toward topically related articles without requiring any live network requests.

---

## Installation

**Requirements**: Python 3.11+

```bash
git clone https://github.com/khizar-z/wikifish.git
cd wikifish
pip install -r requirements.txt
```

### Modern Snapshot Workflow

Download the following English Wikipedia SQL dumps into one directory:

- `*-page.sql.gz`
- `*-redirect.sql.gz`
- `*-linktarget.sql.gz`
- `*-pagelinks.sql.gz`
- `*-categorylinks.sql.gz`

Then compile them into WikiFish runtime artifacts:

```bash
python3 main.py compile --dump-dir /path/to/enwiki-dump --output-dir data/enwiki_snapshot
```

Once compilation completes, start the app:

```bash
python3 main.py serve --data-dir data/enwiki_snapshot
```

If you omit `serve`, `python3 main.py` will use the compiled snapshot from `data/enwiki_snapshot` by default.

### Legacy SNAP Workflow

The original `wikifish-lite` dataset still works as a fallback. Download the three [SNAP wiki-topcats](https://snap.stanford.edu/data/wiki-topcats.html) files and place them in the project root:

- `wiki-topcats.txt`
- `wiki-topcats-page-names.txt`
- `wiki-topcats-categories.txt`

If no compiled snapshot exists, `python3 main.py` falls back to this legacy backend automatically.

---

## Usage

```bash
python3 main.py
```

Once you see `Starting server at http://127.0.0.1:8050`, open that URL in your browser. The startup banner will show which snapshot is currently loaded.

1. Paste your WikiRace path into the text area, one article per line
2. Choose an algorithm: **Bidirectional BFS** or **A\* (category heuristic)**
3. Select how many optimal paths to show (1–5)
4. Click **Analyse**

**Interacting with results:**
- Click any point on the evaluation chart to inspect that move — the path graph zooms in and a detail panel appears
- Click **Reset view** to return to the full path overview

**Title lookup notes:**
- Underscores and spaces are treated interchangeably
- Redirect titles resolve to their canonical target article automatically

---

## Project structure

```
wikifish/
├── main.py            # CLI for compiling dumps and starting the Dash app
├── app.py             # Dash web application, layout and callbacks
├── wiki_backend.py    # Backend interface plus SNAP and dump runtime loaders
├── dump_compiler.py   # SQL dump compiler for modern Wikimedia snapshots
├── load_graph.py      # Legacy SNAP dataset loader
├── graph.py           # Legacy Graph and _Vertex classes
├── pathfinding.py     # Backend-based BFS, A*, and reverse-distance helpers
├── analysis.py        # Post-game analysis logic and move scoring
├── graph_viz.py       # Plotly/NetworkX chart and subgraph figure builders
└── tests/             # Fixture-driven regression and integration tests
```

---

## Algorithms

| Algorithm | Completeness | Optimality | Notes |
|---|---|---|---|
| Bidirectional BFS | ✓ | ✓ | Exact shortest paths over the local snapshot backend |
| A\* (Jaccard) | ✓ | ✓ | Uses category overlap from the local snapshot to guide search |

Both algorithms support multi-path mode, returning up to `max_paths` shortest routes.

---

## Built with

- [Dash](https://dash.plotly.com/) — web interface
- [Plotly](https://plotly.com/python/) — interactive charts
- [NetworkX](https://networkx.org/) — graph layout for the path visualisation
- [SNAP wiki-topcats](https://snap.stanford.edu/data/wiki-topcats.html) — legacy Wikipedia hyperlink dataset (Yin et al., KDD 2017)
- [Wikimedia dumps](https://meta.wikimedia.org/wiki/Data_dumps/What's_available_for_download) — current English Wikipedia SQL dump sources

---

## Authors

Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick — University of Toronto, CSC111, 2026
