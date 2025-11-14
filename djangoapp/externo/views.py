from django.shortcuts import render
from django.utils.timezone import localtime
from fila_cirurgica.models import ListaEsperaCirurgica
from django.utils.timezone import now
from django.db.models.functions import TruncMonth
from django.db.models import Count, Min
from django.shortcuts import render
from datetime import timedelta

from fila_cirurgica.models import ListaEsperaCirurgica

def indicadores_especialidades(request):
    # Período ~3 meses (1º dia do mês atual - 60 dias)
    hoje = now().date()
    inicio_periodo = hoje.replace(day=1) - timedelta(days=60)

    # ---- MÉTRICAS (apenas ENTRADAS ATIVAS) ----
    ativos = ListaEsperaCirurgica.objects.filter(ativo=True)

    # distintos na fila
    pacientes_na_fila = ativos.values("paciente_id").distinct().count()
    especialidades_na_fila = ativos.values("especialidade_id").distinct().count()
    procedimentos_na_fila = ativos.values("procedimento_id").distinct().count()

    # recortes por prioridade/flag
    count_eletivos = ativos.filter(prioridade="SEM", medida_judicial=False).count()
    count_oncologicos = ativos.filter(prioridade="ONC").count()
    count_judicializados = ativos.filter(medida_judicial=True).count()

    # ---- GRÁFICOS ----
    # pizza: distribuição por especialidade (todas as entradas)
    dist_qs = (
        ListaEsperaCirurgica.objects
        .values('especialidade__nome_especialidade')
        .annotate(total=Count('id'))
        .order_by('especialidade__nome_especialidade')
    )
    labels = [row['especialidade__nome_especialidade'] or '—' for row in dist_qs]
    data = [row['total'] for row in dist_qs]
    total_geral = sum(data) or 1
    percentages = [round((v / total_geral) * 100, 2) for v in data]

    # barras: entradas por mês (últimos 3 meses ~)
    mensal_qs = (
        ListaEsperaCirurgica.objects
        .filter(data_entrada__date__gte=inicio_periodo)
        .annotate(mes=TruncMonth('data_entrada'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    labels_bar = [row['mes'].strftime('%b/%Y') for row in mensal_qs]
    data_bar = [row['total'] for row in mensal_qs]

    # top-10 por quantidade (procedimentos)
    proc_count_qs = (
        ListaEsperaCirurgica.objects
        .values('procedimento__nome')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    labels_proc_count = [row['procedimento__nome'] or '—' for row in proc_count_qs]
    data_proc_count = [row['total'] for row in proc_count_qs]

    # top-10 por maior tempo de espera (dias) por procedimento
    first_dt_qs = (
        ListaEsperaCirurgica.objects
        .values('procedimento__nome')
        .annotate(first_dt=Min('data_entrada'))
    )
    hoje_dt = now()
    wait_list = [
        (row['procedimento__nome'] or '—',
         (hoje_dt - row['first_dt']).days if row['first_dt'] else 0)
        for row in first_dt_qs if row['first_dt'] is not None
    ]
    wait_list.sort(key=lambda x: x[1], reverse=True)
    wait_list = wait_list[:10]
    labels_proc_wait = [name for name, _ in wait_list]
    data_proc_wait = [days for _, days in wait_list]

    context = {
        # métricas
        "pacientes_na_fila": pacientes_na_fila,
        "especialidades_na_fila": especialidades_na_fila,
        "procedimentos_na_fila": procedimentos_na_fila,
        "count_eletivos": count_eletivos,
        "count_oncologicos": count_oncologicos,
        "count_judicializados": count_judicializados,

        # gráficos
        "labels": labels,
        "data": data,
        "percentages": percentages,
        "labels_bar": labels_bar,
        "data_bar": data_bar,
        "labels_proc_count": labels_proc_count,
        "data_proc_count": data_proc_count,
        "labels_proc_wait": labels_proc_wait,
        "data_proc_wait": data_proc_wait,
    }
    return render(request, "externo/indicadores_especialidades.html", context)

def consulta_posicao(request):
    mensagem = None
    prontuario = (request.POST.get("prontuario") or request.GET.get("prontuario") or "").strip()

    entradas_ativas = []
    entradas_inativas = []

    if request.method in ("POST", "GET") and prontuario:
        # Mapa de posições para TODA a fila ativa (uma só passada)
        ids_ativos_em_ordem = list(
            ListaEsperaCirurgica.objects.ordered()
            .filter(ativo=True)
            .values_list("id", flat=True)
        )
        pos_map = {obj_id: idx + 1 for idx, obj_id in enumerate(ids_ativos_em_ordem)}

        # Todas as entradas (ativas e inativas) do prontuário consultado
        qs = (
            ListaEsperaCirurgica.objects.select_related(
                "especialidade", "procedimento", "paciente", "medico"
            )
            .filter(paciente__prontuario=prontuario)
        )

        if not qs.exists():
            mensagem = "❌ Prontuário inválido ou sem entradas na fila."
        else:
            # Separe em ativas/inativas e anexe posição (ativas)
            for entrada in qs:
                item = {
                    "id": entrada.id,
                    "prontuario": entrada.paciente.prontuario,
                    "especialidade": getattr(entrada.especialidade, "nome_especialidade", ""),
                    "procedimento": getattr(entrada.procedimento, "nome", ""),
                    "posicao": pos_map.get(entrada.id, None) if entrada.ativo else None,
                    "ativo": entrada.ativo,
                    "data_entrada": localtime(entrada.data_entrada),
                }
                if entrada.ativo:
                    entradas_ativas.append(item)
                else:
                    entradas_inativas.append(item)

            # Ordene: ativas por posição asc; inativas por data_entrada desc
            entradas_ativas.sort(key=lambda x: (x["posicao"] or 10**9))
            entradas_inativas.sort(key=lambda x: x["data_entrada"], reverse=True)

    elif request.method == "POST" and not prontuario:
        mensagem = "⚠️ Por favor, digite um número de prontuário."

    context = {
        "mensagem": mensagem,
        "prontuario": prontuario,
        "entradas_ativas": entradas_ativas,
        "entradas_inativas": entradas_inativas,
    }
    return render(request, "externo/consulta_posicao.html", context)
