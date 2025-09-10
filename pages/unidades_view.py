# pages/contratos_view.py
import dash
from dash import State, html, dcc, dash_table, callback, Output, Input, no_update
import numpy as np
import pandas as pd
import plotly.express as px


from db import engine  # <<< usa la conexión global

dash.register_page(__name__, path="/unidades", name="Unidades")

def fetch_unidades():
    sql = """
        SELECT p.Nombre       AS ProyectoId,
            COUNT(un.PK_Unidad)   AS Disponibles
        FROM dbo.AR_Unidades as un join dbo.AR_Proyectos as p on un.FK_Proyecto = p.PK_Proyecto
        WHERE FK_EstatusUnidadRentable = 1
        GROUP BY p.Nombre
        ORDER BY Disponibles DESC
    """
    return pd.read_sql(sql, engine)


layout = html.Div(
    className="main-unidades",
    children=[
        dcc.Interval(id="tick-unidades", interval=60_000, n_intervals=0),  # refresco cada min
        dcc.Loading( dcc.Graph(id="unidades-graph", style={"height": "60vh", "width": "100%"}))
    ]
) 

@callback(Output("unidades-graph", "figure"),
          Input("tick-unidades", "n_intervals"))
def plot_unidades(_):
    df = fetch_unidades()
    if df.empty:
        return px.bar(title="Unidades disponibles por proyecto")

    fig = px.bar(df, x="ProyectoId", y="Disponibles", text="Disponibles",
                 title="Unidades disponibles por proyecto")
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Proyecto", yaxis_title="Disponibles",
                      xaxis=dict(categoryorder="total descending"))
    return fig