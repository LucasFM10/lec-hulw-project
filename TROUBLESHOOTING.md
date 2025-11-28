# 🔧 Guia de Solução de Problemas - HULW Project

## 🐛 Problemas Comuns e Soluções

### 1. ❌ Erro: "env file not found"

**Problema:** O arquivo `.env` não foi criado.

**Solução:**
```bash
# Windows
Copy-Item -Path "dotenv_files\.env-example" -Destination "dotenv_files\.env"

# Linux/Mac
cp dotenv_files/.env-example dotenv_files/.env
```

---

### 2. ❌ CSS não carrega / Página sem estilo

**Problema:** O Tailwind CSS não foi compilado.

**Solução:**
```bash
npm install
npm run build:css
docker compose restart djangoapp
docker compose exec djangoapp python manage.py collectstatic --noinput
```

---

### 3. ❌ Page Not Found ao clicar em "Sou da equipe"

**Problema:** URLs de autenticação não configuradas.

**Solução:**
Verifique se o arquivo `djangoapp/gestor_fila_hulw/settings.py` contém:
```python
LOGIN_URL = "/portal/login/"
LOGIN_REDIRECT_URL = "/portal/fila/"
LOGOUT_REDIRECT_URL = "/externo/consulta-posicao"
```

Se não tiver, adicione essas linhas e reinicie:
```bash
docker compose restart djangoapp
```

---

### 4. ❌ Containers não iniciam

**Problema:** Conflito de portas ou volumes corrompidos.

**Solução:**
```bash
# Parar tudo e limpar volumes
docker compose down -v

# Reconstruir do zero
docker compose build --no-cache
docker compose up -d
```

---

### 5. ❌ Django não conecta ao PostgreSQL

**Problema:** Configuração incorreta do host do banco.

**Solução:**
Verifique o arquivo `dotenv_files/.env`:
```bash
POSTGRES_HOST="psql"  # Nome do serviço no Docker Compose
```

**NÃO use** `localhost` quando rodar com Docker Compose.

---

### 6. ❌ Erro: "Password authentication failed"

**Problema:** Credenciais do banco não coincidem.

**Solução:**
```bash
# Limpar volumes antigos
docker compose down -v

# Verificar se .env tem as mesmas credenciais
# POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

# Recriar containers
docker compose up -d
```

---

### 7. ❌ Erro: "exec /scripts/commands.sh: no such file"

**Problema:** Line endings do Windows (CRLF) em vez de Unix (LF).

**Solução (Windows PowerShell):**
```powershell
$content = Get-Content -Path "scripts\commands.sh" -Raw
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText("$PWD\scripts\commands.sh", $content, [System.Text.UTF8Encoding]::new($false))

docker compose down
docker compose up --build -d
```

**Solução (Linux/Mac):**
```bash
dos2unix scripts/commands.sh
docker compose down
docker compose up --build -d
```

---

### 8. ❌ Porta 8050 ou 9000 já em uso

**Problema:** Outro serviço está usando a porta.

**Solução:**
```bash
# Ver o que está usando a porta 8050
netstat -ano | findstr :8050

# Parar o processo ou alterar a porta no docker-compose.yml
# Altere "8050:8050" para "8080:8050" por exemplo
```

---

### 9. ❌ Admin Django não existe

**Problema:** Nenhum superusuário foi criado.

**Solução:**
```bash
docker compose exec djangoapp python manage.py createsuperuser

# Siga as instruções para criar usuário e senha
```

---

### 10. ❌ Migrações não aplicadas

**Problema:** Banco de dados não está atualizado.

**Solução:**
```bash
docker compose exec djangoapp python manage.py makemigrations
docker compose exec djangoapp python manage.py migrate
docker compose restart djangoapp
```

---

## 🔍 Comandos de Diagnóstico

### Ver logs de todos os serviços
```bash
docker compose logs -f
```

### Ver logs apenas do Django
```bash
docker compose logs -f djangoapp
```

### Ver logs apenas da API
```bash
docker compose logs -f fila_api
```

### Ver logs do PostgreSQL
```bash
docker compose logs -f psql
```

### Verificar status dos containers
```bash
docker compose ps
```

### Acessar container Django para debug
```bash
docker compose exec djangoapp sh

# Dentro do container:
python manage.py shell
python manage.py check
ls -la /data/web/static/
```

### Verificar conectividade do banco
```bash
docker compose exec djangoapp python manage.py dbshell
```

---

## 🧹 Limpeza Completa (Reset)

Se nada funcionar, faça uma limpeza completa:

```bash
# 1. Parar e remover tudo
docker compose down -v --rmi all

# 2. Remover node_modules
rm -rf node_modules
rm -rf djangoapp/portal/static/dist

# 3. Reconfigurar .env
rm dotenv_files/.env
cp dotenv_files/.env-example dotenv_files/.env

# 4. Reinstalar tudo
npm install
npm run build:css

# 5. Reconstruir do zero
docker compose build --no-cache
docker compose up -d
```

---

## 📞 Suporte

Se o problema persistir:

1. Verifique os logs: `docker compose logs`
2. Abra uma issue no GitHub com:
   - Descrição do erro
   - Logs relevantes
   - Sistema operacional
   - Versão do Docker e Node.js

**GitHub Issues:** https://github.com/LucasFM10/lec-hulw-project/issues

---

## ✅ Checklist de Verificação

Antes de reportar um problema, verifique:

- [ ] Docker está instalado e rodando
- [ ] Node.js está instalado (versão 18+)
- [ ] Arquivo `.env` existe em `dotenv_files/.env`
- [ ] CSS foi compilado (`npm run build:css`)
- [ ] Containers estão rodando (`docker compose ps`)
- [ ] Portas 8050 e 9000 estão livres
- [ ] Aguardou pelo menos 15 segundos após iniciar containers
- [ ] Verificou os logs (`docker compose logs`)

---

## 🆘 Comandos de Emergência

### Reset rápido
```bash
docker compose restart
```

### Reset médio
```bash
docker compose down
docker compose up -d
```

### Reset completo
```bash
docker compose down -v
docker compose up --build -d
```

### Reset nuclear (remove tudo e recria)
```bash
docker compose down -v --rmi all --remove-orphans
docker system prune -a --volumes -f
docker compose up --build -d
```

⚠️ **Atenção:** O reset nuclear remove TODOS os dados, incluindo o banco de dados!
