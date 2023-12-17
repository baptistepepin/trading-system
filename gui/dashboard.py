import dash
from dash import dcc, html
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import threading
import time
import pandas as pd


# Function to run in the background to listen for new data
def listen_for_data(rx, shared_data):
    while True:
        if rx.poll():
            bar = rx.recv()

            # Check if the key exists in the dictionary
            if bar.symbol not in shared_data:
                # If not, initialize an empty list
                shared_data[bar.symbol] = []

            shared_data[bar.symbol].append(bar)
        time.sleep(0.1)  # Small delay to prevent this loop from hogging CPU


def spawn_dashboard(rx):
    """
    Launches a Dash/Flask dashboard that displays live bar data.

    :param rx: The receiving end of a pipe, used to get live bar data.
    """
    # Shared data storage
    shared_data = {}

    # Start a background thread to listen for new data
    data_thread = threading.Thread(target=listen_for_data, args=(rx, shared_data))
    data_thread.start()

    # Initialize Dash app
    app = dash.Dash(__name__)

    # Dash layout
    app.layout = html.Div([
        html.Div(id='graphs-container'),
        dcc.Interval(
            id='graph-update',
            interval=1000,  # in milliseconds
            n_intervals=0
        ),
    ])

    # Callback to dynamically generate graphs based on symbols
    @app.callback(Output('graphs-container', 'children'),
                  [Input('graph-update', 'n_intervals')])
    def update_graphs(n):
        graphs = []
        for symbol in shared_data.keys():
            graph = dcc.Graph(
                id={
                    'type': 'dynamic-graph',
                    'index': symbol
                },
                animate=True
            )
            graphs.append(graph)
        return graphs

    # Callback for updating each individual graph
    @app.callback(
        Output({'type': 'dynamic-graph', 'index': dash.dependencies.ALL}, 'figure'),
        [Input('graph-update', 'n_intervals')]
    )
    def update_individual_graphs(n):
        figures = []
        for symbol, bars in shared_data.items():
            df = pd.DataFrame([vars(bar) for bar in bars])  # Convert Bar objects to DataFrame

            # Create the Plotly Graph object
            trace = go.Scatter(
                x=df['timestamp'],
                y=df['close'],  # Assuming you want to plot the closing price
                mode='lines+markers'
            )

            layout = go.Layout(
                title=symbol,
                xaxis=dict(title='Timestamp'),
                yaxis=dict(title='Close Price')
            )

            figures.append({'data': [trace], 'layout': layout})
        return figures

    # Running the server
    app.run_server(debug=True, use_reloader=False)
