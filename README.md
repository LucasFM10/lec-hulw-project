# 🏥 Sistema de Gestão de Fila Cirúrgica HULW

Sistema web para gerenciamento da fila cirúrgica do Hospital Universitário Lauro Wanderley (HULW), desenvolvido com Django, FastAPI e PostgreSQL.

## 📋 Índice

- [Pré-requisitos](#-pré-requisitos)
- [Instalação Rápida](#-instalação-rápida)
- [Configuração Manual](#️-configuração-manual)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Desenvolvimento](#-desenvolvimento)
- [Acesso ao Sistema](#-acesso-ao-sistema)
- [Comandos Úteis](#-comandos-úteis)
- [Tecnologias](#-tecnologias)

---

## ⚙️ Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Docker Desktop** (Windows/Mac) ou **Docker + Docker Compose** (Linux)
  - [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Node.js 18+** (para compilar o Tailwind CSS)
  - [Download Node.js](https://nodejs.org/)
- **Git**
  - [Download Git](https://git-scm.com/)

---

## 🚀 Instalação Rápida

### 1️⃣ Clone o repositório

```bash
git clone https://github.com/LucasFM10/lec-hulw-project.git
cd lec-hulw-project
```

### 2️⃣ Configure as variáveis de ambiente

**Windows (PowerShell):**
```powershell
Copy-Item -Path "dotenv_files\.env-example" -Destination "dotenv_files\.env"
```

**Linux/Mac:**
```bash
cp dotenv_files/.env-example dotenv_files/.env
```

> ✅ O arquivo `.env` já vem com configurações prontas para Docker!

### 3️⃣ Compile o CSS do Tailwind

```bash
npm install
npm run build:css
```

### 4️⃣ Inicie os containers Docker

```bash
docker compose up -d
```

Aguarde alguns segundos para os serviços iniciarem (especialmente o PostgreSQL e as migrações do Django).

### 5️⃣ Pronto! ✨

Acesse o sistema em:
- **Consulta Pública**: http://localhost:8050
- **Portal da Equipe**: http://localhost:8050/portal/login/
- **Admin Django**: http://localhost:8050/admin/
- **API FastAPI (Docs)**: http://localhost:9000/docs

---

## 🛠️ Configuração Manual

### Arquivo `.env` (opcional - apenas se quiser personalizar)

Edite o arquivo `dotenv_files/.env` para alterar:

```bash
# Banco de Dados
POSTGRES_DB="hulw_db"              # Nome do banco
POSTGRES_USER="hulw_user"          # Usuário do banco
POSTGRES_PASSWORD="sua_senha_aqui" # Senha do banco

# Django
SECRET_KEY="sua-chave-secreta"     # Gere em: https://djecrety.ir/
DEBUG="1"                          # 1=Desenvolvimento, 0=Produção
```

### Criar superusuário Django (para acessar /admin/)

```bash
docker compose exec djangoapp python manage.py createsuperuser
```

---

## 📁 Estrutura do Projeto

```
lec-hulw-project/
├── djangoapp/              # Aplicação Django principal
│   ├── aih/                # App: Autorização de Internação Hospitalar
│   ├── externo/            # App: Consulta pública (sem login)
│   ├── fila_cirurgica/     # App: Gestão da fila cirúrgica
│   ├── portal/             # App: Portal interno da equipe
│   ├── gestor_fila_hulw/   # Configurações Django
│   └── manage.py
├── fila-api-hulw/          # API FastAPI (backend auxiliar)
├── dotenv_files/
│   └── .env-example        # Template de variáveis de ambiente
├── docker-compose.yml      # Orquestração dos containers
├── Dockerfile              # Imagem Docker do Django
├── package.json            # Dependências Node.js (Tailwind)
├── tailwind.config.js      # Configuração Tailwind CSS
└── README.md
```

---

## 💻 Desenvolvimento

### Modo Watch do Tailwind (recompilação automática do CSS)

Durante o desenvolvimento, para recompilar automaticamente o CSS ao editar arquivos:

```bash
npm run watch:css
```

Ou manualmente:

```bash
npm run build:css
```

### Ver logs em tempo real

```bash
# Todos os serviços
docker compose logs -f

# Apenas Django
docker compose logs -f djangoapp

# Apenas API FastAPI
docker compose logs -f fila_api
```

### Executar comandos Django

```bash
# Migrations
docker compose exec djangoapp python manage.py makemigrations
docker compose exec djangoapp python manage.py migrate

# Coletar arquivos estáticos
docker compose exec djangoapp python manage.py collectstatic --noinput

# Shell Django
docker compose exec djangoapp python manage.py shell
```

### Acessar o container

```bash
docker compose exec djangoapp sh
```

---

## 🌐 Acesso ao Sistema

### URLs Principais

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Página Inicial** | http://localhost:8050 | Redireciona para consulta pública |
| **Consulta Pública** | http://localhost:8050/externo/consulta-posicao | Consultar posição na fila (sem login) |
| **Portal da Equipe** | http://localhost:8050/portal/login/ | Login para equipe médica |
| **Admin Django** | http://localhost:8050/admin/ | Painel administrativo |
| **API FastAPI** | http://localhost:9000/docs | Documentação interativa da API |

### Usuários Padrão

Por padrão, não há usuários criados. Para criar o primeiro usuário admin:

```bash
docker compose exec djangoapp python manage.py createsuperuser
```

Siga as instruções para criar login e senha.

---

## 🎯 Comandos Úteis

### Gerenciamento de Containers

```bash
# Iniciar todos os serviços
docker compose up -d

# Parar todos os serviços
docker compose down

# Parar e remover volumes (limpa banco de dados)
docker compose down -v

# Reconstruir as imagens
docker compose build

# Reconstruir e iniciar
docker compose up --build -d

# Ver status dos containers
docker compose ps

# Reiniciar um serviço específico
docker compose restart djangoapp
```

### Limpeza

```bash
# Remover containers, volumes e imagens antigas
docker compose down -v --rmi all

# Reconstruir do zero
docker compose build --no-cache
docker compose up -d
```

---

## 🛠 Tecnologias

### Backend
- **Django 5.2** - Framework web principal
- **FastAPI** - API auxiliar de alta performance
- **PostgreSQL 16** - Banco de dados relacional
- **WhiteNoise** - Servidor de arquivos estáticos

### Frontend
- **Tailwind CSS 3.4** - Framework CSS utilitário
- **Alpine.js** - Framework JavaScript leve (se aplicável)

### DevOps
- **Docker & Docker Compose** - Containerização
- **Gunicorn** - Servidor WSGI (produção)
- **Uvicorn** - Servidor ASGI para FastAPI

---

## 📝 Observações Importantes

### 1. Line Endings (Windows)

O arquivo `scripts/commands.sh` deve ter line endings Unix (LF), não Windows (CRLF). 
Isso já está configurado no `.gitattributes`, mas se tiver problemas, converta manualmente:

```powershell
# Windows PowerShell
$content = Get-Content -Path "scripts\commands.sh" -Raw
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText("$PWD\scripts\commands.sh", $content, [System.Text.UTF8Encoding]::new($false))
```

### 2. Arquivos Estáticos

O Django usa **WhiteNoise** para servir arquivos estáticos em produção. O CSS compilado pelo Tailwind é automaticamente servido após o `collectstatic`.

### 3. Dados Mock vs. Banco Real

Por padrão, a API FastAPI usa dados mockados (`USE_MOCK_DATA="true"`).
Para usar o banco PostgreSQL real, altere no `.env`:

```bash
USE_MOCK_DATA="false"
```

---

## 🤝 Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto é propriedade do Hospital Universitário Lauro Wanderley (HULW).

---

## 👥 Autores

- **Lucas Fernandes** - Desenvolvedor Principal - [LucasFM10](https://github.com/LucasFM10)

---

## 📞 Suporte

Em caso de problemas, abra uma [issue no GitHub](https://github.com/LucasFM10/lec-hulw-project/issues).
