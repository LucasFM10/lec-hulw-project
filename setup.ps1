# =========================================
# Script de Setup Automático - HULW Project
# =========================================
# Este script configura automaticamente o projeto para execução

Write-Host "🏥 Iniciando configuração do projeto HULW..." -ForegroundColor Cyan
Write-Host ""

# 1. Verificar se Docker está instalado
Write-Host "1️⃣  Verificando Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    Write-Host "   ✅ Docker encontrado!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker não encontrado. Instale o Docker Desktop:" -ForegroundColor Red
    Write-Host "      https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}

# 2. Verificar se Node.js está instalado
Write-Host ""
Write-Host "2️⃣  Verificando Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "   ✅ Node.js encontrado! ($nodeVersion)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Node.js não encontrado. Instale em:" -ForegroundColor Red
    Write-Host "      https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# 3. Criar arquivo .env se não existir
Write-Host ""
Write-Host "3️⃣  Configurando variáveis de ambiente..." -ForegroundColor Yellow
if (Test-Path "dotenv_files\.env") {
    Write-Host "   ⚠️  Arquivo .env já existe. Pulando..." -ForegroundColor Yellow
} else {
    Copy-Item -Path "dotenv_files\.env-example" -Destination "dotenv_files\.env"
    Write-Host "   ✅ Arquivo .env criado!" -ForegroundColor Green
}

# 4. Instalar dependências Node.js
Write-Host ""
Write-Host "4️⃣  Instalando dependências do Tailwind CSS..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Dependências instaladas!" -ForegroundColor Green
} else {
    Write-Host "   ❌ Erro ao instalar dependências" -ForegroundColor Red
    exit 1
}

# 5. Compilar CSS do Tailwind
Write-Host ""
Write-Host "5️⃣  Compilando CSS do Tailwind..." -ForegroundColor Yellow
npm run build:css
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ CSS compilado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "   ❌ Erro ao compilar CSS" -ForegroundColor Red
    exit 1
}

# 6. Construir e iniciar containers Docker
Write-Host ""
Write-Host "6️⃣  Construindo e iniciando containers Docker..." -ForegroundColor Yellow
Write-Host "   (Isso pode levar alguns minutos na primeira vez)" -ForegroundColor Gray
docker compose up --build -d
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Containers iniciados!" -ForegroundColor Green
} else {
    Write-Host "   ❌ Erro ao iniciar containers" -ForegroundColor Red
    exit 1
}

# 7. Aguardar serviços inicializarem
Write-Host ""
Write-Host "7️⃣  Aguardando serviços inicializarem..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host "   ✅ Serviços prontos!" -ForegroundColor Green

# 8. Exibir status dos containers
Write-Host ""
Write-Host "8️⃣  Status dos containers:" -ForegroundColor Yellow
docker compose ps

# Conclusão
Write-Host ""
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✨ Setup concluído com sucesso! ✨" -ForegroundColor Green
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Acesse o sistema em:" -ForegroundColor White
Write-Host "   🌐 Consulta Pública:  http://localhost:8050" -ForegroundColor Cyan
Write-Host "   👥 Portal da Equipe:  http://localhost:8050/portal/login/" -ForegroundColor Cyan
Write-Host "   🔧 Admin Django:      http://localhost:8050/admin/" -ForegroundColor Cyan
Write-Host "   📊 API FastAPI:       http://localhost:9000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 Dica: Para criar um superusuário, execute:" -ForegroundColor Yellow
Write-Host "   docker compose exec djangoapp python manage.py createsuperuser" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 Para ver os logs em tempo real:" -ForegroundColor Yellow
Write-Host "   docker compose logs -f" -ForegroundColor Gray
Write-Host ""
