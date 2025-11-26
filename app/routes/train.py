# app/routes/train.py - ACTUALIZADO

from fastapi import APIRouter, HTTPException, Query
from app.services.ml_electoral import ModeloElectoralService

router = APIRouter()


@router.post("/entrenar/{tipo_eleccion}")
async def entrenar_modelo_electoral(tipo_eleccion: str):
    """
    Entrena modelo para tipo de elección específico
    Compatible con AnalisisEstadistico.jsx
    """
    if tipo_eleccion not in ['presidencial', 'regional', 'distrital']:
        raise HTTPException(
            status_code=400,
            detail="tipo_eleccion debe ser: presidencial, regional o distrital"
        )
    
    resultado = await ModeloElectoralService.entrenar_modelo_por_tipo(tipo_eleccion)
    
    if not resultado.get("success"):
        raise HTTPException(status_code=400, detail=resultado.get("error"))
    
    return resultado


@router.get("/modelos-activos")
async def obtener_modelos_activos():
    """
    Obtiene modelos activos para los 3 tipos de elección
    Usado por el dropdown del frontend
    """
    resultado = await ModeloElectoralService.obtener_modelos_activos()
    
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("error"))
    
    return resultado


@router.get("/predicciones/{tipo_eleccion}")
async def obtener_predicciones(tipo_eleccion: str):
    """
    Obtiene predicciones del modelo activo para un tipo de elección
    """
    if tipo_eleccion not in ['presidencial', 'regional', 'distrital']:
        raise HTTPException(400, "Tipo de elección inválido")
    
    # Buscar modelo más reciente
    try:
        result = supabase_client.table("ml_models")\
            .select("*")\
            .eq("metadata->>tipo_eleccion", tipo_eleccion)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not result.data:
            raise HTTPException(404, f"No hay modelo entrenado para {tipo_eleccion}")
        
        modelo = result.data[0]
        metadata = modelo.get('metadata', {})
        
        return {
            "success": True,
            "tipo_eleccion": tipo_eleccion,
            "modelo_activo": modelo.get('algorithm'),
            "metricas": metadata.get('metricas', {}),
            "participacion_estimada": metadata.get('participacion_estimada'),
            "feature_importance": metadata.get('feature_importance', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")