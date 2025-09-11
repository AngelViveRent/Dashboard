# main.py
import dash
from dash import Dash, html, dcc, Output, Input
import dash_bootstrap_components as dbc
from flask_jwt_extended import jwt_required, get_jwt_identity
from auth import init_jwt
from dash.dependencies import ClientsideFunction


app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server
init_jwt(server)

@server.route("/api/data")
@jwt_required()
def data_api():
    user = get_jwt_identity()
    return {"msg": f"Hola {user}"}


# ---------- Layout base: sidebar + contenido ----------
def sidebar():
    paginas = [ p for p in dash.page_registry.values() if p["path"] not in ("/login",) # <- oculta login 
               ]
    return html.Div(
        className="sider d-flex flex-column p-3 text-white bg-dark",
        style={"width": "10%", "height": "100%", "position": "sticky", "top": 0},
        children=[
            html.H4("ViveRent", className="mb-3"),
            html.Hr(),
            html.Ul(
                className="nav nav-pills flex-column mb-auto",
                children=[
                    html.Li(html.A(p["name"], href=p["relative_path"], className="nav-link text-white"))
                    for p in paginas
                ],
            ),
            html.Button("Cerrar Sesión", id="logout-button", n_clicks=0, className="btn btn-outline-light mt-auto"),
        ],
    )

def shell(children):
    return html.Div(className="d-flex",
                    children=[sidebar(), html.Div(children, className="flex-grow-1 p-3")])

# Layout controlador por URL
app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(id="auth-guard", style={"display":"none"}),
    html.Div(id="frame")
])
app.clientside_callback(
    ClientsideFunction(namespace="guards", function_name="checkToken"),
    Output("auth-guard", "children"),
    Input("url", "pathname")
)

app.clientside_callback(
    ClientsideFunction(namespace="guards", function_name="doLogout"),
    Output("logout-button", "title"),   # prop dummy
    Input("logout-button", "n_clicks")
)

@dash.callback(Output("frame", "children"), Input("url", "pathname"))
def render(path):
    # /login: página independiente (sin sidebar)
    if path == "/login":
        return dash.page_container
    # demás rutas: con shell
    return shell(dash.page_container)


if __name__ == "__main__":
    app.run(debug=True)