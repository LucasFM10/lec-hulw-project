# 🚀 Guia de Início Rápido - HULW Project

## Opção 1: Setup Automático (Recomendado)

### Windows (PowerShell)
```powershell
.\setup.ps1
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

---

## Opção 2: Setup Manual

### Passo 1: Clone o repositório
```bash
git clone https://github.com/LucasFM10/lec-hulw-project.git
cd lec-hulw-project
```

### Passo 2: Configure o arquivo .env

**Windows:**
```powershell
Copy-Item -Path "dotenv_files\.env-example" -Destination "dotenv_files\.env"
```

**Linux/Mac:**
```bash
cp dotenv_files/.env-example dotenv_files/.env
```

### Passo 3: Compile o Tailwind CSS
```bash
npm install
npm run build:css
```

### Passo 4: Inicie o Docker
```bash
docker compose up -d
```

### Passo 5: Aguarde ~15 segundos e acesse
- http://localhost:8050

---

## 📍 URLs do Sistema

| Página | URL |
|--------|-----|
| Consulta Pública | http://localhost:8050 |
| Login da Equipe | http://localhost:8050/portal/login/ |
| Admin Django | http://localhost:8050/admin/ |
| API Docs | http://localhost:9000/docs |

---

## 🔑 Criar Superusuário (Admin)

```bash
docker compose exec djangoapp python manage.py createsuperuser
```

---

## ⚠️ Problemas Comuns

### Containers não iniciam
```bash
docker compose down -v
docker compose up --build -d
```

### CSS não carrega
```bash
npm run build:css
docker compose restart djangoapp
```

### Erro de permissão no Linux/Mac
```bash
chmod +x setup.sh
chmod +x scripts/commands.sh
```

---

## 📝 Comandos Úteis

```bash
# Ver logs
docker compose logs -f

# Parar tudo
docker compose down

# Reiniciar um serviço
docker compose restart djangoapp

# Acessar container Django
docker compose exec djangoapp sh
```

---

## 📚 Documentação Completa

Leia o [README.md](README.md) para mais detalhes.
