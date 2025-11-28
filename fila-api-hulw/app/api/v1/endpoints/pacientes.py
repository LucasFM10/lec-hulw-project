from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, Connection
from typing import List, Optional, Generator

from app.db.session import get_db_connection
from app.schemas.paciente import Paciente
from app.core.config import settings
from app.db import mock_service

router = APIRouter()

# --- DEPENDÊNCIA INTELIGENTE ---
def db_provider() -> Generator[Optional[Connection], None, None]:
    """
    Fornece uma conexão com o banco de dados somente se os dados mock não estiverem em uso.
    """
    if not settings.USE_MOCK_DATA:
        yield from get_db_connection()
    else:
        yield None

@router.get("/", response_model=List[Paciente], summary="Lista ou busca pacientes com paginação")
def read_pacientes(
    term: Optional[str] = None, q: Optional[str] = None,
    page: Optional[int] = None, skip: int = 0, limit: int = 25,
    conn: Optional[Connection] = Depends(db_provider)
):
    search_query = term or q
    if page and page > 0:
        skip = (page - 1) * limit

    if settings.USE_MOCK_DATA:
        results = mock_service.get_mock_data(
            filename="pacientes.json",
            term=search_query,
            key_fields=["NOME_PACIENTE", "PRONTUARIO_PAC"],
            skip=skip,
            limit=limit
        )
    else:
        base_query = """
            SELECT pac.nome AS "NOME_PACIENTE", pac.prontuario AS "PRONTUARIO_PAC",
                   pac.ddd_fone_residencial AS "DDD_FONE_RESIDENCIAL", pac.fone_residencial AS "FONE_RESIDENCIAL",
                   pac.ddd_fone_recado AS "DDD_FONE_RECADO", pac.fone_recado AS "FONE_RECADO"
            FROM agh.aip_pacientes pac
        """
        params = {"skip": skip, "limit": limit}
        if search_query:
            base_query += " WHERE (pac.nome ILIKE :search_term OR CAST(pac.prontuario AS TEXT) ILIKE :search_term)"
            params["search_term"] = f"%{search_query}%"
        final_query = text(base_query + " ORDER BY pac.nome OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY")
        results = conn.execute(final_query, params).fetchall()

    return results

@router.get("/{prontuario}", response_model=Paciente, summary="Busca um paciente pelo prontuário")
def read_paciente_by_id(
    prontuario: int, 
    conn: Optional[Connection] = Depends(db_provider)
):
    if settings.USE_MOCK_DATA:
        result = mock_service.get_mock_data_by_id("pacientes.json", prontuario, "PRONTUARIO_PAC")
    else:
        query = text("""
            SELECT pac.nome AS "NOME_PACIENTE", pac.prontuario AS "PRONTUARIO_PAC",
                   pac.ddd_fone_residencial AS "DDD_FONE_RESIDENCIAL", pac.fone_residencial AS "FONE_RESIDENCIAL",
                   pac.ddd_fone_recado AS "DDD_FONE_RECADO", pac.fone_recado AS "FONE_RECADO"
            FROM agh.aip_pacientes pac
            WHERE pac.prontuario = :prontuario
        """)
        result = conn.execute(query, {"prontuario": prontuario}).fetchone()
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")

    return result
