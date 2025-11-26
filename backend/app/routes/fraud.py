# app/routes/fraud.py
from fastapi import APIRouter, HTTPException
from app.services.fraud_detection import FraudDetectionService
from typing import Dict

router = APIRouter()


@router.get("/fraud/analyze")
async def analyze_fraud() -> Dict:
    """
    Ejecuta análisis completo de detección de fraudes
    
    Retorna:
    - Total de votos analizados
    - Número de anomalías detectadas
    - Porcentaje de fraude
    - Nivel de riesgo (bajo/medio/alto)
    - Lista de anomalías detectadas
    - Resumen por tipo de anomalía
    """
    try:
        result = await FraudDetectionService.analizar_fraudes()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error en análisis de fraudes")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando análisis: {str(e)}"
        )


@router.get("/fraud/history")
async def get_fraud_history() -> Dict:
    """
    Obtiene el historial de análisis de fraudes
    """
    try:
        from app.config.settings import supabase_client
        
        result = supabase_client.table("fraud_detection_log") \
            .select("*") \
            .order("analyzed_at", desc=True) \
            .limit(20) \
            .execute()
        
        return {
            "success": True,
            "history": result.data,
            "total": len(result.data)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial: {str(e)}"
        )


@router.get("/fraud/stats")
async def get_fraud_stats() -> Dict:
    """
    Obtiene estadísticas generales de fraude
    """
    try:
        from app.config.settings import supabase_client
        
        # Obtener último análisis
        last_analysis = supabase_client.table("fraud_detection_log") \
            .select("*") \
            .order("analyzed_at", desc=True) \
            .limit(1) \
            .execute()
        
        if not last_analysis.data:
            return {
                "success": True,
                "message": "No hay análisis previos",
                "stats": None
            }
        
        data = last_analysis.data[0]
        
        return {
            "success": True,
            "stats": {
                "ultimo_analisis": data.get("analyzed_at"),
                "total_votos": data.get("total_votos_analizados"),
                "anomalias": data.get("anomalias_detectadas"),
                "porcentaje_fraude": data.get("porcentaje_fraude"),
                "nivel_riesgo": data.get("nivel_riesgo"),
                "detalles": data.get("detalles")
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )
