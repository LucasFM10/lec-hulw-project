# app/api/v1/endpoints/procedimentos.py

import os
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, Connection
from typing import List, Optional, Generator

from app.db.session import get_db_connection
from app.schemas.procedimento import Procedimento
from app.core.config import settings
from app.db import mock_service

router = APIRouter()

def db_provider() -> Generator[Optional[Connection], None, None]:
    """
    Fornece uma conexão com o banco de dados somente se os dados mock não estiverem em uso.
    """
    if not settings.USE_MOCK_DATA:
        yield from get_db_connection()
    else:
        yield None

@router.get("/", response_model=List[Procedimento], summary="Lista ou busca procedimentos com filtro opcional por especialidade")
def read_procedimentos(
    cod_especialidade: Optional[int] = None, # Parâmetro opcional para filtrar
    term: Optional[str] = None, 
    q: Optional[str] = None,
    page: Optional[int] = None, 
    skip: int = 0, 
    limit: int = 25,
    conn: Optional[Connection] = Depends(db_provider)
):
    """
    Busca procedimentos com paginação.
    - Se `cod_especialidade` for fornecido, filtra os procedimentos daquela especialidade.
    - Se não, retorna todos os procedimentos cirúrgicos ativos.
    - `term` ou `q` podem ser usados para busca textual em ambos os casos.
    """
    search_query = term or q
    if page and page > 0:
        skip = (page - 1) * limit

    if settings.USE_MOCK_DATA:
        # --- CORREÇÃO APLICADA AQUI ---
        # Como mock_service.get_mock_data não aceita 'filter_by',
        # carregamos os dados e aplicamos os filtros manualmente.
        try:
            # O caminho é baseado no script de geração de mock
            mock_data_path = os.path.join("app", "db", "mock_data", "procedimentos.json")
            with open(mock_data_path, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Arquivo de dados mock 'procedimentos.json' não encontrado.")

        # 1. Filtra por especialidade, se fornecido
        if cod_especialidade:
            results = [p for p in all_data if p.get("COD_ESPECIALIDADE_FK") == cod_especialidade]
        else:
            results = all_data

        # 2. Filtra por termo de busca, se fornecido
        if search_query:
            search_query_lower = search_query.lower()
            key_fields = ["PROCEDIMENTO", "COD_PROCEDIMENTO"]
            
            search_results = []
            for item in results:
                for field in key_fields:
                    value = item.get(field)
                    if value and search_query_lower in str(value).lower():
                        search_results.append(item)
                        break  # Evita adicionar o mesmo item múltiplas vezes
            results = search_results
        
        # 3. Aplica a paginação ao resultado final
        return results[skip : skip + limit]

    # Se uma especialidade for fornecida, usa a query específica
    if cod_especialidade:
        base_query = """
            SELECT
                phi.seq AS "COD_PROCEDIMENTO",
                phi.descricao AS "PROCEDIMENTO"
            FROM
                agh.aac_proced_hosp_especialidades php
            JOIN
                agh.fat_proced_hosp_internos phi ON phi.seq = php.phi_seq
            WHERE
                php.ind_consulta = 'N'
                AND php.esp_seq = :cod_especialidade
        """
        params = {"cod_especialidade": cod_especialidade, "skip": skip, "limit": limit}
        if search_query:
            base_query += " AND (phi.descricao ILIKE :search_term OR CAST(phi.seq AS TEXT) ILIKE :search_term)"
            params["search_term"] = f"%{search_query}%"
        
        # Ordena pela descrição do procedimento
        final_query = text(base_query + ' ORDER BY "PROCEDIMENTO" OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY')

    # Se não, usa a query geral de fallback
    else:
        base_query = """
            SELECT
                pro.seq AS "COD_PROCEDIMENTO",
                pro.descricao AS "PROCEDIMENTO"
            FROM
                agh.mbc_procedimento_cirurgicos pro
            WHERE
                pro.ind_situacao = 'A'
        """
        params = {"skip": skip, "limit": limit}
        if search_query:
            base_query += " AND (pro.descricao ILIKE :search_term OR CAST(pro.seq AS TEXT) ILIKE :search_term)"
            params["search_term"] = f"%{search_query}%"
        
        # Ordena pela descrição do procedimento
        final_query = text(base_query + ' ORDER BY "PROCEDIMENTO" OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY')

    results = conn.execute(final_query, params).fetchall()
    return results


@router.get("/{cod_procedimento}", response_model=Procedimento, summary="Busca um procedimento pelo código")
def read_procedimento_by_id(
    cod_procedimento: int, 
    conn: Optional[Connection] = Depends(db_provider)
):
    """
    Busca um procedimento único pelo seu código.
    A busca é feita em ambas as tabelas de procedimentos para garantir consistência
    com a busca geral.
    """
    if settings.USE_MOCK_DATA:
        # A busca por ID no mock continua a mesma e funciona com os dados gerados
        result = mock_service.get_mock_data_by_id("procedimentos.json", cod_procedimento, "COD_PROCEDIMENTO")
    else:
        # Unimos as duas possíveis fontes de procedimentos para encontrar o código.
        # Isso garante que um código retornado pela busca com filtro de especialidade
        # também seja encontrado aqui.
        query = text("""
            (SELECT 
                phi.seq AS "COD_PROCEDIMENTO", 
                phi.descricao AS "PROCEDIMENTO" 
             FROM agh.fat_proced_hosp_internos phi 
             WHERE phi.seq = :cod)
            UNION
            (SELECT 
                pro.seq AS "COD_PROCEDIMENTO", 
                pro.descricao AS "PROCEDIMENTO" 
             FROM agh.mbc_procedimento_cirurgicos pro 
             WHERE pro.ind_situacao = 'A' AND pro.seq = :cod)
            FETCH FIRST 1 ROW ONLY
        """)
        result = conn.execute(query, {"cod": cod_procedimento}).fetchone()
    
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedimento não encontrado")
    return result
