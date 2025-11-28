import json
import sys
from pathlib import Path

def remove_duplicates(json_path: str, key_field: str, output_path: str = None):
    """
    Remove duplicatas de um JSON baseado em um atributo (key_field).
    
    Args:
        json_path (str): Caminho do arquivo JSON de entrada.
        key_field (str): Nome do campo que será usado como chave primária.
        output_path (str, opcional): Caminho do arquivo JSON de saída. 
                                     Se None, sobrescreve o arquivo original.
    """
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"Arquivo {json_path} não encontrado.")

    # Carregar dados
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("O JSON precisa ser uma lista de objetos (array).")

    seen = set()
    unique_data = []
    for item in data:
        key_value = item.get(key_field)
        if key_value not in seen:
            seen.add(key_value)
            unique_data.append(item)

    # Caminho de saída
    output_file = Path(output_path) if output_path else json_file

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique_data, f, indent=2, ensure_ascii=False)

    print(f"✔ JSON processado com sucesso. Salvo em {output_file}")


# Exemplo de uso via terminal:
# python dedup_json.py pacientes.json prontuario pacientes_dedup.json
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python dedup_json.py <arquivo.json> <campo_chave> [arquivo_saida.json]")
    else:
        input_file = sys.argv[1]
        key_field = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        remove_duplicates(input_file, key_field, output_file)
