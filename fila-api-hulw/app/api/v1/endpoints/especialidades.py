from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, Connection
from typing import List, Optional

from app.db.session import get_db_connection
from app.schemas.especialidade import Especialidade
from app.core.config import settings
from app.db import mock_service

from typing import List, Optional, Generator 

router = APIRouter()

# --- NOVA DEPENDÊNCIA INTELIGENTE ---
def db_provider() -> Generator[Optional[Connection], None, None]:
    """
    Fornece uma conexão com o banco de dados somente se os dados mock não estiverem em uso.
    """
    if not settings.USE_MOCK_DATA:
        yield from get_db_connection()
    else:
        yield None

@router.get("/", response_model=List[Especialidade], summary="Lista ou busca especialidades com paginação")
def read_especialidades(
    term: Optional[str] = None, q: Optional[str] = None,
    page: Optional[int] = None, skip: int = 0, limit: int = 25,
    # --- CORREÇÃO APLICADA AQUI ---
    conn: Optional[Connection] = Depends(db_provider)
):
    search_query = term or q
    if page and page > 0:
        skip = (page - 1) * limit

    if settings.USE_MOCK_DATA:
        results = mock_service.get_mock_data(
            filename="especialidades.json",
            term=search_query,
            key_fields=["NOME_ESPECIALIDADE", "COD_ESPECIALIDADE"],
            skip=skip,
            limit=limit
        )
    else:
        base_query = """
            SELECT esp.seq AS "COD_ESPECIALIDADE", esp.nome_especialidade AS "NOME_ESPECIALIDADE"
            FROM agh.agh_especialidades esp WHERE esp.ind_situacao = 'A'
        """
        params = {"skip": skip, "limit": limit}
        if search_query:
            base_query += " AND (esp.nome_especialidade ILIKE :search_term OR CAST(esp.seq AS TEXT) ILIKE :search_term)"
            params["search_term"] = f"%{search_query}%"
        final_query = text(base_query + " ORDER BY esp.nome_especialidade OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY")
        results = conn.execute(final_query, params).fetchall()

    return results

@router.get("/{cod_especialidade}", response_model=Especialidade, summary="Busca uma especialidade pelo código")
def read_especialidade_by_id(
    cod_especialidade: int, 
    # --- CORREÇÃO APLICADA AQUI ---
    conn: Optional[Connection] = Depends(db_provider)
):
    if settings.USE_MOCK_DATA:
        result = mock_service.get_mock_data_by_id("especialidades.json", cod_especialidade, "COD_ESPECIALIDADE")
    else:
        query = text("SELECT esp.seq AS \"COD_ESPECIALIDADE\", esp.nome_especialidade AS \"NOME_ESPECIALIDADE\" FROM agh.agh_especialidades esp WHERE esp.ind_situacao = 'A' AND esp.seq = :cod")
        result = conn.execute(query, {"cod": cod_especialidade}).fetchone()
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidade não encontrada ou inativa")
    return result