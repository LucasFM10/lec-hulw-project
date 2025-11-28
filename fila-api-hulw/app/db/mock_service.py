import json
import os
from typing import List, Dict, Any, Optional

# Caminho para nossos dados mock
MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "mock_data")

def _load_mock_data(filename: str) -> List[Dict[str, Any]]:
    """Carrega um arquivo JSON de dados mock."""
    filepath = os.path.join(MOCK_DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def get_mock_data(filename: str, term: Optional[str], key_fields: List[str], skip: int, limit: int):
    """Função genérica para buscar e paginar dados mock."""
    all_data = _load_mock_data(filename)

    # Filtra os dados se um termo de busca for fornecido
    if term:
        term = term.lower()
        filtered_data = []
        for item in all_data:
            for field in key_fields:
                if term in str(item.get(field, '')).lower():
                    filtered_data.append(item)
                    break # Evita adicionar o mesmo item duas vezes
    else:
        filtered_data = all_data

    # Aplica a paginação
    return filtered_data[skip : skip + limit]

def get_mock_data_by_id(filename: str, id_value: Any, id_field: str):
    """Busca um único item por ID nos dados mock."""
    all_data = _load_mock_data(filename)
    id_value = type(all_data[0][id_field])(id_value) # Garante que os tipos são os mesmos

    for item in all_data:
        if item.get(id_field) == id_value:
            return item
    return None