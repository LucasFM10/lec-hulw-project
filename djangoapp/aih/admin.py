from django.contrib import admin
from .models import AihSolicitacao

@admin.register(AihSolicitacao)
class AihSolicitacaoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_aih',
        'nome_paciente',
        'nome_estabelecimento_solicitante',
        'data_solicitacao',
        'data_autorizacao',
    )
    list_filter = (
        'data_solicitacao',
        'data_autorizacao',
        'sexo',
        'raca_cor',
        'carater_internacao',
    )
    search_fields = (
        'numero_aih',
        'nome_paciente',
        'cartao_nacional_saude',
        'nome_profissional_solicitante',
        'codigo_procedimento',
        'cid10_principal',
    )
    # Readonly fields might be useful for fields filled later in the process
    # readonly_fields = ('data_criacao', 'data_atualizacao')

    # Group fields into fieldsets for better organization in the admin form
    fieldsets = (
        ('Identificação do Estabelecimento', {
            'fields': ('nome_estabelecimento_solicitante', 'cnes_solicitante',
                       'nome_estabelecimento_executante', 'cnes_executante')
        }),
        ('Identificação do Paciente', {
            'fields': ('nome_paciente', 'numero_prontuario', 'cartao_nacional_saude',
                       'data_nascimento', 'sexo', 'raca_cor', 'nome_mae',
                       'telefone_contato_1', 'nome_responsavel', 'telefone_contato_2',
                       'endereco_completo', 'municipio_residencia', 'codigo_ibge_municipio',
                       'uf', 'cep')
        }),
        ('Justificativa da Internação', {
            'fields': ('principais_sinais_sintomas', 'condicoes_justificam_internacao',
                       'resultados_provas_diagnosticas', 'diagnostico_inicial',
                       'cid10_principal', 'cid10_secundario', 'cid10_causas_associadas')
        }),
        ('Procedimento Solicitado', {
            'fields': ('descricao_procedimento_solicitado', 'codigo_procedimento',
                       'clinica', 'carater_internacao')
        }),
        ('Profissional Solicitante', {
            'fields': ('tipo_documento_profissional', 'numero_documento_profissional',
                       'nome_profissional_solicitante', 'data_solicitacao')
        }),
        ('Causas Externas', {
            'classes': ('collapse',), # Start collapsed
            'fields': ('acidente_transito', 'acidente_trabalho_tipico', 'acidente_trabalho_trajeto',
                       'cnpj_seguradora', 'numero_bilhete', 'serie_bilhete', 'cnpj_empresa',
                       'cnae_empresa', 'cbor', 'vinculo_previdencia')
        }),
        ('Autorização (Preenchimento Posterior)', {
             'classes': ('collapse',),
            'fields': ('numero_aih', 'nome_profissional_autorizador', 'codigo_orgao_emissor',
                       'tipo_documento_autorizador', 'numero_documento_autorizador',
                       'data_autorizacao')
        }),
        ('Metadados', {
            'fields': ('data_criacao', 'data_atualizacao'),
        })
    )
    readonly_fields = ('data_criacao', 'data_atualizacao') # Make metadata readonly
