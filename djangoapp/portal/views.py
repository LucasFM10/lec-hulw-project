from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Min
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.timezone import now, localtime
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView, FormView
from django_filters.views import FilterView
from simple_history.utils import update_change_reason

from fila_cirurgica.models import EspecialidadeAghu, ListaEsperaCirurgica, PacienteAghu, ProcedimentoAghu, ProfissionalAghu
from .filters import FilaFilter
from .forms import FilaCreateForm, FilaUpdateForm, FilaDeactivateForm
from django.shortcuts import render

from django.views.generic import ListView, CreateView
from django.shortcuts import redirect

from aih.models import AihSolicitacao
from .forms import AihCreateForm


def error_404(request, exception, template_name="errors/404.html"):
    return render(request, template_name, {"path": request.path}, status=404)


def error_403(request, exception=None, template_name="errors/403.html"):
    # exception=None geralmente indica falha de CSRF (se não usar view dedicada)
    return render(request, template_name, {"path": request.path}, status=403)


def error_500(request, template_name="errors/500.html"):
    return render(request, template_name, status=500)


def csrf_failure(request, reason=""):
    return render(
        request,
        "errors/403_csrf.html",
        {"reason": reason, "path": request.path},
        status=403,
    )

from django.contrib.auth.views import LoginView

class PortalLoginView(LoginView):
    template_name = "login.html"
    def form_valid(self, form):
        response = super().form_valid(form)
        remember = self.request.POST.get("remember_me")
        # 0 = expira ao fechar o navegador; 1209600 = 14 dias
        self.request.session.set_expiry(1209600 if remember else 0)
        return response


# --------------------- Mixins ---------------------


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    def test_func(self) -> bool:
        u = self.request.user
        return u.is_authenticated and u.is_active

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()  # redireciona para login
        # autenticado mas sem permissão → 403 bonito
        return render(self.request, "errors/403.html", status=403)


# --------------------- Dashboard ---------------------
class DashboardView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Dashboard sem dados pessoais (apenas agregados)."""
    permission_required = "fila_cirurgica.view_listaesperacirurgica"
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        hoje = now().date()
        inicio_periodo = hoje.replace(day=1) - timedelta(days=60)

        ativos = ListaEsperaCirurgica.objects.filter(ativo=True)

        # KPIs (apenas ativos)
        ctx["pacientes_na_fila"] = ativos.values(
            "paciente_id").distinct().count()
        ctx["especialidades_na_fila"] = ativos.values(
            "especialidade_id").distinct().count()
        ctx["procedimentos_na_fila"] = ativos.values(
            "procedimento_id").distinct().count()
        ctx["count_eletivos"] = ativos.filter(
            prioridade="SEM", medida_judicial=False).count()
        ctx["count_oncologicos"] = ativos.filter(prioridade="ONC").count()
        ctx["count_judicializados"] = ativos.filter(
            medida_judicial=True).count()

        # Pizza — distribuição por especialidade (apenas ativos)
        dist_qs = (
            ativos.values("especialidade__nome_especialidade")
            .annotate(total=Count("id"))
            .order_by("especialidade__nome_especialidade")
        )
        labels = [row["especialidade__nome_especialidade"]
                  or "—" for row in dist_qs]
        data = [row["total"] for row in dist_qs]
        total_geral = sum(data) or 1
        ctx["labels"] = labels
        ctx["data"] = data
        ctx["percentages"] = [round((v / total_geral) * 100, 2) for v in data]

        # Barras — entradas criadas no período (todas as entradas)
        mensal_qs = (
            ListaEsperaCirurgica.objects.filter(
                data_entrada__date__gte=inicio_periodo)
            .annotate(mes=TruncMonth("data_entrada"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )
        ctx["labels_bar"] = [row["mes"].strftime("%b/%Y") for row in mensal_qs]
        ctx["data_bar"] = [row["total"] for row in mensal_qs]

        # Top 10 procedimentos com mais pacientes (apenas ativos)
        proc_count_qs = ativos.values("procedimento__nome").annotate(
            total=Count("id")).order_by("-total")[:10]
        ctx["labels_proc_count"] = [
            row["procedimento__nome"] or "—" for row in proc_count_qs]
        ctx["data_proc_count"] = [row["total"] for row in proc_count_qs]

        # Top 10 maior tempo de espera (dias) por procedimento (apenas ativos)
        first_dt_qs = ativos.values("procedimento__nome").annotate(
            first_dt=Min("data_entrada"))
        hoje_dt = now()
        wait_pairs = [
            (row["procedimento__nome"] or "—",
             (hoje_dt - row["first_dt"]).days)
            for row in first_dt_qs
            if row["first_dt"] is not None
        ]
        wait_pairs.sort(key=lambda x: x[1], reverse=True)
        wait_pairs = wait_pairs[:10]
        ctx["labels_proc_wait"] = [name for name, _ in wait_pairs]
        ctx["data_proc_wait"] = [days for _, days in wait_pairs]

        ctx["agora"] = now()
        return ctx


# --------------------- Lista / Filtros ---------------------
class FilaListView(StaffRequiredMixin, PermissionRequiredMixin, FilterView):
    """Lista com filtros e paginação."""
    permission_required = "fila_cirurgica.view_listaesperacirurgica"
    model = ListaEsperaCirurgica
    filterset_class = FilaFilter
    paginate_by = 10
    template_name = "portal/fila_list.html"
    context_object_name = "objetos"

    def get_queryset(self):
        """
        Usa manager .ordered() quando disponível; select_related para evitar N+1.
        """
        base = getattr(ListaEsperaCirurgica.objects, "ordered", None)
        qs = (base() if callable(base) else ListaEsperaCirurgica.objects.all())
        return qs.select_related("paciente", "especialidade", "procedimento", "medico")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        print(ctx.keys())
        return ctx


# --------------------- Visualizar ---------------------
class FilaDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "fila_cirurgica.view_listaesperacirurgica"
    model = ListaEsperaCirurgica
    template_name = "portal/fila_detail.html"
    context_object_name = "obj"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        obj = ctx["obj"]
        posicao = None
        if hasattr(obj, "get_posicao") and callable(obj.get_posicao):
            try:
                posicao = obj.get_posicao()
            except Exception:
                posicao = None
        ctx["posicao"] = posicao
        return ctx


# --------------------- Criar ---------------------
class FilaCreateView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "fila_cirurgica.add_listaesperacirurgica"
    model = ListaEsperaCirurgica
    form_class = FilaCreateForm
    template_name = "portal/fila_form.html"
    success_url = reverse_lazy("portal:fila_list")
    
    def get_initial(self):
        """
        Lê os parâmetros da URL (GET) para pré-preencher o formulário.
        """
        initial = super().get_initial()
        
        # Pega os IDs/Prontuário da URL
        aih_id = self.request.GET.get('aih_id')
        prontuario = self.request.GET.get('prontuario')
        especialidade_id = self.request.GET.get('especialidade_api')
        procedimento_id = self.request.GET.get('procedimento_api')
        medico_id = self.request.GET.get('medico_api')

        # Passa os valores para o 'initial' do formulário
        if aih_id:
            initial['aih_id'] = str(aih_id)
        
        # Para os campos Select2, precisamos não apenas do ID (valor),
        # mas também do TEXTO (label) para exibição.
        # Buscamos os objetos para extrair seus nomes.
        
        if prontuario:
            try:
                paciente = PacienteAghu.objects.get(prontuario=prontuario)
                initial['prontuario'] = paciente.prontuario
                initial['prontuario_text'] = paciente.nome
            except PacienteAghu.DoesNotExist:
                pass
        
        if especialidade_id:
            try:
                esp = EspecialidadeAghu.objects.get(pk=especialidade_id)
                initial['especialidade_api'] = esp.cod_especialidade
                initial['especialidade_api_text'] = esp.nome_especialidade
            except EspecialidadeAghu.DoesNotExist:
                pass

        if procedimento_id:
            try:
                proc = ProcedimentoAghu.objects.get(pk=procedimento_id)
                initial['procedimento_api'] = proc.codigo
                initial['procedimento_api_text'] = proc.nome #
            except ProcedimentoAghu.DoesNotExist:
                pass

        if medico_id:
            try:
                med = ProfissionalAghu.objects.get(pk=medico_id)
                initial['medico_api'] = med.matricula
                initial['medico_api_text'] = med.nome #
            except ProfissionalAghu.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        # Pega o aih_id do formulário validado (cleaned_data)
        aih_id = form.cleaned_data.get('aih_id')

        # Salva o objeto da Fila no banco
        obj = form.save(commit=True)
        
        try:
            # Lógica para definir a mensagem do histórico
            if aih_id:
                reason = f"Criado via Portal a partir da AIH ID: {aih_id}"
            else:
                reason = "Criado via Portal"
            
            # Chama a função de histórico com a mensagem correta
            update_change_reason(obj, reason)
        except Exception:
            # Não impede a criação se o log de histórico falhar
            pass 
        
        messages.success(self.request, "Entrada criada com sucesso.")
        return redirect(self.success_url)


# --------------------- Atualizar ---------------------
class FilaUpdateView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "fila_cirurgica.change_listaesperacirurgica"
    model = ListaEsperaCirurgica
    form_class = FilaUpdateForm
    template_name = "portal/fila_form.html"
    success_url = reverse_lazy("portal:fila_list")

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        obj = getattr(self, "object", None)
        if obj and not getattr(obj, "ativo", True):
            # bloqueia todos os campos visualmente
            for field in form.fields.values():
                field.disabled = True
                field.widget.attrs["class"] = (field.widget.attrs.get(
                    "class", "") + " bg-gray-50 cursor-not-allowed").strip()
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        motivo = form.cleaned_data.get("motivo_alteracao")
        if motivo:
            try:
                update_change_reason(self.object, motivo)
            except Exception:
                pass
        messages.success(self.request, "Entrada atualizada com sucesso.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["exclude_fields"] = ["ativo", "motivo_saida"]
        ctx["is_update"] = True
        return ctx


# --------------------- Histórico ---------------------
class FilaHistoryView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Exibe diffs a partir do django-simple-history."""
    permission_required = "fila_cirurgica.view_listaesperacirurgica"
    template_name = "portal/fila_history.html"

    _IGNORE = {"id", "history_id", "history_date", "history_type",
               "history_user", "history_change_reason"}

    def _to_display(self, field, value):
        """Formata valor para exibição (choices, FK, bool, datas)."""
        if value is None:
            return ""
        # choices -> rótulo
        if getattr(field, "choices", None):
            return dict(field.choices).get(value, value)
        # FK -> string amigável
        if getattr(field, "many_to_one", False) and hasattr(field, "remote_field"):
            return str(value) if value else ""
        # boolean
        from django.db.models import BooleanField
        if isinstance(field, BooleanField):
            return "Sim" if bool(value) else "Não"
        # datas
        from django.db.models import DateTimeField, DateField
        if isinstance(field, DateTimeField):
            return localtime(value).strftime("%d/%m/%Y %H:%M") if value else ""
        if isinstance(field, DateField):
            return value.strftime("%d/%m/%Y") if value else ""
        return value

    def _diff_records(self, older, newer):
        """Retorna [(verbose_name, antes, depois)] apenas dos campos que mudaram."""
        if not older or not newer:
            return []
        model_meta = newer.instance._meta
        diffs = []
        for field in model_meta.fields:
            name = field.name
            if name in self._IGNORE:
                continue
            before = getattr(older, name, None)
            after = getattr(newer, name, None)
            if before == after:
                continue
            diffs.append((
                field.verbose_name or name,
                self._to_display(field, before),
                self._to_display(field, after),
            ))
        return diffs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = get_object_or_404(ListaEsperaCirurgica, pk=self.kwargs.get("pk"))

        # ordem decrescente (mais recente primeiro)
        history = obj.history.select_related(
            "history_user").order_by("-history_date")

        linhas = []
        for idx, h in enumerate(history):
            older = history[idx + 1] if (idx + 1) < history.count() else None
            diffs = self._diff_records(older, h)
            linhas.append({
                "data": h.history_date,
                "usuario": getattr(h, "history_user", None),
                "tipo": {"+": "Criado", "~": "Alterado", "-": "Deletado"}.get(h.history_type, h.history_type),
                "motivo": getattr(h, "history_change_reason", "") or getattr(h, "change_reason", ""),
                "diffs": diffs,
            })

        ctx["obj"] = obj
        ctx["linhas"] = linhas
        return ctx


# --------------------- Remoção (inativação) ---------------------
class FilaDeactivateView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    “Excluir” do portal: não deleta, apenas marca ativo=False e registra motivo no histórico.
    """
    permission_required = "fila_cirurgica.change_listaesperacirurgica"
    template_name = "portal/confirm_remove.html"
    form_class = FilaDeactivateForm
    success_url = reverse_lazy("portal:fila_list")

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(
            ListaEsperaCirurgica, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["obj"] = self.object
        return ctx

    def form_valid(self, form):
        motivo_value = form.cleaned_data["motivo"]         # value dos choices
        # justificativa livre
        change_reason = form.cleaned_data["change_reason"]

        obj = self.object
        obj.ativo = False
        obj.motivo_saida = motivo_value
        obj.save(update_fields=["ativo", "motivo_saida"])

        try:
            update_change_reason(obj, change_reason)
        except Exception:
            pass

        messages.success(self.request, f"{obj} removido da fila com sucesso.")
        return redirect(self.get_success_url())

class AihListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista as AIHs existentes com paginação."""
    permission_required = "aih.view_aihsolicitacao"
    model = AihSolicitacao
    template_name = "portal/aih_list.html"
    context_object_name = "aih_list"
    paginate_by = 20 # Ou outro número

    def get_queryset(self):
        return AihSolicitacao.objects.order_by('-data_criacao')
    

class AihCreateView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """Formulário para criar uma nova AIH."""
    permission_required = "aih.add_aihsolicitacao" # Ajuste a permissão se necessário
    model = AihSolicitacao
    form_class = AihCreateForm # Usa o novo formulário
    template_name = "portal/aih_form.html" # Usará um novo template
    success_url = reverse_lazy("portal:aih_list")

    def form_valid(self, form):
        # O método save() do AihCreateForm já lida com a lógica dos _api fields
        self.object = form.save()
        messages.success(self.request, "AIH criada com sucesso.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        print(form.errors)
        messages.error(self.request, "Erro ao criar a AIH. Verifique os campos.")
        return super().form_invalid(form)
    
class AihDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Exibe os detalhes de uma única solicitação de AIH,
    seguindo o padrão da FilaDetailView.
    """
    
    # 1. Permissão necessária (deve ser do app 'aih')
    permission_required = "aih.view_aihsolicitacao"
    
    # 2. Modelo que esta view consulta
    model = AihSolicitacao
    
    # 3. Template para renderizar
    template_name = "portal/aih_detail.html"
    
    # 4. Nome do objeto no contexto
    #    IMPORTANTE: O template deve usar {{ obj.campo }}
    context_object_name = "obj"