FROM python:3.11.14-alpine3.22
LABEL maintainer="lucasfm.py@gmail.com"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências em um virtualenv
COPY requirements.txt /app/requirements.txt
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r /app/requirements.txt

ENV PATH="/venv/bin:$PATH"

# Copia o código da API
COPY app /app/app

# Expondo a porta interna usada pelo Uvicorn
EXPOSE 9000

# Comando para subir a FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
