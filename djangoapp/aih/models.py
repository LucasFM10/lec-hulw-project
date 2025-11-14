from django.db import models

from fila_cirurgica.models import EspecialidadeAghu, PacienteAghu, ProcedimentoAghu, ProfissionalAghu
from simple_history.models import HistoricalRecords

class AihSolicitacao(models.Model):
    """
    Representa o Laudo para Solicitação/Autorização de Internação Hospitalar (AIH).
    Todos os campos são opcionais (blank=True, null=True).
    """
    history = HistoricalRecords()
    
    # Flag para controlar se esta AIH já foi enviada para a fila cirúrgica.
    cadastrado_na_fila = models.BooleanField(
        "Cadastrado na Fila?",
        default=False,
        help_text="Marca 'Verdadeiro' quando esta AIH é usada para criar uma entrada na fila."
    )

    # --- Identificação do Estabelecimento de Saúde ---
    nome_estabelecimento_solicitante = models.CharField(
        "Nome do Estabelecimento Solicitante", max_length=100, blank=True, null=True
    )
    cnes_solicitante = models.CharField(
        "CNES Solicitante", max_length=7, blank=True, null=True
    )
    nome_estabelecimento_executante = models.CharField(
        "Nome do Estabelecimento Executante", max_length=100, blank=True, null=True
    )
    cnes_executante = models.CharField(
        "CNES Executante", max_length=7, blank=True, null=True
    )

    # --- Identificação do Paciente ---
    nome_paciente = models.CharField(
        "Nome do Paciente", max_length=100, blank=True, null=True
    )
    numero_prontuario = models.CharField(
        "Nº do Prontuário", max_length=20, blank=True, null=True
    )
    cartao_nacional_saude = models.CharField(
        "Cartão Nacional de Saúde (CNS)", max_length=15, blank=True, null=True
    )
    data_nascimento = models.DateField(
        "Data de Nascimento", blank=True, null=True
    )
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
    ]
    sexo = models.CharField(
        "Sexo", max_length=1, choices=SEXO_CHOICES, blank=True, null=True
    )
    RACA_COR_CHOICES = [
        ('BR', 'Branca'),
        ('PR', 'Preta'),
        ('PA', 'Parda'),
        ('AM', 'Amarela'),
        ('IN', 'Indígena'),
        ('NI', 'Não Informado'), # Assuming 'NI' for cases where it's not filled
    ]
    raca_cor = models.CharField(
        "Raça/Cor", max_length=2, choices=RACA_COR_CHOICES, blank=True, null=True
    )
    nome_mae = models.CharField(
        "Nome da Mãe", max_length=100, blank=True, null=True
    )
    telefone_contato_1 = models.CharField(
        "Telefone de Contato 1", max_length=20, blank=True, null=True # DDD + Numero
    )
    nome_responsavel = models.CharField(
        "Nome do Responsável", max_length=100, blank=True, null=True
    )
    telefone_contato_2 = models.CharField(
        "Telefone de Contato 2", max_length=20, blank=True, null=True # DDD + Numero
    )
    endereco_completo = models.CharField(
        "Endereço (Rua, Nº, Bairro)", max_length=200, blank=True, null=True
    )
    municipio_residencia = models.CharField(
        "Município de Residência", max_length=100, blank=True, null=True
    )
    codigo_ibge_municipio = models.CharField(
        "Cód. IBGE Município", max_length=7, blank=True, null=True
    )
    uf = models.CharField(
        "UF", max_length=2, blank=True, null=True
    )
    cep = models.CharField(
        "CEP", max_length=9, blank=True, null=True # Formato 12345-678
    )

    # --- Justificativa da Internação ---
    principais_sinais_sintomas = models.TextField(
        "Principais Sinais e Sintomas Clínicos", blank=True, null=True
    )
    condicoes_justificam_internacao = models.TextField(
        "Condições que Justificam a Internação", blank=True, null=True
    )
    resultados_provas_diagnosticas = models.TextField(
        "Principais Resultados de Provas Diagnósticas", blank=True, null=True
    )
    diagnostico_inicial = models.TextField(
        "Diagnóstico Inicial", blank=True, null=True
    )
    cid10_principal = models.CharField(
        "CID 10 Principal", max_length=10, blank=True, null=True # Ex: A00.1
    )
    cid10_secundario = models.CharField(
        "CID 10 Secundário", max_length=10, blank=True, null=True
    )
    cid10_causas_associadas = models.CharField(
        "CID 10 Causas Associadas", max_length=10, blank=True, null=True
    )

    # --- Procedimento Solicitado ---
    descricao_procedimento_solicitado = models.CharField(
        "Descrição do Procedimento Solicitado", max_length=255, blank=True, null=True
    )
    codigo_procedimento = models.CharField(
        "Código do Procedimento", max_length=10, blank=True, null=True
    )
    clinica = models.CharField(
        "Clínica", max_length=50, blank=True, null=True
    )
    carater_internacao = models.CharField(
        "Caráter da Internação", max_length=50, blank=True, null=True
    )

    # --- Profissional Solicitante/Assistente ---
    tipo_documento_profissional = models.CharField(
        "Tipo Documento Profissional Solicitante", max_length=3, blank=True, null=True
    )
    numero_documento_profissional = models.CharField(
        "Nº Documento Profissional Solicitante", max_length=15, blank=True, null=True # Accomodates CNS or CPF
    )
    nome_profissional_solicitante = models.CharField(
        "Nome do Profissional Solicitante/Assistente", max_length=100, blank=True, null=True
    )
    data_solicitacao = models.DateField(
        "Data da Solicitação", blank=True, null=True
    )
    # Assinatura e carimbo não são armazenados como campos, mas podem ser referenciados se digitalizados

    # --- Causas Externas (Acidentes ou Violências) ---
    acidente_transito = models.BooleanField(
        "Acidente de Trânsito", blank=True, null=True
    )
    acidente_trabalho_tipico = models.BooleanField(
        "Acidente Trabalho Típico", blank=True, null=True
    )
    acidente_trabalho_trajeto = models.BooleanField(
        "Acidente Trabalho Trajeto", blank=True, null=True
    )
    cnpj_seguradora = models.CharField(
        "CNPJ da Seguradora", max_length=18, blank=True, null=True # Formato XX.XXX.XXX/YYYY-ZZ
    )
    numero_bilhete = models.CharField(
        "Nº do Bilhete", max_length=30, blank=True, null=True
    )
    serie_bilhete = models.CharField(
        "Série", max_length=10, blank=True, null=True
    )
    cnpj_empresa = models.CharField(
        "CNPJ Empresa", max_length=18, blank=True, null=True
    )
    cnae_empresa = models.CharField(
        "CNAE da Empresa", max_length=10, blank=True, null=True
    )
    cbor = models.CharField( # Classificação Brasileira de Ocupações Revisada? Check official spec
        "CBOR", max_length=10, blank=True, null=True
    )
    vinculo_previdencia = models.CharField(
        "Vínculo com a Previdência", max_length=50, blank=True, null=True
    )

    # --- Autorização ---
    nome_profissional_autorizador = models.CharField(
        "Nome do Profissional Autorizador", max_length=100, blank=True, null=True
    )
    codigo_orgao_emissor = models.CharField(
        "Cód. Órgão Emissor", max_length=10, blank=True, null=True
    )
    tipo_documento_autorizador = models.CharField(
        "Tipo Documento Profissional Autorizador", max_length=3, blank=True, null=True
    )
    numero_documento_autorizador = models.CharField(
        "Nº Documento Profissional Autorizador", max_length=15, blank=True, null=True
    )
    data_autorizacao = models.DateField(
        "Data da Autorização", blank=True, null=True
    )
    numero_aih = models.CharField(
        "Nº da Autorização de Internação Hospitalar", max_length=13, blank=True, null=True # Usually a long number
    )    
    PRIORIDADE_CHOICES = [
        ('ONC', 'Paciente Oncológico'),
        ('BRE', 'Com Prioridade'),
        ('SEM', 'Sem Prioridade'),
        ]
    prioridade = models.CharField(
        blank=True,
        null=True,
        max_length=3,
        choices=PRIORIDADE_CHOICES,
        default='SEM')
    prioridade_justificativa = models.TextField(
        blank=True,
        null=True,
        verbose_name="Justificativa da Prioridade",
        help_text="Motivo pelo qual o paciente recebeu a prioridade informada."
    )
    
    paciente = models.ForeignKey(
        PacienteAghu, # Use o nome correto do seu modelo de paciente
        verbose_name="Paciente (Objeto)",
        on_delete=models.SET_NULL, # Ou models.PROTECT, etc.
        null=True,
        blank=True,
        related_name='aih_solicitacoes'
    )
    # Adiciona a relação com o modelo Especialidade do app fila_cirurgica
    especialidade = models.ForeignKey(
        EspecialidadeAghu, # Use o nome correto do seu modelo de especialidade
        verbose_name="Especialidade (Objeto)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aih_solicitacoes'
    )
    # Adiciona a relação com o modelo Procedimento do app fila_cirurgica
    procedimento = models.ForeignKey(
        ProcedimentoAghu, # Use o nome correto do seu modelo de procedimento
        verbose_name="Procedimento (Objeto)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aih_solicitacoes'
    )
    # Adiciona a relação com o modelo Profissional do app fila_cirurgica
    medico = models.ForeignKey( # Renomeado para 'medico' para consistência com Fila
        ProfissionalAghu, # Use o nome correto do seu modelo de profissional/médico
        verbose_name="Médico Solicitante (Objeto)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aih_solicitacoes_solicitadas'
    )

    # --- Metadados ---
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AIH {self.numero_aih or 'Não Autorizada'} - Paciente: {self.nome_paciente or 'Não Informado'}"

    class Meta:
        verbose_name = "Solicitação/Autorização de AIH"
        verbose_name_plural = "Solicitações/Autorizações de AIH"
        ordering = ['-data_criacao'] # Order by creation date descending by default
