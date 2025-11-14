from django import forms

from fila_cirurgica.api_helpers import validar_procedimento_na_especialidade
from .models import ListaEsperaCirurgica
from django.urls import reverse_lazy


class ListaEsperaCirurgicaForm(forms.ModelForm):

    class RawChoiceField(forms.ChoiceField):
        def validate(self, value):
            if self.required and not value:
                raise forms.ValidationError(
                    self.error_messages['required'], code='required')

    # --- Campo "Fake" para Procedimento ---
    procedimento_api_choice = RawChoiceField(
        label='Procedimento', required=True, widget=forms.Select(attrs={
            'class': 'admin-autocomplete',
            'data-ajax-url': reverse_lazy('fila_cirurgica:procedimento_api_autocomplete'),
            'data-theme': 'admin-autocomplete', 'data-allow-clear': 'false',
            'data-placeholder': 'Busque o procedimento',
        }),
        help_text="Selecione a especialidade antes de selecionar o procedimento."
    )
    # --- Campo "Fake" para Paciente ---
    paciente_api_choice = RawChoiceField(
        label='Paciente', required=True, widget=forms.Select(attrs={
            'class': 'admin-autocomplete',
            'data-ajax-url': reverse_lazy('fila_cirurgica:paciente_api_autocomplete'),
            'data-theme': 'admin-autocomplete', 'data-allow-clear': 'false',
            'data-placeholder': 'Busque o paciente por nome ou prontuário',
        })
    )
    # --- Campo "Fake" para Médico ---
    medico_api_choice = RawChoiceField(
        label='Médico', required=True, widget=forms.Select(attrs={
            'class': 'admin-autocomplete',
            'data-ajax-url': reverse_lazy('fila_cirurgica:medico_api_autocomplete'),
            'data-theme': 'admin-autocomplete', 'data-allow-clear': 'false',
            'data-placeholder': 'Busque o médico por nome ou matrícula',
        })
    )
    # --- Campo "Fake" para Especialidade ---
    especialidade_api_choice = RawChoiceField(
        label='Especialidade', required=True, widget=forms.Select(attrs={
            'class': 'admin-autocomplete',
            'data-ajax-url': reverse_lazy('fila_cirurgica:especialidade_api_autocomplete'),
            'data-theme': 'admin-autocomplete', 'data-allow-clear': 'false',
            'data-placeholder': 'Busque a especialidade',
        })
    )

    change_reason = forms.CharField(
        label="Motivo da alteração",
        max_length=100,
        required=True,
    )

    class Meta:
        model = ListaEsperaCirurgica
        exclude = ('procedimento', 'paciente', 'medico', 'especialidade')
        fields = [
            'especialidade_api_choice',
            'procedimento_api_choice',
            'paciente_api_choice',
            'medico_api_choice',
            'prioridade',
            'medida_judicial',
            'situacao',
            'observacoes',
            'data_novo_contato',
            'change_reason',
            'ativo'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(self.__class__, 'current_request', None)
        # Pré-popula os campos se estivermos editando um registro existente
        if self.instance and self.instance.pk:
            if self.instance.procedimento:
                proc = self.instance.procedimento
                self.fields['procedimento_api_choice'].choices = [
                    (proc.codigo, f"{proc.codigo} - {proc.nome}")]
                self.initial['procedimento_api_choice'] = proc.codigo
            if self.instance.paciente:
                pac = self.instance.paciente
                self.fields['paciente_api_choice'].choices = [(
                    pac.prontuario, f"{pac.nome} (Prontuário: {pac.prontuario}")]
                self.initial['paciente_api_choice'] = pac.prontuario
            if self.instance.medico:
                med = self.instance.medico
                self.fields['medico_api_choice'].choices = [(
                    med.matricula, f"{med.nome} (Matrícula: {med.matricula}")]
                self.initial['medico_api_choice'] = med.matricula
            if self.instance.especialidade:
                esp = self.instance.especialidade
                self.fields['especialidade_api_choice'].choices = [
                    (esp.cod_especialidade, esp.nome_especialidade)]
                self.initial['especialidade_api_choice'] = esp.cod_especialidade

            # if not request.user.is_superuser:
            #     # Se for superuser, permite editar os campos
            #     for field_name in ['procedimento_api_choice', 'paciente_api_choice', 'medico_api_choice', 'especialidade_api_choice']:
            #         self.fields[field_name].disabled = True
            #         # Adiciona um atributo customizado para indicar no template que está readonly
            #         self.fields[field_name].widget.attrs['data-readonly-api'] = 'true'

    def clean(self):
        """
        Sobrescreve o método clean para validar regras de negócio
        que envolvem múltiplos campos.
        """
        cleaned_data = super().clean()

        procedimento_id = cleaned_data.get('procedimento_api_choice')
        especialidade_id = cleaned_data.get('especialidade_api_choice')

        # Prossegue com a validação apenas se ambos os campos tiverem sido preenchidos
        if procedimento_id and especialidade_id:
            # Chama nossa função helper para verificar a combinação na API
            if not validar_procedimento_na_especialidade(procedimento_id, especialidade_id):
                # Se for inválido, adiciona um erro ao campo 'procedimento_api_choice'
                self.add_error(
                    'procedimento_api_choice',
                    forms.ValidationError(
                        "O procedimento selecionado não é válido para a especialidade informada. Por favor, selecione a especialidade novamente e depois o procedimento.",
                        code='invalid_procedure_for_specialty'
                    )
                )

        return cleaned_data