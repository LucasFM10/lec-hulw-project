from pydantic import BaseModel

class Especialidade(BaseModel):
    COD_ESPECIALIDADE: int
    NOME_ESPECIALIDADE: str

    class Config:
        from_attributes = True