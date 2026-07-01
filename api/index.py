import sys
import os
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi import FastAPI
from mangum import Mangum

# --- CRÍTICO: Añade la raíz del proyecto al path de Python ---
# Esto asegura que 'from app.xxx import yyy' funcione en Vercel
# ✅ FORZANDO RECONSTRUCCIÓN - 2026-07-01 - CAMBIO DE MAGNITUD A 2.0
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# --- Importaciones del proyecto original ---
try:
    from app.routers import sismos
    from app.config import sismos_service  # Necesario para que el router funcione
    print("✅ Todas las importaciones exitosas")
    print("🔥 FORZANDO RECONSTRUCCIÓN - VERSIÓN 2.0")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    # Fallback para que la app no muera
    from fastapi import APIRouter
    sismos = APIRouter()
    @sismos.get("/sismos")
    async def fallback_sismos():
        return {"error": f"Error de importación: {str(e)}"}
    @sismos.get("/sismos/stats")
    async def fallback_stats():
        return {"error": f"Error de importación: {str(e)}"}
    @sismos.get("/sismos/recent")
    async def fallback_recent():
        return {"error": f"Error de importación: {str(e)}"}

# --- Crear la aplicación FastAPI ---
app = FastAPI(
    title="SismosVE API",
    description="API para consultar sismos en Venezuela",
    version="1.0.0"
)

# --- Incluir los routers del proyecto ---
app.include_router(sismos.router)

# --- SERVIR EL FRONTEND (index.html) ---
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Sirve el archivo index.html desde la raíz del proyecto."""
    # Buscar en diferentes ubicaciones posibles
    posibles_rutas = [
        Path(__file__).parent.parent / "index.html",  # Raíz del proyecto
        Path("/vercel/path0/index.html"),             # Ruta en Vercel
        Path("index.html"),                           # Ruta relativa
    ]
    
    for ruta in posibles_rutas:
        if ruta.exists():
            contenido = ruta.read_text(encoding='utf-8')
            return contenido
    
    # Si no se encuentra, devolver un mensaje de fallback
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SismosVE - Monitoreo Sísmico</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; text-align: center; background: #0d0d1a; color: #eee; }
            h1 { color: #e94560; }
            a { color: #4CAF50; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>🌋 SismosVE</h1>
        <p>API funcionando correctamente</p>
        <p><a href="/api/sismos">📊 Ver datos de sismos (JSON)</a></p>
        <p><a href="/api/sismos/stats">📈 Ver estadísticas</a></p>
        <p><small>El archivo index.html no se encontró en el despliegue.</small></p>
    </body>
    </html>
    """

# --- ENDPOINT DE PRUEBA ADICIONAL ---
@app.get("/health")
async def health_check():
    """Endpoint para verificar que la API está funcionando."""
    return {
        "status": "online",
        "message": "SismosVE API funcionando correctamente"
    }

# --- Handler para Vercel ---
handler = Mangum(app)

# --- Para ejecutar localmente ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
