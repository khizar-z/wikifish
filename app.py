"""app.py

A module containing the Dash app server that displays and runs
the interactive website and its components.

Copyright (c) 2026 Khizar Zaman, Safid Musabbir, Tanishq Pol, Ali Mallick
"""

from __future__ import annotations
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go

from analysis import run_analysis
from graph_viz import make_evaluation_chart, make_subgraph_figure

# --- Load graph once at startup ---
graph = None
categories = None


def init(g, c):
    """Initialize the Dash app."""
    global graph, categories
    graph = g
    categories = c
    app.run(debug=False)


QUALITY_COLOURS = {
    "OPTIMAL": "#2ecc71",
    "GREAT":   "#1abc9c",
    "NEUTRAL": "#f39c12",
    "BLUNDER": "#e74c3c",
    "UNKNOWN": "#95a5a6",
}

app = dash.Dash(__name__)

app.layout = html.Div(
    style={'backgroundColor': '#1e1e1e', 'minHeight': '100vh', 'padding': '30px',
           'fontFamily': 'sans-serif', 'color': 'white'},
    children=[
        html.H1('WikiFish', style={'marginBottom': '4px'}),
        html.P('Post-game analysis for WikiRace', style={'color': '#aaa', 'marginTop': 0}),

        html.Div(
            id='startup-notice',
            children='Graph loaded and ready.',
            style={'color': 'limegreen', 'fontSize': '13px', 'marginBottom': '10px'}
        ),

        html.Hr(style={'borderColor': '#333'}),

        # --- Input form ---
        html.Div(style={'maxWidth': '600px', 'marginBottom': '30px'}, children=[
            html.H3('Enter your game'),
            html.P('Paste your path below, one article per line:', style={'color': '#aaa'}),
            dcc.Textarea(
                id='path-input',
                placeholder='France\nMontpellier\nCourtyard\nPatio',
                style={
                    'width': '100%', 'height': '160px', 'backgroundColor': '#2a2a2a',
                    'color': 'white', 'border': '1px solid #444', 'borderRadius': '6px',
                    'padding': '10px', 'fontSize': '14px', 'resize': 'vertical'
                }
            ),
            html.Div(style={'display': 'flex', 'gap': '20px', 'marginTop': '12px',
                            'alignItems': 'center', 'flexWrap': 'wrap'}, children=[
                html.Div([
                    html.Label('Algorithm', style={'display': 'block', 'marginBottom': '4px',
                                                   'color': '#aaa', 'fontSize': '13px'}),
                    dcc.Dropdown(
                        id='algorithm-input',
                        options=[
                            {'label': 'Bidirectional BFS', 'value': 'bfs'},
                            {'label': 'A* (category heuristic)', 'value': 'astar'},
                        ],
                        value='bfs',
                        clearable=False,
                        style={'width': '220px', 'backgroundColor': '#2a2a2a',
                               'color': 'black', 'border': 'none'}
                    ),
                ]),
                html.Div([
                    html.Label('Optimal paths to show', style={'display': 'block', 'marginBottom': '4px',
                                                               'color': '#aaa', 'fontSize': '13px'}),
                    dcc.Slider(
                        id='max-paths-input',
                        min=1, max=5, step=1, value=3,
                        marks={i: {'label': str(i), 'style': {'color': 'white'}} for i in range(1, 6)},
                        tooltip=False,
                    ),
                ], style={'flex': 1, 'minWidth': '200px'}),
            ]),
            html.Button(
                'Analyse', id='analyse-button', n_clicks=0,
                style={
                    'marginTop': '16px', 'padding': '10px 28px', 'fontSize': '15px',
                    'backgroundColor': '#2980b9', 'color': 'white', 'border': 'none',
                    'borderRadius': '6px', 'cursor': 'pointer'
                }
            ),
            html.Div(id='error-msg', style={'color': '#e74c3c', 'marginTop': '10px'}),
        ]),

        html.Hr(style={'borderColor': '#333'}),

        # --- Results area (hidden until analysis runs) ---
        dcc.Loading(
            id='loading-results',
            type='circle',
            color='steelblue',
            children=html.Div(id='results-area', style={'display': 'none'}, children=[

                html.Div(id='summary-bar', style={'marginBottom': '20px'}),

                dcc.Graph(id='eval-chart'),

                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '16px',
                                'justifyContent': 'center', 'marginTop': '4px'}, children=[
                    html.P('Click any point on the chart above to inspect that move.',
                           style={'color': '#aaa', 'margin': 0}),
                    html.Button('Reset view', id='reset-button', n_clicks=0,
                                style={'padding': '4px 14px', 'fontSize': '13px',
                                       'backgroundColor': '#333', 'color': '#aaa',
                                       'border': '1px solid #555', 'borderRadius': '4px',
                                       'cursor': 'pointer'}),
                ]),

                dcc.Graph(id='subgraph-chart'),

                html.Div(id='move-inspect-panel', style={'marginTop': '16px'}),

                html.Div(id='move-breakdown', style={'marginTop': '20px'}),

                html.Div(id='optimal-paths-list', style={'marginTop': '20px'}),
            ])
        ),

        # Stores
        dcc.Store(id='analysis-store'),
        dcc.Store(id='click-store', data=None),
    ]
)


@app.callback(
    Output('analysis-store', 'data'),
    Output('error-msg', 'children'),
    Output('results-area', 'style'),
    Input('analyse-button', 'n_clicks'),
    State('path-input', 'value'),
    State('algorithm-input', 'value'),
    State('max-paths-input', 'value'),
    prevent_initial_call=True
)
def run(n_clicks, path_text, algorithm, max_paths):
    """Validate the user's input and run post-game analysis on button click.

    Parses path_text into a list of article names, checks that each article
    exists in the graph, and calls run_analysis(). Serialises the results into
    a JSON-compatible dict for storage in dcc.Store. Returns an error message
    and keeps the results area hidden if validation fails.
    """
    if not path_text or not path_text.strip():
        return None, 'Please enter a path.', {'display': 'none'}

    player_path = [line.strip() for line in path_text.strip().splitlines() if line.strip()]

    if len(player_path) < 2:
        return None, 'Path must have at least two articles.', {'display': 'none'}

    missing = [a for a in player_path if not graph.contains_vertex(a)]
    if missing:
        msg = f'Articles not found in dataset: {", ".join(missing)}'
        return None, msg, {'display': 'none'}

    results = run_analysis(graph, categories, player_path, algorithm, max_paths or 3)

    store = {
        'player_path': results['player_path'],
        'optimal_paths': results['optimal_paths'] or [],
        'optimal_length': results['optimal_length'],
        'hop_counts': results['hop_counts'],
        'move_quality': results['move_quality'],
        'per_move_optimal': [p for p in results['per_move_optimal']],
    }

    return store, '', {'display': 'block'}


@app.callback(
    Output('click-store', 'data'),
    Input('eval-chart', 'clickData'),
    Input('reset-button', 'n_clicks'),
    Input('analysis-store', 'data'),
    prevent_initial_call=True
)
def update_click_store(click_data, reset_clicks, store):
    """Track the active move index for chart inspection.

    Sets the click-store to the x-index of the clicked point on the evaluation
    chart. Clears it to None when the Reset button is pressed or when a new
    analysis is run, restoring the subgraph to full overview mode.
    """
    triggered = callback_context.triggered[0]['prop_id']
    if 'reset-button' in triggered or 'analysis-store' in triggered:
        return None
    if click_data:
        return click_data['points'][0]['x']
    return None


@app.callback(
    Output('eval-chart', 'figure'),
    Output('subgraph-chart', 'figure'),
    Output('summary-bar', 'children'),
    Output('move-breakdown', 'children'),
    Output('optimal-paths-list', 'children'),
    Output('move-inspect-panel', 'children'),
    Input('analysis-store', 'data'),
    Input('click-store', 'data'),
    prevent_initial_call=True
)
def update_visuals(store, move_index):
    """Render all visual components from the analysis store.

    Fires when a new analysis is stored or when click-store changes. Rebuilds
    the evaluation chart, subgraph, summary bar, move breakdown table, optimal
    paths list, and move inspect panel. When move_index is set, the subgraph
    switches to remaining-path mode and the inspect panel shows per-move detail;
    when None, both show the full overview.
    """
    if store is None:
        empty = go.Figure()
        return empty, empty, [], [], [], []

    player_path = store['player_path']
    optimal_paths = store['optimal_paths']
    optimal_length = store['optimal_length']
    hop_counts = store['hop_counts']
    move_quality = store['move_quality']
    per_move_optimal = store['per_move_optimal']

    eval_fig = make_evaluation_chart(player_path, hop_counts, optimal_length or len(player_path) - 1)
    subgraph_fig = make_subgraph_figure(
        player_path,
        optimal_paths or [player_path],
        move_index,
        per_move_optimal
    )

    # Summary bar
    player_hops = len(player_path) - 1
    summary = html.Div(style={'display': 'flex', 'gap': '30px', 'marginBottom': '10px'}, children=[
        html.Div([html.Div(str(player_hops), style={'fontSize': '36px', 'fontWeight': 'bold'}),
                  html.Div('Your hops', style={'color': '#aaa', 'fontSize': '13px'})]),
        html.Div([html.Div(str(optimal_length) if optimal_length is not None else '?',
                           style={'fontSize': '36px', 'fontWeight': 'bold', 'color': 'limegreen'}),
                  html.Div('Optimal hops', style={'color': '#aaa', 'fontSize': '13px'})]),
        html.Div([html.Div(f'+{player_hops - optimal_length}' if optimal_length else '?',
                           style={'fontSize': '36px', 'fontWeight': 'bold', 'color': '#e74c3c'}),
                  html.Div('Extra hops', style={'color': '#aaa', 'fontSize': '13px'})]),
    ])

    # Move breakdown table
    rows = []
    for i, (article, quality) in enumerate(zip(player_path[:-1], move_quality)):
        next_article = player_path[i + 1]
        colour = QUALITY_COLOURS.get(quality, 'white')
        rows.append(html.Tr([
            html.Td(f'{i + 1}', style={'padding': '6px 12px', 'color': '#aaa'}),
            html.Td(article, style={'padding': '6px 12px'}),
            html.Td('→', style={'padding': '6px 4px', 'color': '#aaa'}),
            html.Td(next_article, style={'padding': '6px 12px'}),
            html.Td(quality, style={'padding': '6px 12px', 'color': colour, 'fontWeight': 'bold'}),
            html.Td(f'{hop_counts[i]} → {hop_counts[i + 1]} hops',
                    style={'padding': '6px 12px', 'color': '#aaa', 'fontSize': '13px'}),
        ]))

    breakdown = html.Div([
        html.H3('Move Breakdown'),
        html.Table(rows, style={'borderCollapse': 'collapse', 'width': '100%',
                                'backgroundColor': '#2a2a2a', 'borderRadius': '6px'})
    ])

    # Optimal paths list
    path_items = []
    for i, path in enumerate(optimal_paths):
        path_items.append(html.Div(style={'marginBottom': '12px'}, children=[
            html.B(f'Path {i + 1}: ', style={'color': 'limegreen'}),
            html.Span(' → '.join(path))
        ]))

    paths_section = html.Div([
        html.H3('Optimal Path(s)'),
        html.Div(path_items if path_items else 'No path found.')
    ])

    # Move inspect panel
    inspect_panel = []
    if move_index is not None and move_index < len(player_path) - 1:
        current_article = player_path[move_index]
        player_next = player_path[move_index + 1]
        optimal_from_here = per_move_optimal[move_index]
        optimal_next = optimal_from_here[1] if optimal_from_here and len(optimal_from_here) > 1 else None
        quality = move_quality[move_index] if move_index < len(move_quality) else 'UNKNOWN'
        quality_colour = QUALITY_COLOURS.get(quality, 'white')
        same_move = player_next == optimal_next

        rows_inspect = [
            html.Tr([
                html.Td('You were on', style={'padding': '8px 12px', 'color': '#aaa'}),
                html.Td(current_article, style={'padding': '8px 12px', 'fontWeight': 'bold'}),
            ]),
            html.Tr([
                html.Td('You went to', style={'padding': '8px 12px', 'color': '#aaa'}),
                html.Td(player_next, style={'padding': '8px 12px',
                                            'color': quality_colour, 'fontWeight': 'bold'}),
            ]),
        ]

        # Only show the best available move when the player did not pick optimally
        if not same_move and optimal_next:
            rows_inspect.append(html.Tr([
                html.Td('Best available move', style={'padding': '8px 12px', 'color': '#aaa'}),
                html.Td(optimal_next, style={'padding': '8px 12px',
                                             'color': 'limegreen', 'fontWeight': 'bold'}),
            ]))

        rows_inspect.append(html.Tr([
            html.Td('Move quality', style={'padding': '8px 12px', 'color': '#aaa'}),
            html.Td(quality, style={'padding': '8px 12px',
                                    'color': quality_colour, 'fontWeight': 'bold'}),
        ]))

        if optimal_from_here:
            rows_inspect.append(html.Tr([
                html.Td('Optimal path from here', style={'padding': '8px 12px', 'color': '#aaa',
                                                          'verticalAlign': 'top'}),
                html.Td(' → '.join(optimal_from_here),
                        style={'padding': '8px 12px', 'color': 'limegreen', 'fontSize': '13px'}),
            ]))

        inspect_panel = html.Div([
            html.H3(f'Move {move_index + 1} Inspection', style={'marginBottom': '10px'}),
            html.Table(rows_inspect, style={
                'borderCollapse': 'collapse', 'backgroundColor': '#2a2a2a',
                'borderRadius': '6px', 'width': '100%', 'maxWidth': '700px'
            })
        ])

    return eval_fig, subgraph_fig, summary, breakdown, paths_section, inspect_panel


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    import python_ta
    python_ta.check_all(config={
        'extra-imports': ['graph', 'heapq', 'collections', 'networkx', 'dash', 'plotly', ],
        'allowed-io': ['load_graph', 'run_analysis'],
        'max-line-length': 120
    })
    app.run(debug=True)
