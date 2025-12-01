from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Min
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.timezone import now, localtime
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView, FormView
from django_filters.views import FilterView
from simple_history.utils import update_change_reason
from django.core.files.storage import FileSystemStorage
import csv
import openpyxl
from openpyxl import Workbook
from django.db import transaction
from django.utils import timezone
from django.views.generic import View

from fila_cirurgica.models import EspecialidadeAghu, ListaEsperaCirurgica, PacienteAghu, ProcedimentoAghu, ProfissionalAghu
from lec_legado.models import LecLegado
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


# =====================================================
# LEC LEGADO - Gerenciamento de dados históricos
# =====================================================

class LecLegadoListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista as entradas do LEC Legado com paginação."""
    permission_required = "lec_legado.view_leclegado"
    model = LecLegado
    template_name = "portal/lec_legado_list.html"
    context_object_name = "lec_list"
    paginate_by = 20

    def get_queryset(self):
        queryset = LecLegado.objects.order_by('-id')
        
        # Filtro por status de migração
        status_filter = self.request.GET.get('status')
        if status_filter in ['sucesso', 'parcial', 'erro', 'pendente']:
            queryset = queryset.filter(status_migracao=status_filter)
        
        # Filtro por campo faltante (apenas para registros com status parcial)
        campo_filter = self.request.GET.get('campo')
        if campo_filter in ['especialidade', 'procedimento', 'medico']:
            queryset = queryset.filter(
                status_migracao='parcial',
                mensagem_migracao__icontains=campo_filter
            )
        
        # Filtro por tipo de erro (apenas para registros com status erro)
        erro_filter = self.request.GET.get('erro')
        if erro_filter == 'prontuario':
            queryset = queryset.filter(
                status_migracao='erro',
                mensagem_migracao__icontains='Prontuário'
            )
        elif erro_filter == 'exception':
            queryset = queryset.filter(
                status_migracao='erro'
            ).exclude(mensagem_migracao__icontains='Prontuário')
        
        # Filtro por registros sem data de entrada
        sem_data_filter = self.request.GET.get('sem_data')
        if sem_data_filter == 'true':
            queryset = queryset.filter(
                data_de_entrada_do_paciente_na_lec_preenchido_automaticamente_pelo_sistema_com_a_data_de_cadastro_de_novo_paciente__isnull=True
            ) | queryset.filter(
                data_de_entrada_do_paciente_na_lec_preenchido_automaticamente_pelo_sistema_com_a_data_de_cadastro_de_novo_paciente__exact=''
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calcula estatísticas de migração
        all_records = LecLegado.objects.all()
        context['stats_sucesso'] = all_records.filter(status_migracao='sucesso').count()
        context['stats_parcial'] = all_records.filter(status_migracao='parcial').count()
        context['stats_erro'] = all_records.filter(status_migracao='erro').count()
        context['stats_pendente'] = all_records.filter(status_migracao='pendente').count()
        
        # Calcula estatísticas de campos faltantes (apenas parciais)
        parciais = all_records.filter(status_migracao='parcial')
        context['stats_especialidade'] = parciais.filter(mensagem_migracao__icontains='especialidade').count()
        context['stats_procedimento'] = parciais.filter(mensagem_migracao__icontains='procedimento').count()
        context['stats_medico'] = parciais.filter(mensagem_migracao__icontains='medico').count()
        
        # Calcula estatísticas de tipos de erro
        erros = all_records.filter(status_migracao='erro')
        context['stats_erro_prontuario'] = erros.filter(mensagem_migracao__icontains='Prontuário').count()
        context['stats_erro_exception'] = erros.exclude(mensagem_migracao__icontains='Prontuário').count()
        
        # Calcula estatística de registros sem data de entrada
        context['stats_sem_data'] = all_records.filter(
            data_de_entrada_do_paciente_na_lec_preenchido_automaticamente_pelo_sistema_com_a_data_de_cadastro_de_novo_paciente__isnull=True
        ).count() + all_records.filter(
            data_de_entrada_do_paciente_na_lec_preenchido_automaticamente_pelo_sistema_com_a_data_de_cadastro_de_novo_paciente__exact=''
        ).count()
        
        # Adiciona filtros atuais
        context['status_filter'] = self.request.GET.get('status', '')
        context['campo_filter'] = self.request.GET.get('campo', '')
        context['erro_filter'] = self.request.GET.get('erro', '')
        context['sem_data_filter'] = self.request.GET.get('sem_data', '')
        
        return context


class LecLegadoImportView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Página para importar CSV do LEC Legado."""
    permission_required = "lec_legado.add_leclegado"
    template_name = "portal/lec_legado_import.html"

    def post(self, request, *args, **kwargs):
        """Processa o upload e importação do CSV ou Excel."""
        if 'csv_file' not in request.FILES:
            messages.error(request, "Nenhum arquivo foi enviado.")
            return redirect('portal:lec_legado_import')

        uploaded_file = request.FILES['csv_file']
        
        # Valida extensão
        is_csv = uploaded_file.name.endswith('.csv')
        is_xlsx = uploaded_file.name.endswith(('.xlsx', '.xls'))
        
        if not (is_csv or is_xlsx):
            messages.error(request, "O arquivo deve ser um CSV ou Excel (.xlsx/.xls).")
            return redirect('portal:lec_legado_import')

        # Salva temporariamente
        fs = FileSystemStorage(location='/tmp/')
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)

        # Opção: apagar registros existentes?
        replace = request.POST.get('replace') == 'on'
        
        try:
            # Chama a lógica de importação
            if is_csv:
                created, skipped = self._import_csv(file_path, replace)
            else:
                created, skipped = self._import_excel(file_path, replace)
            
            messages.success(
                request, 
                f"✅ Importação concluída! Criados: {created} | Ignorados: {skipped}"
            )
        except Exception as e:
            messages.error(request, f"❌ Erro ao importar: {str(e)}")
        finally:
            # Remove arquivo temporário
            fs.delete(filename)

        return redirect('portal:lec_legado_list')

    def _import_csv(self, file_path, replace=False):
        """Lógica de importação do CSV."""
        from lec_legado.management.commands.import_lec_csv import normalize
        
        if replace:
            LecLegado.objects.all().delete()

        # Mapeamento de campos
        field_map = {}
        for field in LecLegado._meta.fields:
            if field.name == "id":
                continue
            field_map[normalize(field.name)] = field.name
            if field.db_column:
                field_map[normalize(field.db_column)] = field.name
            if getattr(field, 'verbose_name', None):
                field_map[normalize(str(field.verbose_name))] = field.name

        created = 0
        skipped = 0

        with open(file_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                obj_data = {}
                for key, value in row.items():
                    if value is None:
                        continue
                    norm_key = normalize(key)
                    if norm_key in field_map:
                        obj_data[field_map[norm_key]] = value

                try:
                    LecLegado.objects.create(**obj_data)
                    created += 1
                except Exception:
                    skipped += 1

        return created, skipped

    def _import_excel(self, file_path, replace=False):
        """Lógica de importação do Excel."""
        from lec_legado.management.commands.import_lec_csv import normalize
        
        if replace:
            LecLegado.objects.all().delete()

        # Mapeamento de campos
        field_map = {}
        for field in LecLegado._meta.fields:
            if field.name == "id":
                continue
            field_map[normalize(field.name)] = field.name
            if field.db_column:
                field_map[normalize(field.db_column)] = field.name
            if getattr(field, 'verbose_name', None):
                field_map[normalize(str(field.verbose_name))] = field.name

        created = 0
        skipped = 0

        wb = openpyxl.load_workbook(file_path, read_only=True)
        ws = wb.active
        
        # Lê cabeçalho
        rows = iter(ws.rows)
        header_row = next(rows)
        headers = [cell.value for cell in header_row]
        
        # Processa linhas
        for row in rows:
            obj_data = {}
            for idx, cell in enumerate(row):
                if idx >= len(headers) or cell.value is None:
                    continue
                    
                key = headers[idx]
                if key is None:
                    continue
                    
                norm_key = normalize(str(key))
                if norm_key in field_map:
                    obj_data[field_map[norm_key]] = str(cell.value) if cell.value is not None else None

            if obj_data:
                try:
                    LecLegado.objects.create(**obj_data)
                    created += 1
                except Exception:
                    skipped += 1
        
        wb.close()
        return created, skipped


class LecLegadoDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes de uma entrada do LEC Legado."""
    permission_required = "lec_legado.view_leclegado"
    model = LecLegado
    template_name = "portal/lec_legado_detail.html"
    context_object_name = "obj"


class LecLegadoExportView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Exporta os dados do LEC Legado em CSV ou Excel."""
    permission_required = "lec_legado.view_leclegado"

    def get(self, request, *args, **kwargs):
        # Verifica formato solicitado (default: csv)
        formato = request.GET.get('formato', 'csv')
        
        if formato == 'xlsx':
            return self._export_excel()
        else:
            return self._export_csv()
    
    def _export_csv(self):
        """Exporta em formato CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="lec_legado_export.csv"'
        
        writer = csv.writer(response)
        
        # Cabeçalho
        fields = [f.name for f in LecLegado._meta.fields]
        writer.writerow(fields)
        
        # Dados
        for obj in LecLegado.objects.all():
            writer.writerow([getattr(obj, f, '') for f in fields])
        
        return response
    
    def _export_excel(self):
        """Exporta em formato Excel."""
        wb = Workbook()
        ws = wb.active
        ws.title = "LEC Legado"
        
        # Cabeçalho
        fields = [f.name for f in LecLegado._meta.fields]
        ws.append(fields)
        
        # Dados
        for obj in LecLegado.objects.all():
            ws.append([getattr(obj, f, '') for f in fields])
        
        # Gera resposta
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="lec_legado_export.xlsx"'
        wb.save(response)
        
        return response


class LecLegadoMigrateView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """Migra TODOS os registros do LEC Legado para a fila atual."""
    permission_required = ["lec_legado.view_leclegado", "fila_cirurgica.add_listaesperacirurgica"]
    
    def post(self, request, *args, **kwargs):
        """Executa a migração em massa."""
        
        # Contador de resultados
        total = 0
        sucesso = 0
        parcial = 0  # Criado mas com campos faltantes
        erros = 0
        
        # Busca todos os registros do LEC Legado
        registros_legado = LecLegado.objects.all()
        total = registros_legado.count()
        
        if total == 0:
            messages.warning(request, "Nenhum registro encontrado no LEC Legado.")
            return redirect('portal:lec_legado_list')
        
        # Processa cada registro
        for legado in registros_legado:
            resultado = self._migrar_registro(legado)
            
            if resultado['status'] == 'sucesso':
                sucesso += 1
            elif resultado['status'] == 'parcial':
                parcial += 1
            else:
                erros += 1
        
        # Mensagem de feedback
        messages.success(
            request,
            f"✅ Migração concluída! Sucesso: {sucesso} | Parcial: {parcial} | Erros: {erros} de {total} registros"
        )
        
        return redirect('portal:lec_legado_list')
    
    def _migrar_registro(self, legado):
        """
        Tenta migrar um registro do LEC Legado.
        Retorna dict com 'status' e 'campos_faltantes'.
        """
        campos_faltantes = []
        
        try:
            with transaction.atomic():
                # 1. CRIAR/BUSCAR PACIENTE
                prontuario = legado.no_do_prontuario_do_paciente_utilizado_pelo_medico_para_conferencia_de_qual_paciente_esta_sendo_cadastrado
                nome_paciente = legado.nome_do_paciente_utilizado_pelo_medico_para_conferencia_de_qual_paciente_esta_sendo_cadastrado
                
                if not prontuario or not prontuario.strip():
                    legado.status_migracao = 'erro'
                    legado.mensagem_migracao = 'Prontuário vazio'
                    legado.save()
                    return {'status': 'erro'}
                
                # Busca ou cria paciente
                paciente, created = PacienteAghu.objects.get_or_create(
                    prontuario=prontuario.strip(),
                    defaults={
                        'nome': nome_paciente.strip() if nome_paciente else f'Paciente {prontuario}'
                    }
                )
                
                # 2. CRIAR/BUSCAR ESPECIALIDADE
                especialidade_nome = legado.especialidade_do_medico_cirurgiao_especialidades_cadastradas_no_aplicativo
                
                if not especialidade_nome or not especialidade_nome.strip():
                    campos_faltantes.append('especialidade')
                    # Cria especialidade genérica
                    especialidade, _ = EspecialidadeAghu.objects.get_or_create(
                        cod_especialidade='SEM_INFO',
                        defaults={'nome_especialidade': 'Sem Informação'}
                    )
                else:
                    # Tenta buscar por nome similar
                    especialidade = EspecialidadeAghu.objects.filter(
                        nome_especialidade__icontains=especialidade_nome.strip()
                    ).first()
                    
                    if not especialidade:
                        # Cria nova especialidade com código baseado no nome
                        cod_esp = self._gerar_codigo_unico(
                            EspecialidadeAghu,
                            'cod_especialidade',
                            especialidade_nome[:8].upper().replace(' ', '_')
                        )
                        
                        especialidade, _ = EspecialidadeAghu.objects.get_or_create(
                            cod_especialidade=cod_esp,
                            defaults={'nome_especialidade': especialidade_nome.strip()[:255]}
                        )
                
                # 3. CRIAR/BUSCAR PROCEDIMENTO
                procedimento_nome = legado.procedimento_indicado_pelo_medico_a_ser_realizado_no_paciente_tabela_sigtap
                codigo_proc = legado.codigo_do_procedimento_do_paciente_tabela_sigtap
                
                if not procedimento_nome or not procedimento_nome.strip():
                    campos_faltantes.append('procedimento')
                    # Cria procedimento genérico
                    procedimento, _ = ProcedimentoAghu.objects.get_or_create(
                        codigo='SEM_INFO',
                        defaults={'nome': 'Sem Informação'}
                    )
                else:
                    # Se tem código, usa ele; senão gera um
                    if codigo_proc and str(codigo_proc).strip():
                        cod_final = str(codigo_proc).strip()[:20]
                    else:
                        cod_final = self._gerar_codigo_unico(
                            ProcedimentoAghu,
                            'codigo',
                            procedimento_nome[:8].upper().replace(' ', '_')
                        )
                    
                    procedimento, _ = ProcedimentoAghu.objects.get_or_create(
                        codigo=cod_final,
                        defaults={'nome': procedimento_nome.strip()[:255]}
                    )
                
                # 4. CRIAR/BUSCAR MÉDICO (opcional)
                doc_medico = legado.documento_do_medico_cns_ou_cpf
                nome_medico = legado.medico_cirurgiao_nome_do_profissional_solicitanteassistente_lista_suspensa_de_nomes_de_medicos_cirurgioes_cadastrados_no_aplicativo
                
                medico = None
                if doc_medico and str(doc_medico).strip():
                    matricula = str(doc_medico).strip()[:10]
                    nome = nome_medico.strip()[:255] if nome_medico else f'Médico {matricula}'
                    
                    medico, _ = ProfissionalAghu.objects.get_or_create(
                        matricula=matricula,
                        defaults={'nome': nome}
                    )
                else:
                    campos_faltantes.append('medico')
                
                # 5. MAPEAR PRIORIDADE
                prioridade_map = {
                    '0': 'ONC',  # Oncológico
                    '1': 'BRE',  # Com Prioridade
                    '2': 'BRE',  # Com Prioridade
                    '3': 'SEM',  # Sem prioridade
                }
                
                prioridade_legado = str(legado.prioridade_clinica_0_oncologico_1_urgente_2_prioritario_3_sem_prioridade or '3').strip()
                prioridade = prioridade_map.get(prioridade_legado, 'SEM')
                
                # 6. VERIFICAR MEDIDA JUDICIAL
                judicial_texto = str(legado.informa_se_ha_processo_judicial_para_a_realizacao_da_cirurgia_se_demanda_judicial_preencher_data_limite_para_realizacao_do_procedimento_e_no_do_processo_sei or '').strip().upper()
                medida_judicial = judicial_texto not in ['', 'NÃO', 'NAO', 'N/A', '-', 'NONE']
                
                # 7. DEFINIR SITUAÇÃO
                situacao = 'PP'  # Paciente pronto (padrão)
                
                # 8. PROCESSAR DATA DE ENTRADA
                data_entrada_str = legado.data_de_entrada_do_paciente_na_lec_preenchido_automaticamente_pelo_sistema_com_a_data_de_cadastro_de_novo_paciente
                data_entrada = None
                
                if data_entrada_str and str(data_entrada_str).strip():
                    # Tenta converter a data de diferentes formatos
                    data_entrada = self._parse_data(str(data_entrada_str).strip())
                    
                    if not data_entrada:
                        campos_faltantes.append('data_entrada (formato inválido)')
                
                # Se não conseguiu parsear a data, usa a data atual
                if not data_entrada:
                    data_entrada = timezone.now()
                
                # 9. CRIAR ENTRADA NA FILA
                entrada = ListaEsperaCirurgica(
                    paciente=paciente,
                    especialidade=especialidade,
                    procedimento=procedimento,
                    medico=medico,
                    prioridade=prioridade,
                    prioridade_justificativa=legado.observacao_lec_campo_aberto_para_preenchimento_no_nir or '',
                    medida_judicial=medida_judicial,
                    judicial_numero=legado.sei_judicial if medida_judicial else '',
                    judicial_descricao=judicial_texto[:255] if medida_judicial else '',
                    situacao=situacao,
                    observacoes=f"[MIGRADO DO LEC LEGADO - ID: {legado.id}]\n\n{legado.campo_com_pequena_observacao_aparece_no_card_do_paciente_na_fila or ''}",
                    ativo=True
                )
                
                # Salva primeiro (auto_now_add define data atual)
                entrada.save()
                
                # BYPASSA auto_now_add: Atualiza a data com update() (ignora auto_now_add)
                ListaEsperaCirurgica.objects.filter(pk=entrada.pk).update(
                    data_entrada=data_entrada
                )
                
                # Recarrega o objeto para ter a data correta em memória
                entrada.refresh_from_db()
                
                # 10. ATUALIZAR STATUS NO LEC LEGADO
                if campos_faltantes:
                    legado.status_migracao = 'parcial'
                    legado.mensagem_migracao = f"Criado com campos genéricos/inválidos: {', '.join(campos_faltantes)}"
                    status = 'parcial'
                else:
                    legado.status_migracao = 'sucesso'
                    legado.mensagem_migracao = f"Migrado com sucesso para fila ID: {entrada.id} | Data entrada: {data_entrada.strftime('%d/%m/%Y %H:%M')}"
                    status = 'sucesso'
                
                legado.id_fila_migrada = entrada.id
                legado.data_migracao = timezone.now()
                legado.save()
                
                return {'status': status}
                
        except Exception as e:
            # Erro crítico
            legado.status_migracao = 'erro'
            legado.mensagem_migracao = f"Erro: {str(e)[:200]}"
            legado.save()
            return {'status': 'erro'}
    
    def _parse_data(self, data_str):
        """
        Tenta parsear uma data em vários formatos comuns.
        Retorna um objeto datetime ou None se não conseguir.
        """
        from datetime import datetime
        from dateutil import parser as date_parser
        
        # Remove espaços extras
        data_str = data_str.strip()
        
        # Lista de formatos comuns
        formatos = [
            '%d/%m/%Y',           # 31/12/2023
            '%d/%m/%Y %H:%M:%S',  # 31/12/2023 14:30:00
            '%d/%m/%Y %H:%M',     # 31/12/2023 14:30
            '%Y-%m-%d',           # 2023-12-31
            '%Y-%m-%d %H:%M:%S',  # 2023-12-31 14:30:00
            '%Y-%m-%d %H:%M',     # 2023-12-31 14:30
            '%d-%m-%Y',           # 31-12-2023
            '%d-%m-%Y %H:%M:%S',  # 31-12-2023 14:30:00
        ]
        
        # Tenta cada formato
        for formato in formatos:
            try:
                dt = datetime.strptime(data_str, formato)
                # Garante que tenha timezone
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                return dt
            except (ValueError, TypeError):
                continue
        
        # Última tentativa: usa dateutil (mais flexível)
        try:
            dt = date_parser.parse(data_str, dayfirst=True)  # Formato brasileiro (dia primeiro)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt
        except (ValueError, TypeError, AttributeError):
            pass
        
        return None
    
    def _gerar_codigo_unico(self, model, field_name, base_code):
        """Gera um código único para evitar duplicatas."""
        # Remove caracteres especiais e limita tamanho conforme o modelo
        base_code = base_code.replace(' ', '_').replace('-', '_')
        
        # Define limite baseado no campo
        if field_name == 'cod_especialidade':
            max_length = 10
        elif field_name == 'codigo':
            max_length = 20
        else:
            max_length = 15
        
        base_code = base_code[:max_length - 3]  # Reserva espaço para sufixo
        code = base_code
        counter = 1
        
        while model.objects.filter(**{field_name: code}).exists():
            suffix = f"_{counter}"
            code = f"{base_code[:max_length - len(suffix)]}{suffix}"
            counter += 1
            
            # Proteção contra loop infinito
            if counter > 999:
                import time
                code = f"{base_code[:max_length - 6]}_{int(time.time()) % 10000}"
                break
        
        return code



