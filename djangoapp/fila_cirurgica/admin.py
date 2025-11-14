from django.contrib import admin, messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import AutocompleteSelectMultipleFilter
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.template.response import TemplateResponse
from django.urls import path
from django.http import JsonResponse
from .models import (
    ListaEsperaCirurgica,
    PacienteAghu,
    ProcedimentoAghu,
    EspecialidadeAghu,
    ProfissionalAghu,
    IndicadorEspecialidade,
)
from .api_helpers import (
    get_or_create_paciente,
    get_or_create_procedimento,
    get_or_create_especialidade,
    get_or_create_profissional
)
from django.conf import settings
from django.utils.html import format_html
from .forms import ListaEsperaCirurgicaForm
from django.utils.timezone import now
from datetime import timedelta
from django.db.models.functions import TruncMonth
from django.db.models import Count, Min
from django import forms
from django.shortcuts import redirect, render
from django import forms
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.views.generic import FormView
from unfold.views import UnfoldModelAdminViewMixin
import requests
from simple_history.utils import update_change_reason
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.admin.utils import quote

# Registro de usuário e grupo personalizados
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    pass

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(IndicadorEspecialidade)
class IndicadorEspecialidadeAdmin(admin.ModelAdmin):

    # não exibe os botões de adicionar/editar
    has_add_permission = lambda self, request: False
    has_change_permission = lambda self, request, obj=None: False
    has_delete_permission = lambda self, request, obj=None: False

    change_list_template = 'admin/indicadores_especialidade.html'

    def changelist_view(self, request, extra_context=None):
        # últimos 3 meses
        hoje = now().date()
        inicio_periodo = hoje.replace(day=1) - timedelta(days=60)
        # Obtém contagem por especialidade
        qs = (
            ListaEsperaCirurgica.objects
                .values('especialidade__nome_especialidade')
                .annotate(total=Count('id'))
        )
        # Agrupamento por mês
        qs_mensal = (
            ListaEsperaCirurgica.objects
            .filter(data_entrada__date__gte=inicio_periodo)
            .annotate(mes=TruncMonth('data_entrada'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
        total_geral = ListaEsperaCirurgica.objects.count() or 1
        # prepara dados para gráfico
        labels = [item['especialidade__nome_especialidade'] for item in qs]
        data = [item['total'] for item in qs]
        percentages = [round(item['total'] / total_geral * 100, 2) for item in qs]
        labels_bar = [item['mes'].strftime('%b/%Y') for item in qs_mensal]
        data_bar = [item['total'] for item in qs_mensal]

        context = {
            'labels': labels,
            'data': data,
            'percentages': percentages,
            'labels_bar': labels_bar,
            'data_bar': data_bar,
        }
        
        # Top 10 procedimentos com mais pacientes --------------
        qs_proc_count = (
            ListaEsperaCirurgica.objects
            .values('procedimento__nome')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        labels_proc_count = [i['procedimento__nome'] for i in qs_proc_count]
        data_proc_count   = [i['total'] for i in qs_proc_count]

        #  Top 10 procedimentos com maior tempo de espera -------
        qs_proc_wait = (
            ListaEsperaCirurgica.objects
            .values('procedimento__nome')
            .annotate(first_dt=Min('data_entrada'))
        )
        # converte em lista de tuplas (nome, dias_espera) e ordena
        today = now()
        wait_list = [
            (i['procedimento__nome'], (today - i['first_dt']).days)
            for i in qs_proc_wait if i['first_dt'] is not None
        ]
        wait_list.sort(key=lambda x: x[1], reverse=True)
        wait_list = wait_list[:10]                         # top-10
        labels_proc_wait = [w[0] for w in wait_list]
        data_proc_wait   = [w[1] for w in wait_list]

        context = {
            'labels': labels,
            'data': data,
            'percentages': percentages,
            'labels_bar': labels_bar,
            'data_bar': data_bar,
            # novos conjuntos
            'labels_proc_count': labels_proc_count,
            'data_proc_count': data_proc_count,
            'labels_proc_wait': labels_proc_wait,
            'data_proc_wait': data_proc_wait,
        }
        return TemplateResponse(
            request,
            self.change_list_template,
            {**self.admin_site.each_context(request), **context},
        )


@admin.register(PacienteAghu)
class PacienteAdmin(ModelAdmin):
    list_display = ('nome',)
    search_fields = ['nome']

    class Media:
        js = (
            "js/masks/jquery.mask.min.js",
            "js/masks/custom.js",
        )
    
@admin.action(description="Inserir entrada em campanha")
def add_campanha(modeladmin, request, queryset):
    queryset.update(campanha=True)

@admin.action(description="Remover entrada de campanha")
def remove_campanha(modeladmin, request, queryset):
    queryset.update(campanha=False)

class RemoverDaFilaForm(forms.Form):
    motivo = forms.ChoiceField(
        label="Selecione o motivo da remoção",
        choices=ListaEsperaCirurgica.MOTIVO_SAIDA_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'border border-base-200 bg-white font-medium min-w-20 placeholder-base-400 rounded shadow-sm text-font-default-light text-sm focus:ring focus:ring-primary-300 focus:border-primary-600 focus:outline-none group-[.errors]:border-red-600 group-[.errors]:focus:ring-red-200 dark:bg-base-900 dark:border-base-700 dark:text-font-default-dark dark:focus:border-primary-600 dark:focus:ring-primary-700 dark:focus:ring-opacity-50 dark:group-[.errors]:border-red-500 dark:group-[.errors]:focus:ring-red-600/40 px-3 py-2 w-full pr-8 max-w-2xl appearance-none'
        })
    )
    change_reason = forms.CharField(
        label="Explicação detalhada da exclusão",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Explicação',
            'class': 'border border-base-200 bg-white font-medium min-w-20 placeholder-base-400 rounded shadow-sm text-font-default-light text-sm focus:ring focus:ring-primary-300 focus:border-primary-600 focus:outline-none group-[.errors]:border-red-600 group-[.errors]:focus:ring-red-200 dark:bg-base-900 dark:border-base-700 dark:text-font-default-dark dark:focus:border-primary-600 dark:focus:ring-primary-700 dark:focus:ring-opacity-50 dark:group-[.errors]:border-red-500 dark:group-[.errors]:focus:ring-red-600/40 px-3 py-2 w-full max-w-2xl'
        })
    )

class RemoverDaFilaView(UnfoldModelAdminViewMixin, FormView):
    # Título que aparecerá no cabeçalho da página
    title = "Remover Pacientes da Fila"
    
    # Permissão necessária para acessar esta view
    permission_required = 'fila_cirurgica.change_listaesperacirurgica'
    
    # Template a ser renderizado
    template_name = "admin/remover_da_fila.html"
    
    # Classe do formulário a ser utilizada
    form_class = RemoverDaFilaForm

    def get_context_data(self, **kwargs):
        """Adiciona os pacientes selecionados ao contexto do template."""
        context = super().get_context_data(**kwargs)
        ids = self.request.GET.get('ids', '').split(',')
        # Usa o queryset do model_admin para respeitar filtros, se houver
        queryset = self.model_admin.get_queryset(self.request).filter(pk__in=ids)
        context['pacientes'] = queryset
        return context

    def form_valid(self, form):
        """Processa o formulário quando os dados são válidos."""
        motivo = form.cleaned_data['motivo']
        ids = self.request.GET.get('ids', '').split(',')
        queryset = self.model_admin.get_queryset(self.request).filter(pk__in=ids)
        
        count = queryset.count()
        for obj in queryset:
            obj.ativo = False
            obj.motivo_saida = motivo
            obj.save()
            update_change_reason(obj, form.cleaned_data.get('change_reason', ''))
        
        # Linha correta
        self.model_admin.message_user(self.request, f"{count} pacientes removidos da fila com sucesso.", messages.SUCCESS)
        
        # Redireciona de volta para a lista de registros (changelist)
        changelist_url = reverse(
            f'admin:{self.model_admin.model._meta.app_label}_{self.model_admin.model._meta.model_name}_changelist'
        )
        return HttpResponseRedirect(changelist_url)

class AtivoNaFilaFilter(SimpleListFilter):
    title = "Status na fila"
    parameter_name = "ativo"

    def lookups(self, request, model_admin):
        return (
            ("ativos", "Ativo"),
            ("inativos", "Inativo"),
        )

    def queryset(self, request, queryset):
        if self.value() == "ativos":
            return queryset.filter(ativo=True)
        elif self.value() == "inativos":
            return queryset.filter(ativo=False)
        return queryset 

@admin.register(ListaEsperaCirurgica)
class ListaEsperaCirurgicaAdmin(SimpleHistoryAdmin, ModelAdmin):
    form = ListaEsperaCirurgicaForm
    readonly_fields = ['data_entrada']

    list_display_links = None

    list_display = (
        'get_posicao',
        'paciente',
        'prioridade',
        'judicial_personalizado',
        'especialidade',
        'procedimento',
        'ativo_personalizado',
        'acoes',
    )
    list_filter_submit = True
    list_filter = [
        AtivoNaFilaFilter,
        ('especialidade', AutocompleteSelectMultipleFilter),
        ('procedimento', AutocompleteSelectMultipleFilter),
        ('medico', AutocompleteSelectMultipleFilter),
    ]

    def get_queryset(self, request):
        return ListaEsperaCirurgica.objects.ordered()


    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['change_reason'].widget = forms.TextInput(attrs={
            "class": (
                "border border-base-200 bg-white font-medium min-w-20 placeholder-base-400 rounded shadow-sm "
                "text-font-default-light text-sm focus:ring focus:ring-primary-300 focus:border-primary-600 "
                "focus:outline-none group-[.errors]:border-red-600 group-[.errors]:focus:ring-red-200 "
                "dark:bg-base-900 dark:border-base-700 dark:text-font-default-dark dark:focus:border-primary-600 "
                "dark:focus:ring-primary-700 dark:focus:ring-opacity-50 dark:group-[.errors]:border-red-500 "
                "dark:group-[.errors]:focus:ring-red-600/40 px-3 py-2 w-full max-w-2xl"
            ),
            "placeholder": "Motivo da alteração"
        })
        form.current_request = request
        return form
    

    def delete_model(self, request, obj):
        # Ignora o delete para nenhuma entrada ser deletada
        pass


    def save_model(self, request, obj, form, change):
        """Processa campos de autocomplete com dados da API externa."""
        try:    
            # if not obj:
            # Paciente
            obj.paciente = get_or_create_paciente(form.cleaned_data.get('paciente_api_choice'))

            # Procedimento
            obj.procedimento = get_or_create_procedimento(form.cleaned_data.get('procedimento_api_choice'))

            # Especialidade
            obj.especialidade = get_or_create_especialidade(form.cleaned_data.get('especialidade_api_choice'))

            # Médico (opcional)
            obj.medico = get_or_create_profissional(form.cleaned_data.get('medico_api_choice'))

        except requests.RequestException as e:
            self.message_user(
                request,
                f"ERRO CRÍTICO: Falha na comunicação com a API ({e}). O registro não foi salvo.",
                messages.ERROR
            )
            return

        # Salva o registro
        super().save_model(request, obj, form, change)

        update_change_reason(obj, form.cleaned_data.get('change_reason', ''))
        
    def judicial_personalizado(self, obj):
        if obj.medida_judicial:
            return format_html('''
                <div class="flex items-center ">
                    <div class="block mr-3 outline rounded-full ml-1 h-1 w-1 bg-green-500 outline-green-200 dark:outline-green-500/20"></div>
                    <span>Sim</span>
                </div>
            ''')
        else:
            return format_html('''
                <div class="flex items-center ">
                    <div class="block mr-3 outline rounded-full ml-1 h-1 w-1 bg-red-500 outline-red-200 dark:outline-red-500/20"></div>
                    <span>Não</span>
                </div>
            ''')
    judicial_personalizado.short_description = 'Possui medida judicial??'
    judicial_personalizado.admin_order_field = 'medida_judicial'
        
    def ativo_personalizado(self, obj):
        if obj.ativo:
            return format_html('''
                <div class="flex items-center ">
                    <div class="block mr-3 outline rounded-full ml-1 h-1 w-1 bg-green-500 outline-green-200 dark:outline-green-500/20"></div>
                    <span>Sim</span>
                </div>
            ''')
        else:
            return format_html('''
                <div class="flex items-center ">
                    <div class="block mr-3 outline rounded-full ml-1 h-1 w-1 bg-red-500 outline-red-200 dark:outline-red-500/20"></div>
                    <span>Não</span>
                </div>
            ''')
    ativo_personalizado.short_description = 'Está ativo na fila?'
    ativo_personalizado.admin_order_field = 'ativo'
        
    def get_actions(self, request):
        """
        Sobrescreve o método para remover a ação padrão de deleção.
        """
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected'] # Remove a ação de deleção padrão
        return actions
    
    actions = ['remover_da_fila_action']

    def get_urls(self):
        """Registra a URL da view customizada."""
        urls = super().get_urls()
        
        # O nome da URL é construído dinamicamente para evitar conflitos
        url_name = f'{self.model._meta.app_label}_{self.model._meta.model_name}_remover_da_fila'

        # Admin_view protege a view com as permissões do admin
        custom_view = self.admin_site.admin_view(
            RemoverDaFilaView.as_view(
                model_admin=self # Passa a instância do admin para a view
            )
        )

        custom_urls = [
            path(
                'remover-da-fila/',
                custom_view,
                name=url_name,
            ),
        ]
        return custom_urls + urls

    @admin.action(description="Remover da fila com justificativa")
    def remover_da_fila_action(self, request, queryset):
        """Ação que coleta os IDs e redireciona para a view de remoção."""
        selected_pks = queryset.values_list('pk', flat=True)
        
        # Usa 'reverse' para obter a URL de forma segura
        url_name = f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_remover_da_fila'
        redirect_url = reverse(url_name)
        
        # Adiciona os IDs como parâmetro na URL
        return HttpResponseRedirect(f'{redirect_url}?ids={",".join(map(str, selected_pks))}')

    @admin.display(description="Posição na Fila")
    def get_posicao(self, obj):
        # Implemente a lógica para obter a posição na fila aqui
        # Exemplo simples:
        # return ListaEsperaCirurgica.objects.filter(data_entrada__lt=obj.data_entrada).count() + 1
        return format_html('<div style="text-align:center;min-width:3ch;">{}</div>', obj.get_posicao()) # Se você já tem esse método no modelo

    @admin.display(description="Especialidade")
    def especialidade(self, obj):
        return obj.especialidade or "Sem Especialidade"

    @admin.display(description="Procedimento Realizado")
    def procedimento(self, obj):
        return obj.procedimento
    
    def has_change_permission(self, request, obj=None):
        # if obj and not obj.ativo:   # exemplo
        #     return False            # abre read-only
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if obj and not obj.ativo:   # exemplo
            return False            # abre read-only
        return super().has_delete_permission(request, obj)
        
    @admin.display(description="Ações", ordering=False)
    def acoes(self, obj):
        opts = self.model._meta
        pk = quote(obj.pk)

        change_url  = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[pk])
        history_url = reverse(f"admin:{opts.app_label}_{opts.model_name}_history", args=[pk])
        remover_url = reverse(f"admin:{opts.app_label}_{opts.model_name}_remover_da_fila") + f"?ids={pk}"

        if obj.ativo:
            # Ativo: Editar + Histórico + Remover
            return format_html(
                '''
                <div style="text-align:center;min-width:3ch;">
                <div style="text-align:center" class="flex items-center gap-1.5">
                <a href="{}" class="inline-flex items-center p-1.5 rounded hover:bg-blue-50 text-blue-600" title="Editar">
                    <i class="ti ti-pencil" style="font-size:1.05rem;line-height:1"></i>
                </a>
                <a href="{}" class="inline-flex items-center p-1.5 rounded hover:bg-amber-50 text-amber-600" title="Histórico">
                    <i class="ti ti-history" style="font-size:1.05rem;line-height:1"></i>
                </a>
                <a href="{}" class="inline-flex items-center p-1.5 rounded hover:bg-red-50 text-red-600" title="Remover da fila">
                    <i class="ti ti-x" style="font-size:1.05rem;line-height:1"></i>
                </a>
                </div>
                </div>
                ''',
                change_url, history_url, remover_url
            )
        else:
            # Inativo: só Histórico
            return format_html(
                '''
                <div style="text-align:center;min-width:3ch;>
                <div class="flex items-center gap-1.5">
                <a href="{}" class="inline-flex items-center p-1.5 rounded hover:bg-gray-50 text-gray-700" title="Ver">
                    <i class="ti ti-eye" style="font-size:1.05rem;line-height:1"></i>
                </a>
                <a href="{}" class="inline-flex items-center p-1.5 rounded hover:bg-amber-50 text-amber-600" title="Histórico">
                    <i class="ti ti-history" style="font-size:1.05rem;line-height:1"></i>
                </a>
                </div>
                </div>
                ''',
                change_url, history_url
            )

    # NOVO: Sobrescrever delete_view para redirecionar
    def delete_view(self, request, object_id, extra_context=None):
        """
        Redireciona a deleção tradicional para a nossa view de remoção personalizada.
        """

        # Constrói a URL para a sua view de remoção, passando o ID do objeto
        url_name = f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_remover_da_fila'
        redirect_url = reverse(url_name)
        
        # Redireciona para a sua view, passando o ID do objeto via query parameter
        return HttpResponseRedirect(f'{redirect_url}?ids={object_id}')

@admin.register(ProcedimentoAghu)
class ProcedimentoAdmin(ModelAdmin):
    search_fields = ['codigo', 'nome']

    def get_search_results(self, request, queryset, search_term):
        return super().get_search_results(request, queryset, search_term)


@admin.register(EspecialidadeAghu)
class EspecialidadeAdmin(ModelAdmin):
    list_display = ('cod_especialidade', 'nome_especialidade')
    search_fields = ['nome_especialidade', 'cod_especialidade']


@admin.register(ProfissionalAghu)
class MedicoAdmin(ModelAdmin):
    list_display = ('nome', 'matricula')
    search_fields = ['nome']
