FROM python:3.9-slim

# Dependências mínimas do sistema (numpy/pandas/matplotlib já têm wheels ARM64 oficiais no PyPI,
# por isso não é preciso instalá-los via apt - o pip trata disso sem compilar nada)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

EXPOSE 5004

CMD ["python", "app.py"]
