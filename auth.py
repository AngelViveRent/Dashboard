from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

jwt = JWTManager()

def init_jwt(app):
    app.config["JWT_SECRET_KEY"] = "CLAVE_ULTRA_SECRETA"
    jwt.init_app(app)
