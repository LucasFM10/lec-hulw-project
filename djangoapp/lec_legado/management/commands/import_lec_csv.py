import csv, unicodedata, re, os
from django.core.management.base import BaseCommand
from lec_legado.models import LecLegado

def normalize(s):
    if s is None:
        return ''
    s = unicodedata.normalize('NFKD', str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

class Command(BaseCommand):
    help = "Importa CSV legado (map. inteligente). Use --replace para limpar antes. By default does NOT truncate."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Caminho para o CSV tratado")
        parser.add_argument("--replace", action="store_true", help="Apaga registros existentes antes do import.")
        parser.add_argument("--max-len", type=int, default=0, help="Se >0: trunca valores acima deste comprimento e registra truncations.")

    def handle(self, *args, **options):
        path = options["csv_path"]
        replace = options["replace"]
        max_len = int(options["max_len"])

        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado: {path}"))
            return

        if replace:
            LecLegado.objects.all().delete()
            self.stdout.write(self.style.WARNING("Tabela LecLegado esvaziada (--replace)."))

        # build mapping: normalized -> model_field.name
        field_map = {}
        for field in LecLegado._meta.fields:
            if field.name == "id":
                continue
            field_map[normalize(field.name)] = field.name
            if field.db_column:
                field_map[normalize(field.db_column)] = field.name
            if getattr(field, 'verbose_name', None):
                field_map[normalize(str(field.verbose_name))] = field.name

        self.stdout.write(f"Detectados {len(field_map)} mapeamentos no modelo (inclui db_column/verbose_name).")

        created = 0
        skipped = 0
        truncations = []

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                obj_data = {}
                for key, value in row.items():
                    if value is None:
                        continue
                    norm_key = normalize(key)
                    if norm_key in field_map:
                        mf = field_map[norm_key]
                        val = value
                        if max_len > 0 and isinstance(val, str) and len(val) > max_len:
                            truncations.append((i, key, mf, len(val), val[:200]))
                            val = val[:max_len]
                        obj_data[mf] = val
                try:
                    LecLegado.objects.create(**obj_data)
                    created += 1
                except Exception as e:
                    skipped += 1
                    self.stderr.write(f"Erro linha {i}: {e}")

        if truncations:
            import pandas as pd
            df = pd.DataFrame(truncations, columns=['linha','csv_col','model_field','orig_len','preview'])
            out = '/tmp/truncations_import_lec.csv'
            df.to_csv(out, index=False, encoding='utf-8-sig')
            self.stdout.write(self.style.WARNING(f"Truncations recorded: {len(truncations)} rows. Saved to {out}"))

        self.stdout.write(self.style.SUCCESS(f"Import finalizado. Criados: {created}. Ignorados por erro: {skipped}"))
