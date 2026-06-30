import sys
import os
from pathlib import Path

# --- CRÍTICO: Añade la raíz del proyecto al path de Python ---
# Esto asegura que 'from app.xxx import yyy' funcione en Vercel
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Ahora las importaciones deberían funcionar
try:
    from fastapi import FastAPI
    from mangum import Mangum
    from app.routers import sismos
    from app.config import sismos_service  # Necesario para que el router funcione
    print("✅ Todas las importaciones exitosas")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    # Fallback para que la app no muera
    from fastapi import FastAPI, APIRouter
    sismos = APIRouter()
    @sismos.get("/sismos")
    async def fallback():
        return {"error": f"Error de importación: {str(e)}"}
    @sismos.get("/")
    async def root():
        return {"status": "error", "message": "Configuración incompleta"}

# --- Crear la app ---
app = FastAPI(title="SismosVE API en Vercel")

# Incluir el router
app.include_router(sismos.router)

# Endpoint de prueba simple
@app.get("/")
async def home():
    return {
        "status": "online",
        "message": "SismosVE API funcionando en Vercel"
    }
from fastapi.responses import HTMLResponse
from pathlib import Path

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Sirve el frontend index.html"""
    index_path = Path(__file__).parent.parent / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>Error: index.html no encontrado</h1>"
# Handler para Vercel
handler = Mangum(app)
