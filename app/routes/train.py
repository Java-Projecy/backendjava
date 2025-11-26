# app/routes/train.py - VERSIÓN COMPLETA INTEGRADA

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.ml_training import MLTrainingService
from app.config.settings import supabase_client
from typing import Optional

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================
class TrainModelRequest(BaseModel):
    """Schema para entrenar modelo genérico"""
    model_type: str  # "classification" o "regression"
    algorithm: str   # "random_forest", "logistic_regression", "gradient_boosting"
    test_size: float = 0.2
    random_state: int = 42
    election_type: str = 'presidencial'  # 'presidencial', 'regional', 'distrital'


# ============================================
# ENDPOINTS SIMPLIFICADOS (PARA FRONTEND)
# ============================================
@router.post("/entrenar/{tipo_eleccion}")
async def entrenar_modelo_electoral(tipo_eleccion: str):
    """
    ✅ Endpoint simplificado para el frontend (AnalisisEstadistico.jsx)
    
    Entrena automáticamente un modelo Random Forest de clasificación
    para predecir qué candidato ganará según tipo de elección.
    
    Parámetros:
        tipo_eleccion: 'presidencial', 'regional' o 'distrital'
    
    Retorna:
        Modelo entrenado con métricas y metadata
    """
    # Validar tipo de elección
    if tipo_eleccion not in ['presidencial', 'regional', 'distrital']:
        raise HTTPException(
            status_code=400,
            detail="tipo_eleccion debe ser: presidencial, regional o distrital"
        )
    
    try:
        # Entrenar modelo de clasificación con Random Forest (predeterminado)
        resultado = await MLTrainingService.train_model(
            model_type="classification",
            algorithm="random_forest",
            test_size=0.2,
            random_state=42,
            election_type=tipo_eleccion
        )
        
        if not resultado.get("success"):
            raise HTTPException(
                status_code=400, 
                detail=resultado.get("error", "Error desconocido en entrenamiento")
            )
        
        # Formatear respuesta para el frontend
        return {
            "success": True,
            "tipo_eleccion": tipo_eleccion,
            "modelo_activo": resultado.get("model_name"),
            "algorithm": resultado.get("algorithm"),
            "metricas": {
                "accuracy": resultado["metrics"]["test_accuracy"],
                "precision": resultado["metrics"]["precision"],
                "recall": resultado["metrics"]["recall"],
                "f1_score": resultado["metrics"]["f1_score"],
            },
            "participacion_estimada": f"{resultado['metrics']['test_accuracy'] * 100:.1f}%",
            "feature_importance": resultado["metrics"].get("feature_importance", {}),
            "training_time": resultado.get("training_time"),
            "samples": {
                "train": resultado.get("training_samples"),
                "test": resultado.get("test_samples")
            },
            "model_id": resultado.get("model_id"),
            "session_id": resultado.get("session_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno: {str(e)}"
        )


@router.get("/modelos-activos")
async def obtener_modelos_activos():
    """
    ✅ Obtiene los modelos activos para los 3 tipos de elección
    Usado por el dropdown del frontend
    
    Retorna:
        Lista de modelos activos por tipo de elección
    """
    try:
        modelos = {}
        
        for tipo in ['presidencial', 'regional', 'distrital']:
            # Buscar modelo más reciente para este tipo
            result = supabase_client.table("ml_models")\
                .select("*")\
                .ilike("model_name", f"%{tipo}%")\
                .eq("is_active", True)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                modelo = result.data[0]
                
                # Obtener métricas asociadas
                metrics_result = supabase_client.table("model_metrics")\
                    .select("*")\
                    .eq("model_id", modelo['id'])\
                    .order("recorded_at", desc=True)\
                    .limit(1)\
                    .execute()
                
                metrics = metrics_result.data[0] if metrics_result.data else {}
                
                modelos[tipo] = {
                    "model_id": modelo['id'],
                    "model_name": modelo['model_name'],
                    "algorithm": modelo['algorithm'],
                    "version": modelo.get('version'),
                    "created_at": modelo['created_at'],
                    "training_data_size": modelo.get('training_data_size'),
                    "metrics": {
                        "accuracy": metrics.get('accuracy'),
                        "precision": metrics.get('precision_score'),
                        "recall": metrics.get('recall'),
                        "f1_score": metrics.get('f1_score')
                    } if metrics else None
                }
            else:
                modelos[tipo] = None  # No hay modelo para este tipo
        
        return {
            "success": True,
            "modelos": modelos,
            "timestamp": supabase_client.table("ml_models").select("created_at").order("created_at", desc=True).limit(1).execute().data[0]['created_at'] if supabase_client.table("ml_models").select("created_at").execute().data else None
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error obteniendo modelos: {str(e)}"
        )


@router.get("/predicciones/{tipo_eleccion}")
async def obtener_predicciones(tipo_eleccion: str):
    """
    ✅ Obtiene predicciones del modelo activo para un tipo de elección
    
    Parámetros:
        tipo_eleccion: 'presidencial', 'regional' o 'distrital'
    
    Retorna:
        Predicciones y métricas del modelo activo
    """
    if tipo_eleccion not in ['presidencial', 'regional', 'distrital']:
        raise HTTPException(400, "Tipo de elección inválido")
    
    try:
        # Buscar modelo más reciente para este tipo
        result = supabase_client.table("ml_models")\
            .select("*")\
            .ilike("model_name", f"%{tipo_eleccion}%")\
            .eq("is_active", True)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                404, 
                f"No hay modelo entrenado para {tipo_eleccion}. Entrena uno primero."
            )
        
        modelo = result.data[0]
        
        # Obtener métricas
        metrics_result = supabase_client.table("model_metrics")\
            .select("*")\
            .eq("model_id", modelo['id'])\
            .order("recorded_at", desc=True)\
            .limit(1)\
            .execute()
        
        metrics = metrics_result.data[0] if metrics_result.data else {}
        
        # Calcular participación estimada (basada en accuracy)
        accuracy = metrics.get('accuracy', 0.7)
        participacion_estimada = f"{accuracy * 100:.1f}%"
        
        # Feature importance
        feature_importance = {}
        if metrics.get('feature_importance'):
            import json
            try:
                feature_importance = json.loads(metrics['feature_importance'])
            except:
                feature_importance = {}
        
        return {
            "success": True,
            "tipo_eleccion": tipo_eleccion,
            "modelo_activo": modelo.get('algorithm'),
            "model_name": modelo.get('model_name'),
            "model_id": modelo['id'],
            "created_at": modelo['created_at'],
            "metricas": {
                "accuracy": metrics.get('accuracy'),
                "precision": metrics.get('precision_score'),
                "recall": metrics.get('recall'),
                "f1_score": metrics.get('f1_score')
            },
            "participacion_estimada": participacion_estimada,
            "feature_importance": feature_importance,
            "training_data_size": modelo.get('training_data_size')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error: {str(e)}")


# ============================================
# ENDPOINTS AVANZADOS (PARA USO PROGRAMÁTICO)
# ============================================
@router.post("/train")
async def train_model(request: TrainModelRequest):
    """
    ✅ Endpoint avanzado para entrenar modelos con configuración personalizada
    
    Body:
        {
          "model_type": "classification" | "regression",
          "algorithm": "random_forest" | "logistic_regression" | "gradient_boosting",
          "test_size": 0.2,
          "random_state": 42,
          "election_type": "presidencial" | "regional" | "distrital"
        }
    """
    try:
        result = await MLTrainingService.train_model(
            model_type=request.model_type,
            algorithm=request.algorithm,
            test_size=request.test_size,
            random_state=request.random_state,
            election_type=request.election_type
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Error en entrenamiento")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/models")
async def get_models():
    """✅ Obtiene todos los modelos entrenados"""
    try:
        result = await MLTrainingService.get_all_models()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener modelos: {str(e)}"
        )


@router.get("/models/{model_id}")
async def get_model_details(model_id: int):
    """✅ Obtiene detalles de un modelo específico"""
    try:
        result = await MLTrainingService.get_model_details(model_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Modelo no encontrado"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener modelo: {str(e)}"
        )


@router.get("/models/{model_id}/metrics")
async def get_model_metrics(model_id: int):
    """✅ Obtiene métricas de un modelo específico"""
    try:
        result = await MLTrainingService.get_model_metrics(model_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Métricas no encontradas"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener métricas: {str(e)}"
        )


@router.get("/models/{model_id}/history")
async def get_training_history(model_id: int):
    """✅ Obtiene historial de entrenamiento"""
    try:
        result = await MLTrainingService.get_training_history(model_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener historial: {str(e)}"
        )


@router.delete("/models/{model_id}")
async def delete_model(model_id: int):
    """✅ Elimina un modelo"""
    try:
        result = await MLTrainingService.delete_model(model_id)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail="Modelo no encontrado"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar modelo: {str(e)}"
        )