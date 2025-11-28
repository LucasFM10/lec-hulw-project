# app/db/session.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Criamos o motor de conexão com o banco de dados
engine = create_engine(str(settings.DATABASE_URL))

# Função para obter uma conexão (será usada como dependência no FastAPI)
def get_db_connection():
    conn = None
    try:
        conn = engine.connect()
        yield conn
    finally:
        if conn:
            conn.close()