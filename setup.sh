#!/bin/bash

# =========================================
# Script de Setup Automático - HULW Project
# Para Linux/Mac
# =========================================

echo "🏥 Iniciando configuração do projeto HULW..."
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 1. Verificar se Docker está instalado
echo -e "${YELLOW}1️⃣  Verificando Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "   ${GREEN}✅ Docker encontrado!${NC}"
else
    echo -e "   ${RED}❌ Docker não encontrado. Instale em:${NC}"
    echo -e "      https://docs.docker.com/get-docker/"
    exit 1
fi

# 2. Verificar se Node.js está instalado
echo ""
echo -e "${YELLOW}2️⃣  Verificando Node.js...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "   ${GREEN}✅ Node.js encontrado! ($NODE_VERSION)${NC}"
else
    echo -e "   ${RED}❌ Node.js não encontrado. Instale em:${NC}"
    echo -e "      https://nodejs.org/"
    exit 1
fi

# 3. Criar arquivo .env se não existir
echo ""
echo -e "${YELLOW}3️⃣  Configurando variáveis de ambiente...${NC}"
if [ -f "dotenv_files/.env" ]; then
    echo -e "   ${YELLOW}⚠️  Arquivo .env já existe. Pulando...${NC}"
else
    cp dotenv_files/.env-example dotenv_files/.env
    echo -e "   ${GREEN}✅ Arquivo .env criado!${NC}"
fi

# 4. Instalar dependências Node.js
echo ""
echo -e "${YELLOW}4️⃣  Instalando dependências do Tailwind CSS...${NC}"
npm install
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Dependências instaladas!${NC}"
else
    echo -e "   ${RED}❌ Erro ao instalar dependências${NC}"
    exit 1
fi

# 5. Compilar CSS do Tailwind
echo ""
echo -e "${YELLOW}5️⃣  Compilando CSS do Tailwind...${NC}"
npm run build:css
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ CSS compilado com sucesso!${NC}"
else
    echo -e "   ${RED}❌ Erro ao compilar CSS${NC}"
    exit 1
fi

# 6. Construir e iniciar containers Docker
echo ""
echo -e "${YELLOW}6️⃣  Construindo e iniciando containers Docker...${NC}"
echo -e "   ${CYAN}(Isso pode levar alguns minutos na primeira vez)${NC}"
docker compose up --build -d
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Containers iniciados!${NC}"
else
    echo -e "   ${RED}❌ Erro ao iniciar containers${NC}"
    exit 1
fi

# 7. Aguardar serviços inicializarem
echo ""
echo -e "${YELLOW}7️⃣  Aguardando serviços inicializarem...${NC}"
sleep 10
echo -e "   ${GREEN}✅ Serviços prontos!${NC}"

# 8. Exibir status dos containers
echo ""
echo -e "${YELLOW}8️⃣  Status dos containers:${NC}"
docker compose ps

# Conclusão
echo ""
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}✨ Setup concluído com sucesso! ✨${NC}"
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo ""
echo "📍 Acesse o sistema em:"
echo -e "   ${CYAN}🌐 Consulta Pública:  http://localhost:8050${NC}"
echo -e "   ${CYAN}👥 Portal da Equipe:  http://localhost:8050/portal/login/${NC}"
echo -e "   ${CYAN}🔧 Admin Django:      http://localhost:8050/admin/${NC}"
echo -e "   ${CYAN}📊 API FastAPI:       http://localhost:9000/docs${NC}"
echo ""
echo -e "${YELLOW}💡 Dica: Para criar um superusuário, execute:${NC}"
echo "   docker compose exec djangoapp python manage.py createsuperuser"
echo ""
echo -e "${YELLOW}📝 Para ver os logs em tempo real:${NC}"
echo "   docker compose logs -f"
echo ""
