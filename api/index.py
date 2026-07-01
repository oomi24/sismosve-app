import sys
import os
import logging
print("🚀 INICIANDO api/index.py - VERSIÓN CON USGS 2.0")
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from mangum import Mangum
import requests
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Añadir la raíz del proyecto al path ---
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# --- Crear la aplicación FastAPI ---
app = FastAPI(title="SismosVE API")

# --- ENDPOINT: SISMOS DESDE USGS ---
@app.get("/api/sismos")
async def get_sismos():
    """Obtiene sismos de la API de USGS con magnitud >= 2.0"""
    try:
        print("🔍 Entrando a get_sismos...")
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        params = {
            "format": "geojson",
            "starttime": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "minmagnitude": 2.0,
            "orderby": "time",
            "limit": 100,
            "minlatitude": 0.0,
            "maxlatitude": 15.0,
            "minlongitude": -75.0,
            "maxlongitude": -60.0,
        }
        print(f"📤 Parámetros: {params}")
        response = requests.get(url, params=params, timeout=15)
        print(f"📥 Código de respuesta: {response.status_code}")
        data = response.json()
        print(f"📊 Sismos encontrados: {len(data.get('features', []))}")
        
        # Si no hay sismos, devolver un error visible
        if not data.get('features'):
            print("❌ No se encontraron sismos")
            return {"type": "sismos", "features": [], "error": "No se encontraron sismos"}
        
        # Transformar datos
        features = []
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [0, 0, 0])
            time_ms = props.get('time', 0)
            if time_ms > 0:
                date_time = datetime.fromtimestamp(time_ms / 1000)
                fecha_str = date_time.strftime("%d-%m-%Y")
                hora_str = date_time.strftime("%H:%M")
            else:
                fecha_str = "N/D"
                hora_str = "N/D"
            mag = props.get('mag', 0)
            features.append({
                "type": "Sismo",
                "geometry": {
                    "type": "Point",
                    "coordinates": [coords[0], coords[1]],
                    "marcador": "marker"
                },
                "properties": {
                    "depth": f"{coords[2]:.1f} km" if coords[2] else "N/D",
                    "value": f"{mag:.1f}",
                    "addressFormatted": props.get('place', 'Ubicación desconocida'),
                    "time": hora_str,
                    "country": "Venezuela",
                    "date": fecha_str,
                    "lat": str(coords[1]) if coords[1] else "0",
                    "long": str(coords[0]) if coords[0] else "0"
                }
            })
        print(f"✅ Features transformados: {len(features)}")
        return {"type": "sismos", "features": features}
    except Exception as e:
        print(f"❌ Error en get_sismos: {e}")
        import traceback
        traceback.print_exc()
        return {"type": "sismos", "features": [], "error": str(e)}
# --- ENDPOINT: ESTADÍSTICAS ---
@app.get("/api/sismos/stats")
async def get_stats():
    """Obtiene estadísticas de los sismos"""
    try:
        logger.info("📊 Calculando estadísticas...")
        sismos_data = await get_sismos()
        features = sismos_data.get('features', [])
        if not features:
            logger.warning("⚠️ No hay sismos para calcular estadísticas")
            return {"total_sismos": 0, "magnitud_minima": 0, "magnitud_maxima": 0, "magnitud_promedio": 0}
        magnitudes = []
        for f in features:
            try:
                mag = float(f['properties']['value'])
                magnitudes.append(mag)
            except:
                pass
        if not magnitudes:
            return {"total_sismos": 0, "magnitud_minima": 0, "magnitud_maxima": 0, "magnitud_promedio": 0}
        return {
            "total_sismos": len(magnitudes),
            "magnitud_minima": min(magnitudes),
            "magnitud_maxima": max(magnitudes),
            "magnitud_promedio": sum(magnitudes) / len(magnitudes),
            "ultimo_sismo": features[0] if features else None,
            "ultima_actualizacion": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error en /api/sismos/stats: {e}")
        import traceback
        traceback.print_exc()
        return {"total_sismos": 0, "magnitud_minima": 0, "magnitud_maxima": 0, "magnitud_promedio": 0}

# --- SERVIR EL FRONTEND ---
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    posibles_rutas = [
        Path("/opt/render/project/src/index.html"),
        Path("/app/index.html"),
        Path(__file__).parent.parent / "index.html",
        Path("index.html"),
    ]
    for ruta in posibles_rutas:
        if ruta.exists():
            return ruta.read_text(encoding='utf-8')
    return "<h1>🌋 SismosVE</h1><p>API funcionando</p>"

# --- HEALTH CHECK ---
@app.get("/health")
async def health():
    return {"status": "online", "message": "SismosVE API"}

# --- Handler para Vercel ---
handler = Mangum(app)

# --- Para ejecutar localmente ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
