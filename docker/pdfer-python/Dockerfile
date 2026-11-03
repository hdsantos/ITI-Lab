FROM ubuntu:26.04

WORKDIR /app

# Instalar o Python e as bibliotecas necessárias diretamente via apt
RUN apt-get update && apt-get install -y \
    python3 \
    python3-flask \
    python3-cryptography \
    && rm -rf /var/lib/apt/lists/*

# Copiar o script do servidor
COPY pdfer.py /app/pdfer.py

# Garantir que a pasta store existe
RUN mkdir -p /app/store

EXPOSE 8080

ENTRYPOINT ["python3", "/app/pdfer.py"]
