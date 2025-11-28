from fastapi import FastAPI
from app.api.v1.api import api_router

app = FastAPI(
    title="API de Consulta HULW",
    description="API para consultar dados do sistema hospitalar.",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Bem-vindo à API do HULW!"}