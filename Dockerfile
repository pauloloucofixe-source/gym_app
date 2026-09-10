FROM python:3.9-slim

# Instalar dependências do sistema e pacotes pesados já compilados para ARM (evita compilação no Pi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-numpy \
    python3-pandas \
    python3-matplotlib \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar apenas o Flask (o resto já vem pré-instalado pelo apt-get)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

EXPOSE 5004

CMD ["python", "app.py"]
