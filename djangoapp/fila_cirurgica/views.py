# fila_cirurgica/views.py
from .utils import api_autocomplete_proxy, api_autocomplete_procedimento

def procedimento_api_autocomplete(request):
    return api_autocomplete_procedimento(request)

def paciente_api_autocomplete(request):
    return api_autocomplete_proxy(request, 'pacientes', 'PRONTUARIO_PAC', '{NOME_PACIENTE} (Prontuário: {PRONTUARIO_PAC})')

def medico_api_autocomplete(request):
    return api_autocomplete_proxy(request, 'profissionais', 'MATRICULA', '{NOME_PROFISSIONAL} (Matrícula: {MATRICULA})')

# djangoapp/fila_cirurgica/views.py
def especialidade_api_autocomplete(request):
    print(">>> [VIEW] especialidade_api_autocomplete chamada")
    print(">>> [VIEW] GET:", request.GET)

    return api_autocomplete_proxy(
        request,
        'especialidades',
        'COD_ESPECIALIDADE',
        '{NOME_ESPECIALIDADE}'
    )
