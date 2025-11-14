# fila_cirurgica/api_helpers.py

import requests
from django.conf import settings
from .models import (
    PacienteAghu,
    ProcedimentoAghu,
    EspecialidadeAghu,
    ProfissionalAghu,
)

def get_or_create_paciente(prontuario):
    if not prontuario:
        return None

    response = requests.get(f"{settings.API_BASE_URL}/api/v1/pacientes/{prontuario}")
    response.raise_for_status()
    data = response.json()

    obj, created = PacienteAghu.objects.get_or_create(
        prontuario=data['PRONTUARIO_PAC'],
        defaults={'nome': data['NOME_PACIENTE']}
    )
    if not created and obj.nome != data['NOME_PACIENTE']:
        obj.nome = data['NOME_PACIENTE']
        obj.save()
    return obj

def get_or_create_procedimento(codigo):
    if not codigo:
        return None

    response = requests.get(f"{settings.API_BASE_URL}/api/v1/procedimentos/{codigo}")
    response.raise_for_status()
    data = response.json()

    obj, created = ProcedimentoAghu.objects.get_or_create(
        codigo=data['COD_PROCEDIMENTO'],
        defaults={'nome': data['PROCEDIMENTO']}
    )
    if not created and obj.nome != data['PROCEDIMENTO']:
        obj.nome = data['PROCEDIMENTO']
        obj.save()
    return obj

def get_or_create_especialidade(cod_especialidade):
    if not cod_especialidade:
        return None

    response = requests.get(f"{settings.API_BASE_URL}/api/v1/especialidades/{cod_especialidade}")
    response.raise_for_status()
    data = response.json()

    obj, created = EspecialidadeAghu.objects.get_or_create(
        cod_especialidade=data['COD_ESPECIALIDADE'],
        defaults={'nome_especialidade': data['NOME_ESPECIALIDADE']}
    )
    if not created and obj.nome_especialidade != data['NOME_ESPECIALIDADE']:
        obj.nome_especialidade = data['NOME_ESPECIALIDADE']
        obj.save()
    return obj

def get_or_create_profissional(matricula):
    if not matricula:
        return None

    response = requests.get(f"{settings.API_BASE_URL}/api/v1/profissionais/{matricula}")
    response.raise_for_status()
    data = response.json()

    obj, created = ProfissionalAghu.objects.get_or_create(
        matricula=data['MATRICULA'],
        defaults={'nome': data['NOME_PROFISSIONAL']}
    )
    if not created and obj.nome != data['NOME_PROFISSIONAL']:
        obj.nome = data['NOME_PROFISSIONAL']
        obj.save()
    return obj
# Adicionar no final de fila_cirurgica/api_helpers.py

def validar_procedimento_na_especialidade(procedimento_id: str, especialidade_id: str) -> bool:
    """
    Verifica via API se um procedimento específico pertence a uma especialidade.

    Esta função é usada para validação no backend (forms.py) para garantir
    que a combinação enviada pelo usuário é válida.

    Retorna True se a combinação for válida, False caso contrário.
    """
    if not procedimento_id or not especialidade_id:
        return False

    # A URL e os parâmetros são baseados na lógica encontrada em `utils.api_autocomplete_procedimento`
    api_url = f"{settings.API_BASE_URL}/procedimentos/"
    params = {
        'cod_especialidade': especialidade_id,
        'term': procedimento_id,  # Usamos 'term' para buscar o código específico
        'limit': 1                # Só precisamos de 1 resultado para confirmar a existência
    }

    try:
        # Assumindo que a validação não precisa de autenticação especial,
        # caso contrário, adicione os headers necessários.
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()  # Lança erro para status 4xx/5xx
        data = response.json()

        # Normaliza a resposta (pode ser lista ou dict com 'results')
        if isinstance(data, dict) and 'results' in data:
            items = data['results']
        else:
            items = data
        
        # Se a API retornou algum item que corresponde à busca, a combinação é válida.
        # Para uma validação mais estrita, poderíamos verificar se o ID do item retornado
        # é exatamente igual ao `procedimento_id`, mas `len(items) > 0` é suficiente aqui.
        return len(items) > 0

    except requests.RequestException as e:
        # Em caso de falha na API, é mais seguro invalidar a submissão
        # para forçar uma nova tentativa do usuário.
        print(f"ERRO DE VALIDAÇÃO: Falha ao contatar a API para validar procedimento. {e}")
        return False