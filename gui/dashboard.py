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
            if bar.symbol == 'BTC/USD':
                shared_data.append(bar)
        time.sleep(0.1)  # Small delay to prevent this loop from hogging CPU


def spawn_dashboard(rx):
    """
    Launches a Dash/Flask dashboard that displays live bar data.

    :param rx: The receiving end of a pipe, used to get live bar data.
    """
    # Shared data storage
    shared_data = []

    # Start a background thread to listen for new data
    data_thread = threading.Thread(target=listen_for_data, args=(rx, shared_data))
    data_thread.start()

    # Initialize Dash app
    app = dash.Dash(__name__)

    # Dash layout
    app.layout = html.Div([
        dcc.Graph(id='live-graph', animate=True),
        dcc.Interval(
            id='graph-update',
            interval=1000,  # in milliseconds
            n_intervals=0
        ),
    ])

    @app.callback(Output('live-graph', 'figure'),
                  [Input('graph-update', 'n_intervals')])
    def update_graph_scatter(n):
        if shared_data:
            df = pd.DataFrame([vars(bar) for bar in shared_data])  # Convert Bar objects to DataFrame

            # Create the Plotly Graph object
            trace = go.Scatter(
                x=df['timestamp'],
                y=df['close'],  # Assuming you want to plot the closing price
                name='Scatter',
                mode='lines+markers'
            )

            return {'data': [trace], 'layout': go.Layout(xaxis=dict(range=[min(df['timestamp']), max(df['timestamp'])]),
                                                         yaxis=dict(range=[min(df['close']), max(df['close'])]))}
        else:
            return {'data': [], 'layout': go.Layout()}

    # Running the server
    app.run_server(debug=True, use_reloader=False)
