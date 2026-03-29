"""graph_viz.py

A module containing two functions (make_evaluation_chart and
make_subgraph_figure) that use the networkx and plotly modules
to create the evaluation line graph and pathfinding graphs
displayed in the results section of the website.

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""
from __future__ import annotations
import networkx as nx
import plotly.graph_objects as go


def make_evaluation_chart(
    player_path: list[str],
    hop_counts: list[int],
    optimal_length: int
) -> go.Figure:
    """Return a Plotly line chart showing the player's position evaluation over time.

    Plots two traces: the player's actual hop-count to the target after each move,
    and a reference line representing perfect play (decrementing by 1 per move from
    optimal_length down to 0). The y-axis is inverted so that 0 (target reached)
    appears at the top. Each data point is clickable via Dash callbacks to trigger
    move inspection.

    Preconditions:
        - len(player_path) == len(hop_counts)
        - optimal_length >= 0
    """
    moves = list(range(len(player_path)))

    # Optimal line spans only optimal_length + 1 points, then stops
    optimal_x = list(range(min(optimal_length + 1, len(player_path))))
    optimal_y = [optimal_length - i for i in optimal_x]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=moves, y=hop_counts,
        mode='lines+markers', name='Your path',
        line=dict(color='steelblue', width=2), marker=dict(size=10),
        text=player_path,
        hovertemplate='%{text}<br>Hops to target: %{y}<extra></extra>',
    ))

    fig.add_trace(go.Scatter(
        x=optimal_x, y=optimal_y,
        mode='lines', name=f'Optimal ({optimal_length} hops)',
        line=dict(color='limegreen', width=2, dash='dash'),
        hoverinfo='skip'
    ))

    fig.update_layout(
        title='Position Evaluation — click a point to inspect that move',
        xaxis=dict(
            title='Move',
            tickmode='array', tickvals=moves, ticktext=player_path, tickangle=45
        ),
        yaxis=dict(
            title='Hops to target',
            autorange='reversed',
            dtick=1,
            tick0=0,
        ),
        plot_bgcolor='#1e1e1e', paper_bgcolor='#1e1e1e',
        font=dict(color='white'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        clickmode='event'
    )

    return fig


def make_subgraph_figure(
    player_path: list[str],
    optimal_paths: list[list[str]],
    move_index: int | None = None,
    per_move_optimal: list[list[str] | None] | None = None,
) -> go.Figure:
    """Return a Plotly network diagram comparing the player's path to the optimal path(s).

    Operates in one of two modes depending on whether move_index is provided:

    Full overview mode (move_index is None): displays the player's entire path
    and all optimal paths as a single network, with nodes colour-coded by role
    (gold = start/end, steelblue = player only, limegreen = optimal only,
    mediumpurple = shared).

    Move inspection mode (move_index is set): displays only the subgraph from
    player_path[move_index] onward, comparing the player's remaining path to the
    optimal path from that position. The player's immediate next move is
    highlighted in steelblue, and the optimal next move in limegreen (or
    mediumpurple if they coincide).

    Node layout is computed using a spring layout with a fixed seed for
    stability across re-renders.

    Preconditions:
        - len(player_path) >= 2
        - move_index is None or 0 <= move_index < len(player_path)
        - per_move_optimal is None or len(per_move_optimal) == len(player_path)
    """
    G = nx.DiGraph()

    # --- Move inspection mode ---
    if move_index is not None and per_move_optimal is not None:
        remaining_player = player_path[move_index:]
        optimal_from_here = per_move_optimal[move_index] if move_index < len(per_move_optimal) else None

        player_next = player_path[move_index + 1] if move_index + 1 < len(player_path) else None
        optimal_next = optimal_from_here[1] if optimal_from_here and len(optimal_from_here) > 1 else None

        for i in range(len(remaining_player) - 1):
            G.add_edge(remaining_player[i], remaining_player[i + 1], kind='player')

        if optimal_from_here:
            for i in range(len(optimal_from_here) - 1):
                G.add_edge(optimal_from_here[i], optimal_from_here[i + 1], kind='optimal')

        pos = nx.spring_layout(G, seed=42)

        player_edge_x, player_edge_y = [], []
        optimal_edge_x, optimal_edge_y = [], []

        for u, v, data in G.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            if data['kind'] == 'player':
                player_edge_x += [x0, x1, None]
                player_edge_y += [y0, y1, None]
            else:
                optimal_edge_x += [x0, x1, None]
                optimal_edge_y += [y0, y1, None]

        node_x, node_y, node_text, node_colors = [], [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)

            if node == remaining_player[0] or node == remaining_player[-1]:
                node_colors.append('gold')
            elif node == player_next and node == optimal_next:
                node_colors.append('mediumpurple')
            elif node == player_next:
                node_colors.append('steelblue')
            elif node == optimal_next:
                node_colors.append('limegreen')
            elif node in set(remaining_player):
                node_colors.append('steelblue')
            else:
                node_colors.append('limegreen')

        title = f'From: {remaining_player[0]}  ->  Target: {remaining_player[-1]}'

    # --- Full overview mode ---
    else:
        optimal_nodes = {node for path in optimal_paths for node in path}
        player_nodes = set(player_path)
        shared_nodes = player_nodes & optimal_nodes

        for i in range(len(player_path) - 1):
            G.add_edge(player_path[i], player_path[i + 1], kind='player')
        for path in optimal_paths:
            for i in range(len(path) - 1):
                G.add_edge(path[i], path[i + 1], kind='optimal')

        pos = nx.spring_layout(G, seed=42)

        player_edge_x, player_edge_y = [], []
        optimal_edge_x, optimal_edge_y = [], []

        for u, v, data in G.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            if data['kind'] == 'player':
                player_edge_x += [x0, x1, None]
                player_edge_y += [y0, y1, None]
            else:
                optimal_edge_x += [x0, x1, None]
                optimal_edge_y += [y0, y1, None]

        node_x, node_y, node_text, node_colors = [], [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)

            if node == player_path[0] or node == player_path[-1]:
                node_colors.append('gold')
            elif node in shared_nodes:
                node_colors.append('mediumpurple')
            elif node in player_nodes:
                node_colors.append('steelblue')
            else:
                node_colors.append('limegreen')

        title = 'Full Path Overview — click a point on the chart to inspect a move'

    fig = go.Figure(data=[
        go.Scatter(x=player_edge_x, y=player_edge_y, mode='lines',
                   line=dict(color='steelblue', width=2), hoverinfo='none', name='Your path'),
        go.Scatter(x=optimal_edge_x, y=optimal_edge_y, mode='lines',
                   line=dict(color='limegreen', width=2, dash='dash'), hoverinfo='none', name='Optimal path'),
        go.Scatter(x=node_x, y=node_y, mode='markers+text',
                   marker=dict(size=14, color=node_colors, line=dict(width=1, color='white')),
                   text=node_text, textposition='top center',
                   textfont=dict(color='white', size=11),
                   hovertemplate='%{text}<extra></extra>', name='Articles'),
    ])

    fig.update_layout(
        title=title,
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font=dict(color='white'),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True
    )

    return fig


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    import python_ta
    python_ta.check_all(config={
        'extra-imports': ['graph', 'heapq', 'collections', 'networkx', 'dash', 'plotly', 'plotly.graph_objects'],
        'allowed-io': ['load_graph', 'run_analysis'],
        'max-line-length': 120
    })
