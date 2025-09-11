# pages/contratos_view.py
import dash
from dash import State, html, dcc, dash_table, callback, Output, Input, no_update
import numpy as np
import pandas as pd
import plotly.express as px


from db import engine  # <<< usa la conexión global

dash.register_page(__name__, path="/", name="Contratos")

def fetch_contratos():
    sql = """
SELECT
    cl.PK_Cliente        AS ID,
    cl.Alias            AS Nombre,
    c.Alias              as Producto,
    p.Nombre             AS Proyecto,
    CASE 
        WHEN c.MontoInversion < 0 
            THEN '-' + '$' + CONVERT(varchar(20), CONVERT(money, ABS(c.MontoInversion)), 1)
        ELSE        '$' + CONVERT(varchar(20), CONVERT(money, c.MontoInversion), 1)
        END AS Inversion,
    c.MontoInversion                AS Total_de_pagos,
    CASE 
    WHEN ISNULL(SUM(i.Monto),0) < 0 
        THEN '-' + '$' + CONVERT(varchar(20), CONVERT(money, ABS(ISNULL(SUM(i.Monto),0))), 1)
    ELSE        '$' + CONVERT(varchar(20), CONVERT(money, ISNULL(SUM(i.Monto),0)), 1)
    END AS Total_de_pagos_fmt,
    ISNULL(SUM(i.Monto), 0) AS Pagos_reales,
    CAST(c.LastUpdateDate AS date)   as Ultima_Actualizacion,
    e.Estatus AS Estatus,
    CASE WHEN c.FechaFirma IS NULL THEN 'Pendiente' ELSE 'En Proceso' END AS Tiene_Firma,
    CAST(c.FechaFirma AS date) AS FechaFirma,
    u.Nombre             AS Asesor,
    c.IsActive  AS Activado

FROM dbo.AR_Contratos   AS c
JOIN dbo.AR_Clientes    AS cl ON cl.PK_Cliente = c.FK_Cliente
LEFT join dbo.AR_Unidades as un ON un.PK_Unidad = c.FK_Unidad
LEFT JOIN dbo.AR_Proyectos AS p ON un.FK_Proyecto = p.PK_Proyecto
LEFT JOIN dbo.AR_Ingresos  AS i ON i.FK_Contrato = c.PK_Contrato
left join dbo.CT_EstatusContrato as e on c.FK_EstatusContrato = e.PK_EstatusContrato
LEFT JOIN dbo.AspNetUsers as u on u.UserId = c.FK_UsuarioAsesor WHERE c.IsActive = 1 and c.ID_interno_consolidado is null
GROUP BY
    cl.PK_Cliente,
    cl.Alias,
    c.Alias,
    p.Nombre,
    c.MontoInversion,
    c.LastUpdateDate, 
    e.Estatus,
    c.FechaFirma,
    u.Nombre,
    c.IsActive
ORDER BY Inversion DESC
    """
    return pd.read_sql(sql, engine)


@callback(
    Output("resumen-contratos", "children"),
    Input("memory-table", "derived_virtual_data")
)
def resumen(rows):
    import pandas as pd
    df = pd.DataFrame(rows or [])

    total_pagos = (
        pd.to_numeric(df.get("Total_de_pagos"), errors="coerce")
          .fillna(0).sum()
        if "Total_de_pagos" in df.columns else 0.0
    )

    pagos_real = (
        pd.to_numeric(df.get("Pagos_reales"), errors="coerce")
        .fillna(0).sum()
        if "Pagos_reales" in df.columns else 0.0
    )
    activos = int(pd.Series(df.get("Activado")).eq(1).sum())  # o .eq("activo") si es texto

    return html.Div([
        html.H4("Activos", className="text-center mb-2"),
        html.Div(className="d-flex gap-4 justify-content-between", children=[
            html.Div([
                html.H6("💰Valor", className="mb-1"),
                html.H4(f"${total_pagos:,.2f}", className="mb-0 fw-bold text-primary")
            ]),
            html.Div([
                html.H6("Cantidad", className="mb-1"),
                html.H4(f"{activos:,}", className="mb-0 fw-bold text-success")
            ]),
            html.Div([
                html.H6("💰Pagado", className="mb-1"),
                html.H4(f"${pagos_real:,.2f}", className="mb-0 fw-bold text-primary")
            ]),
        ])
    ], className="p-2", style={"height": "100%"})

@callback(
    Output("revicion-contratos", "children"),
    Input("memory-table", "derived_virtual_data")
)
def revicion_contratos(rows):
    import pandas as pd
    df = pd.DataFrame(rows or [])

    # 1) Normaliza estatus y máscara de firmados
    est = (df.get("Estatus", pd.Series(dtype=str))
             .astype(str).str.strip().str.lower())
    mask_firma = est.eq("firma")  # o .isin(["firma","firmado"])

    # 2) Inversión numérica: usa InversionNum si existe; si no, parsea "Inversion"
    if "InversionNum" in df.columns:
        inv = pd.to_numeric(df["InversionNum"], errors="coerce").fillna(0)
    else:
        inv = (df.get("Inversion", pd.Series(dtype=str)).astype(str)
                 .replace(r"[^\d\.-]", "", regex=True)
                 .replace("", None).astype(float)).fillna(0)

    firmados = int(mask_firma.sum())
    total_inv_firmados = float(inv.where(mask_firma).sum())


    return html.Div([
            html.H4("Firmados", className="text-center mb-2"),
            html.Div(className="d-flex gap-4 justify-content-between", children=[
                html.Div([
                    html.H6("💰Total", className="mb-1"),
                    html.H4(f"${total_inv_firmados:,.2f}", className="mb-0 fw-bold text-success")
                ]),
                html.Div([
                    html.H6("Cantidad", className="mb-1"),
                    html.H4(f"{firmados:,}", className="mb-0 fw-bold text-primary")
                ]),
            ])
        ], className="p-2", style={"height": "100%"})


layout = html.Div(
    className=" main-contrato",
    children=[
        dcc.Loading(
        html.Div(
        className="content d-flex flex-column",
        children=[
            html.Div(
                className="resultados d-flex flex-wrap mb-4",  # flex-wrap permite múltiples en fila
                children=[
                    dcc.Interval(id='init-load', interval=1*1000, n_intervals=0),
                    html.Div(id='resumen-contratos', className="card p-3 m-2 shadow", style={"width": "40rem"}),
                    html.Div(id="revicion-contratos", className="card p-3 m-2 shadow", style={"width": "40rem"}),
                ]
            ),
            html.Div([
                dcc.Interval(id="tick", interval=60*1000, n_intervals=0),  # refresco cada minuto
                dcc.Store(id="store-contratos"),                           # aquí guardas el DF completo
                dcc.Dropdown(
                    id="memory-clientes",
                    options=[],            # se llena por callback
                    value=[],              # selección inicial vacía
                    multi=True,
                    placeholder="Elige clientes…",
                    clearable=True,
                    style={"width": "40%"}
                ),

                dcc.Dropdown(
                    id="memory-proyecto",
                    options=[], value=None, multi=False,
                    placeholder="Elige proyecto…", clearable=True,
                    style={"width": "40%"},
                ),
                dcc.Graph(id="memory-graph",style={"height": "60vh", "width": "100%"}),
                html.Button("Descargar CSV", id="download-button", className="btn btn-outline-primary"),
                dcc.Download(id="download-contratos"),
                dash_table.DataTable(id="memory-table",
                        fixed_rows={"headers": True},
                        sort_action="native",
                        virtualization=True,
                        style_table={"overflowX": "auto","overflowY": "auto",
                                     "height": "80vh",
                                     "minWidth": "0",
                                     "width": "100%",
                                     "margin": "0", "padding": "0",
                                      },
                        hidden_columns=["Activado", "Total_de_pagos", "Pagos_reales"],
                        css=[{"selector": ".show-hide", "rule": "display: none"}],
                        style_cell={
                            "whiteSpace": "nowrap", "textOverflow": "ellipsis",
                            "minWidth": "90px","maxWidth": "240px", "margin-top": "1%",
                            "fontFamily": "Helvetica, Arial, 'Helvetica Neue', sans-serif",
                            "fontSize": "13px",
                        },
                        style_header={
                            "fontFamily": "Helvetica, Arial, 'Helvetica Neue', sans-serif",
                            "fontWeight": "600",
                        },
                    )
            ])
        ]  
        )
        )
    ]
) 
# 1) Cargar datos a memoria (una vez y luego cada minuto)
@callback(Output("store-contratos", "data"), Input("tick", "n_intervals"))
def load_data(_):
    df = fetch_contratos()
    return df.to_dict("records")

# 2) Poblar el dropdown de clientes
@callback(Output("memory-clientes", "options"), Input("store-contratos", "data"))
def opts_clientes(data):
    import pandas as pd
    df = pd.DataFrame(data or [])
    clientes = sorted(df["Nombre"].dropna().unique()) if "Nombre" in df else []
    return [{"label": c, "value": c} for c in clientes]

# 3) Poblar el dropdown de proyectos
@callback(Output("memory-proyecto","options"),
          Input("store-contratos","data"))
def opts_proyectos(data):
    import pandas as pd
    df = pd.DataFrame(data or [])
    if "Proyecto" not in df.columns:
        return []
    proyectos = sorted(df["Proyecto"].dropna().astype(str).unique())
    return [{"label": p, "value": p} for p in proyectos]


# 4) Filtrar en memoria según el dropdown
@callback(
    Output("memory-table","data"),
    Output("memory-table","columns"),
    Output("memory-graph","figure"),
    Input("store-contratos","data"),
    Input("memory-clientes","value"),
    Input("memory-proyecto","value"),
)
def update_table_graph(raw, clientes, proyecto):
    import numpy as np
    import pandas as pd, plotly.express as px

    df = pd.DataFrame(raw or [])

    if clientes and "Nombre" in df.columns:
        df = df[df["Nombre"].isin(clientes)]
    if proyecto and "Proyecto" in df.columns:
        df = df[df["Proyecto"] == proyecto]

    # Fecha (primera no nula)
    cand = [c for c in ["FechaFirma","Fecha_de_Firma","Ultima_Actualizacion","LastUpdateDate"] if c in df.columns]
    if cand:
        fecha = pd.to_datetime(df[cand[0]], errors="coerce")
        for c in cand[1:]:
            fecha = fecha.combine_first(pd.to_datetime(df[c], errors="coerce"))
        dff = df.assign(Fecha=fecha)   # ← solo en copia
    else:
        dff = df.copy()

    # Métrica fija: Total_de_pagos -> Valor_total
    def parse_money(s):
        return (s.astype(str).str.replace(r"[^\d\.-]", "", regex=True)
                .replace("", None).astype(float))
    
    col = df.get("Total_de_pagos")
    y = pd.to_numeric(col, errors="coerce") if col is not None else pd.Series(index=df.index, dtype=float)
    if np.all(pd.isna(np.atleast_1d(y))) and "Total_de_pagos_fmt" in df.columns:
        y = parse_money(df["Total_de_pagos_fmt"])
    df["Valor_total"] = y
    dff["Valor_total"] = y  

# -------- BARRAS (agregado mensual) --------
    dff = dff.dropna(subset=["Valor_total"])
    if "Fecha" in dff.columns:
        dff["Fecha"] = pd.to_datetime(dff["Fecha"], errors="coerce")
        dff = dff.dropna(subset=["Fecha"])
        # agregamos por mes para reducir número de barras
        dff = (dff.assign(Fecha=dff["Fecha"].dt.to_period("M").dt.to_timestamp())
                 .groupby(["Fecha","Nombre"], as_index=False)["Valor_total"].sum())

    # (Opcional) dejar solo top N clientes y agrupar el resto
    TOP_N = 12
    if "Nombre" in dff.columns and dff["Nombre"].nunique() > TOP_N:
        tot = dff.groupby("Nombre")["Valor_total"].sum().nlargest(TOP_N).index
        dff["Nombre"] = np.where(dff["Nombre"].isin(tot), dff["Nombre"], "Otros")
        dff = dff.groupby(["Fecha","Nombre"], as_index=False)["Valor_total"].sum()

    fig = px.bar(
        dff,
        x=("Fecha" if "Fecha" in dff.columns else "Nombre"),
        y="Valor_total",
        color=("Nombre" if "Nombre" in dff.columns else None),
        barmode="relative",  # usa "group" si prefieres agrupadas
        labels={"Valor_total": "Total de pagos", "Fecha": "Fecha"},
        height=500
    )
    fig.update_layout(bargap=0.05, hovermode="x unified")

    # Tabla
    cols = [{"name": c, "id": c} for c in df.columns if c != "Valor_total"]
    return df.to_dict("records"), cols, fig 

@callback(
    Output("memory-proyecto", "options",allow_duplicate=True),
    Output("memory-proyecto", "value"),
    Input("store-contratos", "data"),
    State("memory-proyecto", "value"),   # para no reescribir si ya hay selección}
    prevent_initial_call=True
)
def opts_proyectos(data, current_value):
    df = pd.DataFrame(data or [])
    if "Proyecto" not in df.columns:
        return [], None

    proyectos = sorted(df["Proyecto"].dropna().astype(str).unique())
    options = [{"label": p, "value": p} for p in proyectos]

    # si el usuario ya eligió algo, no lo cambies
    if current_value:
        return options, no_update

    # default
   #default = "AURUM TULUM" if "AURUM TULUM" in proyectos else (proyectos[0] if proyectos else None)
    return options, None

@callback(
    Output("download-contratos", "data",allow_duplicate=True),
    Input("download-button", "n_clicks"),
    State("memory-table", "derived_virtual_data"),  # respeta filtros/orden
    prevent_initial_call=True
)
def download_csv(n, rows):
    df = pd.DataFrame(rows or [])
    return dcc.send_data_frame(df.to_csv, "unidades.csv", index=False, encoding="utf-8-sig")