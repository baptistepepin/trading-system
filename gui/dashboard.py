import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from flask import Flask
import pandas as pd


def spawn_dashboard(rx):
    server = Flask(__name__)
    app = dash.Dash(__name__, server=server, url_base_pathname='/')

    app.layout = html.Div(children=[
        html.H1(children='Trading Dashboard'),

        dcc.Graph(id='live-update-graph'),
        dcc.Interval(
            id='interval-component',
            interval=1 * 1000,
            n_intervals=0
        )
    ])

    @app.callback(Output('live-update-graph', 'figure'),
                  [Input('interval-component', 'n_intervals')])
    def update_graph_live(n):
        try:
            data = rx.recv()
            df = pd.DataFrame([data])
        except EOFError:
            return go.Figure()
        except Exception as e:
            print(f"Error receiving data: {e}")
            return go.Figure()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ask_prc'], name='Data',
                                 mode='lines+markers'))

        return fig

    app.run_server(debug=True, use_reloader=False)
