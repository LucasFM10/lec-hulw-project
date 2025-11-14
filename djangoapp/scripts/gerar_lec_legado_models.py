#!/usr/bin/env python3
"""
Gera lec_legado/models.py a partir do CSV de cabeçalho.
Gera TextField para preservar texto longo e db_column curto+único (hash).
Usage:
    python scripts/generate_lec_models.py /caminho/para/df_lec_final_tratado.csv
"""
import sys, os, csv, unicodedata, re, hashlib

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else '/content/df_lec_final_tratado.csv'
APP_DIR = os.path.join(os.getcwd(), 'lec_legado')
MODELS_FILE = os.path.join(APP_DIR, 'models.py')

def slugify_field(s):
    if s is None:
        return ''
    s = str(s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r'[^0-9a-z_]', '_', s)
    s = re.sub(r'_+', '_', s)
    s = re.sub(r'^(\d)', r'_\1', s)
    s = s.strip('_')
    return s or 'field'

# read header
with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)

# create unique pythonic field names
seen = {}
fields = []
for col in header:
    base = slugify_field(col)
    candidate = base
    i = 1
    while candidate in seen or not candidate:
        candidate = f"{base}_{i}"
        i += 1
    seen[candidate] = col
    fields.append((candidate, col))

os.makedirs(APP_DIR, exist_ok=True)

with open(MODELS_FILE, 'w', encoding='utf-8') as f:
    f.write("from django.db import models\n\n\n")
    f.write("class LecLegado(models.Model):\n")
    f.write("    \"\"\"Modelo gerado automaticamente a partir do CSV - todos os campos como TextField.\n    Use 'db_column' curto+único para evitar limite de 63 chars no PostgreSQL.\n    \"\"\"\n")
    for fname, orig in fields:
        verbose = orig.replace('\"','\\\"')
        # create short unique db_column
        digest = hashlib.sha1(fname.encode()).hexdigest()[:10]
        base_db = fname[:48]
        db_column = f"{base_db}_{digest}"[:63]
        f.write(f'    {fname} = models.TextField(blank=True, null=True, verbose_name="{verbose}", db_column="{db_column}")\n')
    first_field = fields[0][0] if fields else 'id'
    f.write("\n    def __str__(self):\n")
    f.write(f"        return str(self.{first_field})[:120]\n")
    f.write("\n    class Meta:\n")
    f.write("        verbose_name = 'Lec Legado'\n")
    f.write("        verbose_name_plural = 'Lecs Legado'\n")

print("models.py gerado em: ", MODELS_FILE)
print(f"Campos gerados: {len(fields)}")
