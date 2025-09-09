# pages/login_view.py
import dash
from dash import State, html, dcc, dash_table, callback, Output, Input, no_update
import pandas as pd
import plotly.express as px
from db import engine  # <<< usa la conexión global
from flask_jwt_extended import create_access_token
from dash.dependencies import ClientsideFunction

dash.register_page(__name__, path="/login", name="login")

layout = html.Div(
    className="login",
        children=[
            html.Div([
                html.Label("Correo", htmlFor="email", className="form-label"),
                dcc.Input(type="email", id="email-input", className="form-control")
            ], className="mb-3"),
            html.Div([
                html.Label("Password", htmlFor="password", className="form-label"),
                dcc.Input(type="password", id="password-input", className="form-control")
            ], className="mb-3"),
    
            html.Div([
                html.Div([
                    dcc.Checklist(
                        options=[{"label": " Remember me", "value": "remember"}],
                        value=["remember"],
                        id="remember-check",
                        inputClassName="form-check-input",
                        labelClassName="form-check-label"
                    )
                ], className="form-check")
            ], className="mb-3"),

            html.Button("Sign in", id="login-button", n_clicks=0, className="btn btn-primary btn-block"),
            html.Div(id="login-alert"),
            dcc.Location(id="login-redirect")
        ])

@callback(
    Output("login-alert", "children"),
    Output("login-redirect", "href"),
    Input("login-button", "n_clicks"),
    State("email-input", "value"),
    State("password-input", "value"),
    prevent_initial_call=True
)
def do_login(n, email, password):
    if email == "admin@example.com" and password == "1234":
        token = create_access_token(identity=email)
        return token, "/"      # ← manda token y destino
    return "Credenciales inválidas", dash.no_update

dash.clientside_callback(
    ClientsideFunction(namespace="guards", function_name="saveToken"),
    Output("login-alert", "title"),
    Input("login-alert", "children")
)