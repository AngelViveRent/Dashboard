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
        SELECT
        p.Nombre AS Proyecto,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 1  THEN 1 ELSE 0 END) AS Disponibles,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 10 THEN 1 ELSE 0 END) AS Vendidas,
        COUNT(*) AS Total
        FROM dbo.AR_Unidades AS un
        JOIN dbo.AR_Proyectos AS p ON p.PK_Proyecto = un.FK_Proyecto
        GROUP BY p.Nombre
        HAVING SUM(CASE WHEN un.FK_EstatusUnidadRentable = 1  THEN 1 ELSE 0 END) > 0
        OR SUM(CASE WHEN un.FK_EstatusUnidadRentable = 10 THEN 1 ELSE 0 END) > 0
        ORDER BY Disponibles DESC
    """
    return pd.read_sql(sql, engine)


layout = html.Div(
    className="main-unidades",
    children=[
        dcc.Interval(id="tick-unidades", interval=60_000, n_intervals=0),  # refresco cada min
        dcc.Loading(
                    id="load-unidades",
                    children=html.Div([
                        dcc.Graph(id="unidades-graph"),
                        html.Button("Descargar CSV", id="csv-button", className="btn btn-outline-primary"),
                        dcc.Download(id="download-unidades"), 
                        dash_table.DataTable(
                            id="unidades-table",
                            page_size=20,
                            sort_action="native",
                            style_table={"overflowX":"auto"},
                            style_cell={"fontFamily":"Helvetica, Arial, sans-serif", "padding":"6px"}, 
                        )
                    ])
                ),
    ]
) 

@callback(
    Output("unidades-graph", "figure"),
    Output("unidades-table", "data"),
    Output("unidades-table", "columns"),
    Input("tick-unidades", "n_intervals"),
)
def plot_unidades(_):
    import plotly.express as px

    df = fetch_unidades()  # columnas: Proyecto, Disponibles, Vendidas, Total

    cols = [
        {"name": "Proyecto",    "id": "Proyecto"},
        {"name": "Disponibles", "id": "Disponibles"},
        {"name": "Vendidas",    "id": "Vendidas"},
        {"name": "Total",       "id": "Total"},
    ]

    if df.empty:
        fig = px.bar(title="Unidades por proyecto", height=500)
        return fig, [], cols

    # ordenar por Disponibles
    df = df.sort_values("Disponibles", ascending=False)

    # Barras agrupadas: Disponibles vs Vendidas por proyecto
    dff = df.melt(
        id_vars=["Proyecto"],
        value_vars=["Disponibles", "Vendidas"],
        var_name="Estatus",
        value_name="Unidades",
    )

    fig = px.bar(
        dff,
        x="Proyecto",
        y="Unidades",
        color="Estatus",
        text="Unidades",
        barmode="group",   # 'relative' si prefieres apiladas
        height=500,
        title="Unidades por proyecto",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Proyecto",
        yaxis_title="Unidades",
        xaxis=dict(categoryorder="array", categoryarray=df["Proyecto"]),
    )

    return fig, df.to_dict("records"), cols

@callback(
    Output("download-unidades", "data"),
    Input("csv-button", "n_clicks"),
    State("unidades-table", "derived_virtual_data"),  # respeta filtros/orden
    prevent_initial_call=True
)
def download_csv(n, rows):
    df = pd.DataFrame(rows or [])
    return dcc.send_data_frame(df.to_csv, "unidades.csv", index=False, encoding="utf-8-sig")
