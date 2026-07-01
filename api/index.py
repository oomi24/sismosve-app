from fastapi.responses import HTMLResponse
from pathlib import Path

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Sirve el archivo index.html desde la raíz del proyecto."""
    # Buscar el archivo en diferentes ubicaciones
    posibles_rutas = [
        Path("/app/index.html"),  # Render
        Path("/home/oomiapp/sismosve-main/index.html"),  # PythonAnywhere
        Path(__file__).parent.parent / "index.html",
        Path("index.html"),
    ]
    
    for ruta in posibles_rutas:
        if ruta.exists():
            return ruta.read_text(encoding='utf-8')
    
    return """
    <html>
        <head><title>SismosVE</title></head>
        <body>
            <h1>🌋 SismosVE</h1>
            <p>API funcionando correctamente</p>
            <p><a href="/api/sismos">Ver datos de sismos</a></p>
        </body>
    </html>
    """
