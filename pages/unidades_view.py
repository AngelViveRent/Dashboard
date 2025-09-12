# pages/contratos_view.py
import dash
from dash import State, html, dcc, dash_table, callback, Output, Input, no_update
import numpy as np
import pandas as pd
import plotly.express as px
from dash_ag_grid import AgGrid


from db import engine  # <<< usa la conexión global

dash.register_page(__name__, path="/unidades", name="Unidades")

def fetch_unidades():
    sql = """
        SELECT
        p.Nombre AS Proyecto,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 1  THEN 1 ELSE 0 END) AS Disponibles,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 2  THEN 1 ELSE 0 END) AS Asignada,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 3  THEN 1 ELSE 0 END) AS Pagando,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 4  THEN 1 ELSE 0 END) AS Liquidada,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 5  THEN 1 ELSE 0 END) AS Solicitud,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 6  THEN 1 ELSE 0 END) AS Liberacion,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 7  THEN 1 ELSE 0 END) AS Autorizadas,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 8  THEN 1 ELSE 0 END) AS Escriturada,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 9  THEN 1 ELSE 0 END) AS Bloqueado,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 10 THEN 1 ELSE 0 END) AS Vendidas,
        SUM(CASE WHEN un.FK_EstatusUnidadRentable = 11  THEN 1 ELSE 0 END) AS Desconocido,
        COUNT(*) AS Total
        FROM dbo.AR_Unidades AS un
        JOIN dbo.AR_Proyectos AS p ON p.PK_Proyecto = un.FK_Proyecto
        GROUP BY p.Nombre
        HAVING
            SUM(CASE WHEN un.FK_EstatusUnidadRentable IN (
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
            ) THEN 1 ELSE 0 END) > 0
        ORDER BY Disponibles DESC
    """
    return pd.read_sql(sql, engine)


layout = html.Div(
    className="main-unidades",
    children=[
        dcc.Interval(id="tick-unidades", interval=300*1000, n_intervals=0),  # refresco cada min
        dcc.Loading(
                    id="load-unidades",
                    children=html.Div([
                        dcc.Graph(id="unidades-graph"),
                        html.Button("Descargar CSV", id="csv-button", className="btn btn-outline-primary"),
                        dcc.Download(id="download-unidades"), 
                        AgGrid(
                            id="unidades-table",
                            columnDefs=[], 
                            rowData=[],
                            columnSize="autoSize",  # ← Auto-ajuste de ancho de columna
                            defaultColDef={
                                "sortable": True,
                                "filter": True,
                                "resizable": True,
                                "floatingFilter": True,  # ← filtros visibles bajo el header
                            },
                            style={"height": "60vh", "width": "auto", "fontFamily": "Helvetica, Arial, sans-serif", "padding": "6px"},
                            className="ag-theme-alpine",  # puedes usar otros como "ag-theme-balham"
                        )
                    ])
                ),
    ]
) 

@callback(
    Output("unidades-graph", "figure"),
    Output("unidades-table", "rowData"),
    Output("unidades-table", "columnDefs"),
    Input("tick-unidades", "n_intervals"),
)
def plot_unidades(_):
    import plotly.express as px

    df = fetch_unidades()  # columnas: Proyecto, Disponibles, Vendidas, Total

    cols = [
        {"field": "Proyecto"},
        {"field": "Disponibles", "type": "numericColumn"},
        {"field": "Asignada", "type": "numericColumn"},
        {"field": "Pagando", "type": "numericColumn"},
        {"field": "Liquidada", "type": "numericColumn"},
        {"field": "Solicitud", "type": "numericColumn"},        
        {"field": "Liberacion", "type": "numericColumn"},
        {"field": "Autorizadas", "type": "numericColumn"},
        {"field": "Escriturada", "type": "numericColumn"},
        {"field": "Bloqueado", "type": "numericColumn"},
        {"field": "Vendidas", "type": "numericColumn"},
        {"field": "Total", "type": "numericColumn"},
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
    State("unidades-table", "rowData"),  # ← usa rowData en AG Grid
    prevent_initial_call=True
)
def download_csv(n, rows):
    # Asegura que rows no esté vacío
    df = pd.DataFrame(rows or [])

    # Ordenar columnas deseadas, si existen
    columnas_deseadas = ["Proyecto", "Disponibles","Asignada","Pagando","Liquidada", "Solicitud", "Liberacion", "Autorizadas","Escriturada", "Bloqueado","Vendidas", "Total"]
    columnas_presentes = [col for col in columnas_deseadas if col in df.columns]
    df = df[columnas_presentes]

    # Exporta a CSV
    return dcc.send_data_frame(df.to_csv, "Unidades.csv", index=False, encoding="utf-8-sig")
