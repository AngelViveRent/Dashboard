# pages/contratos_view.py
import dash
from dash import State, html, dcc, dash_table, callback, Output, Input, no_update
import pandas as pd
import plotly.express as px


from db import engine  # <<< usa la conexión global

dash.register_page(__name__, path="/contratos", name="Contratos")

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
    activos = int(pd.Series(df.get("Activado")).eq(1).sum())  # o .eq("activo") si es texto


    return html.Div(className="d-flex gap-4", children=[
        html.Div([html.H6("💰 Valor Total", className="mb-1"),
                  html.H4(f"${total_pagos:,.2f}", className="mb-0 fw-bold text-success")]),
        html.Div([html.H6("Total de contratos activos", className="mb-1"),
                  html.H4(f"{activos:,}", className="mb-0 fw-bold text-primary")]),
    ])

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

    return html.Div(className="d-flex gap-4", children=[
        html.Div([html.H6("Total de contratos firmados", className="mb-1"),
                  html.H4(f"{firmados:,}", className="mb-0 fw-bold text-primary")]),
        html.Div([html.H6("💰 Valor Contratos Firmados", className="mb-1"),
                  html.H4(f"${total_inv_firmados:,.2f}", className="mb-0 fw-bold text-success")]),
    ])

layout = html.Div(
    className="main-contrato",
    children=[
        html.Div(
        className="content d-flex flex-column",
        children=[
            html.Div(
                className="resultados d-flex flex-wrap mb-4",  # flex-wrap permite múltiples en fila
                children=[
                    dcc.Interval(id='init-load', interval=1*1000, n_intervals=0),
                    html.Div(id='resumen-contratos', className="card p-3 m-2 shadow", style={"width": "32rem"}),
                    html.Div(id="revicion-contratos", className="card p-3 m-2 shadow", style={"width": "32rem"}),
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
                    style={"width": "80%"}
                ),

                dcc.Dropdown(
                    id="memory-field",
                    style={"width": "80%"},
                    options=[
                        {"label":"Inversión","value":"InversionNum"},
                        {"label":"Total de pagos","value":"Total_de_pagos"},
                        # {"label":"# Contratos","value":"_count"},
                    ],
                    value="Total_de_pagos",   # ← evita quedarte en una columna inexistente
                    clearable=False
                ),
                dcc.Graph(id="memory-graph"),
                dash_table.DataTable(id="memory-table",                 
                        fixed_rows={"headers": True},
                        virtualization=True,
                        fill_width=False, 
                        style_table={"overflowX": "auto","overflowY": "auto",
                                     "height": "80vh", 
                                     "minWidth": "100%", 
                                     "width": "65vh", 
                                     "margin": "0 auto", "padding": "0",
                                      },
                        hidden_columns=["Activado", "Total_de_pagos"],
                        css=[{"selector": ".show-hide", "rule": "display: none"}],
                        style_cell={
                            "whiteSpace": "nowrap", "textOverflow": "ellipsis",
                            "minWidth": "90px", "width": "120px", "maxWidth": "240px", "margin-top": "1%",
                        })
            ])
        ]  
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

# 3) Filtrar en memoria según el dropdown
@callback(
    Output("memory-table","data"),
    Output("memory-table","columns"),
    Output("memory-graph","figure"),
    Input("store-contratos","data"),
    Input("memory-clientes","value"),
    Input("memory-field","value"),
)
def update_table_graph(raw, clientes, field):
    import pandas as pd, plotly.express as px

    df = pd.DataFrame(raw or [])
    if clientes:
        df = df[df["Nombre"].isin(clientes)]

    # --- 1) Fecha: primera NO NULA entre varias columnas ---
    cand = [c for c in ["FechaFirma", "Fecha_de_Firma", "Ultima_Actualizacion", "LastUpdateDate"] if c in df.columns]
    if cand:
        fecha = pd.to_datetime(df[cand[0]], errors="coerce")
        for c in cand[1:]:
            fecha = fecha.combine_first(pd.to_datetime(df[c], errors="coerce"))
        df["Fecha"] = fecha

    # --- 2) Métrica Y: numérica con fallbacks ---
    def parse_money(s):
        return (s.astype(str)
                 .str.replace(r"[^\d\.-]", "", regex=True)
                 .replace("", None).astype(float))

    if field == "InversionNum":
        if "InversionNum" in df.columns:
            y = pd.to_numeric(df["InversionNum"], errors="coerce")
        elif "Inversion" in df.columns:
            y = parse_money(df["Inversion"])
        else:
            y = pd.Series(index=df.index, dtype=float)
    elif field == "Total_de_pagos":
        y = pd.to_numeric(df.get("Total_de_pagos"), errors="coerce")
        if y.isna().all() and "Total_de_pagos_fmt" in df:
            y = parse_money(df["Total_de_pagos_fmt"])
    # elif field == "_count":
    #     y = pd.Series(1, index=df.index, dtype="int64")
    # else:
    #     y = pd.Series(dtype=float)

    df["valor"] = y

    # --- 3) Limpieza y figura ---
    dff = df.copy()
    if "Fecha" in dff:
        dff = dff.dropna(subset=["Fecha"]).sort_values("Fecha")
    dff = dff.dropna(subset=["valor"])

    fig = px.line(
        dff, x=("Fecha" if "Fecha" in dff else None),
        y="valor", color="Nombre", markers=True,
        title=("Serie por fecha" if "Fecha" in dff else "Serie")
    )

    cols = [{"name": c, "id": c} for c in df.columns if c != "valor"]
    return df.to_dict("records"), cols, fig