import sys
import os
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi import FastAPI
from mangum import Mangum

# --- CRÍTICO: Añade la raíz del proyecto al path de Python ---
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# --- Importaciones del proyecto original ---
try:
    from app.routers import sismos
    from app.config import sismos_service
    print("✅ Todas las importaciones exitosas")
    print("🔥 FORZANDO RECONSTRUCCIÓN - VERSIÓN 2.0")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
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

# --- SERVIR EL FRONTEND ---
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Sirve el archivo index.html desde la raíz del proyecto."""
    # Buscar en diferentes ubicaciones
    posibles_rutas = [
        Path("/opt/render/project/src/index.html"),  # Render
        Path("/app/index.html"),  # Render (alternativo)
        Path(__file__).parent.parent / "index.html",  # Local
        Path("index.html"),  # CWD
    ]
    
    for ruta in posibles_rutas:
        if ruta.exists():
            contenido = ruta.read_text(encoding='utf-8')
            print(f"✅ Sirviendo frontend desde: {ruta}")
            return contenido
    
    print("❌ No se encontró index.html en ninguna ruta")
    return """
    <html>
        <head><title>SismosVE</title></head>
        <body>
            <h1>🌋 SismosVE</h1>
            <p>API funcionando correctamente</p>
            <p><a href="/api/sismos">📊 Ver datos de sismos (JSON)</a></p>
            <p><a href="/api/sismos/stats">📈 Ver estadísticas</a></p>
        </body>
    </html>
    """

# --- ENDPOINT DE PRUEBA ---
@app.get("/health")
async def health_check():
    return {"status": "online", "message": "SismosVE API funcionando correctamente"}

# --- Handler para Vercel ---
handler = Mangum(app)

# --- Para ejecutar localmente ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
