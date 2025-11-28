from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, Connection
from typing import List, Optional

from app.db.session import get_db_connection
from app.schemas.profissional import Profissional
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

@router.get("/", response_model=List[Profissional], summary="Lista ou busca profissionais com paginação")
def read_profissionais(
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
            filename="profissionais.json",
            term=search_query,
            key_fields=["NOME_PROFISSIONAL", "MATRICULA"],
            skip=skip,
            limit=limit
        )
    else:
        base_query = """
            SELECT serv.matricula AS "MATRICULA", pes.nome AS "NOME_PROFISSIONAL", serv.matricula AS "PROF_RESPONSAVEL"
            FROM agh.rap_servidores serv LEFT JOIN agh.rap_pessoas_fisicas pes ON pes.codigo = serv.pes_codigo
            WHERE serv.ind_situacao = 'A'
        """
        params = {"skip": skip, "limit": limit}
        if search_query:
            base_query += " AND (pes.nome ILIKE :search_term OR CAST(serv.matricula AS TEXT) ILIKE :search_term)"
            params["search_term"] = f"%{search_query}%"
        final_query = text(base_query + " ORDER BY pes.nome OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY")
        results = conn.execute(final_query, params).fetchall()

    return results

@router.get("/{matricula}", response_model=Profissional, summary="Busca um profissional pela matrícula")
def read_profissional_by_id(
    matricula: int, 
    # --- CORREÇÃO APLICADA AQUI ---
    conn: Optional[Connection] = Depends(db_provider)
):
    if settings.USE_MOCK_DATA:
        result = mock_service.get_mock_data_by_id("profissionais.json", matricula, "MATRICULA")
    else:
        query = text("""
            SELECT 
                serv.matricula AS "MATRICULA", 
                pes.nome AS "NOME_PROFISSIONAL", 
                serv.matricula AS "PROF_RESPONSAVEL" 
            FROM agh.rap_servidores serv 
            LEFT JOIN agh.rap_pessoas_fisicas pes ON pes.codigo = serv.pes_codigo 
            WHERE serv.ind_situacao = 'A' AND serv.matricula = :matricula
        """)
        result = conn.execute(query, {"matricula": matricula}).fetchone()
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profissional não encontrado ou inativo")
    
    return result