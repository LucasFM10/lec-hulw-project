from pydantic import BaseModel

class Profissional(BaseModel):
    NOME_PROFISSIONAL: str
    MATRICULA: int

    class Config:
        from_attributes = True