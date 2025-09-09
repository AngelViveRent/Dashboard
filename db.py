# db.py
from sqlalchemy import create_engine

conn_str = (
    "mssql+pyodbc://arquimedes_readonly_user:3Gas%2545rTjA3.zPm"
    "@arquimedes.database.windows.net:1433/arquimedes"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)
engine = create_engine(conn_str, pool_pre_ping=True)
