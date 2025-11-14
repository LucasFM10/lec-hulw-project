# fila_cirurgica/utils.py
import requests
from django.http import JsonResponse
from django.conf import settings

def api_autocomplete_proxy(request, api_endpoint, id_field, text_format_str):
    term = request.GET.get('term', '')
    page = request.GET.get('page')
    limit = request.GET.get('limit', 25)
    params = {'term': term, 'limit': 25}
    if page:
        params['page'] = page
    if limit:
        params['limit'] = limit

    try:
        response = requests.get(f"{settings.API_BASE_URL}/{api_endpoint}/", params=params)
        response.raise_for_status()
        api_data = response.json()

        results = [
            {"id": str(item[id_field]), "text": text_format_str.format(**item)}
            for item in api_data
        ]
        more = str(len(results)) == params.get('limit', 25)
        return JsonResponse({"results": results, "pagination": {"more": more}})
    except requests.RequestException:
        print("api_autocomplete_proxy: erro ao chamar API")
        return JsonResponse({'error': 'Falha ao contatar a API'}, status=500)
    

# adicionar em fila_cirurgica/utils.py (abaixo da api_autocomplete_proxy existente)

def api_autocomplete_procedimento(request,
                                  api_endpoint='procedimentos',
                                  id_field='COD_PROCEDIMENTO',
                                  text_format_str='{COD_PROCEDIMENTO} - {PROCEDIMENTO}',
                                  especialidade_param='cod_especialidade',
                                  limit=5,
                                  timeout=10):
    """
    Proxy autocomplete específico para PROCEDIMENTOS que:
      - aceita ?term=... & page=...
      - se receber ?especialidade_id=... envia esse filtro para a API
      - se receber ?id=NNN tenta buscar o item único em /<endpoint>/<id>/ (útil para pré-carregar Select2 no edit)
    Retorna JSON no formato: { "results": [...], "pagination": {"more": True/False} }
    """
    # --- caso pré-carregamento por id (edição) ---
    requested_id = request.GET.get('id')
    if requested_id:
        try:
            resp = requests.get(f"{settings.API_BASE_URL}/{api_endpoint}/{requested_id}/", timeout=timeout)
            resp.raise_for_status()
            item = resp.json()
            # aceita resposta objeto ou lista
            if isinstance(item, list):
                item = item[0] if item else None
            if not item:
                return JsonResponse({"results": [], "pagination": {"more": False}})
            return JsonResponse({
                "results": [
                    {"id": item[id_field], "text": text_format_str.format(**item)}
                ],
                "pagination": {"more": False}
            })
        except requests.RequestException:
            return JsonResponse({'error': 'Falha ao contatar a API'}, status=500)

    # --- caso busca/paginação normal ---
    term = request.GET.get('term', '')
    page = request.GET.get('page')
    params = {'term': term, 'limit': limit}
    if page:
        params['page'] = page

    # pega especialidade_id do querystring
    especialidade_val = request.GET.get('especialidade_id')
    if especialidade_val:
        params[especialidade_param] = especialidade_val

    try:
        response = requests.get(f"{settings.API_BASE_URL}/{api_endpoint}/", params=params, timeout=timeout)
        response.raise_for_status()
        api_data = response.json()
        # se a API devolve wrapper { results: [...] }, normalize
        if isinstance(api_data, dict) and 'results' in api_data:
            items = api_data['results']
        else:
            items = api_data

        results = []
        for item in items:
            try:
                results.append({"id": item[id_field], "text": text_format_str.format(**item)})
            except Exception:
                # pula itens mal formatados
                continue

        more = len(results) == limit
        return JsonResponse({"results": results, "pagination": {"more": more}})
    except requests.RequestException:
        return JsonResponse({'error': 'Falha ao contatar a API'}, status=500)

