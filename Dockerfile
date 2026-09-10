FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da app
COPY . .

# Expor a porta que escolheste
EXPOSE 5004

# Arrancar com a aplicação
CMD ["python", "app.py"]