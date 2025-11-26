# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import get_settings
from app.routes import candidatos, votantes, votos, estadisticas, upload, train, analytics, fraud

settings = get_settings()

app = FastAPI(
    title="Backend Electoral ONPE",
    description="API Backend Electoral con Supabase y Detección Automática de CSV",
    version="2.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# RUTAS
app.include_router(candidatos.router, prefix="/api/candidatos", tags=["Candidatos"])
app.include_router(votantes.router, prefix="/api/votantes", tags=["Votantes"])
app.include_router(votos.router, prefix="/api/votos", tags=["Votos"])
app.include_router(estadisticas.router, prefix="/api/estadisticas", tags=["Estadísticas"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload CSV"])
app.include_router(train.router, prefix="/api/train", tags=["ML Training"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(fraud.router, prefix="/api", tags=["Fraud Detection"])  # ← NUEVA RUTA

@app.get("/")
async def root():
    return {
        "message": "Backend Electoral ONPE API",
        "version": "2.1.0",
        "features": [
            "Detección automática de tipo de elección en CSV",
            "Carga a tablas temporales",
            "Limpieza inteligente de datos"
        ],
        "docs": "/docs",
        "cors_origins": settings.get_cors_origins()
    }

@app.get("/health")
async def health_check():
    from app.config.settings import supabase_client
    
    try:
        supabase_client.table("candidatos").select("id").limit(1).execute()
        status = "healthy"
        supabase_status = "connected"
    except Exception as e:
        status = "unhealthy"
        supabase_status = f"error: {str(e)}"
    
    return {
        "status": status,
        "supabase": supabase_status,
        "cors_enabled": True,
        "features": {
            "csv_upload": True,
            "auto_detection": True
        }
    }