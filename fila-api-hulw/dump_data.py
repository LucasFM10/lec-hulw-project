import os
import json
from sqlalchemy import create_engine, text
from app.core.config import settings

# --- CONFIGURAÇÃO ---
# Número de registros a serem exportados de cada tabela
ROW_LIMIT = 300
# Diretório de saída para os arquivos JSON
OUTPUT_DIR = "app/db/mock_data"

# Garante que o diretório de saída exista
os.makedirs(OUTPUT_DIR, exist_ok=True)

def export_data():
    print("Iniciando a exportação de dados do banco...")

    engine = create_engine(str(settings.DATABASE_URL))
    all_data_to_write = {}

    with engine.connect() as conn:
        # 1. Buscar as 100 primeiras especialidades ativas
        print("Buscando até 100 especialidades ativas...")
        especialidades_query = text("""
            SELECT esp.seq AS "COD_ESPECIALIDADE", esp.nome_especialidade AS "NOME_ESPECIALIDADE"
            FROM agh.agh_especialidades esp
            WHERE esp.ind_situacao = 'A'
            ORDER BY esp.seq
            FETCH FIRST 100 ROWS ONLY
        """)
        result_especialidades = conn.execute(especialidades_query)
        especialidades_data = [dict(row._mapping) for row in result_especialidades]
        all_data_to_write["especialidades.json"] = especialidades_data
        print(f"-> {len(especialidades_data)} especialidades ativas encontradas.")

        # 2. Para cada especialidade, buscar até 100 procedimentos associados
        procedimentos_list = []

        procedimentos_query_template = text("""
            SELECT
                phi.seq AS "COD_PROCEDIMENTO",
                phi.descricao AS "PROCEDIMENTO",
                php.esp_seq AS "COD_ESPECIALIDADE_FK"
            FROM agh.aac_proced_hosp_especialidades php
            JOIN agh.fat_proced_hosp_internos phi ON phi.seq = php.phi_seq
            WHERE php.ind_consulta = 'N'
              AND php.esp_seq = :esp_seq
            ORDER BY phi.seq
            FETCH FIRST 100 ROWS ONLY
        """)

        for esp in especialidades_data:
            esp_seq = esp["COD_ESPECIALIDADE"]
            print(f"Buscando procedimentos para especialidade {esp_seq} - {esp['NOME_ESPECIALIDADE']}...")
            result_procedimentos = conn.execute(procedimentos_query_template, {"esp_seq": esp_seq})
            procedimentos_data = [dict(row._mapping) for row in result_procedimentos]
            procedimentos_list.extend(procedimentos_data)
            print(f"-> {len(procedimentos_data)} procedimentos encontrados para especialidade {esp_seq}")

        all_data_to_write["procedimentos.json"] = procedimentos_list

        # 3. Exportar outras tabelas independentes (profissionais, pacientes) como antes
        INDEPENDENT_QUERIES = {
            "profissionais.json": """
                SELECT serv.matricula AS "MATRICULA", pes.nome AS "NOME_PROFISSIONAL", serv.matricula AS "PROF_RESPONSAVEL"
                FROM agh.rap_servidores serv
                LEFT JOIN agh.rap_pessoas_fisicas pes ON pes.codigo = serv.pes_codigo
                WHERE serv.ind_situacao = 'A'
                ORDER BY pes.nome
                FETCH FIRST :limit ROWS ONLY
            """,
            "pacientes.json": """
                SELECT
                    pac.nome AS "NOME_PACIENTE", pac.prontuario AS "PRONTUARIO_PAC",
                    pac.ddd_fone_residencial AS "DDD_FONE_RESIDENCIAL",
                    pac.fone_residencial AS "FONE_RESIDENCIAL",
                    pac.ddd_fone_recado AS "DDD_FONE_RECADO",
                    pac.fone_recado AS "FONE_RECADO"
                FROM agh.aip_pacientes pac
                ORDER BY pac.prontuario
                FETCH FIRST :limit ROWS ONLY
            """
        }

        for filename, query_str in INDEPENDENT_QUERIES.items():
            print(f"Exportando dados para {filename}...")
            query = text(query_str)
            result = conn.execute(query, {"limit": ROW_LIMIT})
            data = [dict(row._mapping) for row in result]
            all_data_to_write[filename] = data
            print(f"-> {len(data)} registros encontrados para {filename}.")

    # 4. Salvar os arquivos JSON
    print("\nSalvando arquivos JSON...")
    for filename, data in all_data_to_write.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"-> Arquivo salvo: {filepath}")

    print("\nExportação concluída com sucesso!")

if __name__ == "__main__":
    export_data()