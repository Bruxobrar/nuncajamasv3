FROM python:3.10-slim

WORKDIR /app

# Dependencias (cache layer)
COPY apps/api/requirements.txt ./apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

# Código
COPY apps/api ./apps/api
COPY apps/portal ./apps/portal
COPY apps/dashboard ./apps/dashboard

WORKDIR /app/apps/api

EXPOSE 8000

# Dev: recarga en caliente
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
