from pydantic import BaseModel

class Procedimento(BaseModel):
    COD_PROCEDIMENTO: int
    PROCEDIMENTO: str

    class Config:
        from_attributes = True