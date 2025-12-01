# 🧹 Guia: Como Limpar a Tabela da Fila Cirúrgica

Este guia explica como apagar todos os registros da **Lista de Espera Cirúrgica** (fila atual) para remigrar os dados do LEC Legado com as datas corretas.

---

## ⚠️ **ATENÇÃO: Procedimento Irreversível**

- Esta operação **apaga permanentemente** todos os registros da fila.
- Certifique-se de que tem um backup atualizado antes de prosseguir.
- Os dados do **LEC Legado não serão afetados** (apenas a fila atual).

---

## 📋 **Passo a Passo**

### **Opção 1: Via Django Shell (Recomendado)**

#### 1. Acesse o container Django
```powershell
docker compose exec djangoapp python manage.py shell
```

#### 2. Execute o comando de limpeza
```python
from fila_cirurgica.models import ListaEsperaCirurgica

# Conta quantos registros existem
total = ListaEsperaCirurgica.objects.count()
print(f"🔢 Total de registros na fila: {total}")

# APAGA TODOS OS REGISTROS (inclusive histórico)
ListaEsperaCirurgica.objects.all().delete()

# Verifica se foi limpo
restante = ListaEsperaCirurgica.objects.count()
print(f"✅ Registros restantes: {restante}")
print(f"🗑️  {total} registros foram apagados com sucesso!")
```

#### 3. Saia do shell
```python
exit()
```

---

### **Opção 2: Via SQL Direto (Mais Rápido)**

#### 1. Acesse o container PostgreSQL
```powershell
docker compose exec postgres psql -U postgres -d lec_hulw
```

#### 2. Execute os comandos SQL
```sql
-- Conta registros antes de apagar
SELECT COUNT(*) AS total_registros FROM fila_cirurgica_listaesperacirurgica;

-- APAGA TODOS OS REGISTROS DA FILA
TRUNCATE TABLE fila_cirurgica_listaesperacirurgica CASCADE;

-- APAGA O HISTÓRICO (django-simple-history)
TRUNCATE TABLE fila_cirurgica_historicallistaesperacirurgica CASCADE;

-- Reseta o contador de IDs (opcional, reinicia em 1)
ALTER SEQUENCE fila_cirurgica_listaesperacirurgica_id_seq RESTART WITH 1;

-- Verifica se foi limpo
SELECT COUNT(*) AS registros_restantes FROM fila_cirurgica_listaesperacirurgica;
```

#### 3. Saia do PostgreSQL
```sql
\q
```

---

### **Opção 3: Via Django Admin (Interface Gráfica)**

⚠️ **Não recomendado para muitos registros** (pode demorar muito e dar timeout)

1. Acesse: `http://localhost:8050/admin/fila_cirurgica/listaesperacirurgica/`
2. Marque a checkbox "Selecionar todos os X registros"
3. No dropdown "Ação", escolha **"Excluir registros selecionados"**
4. Clique em **"Ir"**
5. Confirme a exclusão na próxima tela

---

## 🔄 **Depois da Limpeza: Remigrar com Datas Corretas**

### 1. Instale a nova dependência
```powershell
docker compose exec djangoapp pip install python-dateutil
```

### 2. Reinicie o container
```powershell
docker compose restart djangoapp
```

### 3. Limpe os status de migração do LEC Legado (opcional)
```powershell
docker compose exec djangoapp python manage.py shell
```

```python
from lec_legado.models import LecLegado

# Reseta todos os registros para "pendente"
LecLegado.objects.update(
    status_migracao='pendente',
    mensagem_migracao='',
    id_fila_migrada=None,
    data_migracao=None
)

print("✅ Status de migração resetados! Todos os registros estão pendentes novamente.")
exit()
```

### 4. Execute a migração via interface web
1. Acesse: `http://localhost:8050/portal/lec-legado/`
2. Clique em **"Migrar Todos"**
3. Confirme a operação
4. Aguarde o processamento (pode demorar alguns minutos)

---

## 🧪 **Verificação Após Migração**

### Verifique as datas migradas
```powershell
docker compose exec djangoapp python manage.py shell
```

```python
from fila_cirurgica.models import ListaEsperaCirurgica
from django.db.models import Min, Max

# Estatísticas das datas
stats = ListaEsperaCirurgica.objects.aggregate(
    primeira=Min('data_entrada'),
    ultima=Max('data_entrada'),
    total=Count('id')
)

print(f"📊 Estatísticas de Migração:")
print(f"   Total de registros: {stats['total']}")
print(f"   Data mais antiga: {stats['primeira']}")
print(f"   Data mais recente: {stats['ultima']}")

# Mostra os 5 primeiros registros
print("\n📋 Primeiros 5 registros:")
for entrada in ListaEsperaCirurgica.objects.all()[:5]:
    print(f"   ID: {entrada.id} | Paciente: {entrada.paciente.nome} | Data: {entrada.data_entrada}")

exit()
```

---

## 🆘 **Em Caso de Erro**

### Erro: "Cannot delete protected foreign key"
```powershell
# Apaga primeiro as referências do LEC Legado
docker compose exec djangoapp python manage.py shell
```

```python
from lec_legado.models import LecLegado

# Remove as referências à fila
LecLegado.objects.update(id_fila_migrada=None)
print("✅ Referências removidas!")
exit()
```

Depois execute a limpeza novamente.

---

### Erro: "dateutil module not found"
```powershell
# Instala a dependência manualmente
docker compose exec djangoapp pip install python-dateutil

# Ou rebuild o container
docker compose down
docker compose build --no-cache djangoapp
docker compose up -d
```

---

## 📝 **Checklist Final**

- [ ] Backup do banco de dados criado
- [ ] Fila cirúrgica limpa (0 registros)
- [ ] python-dateutil instalado
- [ ] Container Django reiniciado
- [ ] Status de migração do LEC Legado resetados (opcional)
- [ ] Migração executada via web
- [ ] Datas verificadas e corretas
- [ ] Estatísticas conferidas

---

## 🎯 **Resultado Esperado**

Após seguir este guia:

✅ Todos os registros da fila foram apagados  
✅ LEC Legado migrado novamente com datas históricas corretas  
✅ Cada entrada tem `data_entrada` preservada do sistema legado  
✅ Mensagens de sucesso mostram a data migrada: `"Data entrada: 15/03/2023 10:30"`

---

## 📞 **Suporte**

Se encontrar problemas:
1. Verifique os logs: `docker compose logs djangoapp`
2. Confira o status no admin: `/admin/fila_cirurgica/listaesperacirurgica/`
3. Execute comandos SQL diretamente para diagnóstico
