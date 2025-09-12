# pages/contratos_view.py
import dash
from dash import State, html, dcc, dash_table, callback, Output, Input, no_update
import numpy as np
import pandas as pd
from dash_ag_grid import AgGrid
import plotly.express as px


from db import engine  # <<< usa la conexión global

dash.register_page(__name__, path="/", name="Contratos")

def fetch_contratos():
    sql = """
        SELECT
            -- Identificación
            cl.PK_Cliente                         AS ID,
            cl.Alias                              AS Nombre,
            c.Alias                               AS Producto,
            p.Nombre                              AS Proyecto,

            -- Inversión
            c.MontoInversion                      AS Total_de_pagos,
            c.MontoInversion                      AS Inversion,

            -- Apartado
            c.MontoApartado,
            c.MontoApartado                       AS Apartado,
            CASE  
                WHEN c.MontoApartado < 50000 THEN 1
                ELSE NULL
            END                                   AS Apartados_menores_50k,

            -- Pagos realizados
            ISNULL(SUM(i.Monto), 0)              AS Pagos_reales,
            ISNULL(SUM(i.Monto), 0) AS Pagado,

            -- Fechas y estatus
            CAST(c.LastUpdateDate AS date)       AS Ultima_Actualizacion,
            e.Estatus                            AS Estatus,
            CASE 
                WHEN c.FechaFirma IS NULL THEN 'Pendiente'
                ELSE 'En Proceso'
            END                                   AS Tiene_Firma,
            CAST(c.FechaFirma AS date)          AS FechaFirma,

            -- Asesor y estado
            u.Nombre                             AS Asesor,
            c.IsActive                           AS Activado

        FROM dbo.AR_Contratos       AS c
        JOIN dbo.AR_Clientes        AS cl  ON cl.PK_Cliente = c.FK_Cliente
        LEFT JOIN dbo.AR_Unidades   AS un  ON un.PK_Unidad = c.FK_Unidad
        LEFT JOIN dbo.AR_Proyectos  AS p   ON un.FK_Proyecto = p.PK_Proyecto
        LEFT JOIN dbo.AR_Ingresos   AS i   ON i.FK_Contrato = c.PK_Contrato
        LEFT JOIN dbo.CT_EstatusContrato AS e ON c.FK_EstatusContrato = e.PK_EstatusContrato
        LEFT JOIN dbo.AspNetUsers   AS u   ON u.UserId = c.FK_UsuarioAsesor

        WHERE 
            c.IsActive = 1 
            AND c.ID_interno_consolidado IS NULL

        GROUP BY
            cl.PK_Cliente, cl.Alias,
            c.Alias, p.Nombre,
            c.MontoInversion, c.MontoApartado,
            c.LastUpdateDate, c.FechaFirma,
            e.Estatus, u.Nombre,
            c.IsActive

    """
    return pd.read_sql(sql, engine)


@callback(
    Output("resumen-contratos", "children"),
    Input("store-contratos", "data"),
    Input("memory-proyecto", "data")  # el nombre del proyecto seleccionado en la gráfica
)
def resumen(data, proyecto_seleccionado):
    import pandas as pd
    df = pd.DataFrame(data or [])
    
    # Si no hay proyecto seleccionado, usa todos los datos
    if proyecto_seleccionado:
        df = df[df["Proyecto"].isin(proyecto_seleccionado)]
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

    activos = int(pd.Series(df.get("Activado")).eq(1).sum())

    return html.Div([ 
        html.H5("Activos", className="text-center mb-2"),
        html.Div(className="d-flex gap-4 justify-content-between", children=[
            html.Div([
                html.H6("💰Valor", className="mb-1"),
                html.H5(f"${total_pagos:,.2f}", className="mb-0 fw-bold text-primary")
            ]),
            html.Div([
                html.H6("💰Cobrado", className="mb-1"),
                html.H5(f"${pagos_real:,.2f}", className="mb-0 fw-bold text-primary")
            ]),
            html.Div([
                html.H6("Cantidad", className="mb-1"),
                html.H5(f"{activos:,}", className="mb-0 fw-bold text-success")
            ]),                            
        ])
    ], className="p-2", style={"height": "100%"})


@callback(
    Output("resumen-apartados", "children"),
    Input("memory-table", "rowData")
)
def menores_50(rows):
    import pandas as pd
    df = pd.DataFrame(rows or [])

    menores_50 = int(pd.Series(df.get("Apartados_menores_50k")).eq(1).sum())

    return html.Div([ 
        html.H5("Apartados menor a 50k", className="text-center mb-2"),
        html.Div(className="d-flex gap-4 justify-content-center",  children=[
            html.Div([
                html.H1(f"{menores_50:,}", className="mb-0 fw-bold text-primary")]),
                ])
                ], className="p-2", style={"height": "100%", })

@callback(
    Output("revicion-contratos", "children"),
    Input("memory-table", "rowData")
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
                    html.H6("💰Valor", className="mb-1"),
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
        html.H2("Contratos", className="page-title"),
        dcc.Loading(
            html.Div(
            className="content d-flex flex-column",
            children=[
                html.Div(
                    className="resultados d-flex flex-wrap mb-4",  # flex-wrap permite múltiples en fila
                    children=[
                        dcc.Interval(id='init-load', interval=1*1000, n_intervals=0),
                        html.Div(id='resumen-contratos', className="card p-3 m-2 shadow", style={"width": "auto"}),
                        html.Div(id='resumen-apartados', className="card p-3 m-2 shadow", style={"width": "auto"}),                        
                        html.Div(id="revicion-contratos", className="card p-3 m-2 shadow", style={"width": "auto"}),
                    ]
                ),
                html.Div([
                    dcc.Interval(id="tick", interval=300*1000, n_intervals=0),  # refresco cada minuto
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
                    dcc.Store(id="memory-cliente", data=[]),
                    dcc.Store(id="memory-proyecto", data=[]),
                    dcc.Graph(id="memory-graph",style={"height": "60vh", "width": "100%"}),
                    html.Button("Descargar CSV", id="download-button", className="btn btn-outline-primary"),
                    dcc.Download(id="download-contratos"),
                    AgGrid(
                        id="memory-table",
                        columnDefs=[],
                        rowData=[],  # aquí le pasas los registros
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                            "floatingFilter": True,
                        },
                        style={"height": "60vh", "width": "100%"},
                        className="ag-theme-alpine"  # o "ag-theme-balham" si quieres otro estilo
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



@callback(
    Output("memory-cliente", "options"),
    Input("store-contratos", "data"),
    Input("memory-proyecto", "data")  # <-- nuevo

)
def opts_clientes(data, proyecto):
    import pandas as pd
    df = pd.DataFrame(data or [])

    if "Nombre" not in df.columns:
        return []
    if proyecto and proyecto != None and "Proyecto" in df.columns:
        df = df[df["Proyecto"] == proyecto]

    clientes = sorted(df["Nombre"].dropna().astype(str).unique())
    return [{"label": c, "value": c} for c in clientes]

@callback(
    Output("memory-proyecto", "data", allow_duplicate=True),
    Input("memory-graph", "relayoutData"),
    State("store-contratos", "data"),
    prevent_initial_call=True
)
def actualizar_proyectos_visibles(relayoutData, data):
    import pandas as pd
    df = pd.DataFrame(data or [])

    # Asegúrate que la columna exista antes de operar
    if "Proyecto" not in df.columns:
        return []

    if relayoutData is None or "hiddenlabels" not in relayoutData:
        # Si no hay ocultos, todos los proyectos están activos
        return df["Proyecto"].dropna().unique().tolist()

    ocultos = set(relayoutData["hiddenlabels"])
    visibles = df["Proyecto"].dropna().unique()
    activos = [p for p in visibles if p not in ocultos]
    return activos




@callback(
    Output("memory-table", "rowData",allow_duplicate=True),
    Input("store-contratos", "data"),
    Input("memory-proyecto", "data"),
    Input("memory-cliente", "value"), # <- puedes seleccionar múltiples
    prevent_initial_call=True  
)
def actualizar_tabla(data, proyecto, clientes):
    import pandas as pd
    df = pd.DataFrame(data or [])

    if proyecto and proyecto != None and "Proyecto" in df.columns:
        df = df[df["Proyecto"] == proyecto]


    if clientes and "Nombre" in df.columns:
        df = df[df["Nombre"].isin(clientes)]

    return df.to_dict("records")



# 4) Filtrar en memoria según el dropdown
@callback(
    Output("memory-table","rowData"),
    Output("memory-table","columnDefs"),
    Output("memory-graph","figure"),
    Input("store-contratos","data"),
    Input("memory-clientes","value"),
    Input("memory-proyecto","data"),
)
def update_table_graph(raw, clientes, proyecto):
    import numpy as np
    import pandas as pd, plotly.express as px

    df = pd.DataFrame(raw or [])

    if clientes and "Nombre" in df.columns:
        df = df[df["Nombre"].isin(clientes)]
    if proyecto and proyecto != None and "Proyecto" in df.columns:
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
    if np.all(pd.isna(np.atleast_1d(y))) and "Pagado" in df.columns:
        y = parse_money(df["Pagado"])
    df["Valor_total"] = y
    dff["Valor_total"] = y  


# -------- BARRAS (agregado mensual) --------

    bar_df = dff.groupby("Proyecto", as_index=False)["Valor_total"].sum()

    fig = px.bar(
            bar_df,
            x="Proyecto",
            y="Valor_total",
            color="Proyecto" if "Proyecto" in dff.columns else None,
            barmode="relative",
            labels={"Valor_total": "Valor", "Fecha": "Fecha"},
            height=500
        )
    # Determina qué puntos estarán seleccionados (si hay uno activo)
    if proyecto:
        selected = bar_df[bar_df["Proyecto"] == proyecto].index.tolist()
    else:
        selected = list(range(len(bar_df)))

    fig.update_traces(
        selectedpoints=selected,
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.3))
    )
    fig.update_layout(bargap=0.05, hovermode="x unified")

    # Tabla
    column_defs = [
        {"field": "ID"},
        {"field": "Nombre"},
        {"field": "Producto"},
        {"field": "Proyecto"},
        {"field": "Inversion", "type": "numericColumn", "valueFormatter": {"function": "d3.format('$,.2f')(params.value)"} }, 
        { "field": "Apartado", "type": "numericColumn", "valueFormatter": {"function": "d3.format('$,.2f')(params.value)"} }, 
        { "field": "Pagado", "type": "numericColumn", "valueFormatter": {"function": "d3.format('$,.2f')(params.value)"} },
        {"field": "Ultima_Actualizacion"},
        {"field": "Estatus"},
        {"field": "Tiene_Firma"},
        {"field": "Asesor"}
    ]

    return df.to_dict("records"), column_defs, fig 


@callback(
    Output("download-contratos", "data", allow_duplicate=True),
    Input("download-button", "n_clicks"),
    State("memory-table", "rowData"),
    prevent_initial_call=True
)
def download_csv(n, rows):
    df = pd.DataFrame(rows or [])

    column_defs = [
        {"field": "ID"},
        {"field": "Nombre"},
        {"field": "Producto"},
        {"field": "Proyecto"},
        {"field": "Inversion", "type": "numericColumn", "valueFormatter": {"function": "d3.format('$,.2f')(params.value)"} }, 
        { "field": "Apartado", "type": "numericColumn", "valueFormatter": {"function": "d3.format('$,.2f')(params.value)"} }, 
        { "field": "Pagado", "type": "numericColumn", "valueFormatter": {"function": "d3.format('$,.2f')(params.value)"} },
        {"field": "Ultima_Actualizacion"},
        {"field": "Estatus"},
        {"field": "Tiene_Firma"},
        {"field": "Asesor"}
    ]

    column_names = [col["field"] for col in column_defs]
    df = df[[col for col in column_names if col in df.columns]]

    return dcc.send_data_frame(df.to_csv, "Contratos.csv", index=False, encoding="utf-8-sig")
