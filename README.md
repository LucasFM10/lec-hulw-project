## Projeto LEC HULW

### Ambiente Docker + Tailwind

Foi adicionada uma etapa de build para Tailwind CSS usando multi-stage no Docker.

Arquivos principais:
- `Dockerfile` (estágio `tailwind-build` + estágio Django)
- `docker-compose.yml` (serviço opcional `tailwind` em modo watch, perfil `dev`)
- `package.json`, `tailwind.config.js`, `postcss.config.js`
- `djangoapp/portal/static/src/styles.css` (fonte Tailwind)
- Saída compilada: `djangoapp/portal/static/dist/main.css` (referenciada no template como `{% static 'dist/main.css' %}`)

### Fluxos de uso

Produção (gera CSS durante build):
```bash
docker compose build
docker compose up -d
```

Desenvolvimento com recompilação automática do CSS (watch):
```bash
docker compose --profile dev up tailwind -d
```
O serviço `tailwind` observa alterações em templates e no arquivo `styles.css` e regenera `static/dist/main.css`.

### Comandos npm diretos (fora do Docker, opcional)
Instalar dependências:
```bash
npm ci
```
Build manual:
```bash
npm run build:css
```
Watch local:
```bash
npm run watch:css
```

### Observação
WhiteNoise servirá os arquivos compilados em produção após `collectstatic`.
