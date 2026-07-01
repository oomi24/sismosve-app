@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Sirve el archivo index.html desde la raíz del proyecto."""
    # Buscar el archivo en diferentes ubicaciones (Render)
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
            <p><a href="/api/sismos">Ver datos de sismos</a></p>
        </body>
    </html>
    """
