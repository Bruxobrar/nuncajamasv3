FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias primero para cachear la capa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del backend (main.py y generators/)
COPY . .

# Exponer el puerto de la API
EXPOSE 8000

# Iniciamos FastAPI con --reload para que tome mis cambios en vivo
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
