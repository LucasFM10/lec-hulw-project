from pydantic import BaseModel, Field
from typing import Optional

class Paciente(BaseModel):
    NOME_PACIENTE: str
    PRONTUARIO_PAC: Optional[int] = None
    DDD_FONE_RESIDENCIAL: Optional[str] = None
    FONE_RESIDENCIAL: Optional[str] = None
    DDD_FONE_RECADO: Optional[str] = None
    FONE_RECADO: Optional[str] = None

    class Config:
        from_attributes = True