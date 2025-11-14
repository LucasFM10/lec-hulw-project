from django.shortcuts import render, redirect
from fila_cirurgica.models import PacienteAghu, ProcedimentoAghu, EspecialidadeAghu
import re
from bs4 import BeautifulSoup
from django.core.files.storage import default_storage
from django.contrib import messages
import csv

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required  # Garante que apenas usuários autenticados acessem
def especialidade_autocomplete(request):
    term = request.GET.get("q", "").strip()  # Obtém o termo de pesquisa
    if not term:
        return JsonResponse([], safe=False)

    especialidades = EspecialidadeAghu.objects.filter(
        nome_especialidade__icontains=term)
    data = [{"id": e.id, "text": e.nome_especialidade} for e in especialidades]

    return JsonResponse(data, safe=False)


def home(request):
    if request.method == 'POST' and request.FILES.get('file'):
        # Obter o arquivo HTML enviado
        html_file = request.FILES['file']

        processar_html_para_procedimentos_sigtap(html_file)
        return render(request, 'upload.html')

    return render(request, 'upload.html')


def processar_html_para_procedimentos_sigtap(html_file):
    pass

def extrair_texto_de_tr(row):
    cells = row.find_all('td')
    text = ''
    for cell in cells:
        text += cell.get_text().strip().replace('\n', ' ')
    palavras = text.split()
    text = ' '.join(palavras)
    return text


def extrair_valor(texto, campo):
    match = re.search(rf"{campo}R\$(\d+,\d+)", texto)
    return float(match.group(1).replace(',', '.')) if match else 0.0


def extrair_idade(texto, tipo):
    match = re.search(rf"Idade {tipo}:(\d+)", texto)
    return int(match.group(1)) if match else 0


def extrair_quantidade_maxima(texto):
    match = re.search(r"Quantidade Máxima:(\d+)", texto)
    return int(match.group(1)) if match else 0


def extrair_media_permanencia(texto):
    match = re.search(r"Média Permanência:(\d+)", texto)
    return int(match.group(1)) if match else 0


def extrair_pontos(texto):
    match = re.search(r"Pontos:(\d+)", texto)
    return int(match.group(1)) if match else 0


def processar_csv_pacientes(request):
    if request.method == "POST":
        arquivo = request.FILES.get("file_pacientes")

        if not arquivo.name.endswith(".csv"):
            messages.error(request, "Por favor, envie um arquivo CSV válido.")
            return redirect("importar_pacientes")

        # Salvar o arquivo temporariamente
        file_path = default_storage.save(f"temp/{arquivo.name}", arquivo)

        with open(default_storage.path(file_path), newline='', encoding="utf-8-sig") as csvfile:
            # Usa tabulação como delimitador
            leitor = csv.DictReader(csvfile, delimiter=";")

            for linha in leitor:
                nome_paciente = linha.get("NOME_PACIENTE", "").strip()

                if nome_paciente:
                    PacienteAghu.objects.get_or_create(nome=nome_paciente)

        messages.success(request, "Pacientes importados com sucesso!")
        return redirect("importar_pacientes")

    return render(request, 'upload.html')


def processar_csv_procedimentos(request):
    if request.method == "POST":
        arquivo = request.FILES.get("file_procedimentos")

        if not arquivo.name.endswith(".csv"):
            messages.error(request, "Por favor, envie um arquivo CSV válido.")
            return redirect("importar_procedimentos")
        # Salvar o arquivo temporariamente
        file_path = default_storage.save(f"temp/{arquivo.name}", arquivo)

        with open(default_storage.path(file_path), newline='', encoding="utf-8-sig") as csvfile:
            # Usa tabulação como delimitador
            leitor = csv.DictReader(csvfile, delimiter=";")

            for linha in leitor:
                codigo = linha.get("COD_PROCEDIMENTO", "").strip()
                nome = linha.get("PROCEDIMENTO", "").strip()

                if codigo and nome:
                    print(f"Importando procedimento: {codigo} - {nome}")
                    ProcedimentoAghu.objects.get_or_create(
                        codigo=codigo, nome=nome)

        messages.success(request, "Procedimentos importados com sucesso!")
        return redirect("importar_procedimentos")


def processar_csv_especialidades(request):
    if request.method == "POST":
        arquivo = request.FILES.get("file_especialidades")

        if not arquivo.name.endswith(".csv"):
            messages.error(request, "Por favor, envie um arquivo CSV válido.")
            return redirect("importar_especialidades")

        # Salvar o arquivo temporariamente
        file_path = default_storage.save(f"temp/{arquivo.name}", arquivo)

        with open(default_storage.path(file_path), newline='', encoding="utf-8-sig") as csvfile:
            # Usa ponto e vírgula como delimitador
            leitor = csv.DictReader(csvfile, delimiter=";")

            for linha in leitor:
                codigo = linha.get("COD_ESPECIALIDADE", "").strip()
                nome = linha.get("NOME_ESPECIALIDADE", "").strip()

                if codigo and nome:
                    EspecialidadeAghu.objects.get_or_create(
                        cod_especialidade=codigo, nome_especialidade=nome)

        messages.success(request, "Especialidades importadas com sucesso!")
        return redirect("importar_especialidades")

    return render(request, 'upload.html')


def processar_csv_especialidades_procedimentos(request):
    if request.method == "POST":
        arquivo = request.FILES.get("file_especialidade_procedimento")

        if not arquivo.name.endswith(".csv"):
            messages.error(request, "Por favor, envie um arquivo CSV válido.")
            return redirect("importar_especialidades_procedimentos")

        file_path = default_storage.save(f"temp/{arquivo.name}", arquivo)

        with open(default_storage.path(file_path), newline='', encoding="utf-8-sig") as csvfile:
            leitor = csv.DictReader(csvfile, delimiter=";")

            for linha in leitor:
                cod_especialidade = linha.get("cod_especialidade", "").strip()
                nome_especialidade = linha.get("especialidade", "").strip()
                cod_procedimento = linha.get("cod_procedimento", "").strip()
                nome_procedimento = linha.get("nome_procedimento", "").strip()
                situacao_procedimento = linha.get(
                    "situacao_procedimento", "").strip()

                if cod_especialidade and nome_especialidade and cod_procedimento and nome_procedimento:
                    especialidade, _ = EspecialidadeAghu.objects.get_or_create(
                        cod_especialidade=cod_especialidade, nome_especialidade=nome_especialidade
                    )
                    procedimento, _ = ProcedimentoAghu.objects.get_or_create(
                        codigo=cod_procedimento, nome=nome_procedimento
                    )

        messages.success(
            request, "Especialidades e Procedimentos importados com sucesso!")
        return redirect("importar_especialidades_procedimentos")

    return render(request, 'upload.html')
