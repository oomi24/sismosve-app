FROM python:3.12-slim

WORKDIR /app

# Copiar requirements.txt y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
