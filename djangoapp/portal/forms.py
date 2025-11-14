from __future__ import annotations

from django import forms
from django.urls import reverse_lazy  # Importado para resolver URLs no widget
from fila_cirurgica.api_helpers import (
    get_or_create_especialidade,
    get_or_create_paciente,
    get_or_create_procedimento,
    get_or_create_profissional,
)
from fila_cirurgica.models import ListaEsperaCirurgica
from aih.models import AihSolicitacao


class FilaUpdateForm(forms.ModelForm):
    """
    Formulário para EDIÇÃO de uma entrada da fila.
    - Trava os campos-chave (FKs).
    - Exige um motivo para a alteração (compliance/histórico).
    """

    # Campo obrigatório para rastrear o motivo da alteração no histórico
    motivo_alteracao = forms.CharField(
        label="Motivo da alteração",
        required=True,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Explique o que mudou e por quê (obrigatório)."}),
    )

    # =================================================================
    # CAMPOS JUDICIAIS (espelhados do CreateForm)
    # =================================================================
    judicial_numero = forms.CharField(
        label="Número do Processo Judicial",
        required=False,
        widget=forms.TextInput(attrs={"id": "id_judicial_numero"})
    )
    judicial_descricao = forms.CharField(
        label="Descrição da Medida Judicial",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "id": "id_judicial_descricao"})
    )
    judicial_anexos = forms.FileField(
        label="Anexar Documentos",
        required=False,
    )

    # Lista de campos que não podem ser alterados após a criação
    LOCKED_FIELDS = (
        "especialidade",
        "procedimento",
        "procedimento_secundario",
        "especialidade_secundario",
        "paciente",
        "medico",
    )

    class Meta:
        model = ListaEsperaCirurgica
        fields = [
            # FKs principais (serão travados)
            "especialidade",
            "procedimento",
            "procedimento_secundario",
            "especialidade_secundario",
            "paciente",
            "medico",
            
            # Campos editáveis
            "prioridade",
            "prioridade_justificativa",
            "medida_judicial",
            "situacao",
            "observacoes",
            "data_novo_contato",
            
            # Campos judiciais
            "judicial_numero",
            "judicial_descricao",
            "judicial_anexos",
            
            # Campo de auditoria
            "motivo_alteracao",
        ]
        widgets = {
            "medida_judicial": forms.CheckboxInput(
                attrs={'class': 'absolute w-4 h-4 opacity-0 peer', 
                'id': 'id_medida_judicial'}
            ),
            "observacoes": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Observações…"}
            ),
            "data_novo_contato": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }
        labels = {
            "prioridade": "Prioridade",
            "medida_judicial": "Medida judicial",
            "situacao": "Situação",
            "observacoes": "Observações",
        }
        help_texts = {
            "prioridade": "Selecione a prioridade conforme a regra do serviço.",
            "prioridade_justificativa": "Campo obrigatório caso a prioridade não seja 'Sem Prioridade'",
            "medida_judicial": "Marque se há decisão judicial aplicável.",
            "situacao": "Estado atual do paciente na fila.",
            "observacoes": "Anotações internas/observações livres.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.LOCKED_FIELDS:
            if name in self.fields:
                current_class = self.fields[name].widget.attrs.get("class", "")
                
                self.fields[name].widget.attrs.update(
                    {
                        "readonly": True, # Ajuda, embora <select> não o respeite
                        "class": (current_class + " bg-gray-50 cursor-not-allowed pointer-events-none appearance-none").strip(),
                        "title": "Campo bloqueado na edição",
                    }
                )
        
        # Define a ordem visual dos campos no formulário
        desired_order = [
            "especialidade",
            "procedimento",
            "procedimento_secundario",
            "especialidade_secundario",
            "medico",
            "paciente",
            "prioridade", "prioridade_justificativa", "medida_judicial",
            "judicial_numero", "judicial_descricao", "judicial_anexos",
            "situacao",
            "observacoes",
            "data_novo_contato",
            "motivo_alteracao"
        ]
        self.order_fields([f for f in desired_order if f in self.fields])

        # Permite que o campo de data aceite formatos comuns
        if "data_novo_contato" in self.fields:
            self.fields["data_novo_contato"].input_formats = ["%Y-%m-%d", "%d/%m/%Y"]

        # Oculta "motivo_alteracao" se o registro já estiver inativo (não faz sentido exigir)
        if self.instance and not self.instance.ativo and "motivo_alteracao" in self.fields:
            self.fields.pop("motivo_alteracao")

    def clean(self):
        cleaned = super().clean()
        
        # Validação extra para impedir mudanças nos campos travados (via POST injection)
        for name in self.LOCKED_FIELDS:
            if name in self.changed_data:
                self.add_error(name, "Este campo não pode ser alterado.")
                cleaned[name] = getattr(self.instance, name)

        # Validação da regra de negócio: prioridade não-padrão exige justificativa
        prioridade = (cleaned.get("prioridade") or "").strip()
        prioridade_justificativa = (cleaned.get("prioridade_justificativa") or "").strip()
        if prioridade != "SEM" and not prioridade_justificativa:
            self.add_error("prioridade_justificativa",
                           "Informe o motivo dessa prioridade.")
            
        return cleaned


class FilaCreateForm(forms.ModelForm):
    """
    Formulário para CRIAÇÃO de uma entrada da fila.
    - Usa campos `*_api` (ChoiceFields) que são populados via AJAX (Select2).
    - O método .save() resolve esses IDs em objetos reais do banco.
    """
    
    # =================================================================
    # CAMPOS DE BUSCA (Select2 + AJAX)
    #
    # O atributo 'data-autocomplete-url' é a "ponte" entre o Django e o
    # JavaScript. O Django renderiza a URL correta, e o JS a consome.
    # =================================================================

    especialidade_api = forms.ChoiceField(
        label="Especialidade",
        required=True,
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_especialidade_api",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:especialidade_api_autocomplete")
        }),
    )
    procedimento_api = forms.ChoiceField(
        label="Procedimento",
        required=True,
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_procedimento_api",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:procedimento_api_autocomplete")
        }),
    )
    especialidade_secundario_api = forms.ChoiceField(
        label="Especialidade Secundária",
        required=False,
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_especialidade_secundario_api",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:especialidade_api_autocomplete")
        }),
    )
    procedimento_secundario_api = forms.ChoiceField(
        label="Procedimento Secundário",
        required=False,
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_procedimento_secundario_api",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:procedimento_api_autocomplete")
        }),
    )
    medico_api = forms.ChoiceField(
        label="Médico",
        required=True,
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_medico_api",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:medico_api_autocomplete")
        }),
    )
    prontuario = forms.ChoiceField(
        label="Prontuário",
        required=True,
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_prontuario",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:paciente_api_autocomplete")
        }),
    )

    # =================================================================
    # CAMPOS JUDICIAIS
    # =================================================================
    judicial_numero = forms.CharField(
        label="Número do Processo Judicial",
        required=False,
        widget=forms.TextInput(attrs={"id": "id_judicial_numero"})
    )
    judicial_descricao = forms.CharField(
        label="Descrição da Medida Judicial",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "id": "id_judicial_descricao"})
    )
    judicial_anexos = forms.FileField(
        label="Anexos do Processo",
        required=False,
        widget=forms.FileInput(attrs={"id": "id_judicial_anexos"})
    )

    class Meta:
        model = ListaEsperaCirurgica
        # Campos do modelo que serão renderizados diretamente
        fields = [
           # Campos editáveis
            "prioridade",
            "prioridade_justificativa",
            "medida_judicial",
            "situacao",
            "observacoes",
            "data_novo_contato",
            
            # Campos judiciais
            "judicial_numero",
            "judicial_descricao",
            "judicial_anexos",
        ]
        widgets = {
            "medida_judicial": forms.CheckboxInput(
                attrs={'class': 'absolute w-4 h-4 opacity-0 peer', 
                'id': 'id_medida_judicial'}
            ),
            "observacoes": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Observações…"}
            ),
            "data_novo_contato": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }
        labels = {
            "prioridade": "Prioridade",
            "medida_judicial": "Medida judicial",
            "situacao": "Situação",
            "observacoes": "Observações",
        }
        help_texts = {
            "prioridade": "Selecione a prioridade conforme a regra do serviço.",
            "medida_judicial": "Marque se há decisão judicial aplicável.",
            "situacao": "Estado atual do paciente na fila.",
            "observacoes": "Anotações internas/observações livres.",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.initial_data = kwargs.get('initial', {})

        if self.initial_data.get('aih_id'):
            FIELDS_TO_LOCK = [
                'prontuario', 
                'especialidade_api', 
                'procedimento_api', 
                'medico_api'
            ]
            
            for name in FIELDS_TO_LOCK:
                if name in self.fields:
                    widget = self.fields[name].widget
                    current_class = widget.attrs.get("class", "")
                    
                    # Adiciona classes CSS para parecer desabilitado.
                    # Não usamos 'disabled=True' pois o valor não seria enviado no POST.
                    # 'pointer-events-none' impede o clique.
                    widget.attrs.update(
                        {
                            'class': (current_class + " bg-gray-50 cursor-not-allowed pointer-events-none").strip(),
                            'title': "Campo bloqueado (originado da AIH)",
                        }
                    )

        def prefill_choice(field_name: str) -> None:
            """
            Verifica se há dados iniciais para um campo Select2.
            Se houver, adiciona o par (valor, texto) aos 'choices'
            para que o Select2 possa renderizá-lo na carga inicial.
            """
            field = self.fields[field_name]
            value = self.initial_data.get(field_name)
            label = self.initial_data.get(f"{field_name}_text") or value # Usa o _text da View

            if value and label:
                # Adiciona o (valor, label) aos choices se ainda não existir
                if not any(str(value) == str(v) for v, _ in field.choices):
                    field.choices = list(field.choices) + [(str(value), label)]
                
                # Define o 'initial' no próprio campo
                field.initial = value
                
        for name in (
            "especialidade_api", "procedimento_api", 
            "medico_api", "prontuario"
        ):
            prefill_choice(name)

        def ensure_choice(field_name: str) -> None:
            """
            Garante que o valor enviado (via POST) em um Select2 AJAX
            seja adicionado aos 'choices' do campo. Isso é necessário
            para que o Django valide um valor que ele não conhece (pois
            foi carregado via API).
            """
            field = self.fields[field_name]
            # Pega o valor enviado (do POST ou 'initial')
            value = self.data.get(field_name) or self.initial.get(field_name)
            if not value:
                return
            
            # Pega o texto (label) do valor
            label = self.data.get(f"{field_name}_text") or str(value)
            
            # Adiciona (valor, label) aos choices se ainda não existir
            if not any(str(value) == str(v) for v, _ in field.choices):
                field.choices = list(field.choices) + [(str(value), label)]

        # Aplica a função 'ensure_choice' em todos os campos de Select2 AJAX
        for name in (
            "especialidade_api", "procedimento_api", 
            "especialidade_secundario_api", "procedimento_secundario_api",
            "medico_api", "prontuario"
        ):
            ensure_choice(name)

        # Define a ordem visual dos campos
        desired_order = [
            "especialidade_api",
            "procedimento_api",
            "especialidade_secundario_api",
            "procedimento_secundario_api",
            "medico_api",
            "prontuario",
            "prioridade",
            "prioridade_justificativa",
            "medida_judicial",
            "judicial_numero", 
            "judicial_descricao", 
            "judicial_anexos",
            "situacao",
            "observacoes",
            "data_novo_contato",
        ]
        # Filtra 'desired_order' para conter apenas campos que existem neste form
        self.order_fields([f for f in desired_order if f in self.fields])

    def clean(self) -> dict:
        cleaned = super().clean()
        
        # Validação da regra de negócio: prioridade não-padrão exige justificativa
        prioridade = (cleaned.get("prioridade") or "").strip()
        prioridade_justificativa = (cleaned.get("prioridade_justificativa") or "").strip()
        if prioridade != "SEM" and not prioridade_justificativa:
            self.add_error("prioridade_justificativa",
                           "Informe o motivo dessa prioridade.")

        aih_id = self.initial_data['aih_id'] # Pega o aih_id do POST

        # Se veio de uma AIH, os campos devem estar travados
        if aih_id: 
            FIELDS_TO_LOCK = ['prontuario', 'especialidade_api', 'procedimento_api', 'medico_api']
            
            for name in FIELDS_TO_LOCK:
                # Compara o valor enviado (cleaned_data) com o valor original (initial)
                # Usamos .get() e str() para comparar com segurança
                enviado = str(cleaned.get(name) or '')
                inicial = str(self.initial.get(name) or '')

                if enviado != inicial:
                    self.add_error(name, "Este campo não pode ser alterado pois foi originado de uma AIH.")
                    # (Opcional) Força o valor de volta para o inicial
                    cleaned[name] = self.initial.get(name)
        return cleaned

    def save(self, commit: bool = True) -> ListaEsperaCirurgica:
        """
        Sobrescreve o .save() para resolver os IDs dos campos `*_api`
        em objetos reais do banco, usando os `api_helpers`.
        """
        # Cria a instância do modelo, mas não salva no banco ainda
        instance: ListaEsperaCirurgica = super().save(commit=False)

        # 1. Coleta os IDs enviados pelos campos Select2
        prontuario = self.cleaned_data["prontuario"].strip()
        esp_id = str(self.cleaned_data["especialidade_api"])
        proc_id = str(self.cleaned_data["procedimento_api"])
        med_id = str(self.cleaned_data["medico_api"])
        proc_sec_id = self.cleaned_data.get("procedimento_secundario_api")
        esp_sec_id = self.cleaned_data.get("especialidade_secundario_api")

        # 2. Usa os 'helpers' para buscar ou criar os objetos FK
        # (Isso desacopla o form da lógica de API)
        instance.paciente = get_or_create_paciente(prontuario=prontuario)
        instance.especialidade = get_or_create_especialidade(esp_id)
        instance.procedimento = get_or_create_procedimento(proc_id)
        instance.medico = get_or_create_profissional(med_id)

        # 3. Processa os campos secundários (opcionais)
        if proc_sec_id and esp_sec_id:
            instance.procedimento_secundario = get_or_create_procedimento(proc_sec_id)
            instance.especialidade_secundario = get_or_create_especialidade(esp_sec_id)
        else:
            instance.procedimento_secundario = None
            instance.especialidade_secundario = None

        # 4. Salva a instância no banco (se commit=True)
        if commit:
            instance.save()
            
        aih_id = self.initial_data["aih_id"]
        if aih_id:
            try:
                aih = AihSolicitacao.objects.get(pk=aih_id)
                aih.cadastrado_na_fila = True
                aih.save(update_fields=['cadastrado_na_fila'])
            except AihSolicitacao.DoesNotExist:
                # Se a AIH original não for encontrada, não faz nada.
                pass
            
        return instance


class FilaDeactivateForm(forms.Form):
    """
    Formulário para "remoção" (inativação) de uma entrada.
    Pede um motivo estruturado (choices) e uma justificativa textual.
    """
    motivo = forms.ChoiceField(
        label="Motivo da remoção",
        choices=(),  # Preenchido dinamicamente no __init__
        required=True,
        widget=forms.RadioSelect,
    )
    change_reason = forms.CharField(
        label="Justificativa",
        required=True,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Descreva o contexto da remoção (obrigatório)."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Carrega dinamicamente os 'choices' do modelo.
        # Isso garante que o form esteja sempre em sincronia com o models.py.
        try:
            field = ListaEsperaCirurgica._meta.get_field("motivo_saida")
            if getattr(field, "choices", None):
                self.fields["motivo"].choices = list(field.choices)
        except Exception:
            # Em caso de falha, o campo 'motivo' ficará sem opções
            pass


   
# ==============================================================================
# FORMULÁRIO DE CRIAÇÃO AIH (AihCreateForm) - REFATORADO
# ==============================================================================
class AihCreateForm(forms.ModelForm):
    """
    Formulário simplificado para criação de AIH via Portal.
    Usa a mesma definição dos campos _api do FilaCreateForm para consistência.
    Apenas estes 4 campos _api são estritamente obrigatórios para submissão inicial.
    """

    # --- Campos de Busca AJAX (Definição idêntica ao FilaCreateForm) ---
    especialidade_api = forms.ChoiceField(
        label="Especialidade",
        required=True, # Obrigatório no formulário
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_especialidade_api",
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:especialidade_api_autocomplete"),
        }),
    )
    procedimento_api = forms.ChoiceField(
        label="Procedimento",
        required=True, # Obrigatório no formulário
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_procedimento_api", # Mesmo ID
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:procedimento_api_autocomplete"),
        }),
    )
    medico_api = forms.ChoiceField(
        label="Médico Solicitante",
        required=True, # Obrigatório no formulário
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_medico_api", # Mesmo ID
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:medico_api_autocomplete"),
        }),
    )
    prontuario = forms.ChoiceField( # Identificador do paciente
        label="Paciente (Prontuário)",
        required=True, # Obrigatório no formulário
        choices=[("", "Digite para buscar…")],
        widget=forms.Select(attrs={
            "id": "id_prontuario", # Mesmo ID
            "data-autocomplete-url": reverse_lazy("fila_cirurgica:paciente_api_autocomplete"),
        }),
    )

    class Meta:
        model = AihSolicitacao
        exclude = [
            'especialidade',
            'procedimento',
            'medico',
            'paciente',
        ]
        widgets = {
             "data_nascimento": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "peer"}),
             "data_solicitacao": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "peer"}),
             "principais_sinais_sintomas": forms.Textarea(attrs={"rows": 3, "class": "peer"}),
             "condicoes_justificam_internacao": forms.Textarea(attrs={"rows": 3, "class": "peer"}),
             "resultados_provas_diagnosticas": forms.Textarea(attrs={"rows": 3, "class": "peer"}),
             "diagnostico_inicial": forms.Textarea(attrs={"rows": 3, "class": "peer"}),
             "nome_estabelecimento_solicitante": forms.TextInput(attrs={'class': 'peer'}),
             "cnes_solicitante": forms.TextInput(attrs={'class': 'peer'}),
             "nome_estabelecimento_executante": forms.TextInput(attrs={'class': 'peer'}),
             "nome_paciente": forms.TextInput(attrs={'class': 'peer'}),
             "numero_prontuario": forms.TextInput(attrs={'class': 'peer'}),
             "cartao_nacional_saude": forms.TextInput(attrs={'class': 'peer'}),
             "sexo": forms.Select(attrs={'class': 'peer'}),
             "raca_cor": forms.Select(attrs={'class': 'peer'}),
             "nome_mae": forms.TextInput(attrs={'class': 'peer'}),
             "telefone_contato_1": forms.TextInput(attrs={'class': 'peer'}),
             "nome_responsavel": forms.TextInput(attrs={'class': 'peer'}),
             "telefone_contato_2": forms.TextInput(attrs={'class': 'peer'}),
             "endereco_completo": forms.TextInput(attrs={'class': 'peer'}),
             "municipio_residencia": forms.TextInput(attrs={'class': 'peer'}),
             "codigo_ibge_municipio": forms.TextInput(attrs={'class': 'peer'}),
             "uf": forms.TextInput(attrs={'class': 'peer'}),
             "cep": forms.TextInput(attrs={'class': 'peer'}),
             "cid10_principal": forms.TextInput(attrs={'class': 'peer'}),
             "cid10_secundario": forms.TextInput(attrs={'class': 'peer'}),
             "cid10_causas_associadas": forms.TextInput(attrs={'class': 'peer'}),
             "descricao_procedimento_solicitado": forms.TextInput(attrs={'class': 'peer'}),
             "codigo_procedimento": forms.TextInput(attrs={'class': 'peer'}),
             "clinica": forms.TextInput(attrs={'class': 'peer'}),
             "carater_internacao": forms.Select(attrs={'class': 'peer'}),
             "tipo_documento_profissional": forms.Select(attrs={'class': 'peer'}),
             "numero_documento_profissional": forms.TextInput(attrs={'class': 'peer'}),
             "acidente_transito": forms.CheckboxInput(attrs={'class': 'peer'}), # Checkboxes não precisam das classes de esconder
             "acidente_trabalho_tipico": forms.CheckboxInput(attrs={'class': 'peer'}),
             "acidente_trabalho_trajeto": forms.CheckboxInput(attrs={'class': 'peer'}),
             "cnpj_seguradora": forms.TextInput(attrs={'class': 'peer'}),
             "numero_bilhete": forms.TextInput(attrs={'class': 'peer'}),
             "serie_bilhete": forms.TextInput(attrs={'class': 'peer'}),
             "cnpj_empresa": forms.TextInput(attrs={'class': 'peer'}),
             "cnae_empresa": forms.TextInput(attrs={'class': 'peer'}),
             "cbor": forms.TextInput(attrs={'class': 'peer'}),
             "vinculo_previdencia": forms.Select(attrs={'class': 'peer'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'prioridade' in self.fields:
            self.fields['prioridade'].widget.attrs['id'] = 'id_prioridade'
            # Adiciona a classe 'peer' para consistência de estilo
            current_class = self.fields['prioridade'].widget.attrs.get("class", "")
            if "peer" not in current_class:
                self.fields['prioridade'].widget.attrs['class'] = (current_class + " peer").strip()

        if 'prioridade_justificativa' in self.fields:
            self.fields['prioridade_justificativa'].widget.attrs['id'] = 'id_prioridade_justificativa'
            # Adiciona a classe 'peer' para consistência de estilo
            current_class = self.fields['prioridade_justificativa'].widget.attrs.get("class", "")
            if "peer" not in current_class:
                self.fields['prioridade_justificativa'].widget.attrs['class'] = (current_class + " peer").strip()

        # Garante que as opções enviadas via AJAX sejam válidas (necessário para Select2/TomSelect)
        def ensure_choice(field_name: str) -> None:
            field = self.fields.get(field_name); value = self.data.get(field_name) or self.initial.get(field_name)
            if not field or not value: return
            label = self.data.get(f"{field_name}_text") or str(value) # Usado se o JS enviar o texto junto
            if not any(str(value) == str(v) for v, _ in field.choices): field.choices = list(field.choices) + [(str(value), label)]

        for name in ("especialidade_api", "procedimento_api", "medico_api", "prontuario"): ensure_choice(name)

        # Garante que campos required=True no form tenham o atributo HTML 'required'
        # Adiciona 'peer' a todos os campos para consistência CSS (exceto uploads)
        for field_name, field in self.fields.items():
             if field.required:
                 field.widget.attrs['required'] = True
             current_class = field.widget.attrs.get("class", "")
             if "peer" not in current_class and not isinstance(field.widget, forms.FileInput):
                  field.widget.attrs['class'] = (current_class + " peer").strip()

        # Define ordem visual (campos obrigatórios primeiro)
        desired_order = ["especialidade_api", "procedimento_api", "medico_api", "prontuario", "cid10_principal", "diagnostico_inicial"]
        all_fields = list(self.fields.keys()); ordered_fields = desired_order + [f for f in all_fields if f not in desired_order]
        self.order_fields(ordered_fields)
        
    def clean(self) -> dict:
        cleaned = super().clean()
        
        prioridade = (cleaned.get("prioridade") or "").strip()
        prioridade_justificativa = (cleaned.get("prioridade_justificativa") or "").strip()
        
        # 'SEM' é o valor para "Sem Prioridade" no seu modelo AihSolicitacao
        if prioridade and prioridade != "SEM" and not prioridade_justificativa:
            self.add_error("prioridade_justificativa",
                           "Informe o motivo dessa prioridade.")
        return cleaned

    def save(self, commit: bool = True) -> AihSolicitacao:
        """
        Converte IDs externos (_api) em FKs reais, preenche nomes automaticamente
        e salva a AIH.
        """
        instance: AihSolicitacao = super().save(commit=False)

        # Coleta IDs dos campos AJAX
        prontuario_str = self.cleaned_data["prontuario"].strip()
        esp_id = str(self.cleaned_data["especialidade_api"])
        proc_id = str(self.cleaned_data["procedimento_api"])
        med_id = str(self.cleaned_data["medico_api"])

        # Usa os helpers para buscar/criar os objetos relacionados
        # Assumindo que os helpers retornam o objeto ou None se não encontrado/criado
        paciente_obj = get_or_create_paciente(prontuario=prontuario_str)
        especialidade_obj = get_or_create_especialidade(esp_id)
        procedimento_obj = get_or_create_procedimento(proc_id)
        medico_obj = get_or_create_profissional(med_id)

        # --- PREENCHIMENTO DOS CAMPOS ---

        # 1. Preenche os NOVOS campos ForeignKey
        instance.paciente = paciente_obj
        instance.especialidade = especialidade_obj
        instance.procedimento = procedimento_obj
        instance.medico = medico_obj # Associa ao campo 'medico' no modelo

        # 2. Preenche os campos de NOME automaticamente (se ainda não preenchidos)
        #    Use getattr para evitar erros se o objeto ou atributo não existir.
        if not instance.nome_paciente and paciente_obj:
             instance.nome_paciente = getattr(paciente_obj, 'nome', None) # Assumindo que PacienteAghu tem 'nome'
        if not instance.cartao_nacional_saude and paciente_obj: # Bônus: CNS também
            instance.cartao_nacional_saude = getattr(paciente_obj, 'cartao_sus', None) # Assumindo 'cartao_sus'
        if not instance.descricao_procedimento_solicitado and procedimento_obj:
             instance.descricao_procedimento_solicitado = getattr(procedimento_obj, 'nome', None) # Assumindo que Procedimento tem 'nome'
        if not instance.codigo_procedimento and procedimento_obj: # Bônus: Código também
             instance.codigo_procedimento = getattr(procedimento_obj, 'codigo', None) # Assumindo 'codigo'
        if not instance.nome_profissional_solicitante and medico_obj:
             instance.nome_profissional_solicitante = getattr(medico_obj, 'nome', None) # Assumindo que Profissional tem 'nome'

        # --- FIM DO PREENCHIMENTO ---

        # Salva a instância no banco se commit=True
        if commit:
            instance.save()
            # Se você usar ManyToManyFields, eles precisam ser salvos *depois* do instance.save() inicial
            # self.save_m2m() # Descomente se AihSolicitacao tiver M2M
        return instance