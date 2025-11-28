from fastapi import APIRouter
from app.api.v1.endpoints import procedimentos, profissionais, especialidades, pacientes

api_router = APIRouter()

api_router.include_router(procedimentos.router, prefix="/procedimentos", tags=["Procedimentos"])
api_router.include_router(profissionais.router, prefix="/profissionais", tags=["Profissionais"])
api_router.include_router(especialidades.router, prefix="/especialidades", tags=["Especialidades"])
api_router.include_router(pacientes.router, prefix="/pacientes", tags=["Pacientes"])