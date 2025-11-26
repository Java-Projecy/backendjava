# app/routes/estadisticas.py
from fastapi import APIRouter, HTTPException
from app.config.settings import supabase_client

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats():
    """Obtiene todas las estadísticas para el dashboard"""
    try:
        # Total votantes
        votantes = supabase_client.table("votantes").select("id", count="exact").execute()
        
        # Total votos por tipo
        votos_pres = supabase_client.table("votos_presidenciales").select("id", count="exact").execute()
        votos_reg = supabase_client.table("votos_regionales").select("id", count="exact").execute()
        votos_dist = supabase_client.table("votos_distritales").select("id", count="exact").execute()
        
        total_votos = votos_pres.count + votos_reg.count + votos_dist.count
        
        # Calcular porcentaje de datos procesados
        datos_procesados = (total_votos / max(votantes.count, 1)) * 100 if votantes.count > 0 else 0
        
        # Actividad reciente (últimos 5 registros de votos)
        actividad_pres = supabase_client.table("votos_presidenciales") \
            .select("*, votantes(nombres, apellido_paterno, apellido_materno)") \
            .order("fecha_voto", desc=True) \
            .limit(2) \
            .execute()
        
        actividad_reg = supabase_client.table("votos_regionales") \
            .select("*, votantes(nombres, apellido_paterno, apellido_materno)") \
            .order("fecha_voto", desc=True) \
            .limit(2) \
            .execute()
        
        actividad_dist = supabase_client.table("votos_distritales") \
            .select("*, votantes(nombres, apellido_paterno, apellido_materno)") \
            .order("fecha_voto", desc=True) \
            .limit(1) \
            .execute()
        
        # Combinar actividad
        actividad = []
        for voto in actividad_pres.data:
            actividad.append({
                "action": "Voto Presidencial registrado",
                "time": voto.get("fecha_voto", ""),
                "status": "success"
            })
        for voto in actividad_reg.data:
            actividad.append({
                "action": "Voto Regional registrado",
                "time": voto.get("fecha_voto", ""),
                "status": "success"
            })
        for voto in actividad_dist.data:
            actividad.append({
                "action": "Voto Distrital registrado",
                "time": voto.get("fecha_voto", ""),
                "status": "success"
            })
        
        return {
            "success": True,
            "data": {
                "total_votantes": votantes.count,
                "registros_cargados": total_votos,
                "datos_procesados": round(datos_procesados, 1),
                "validacion_completa": total_votos,
                "votos": {
                    "presidencial": votos_pres.count,
                    "regional": votos_reg.count,
                    "distrital": votos_dist.count,
                    "total": total_votos
                },
                "actividad_reciente": actividad[:5]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/general")
async def get_estadisticas_generales():
    """Obtiene estadísticas generales"""
    try:
        # Total votantes
        votantes = supabase_client.table("votantes").select("id", count="exact").execute()
        total_votantes = votantes.count
        
        # Total candidatos
        candidatos = supabase_client.table("candidatos").select("id", count="exact").eq("is_active", True).execute()
        total_candidatos = candidatos.count
        
        # Total votos por tipo
        votos_pres = supabase_client.table("votos_presidenciales").select("id", count="exact").execute()
        votos_reg = supabase_client.table("votos_regionales").select("id", count="exact").execute()
        votos_dist = supabase_client.table("votos_distritales").select("id", count="exact").execute()
        
        return {
            "success": True,
            "data": {
                "total_votantes": total_votantes,
                "total_candidatos": total_candidatos,
                "votos": {
                    "presidencial": votos_pres.count,
                    "regional": votos_reg.count,
                    "distrital": votos_dist.count,
                    "total": votos_pres.count + votos_reg.count + votos_dist.count
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tipo_eleccion}")
async def get_estadisticas_por_tipo(tipo_eleccion: str):
    """Obtiene estadísticas por tipo de elección"""
    if tipo_eleccion not in ['presidencial', 'regional', 'distrital']:
        raise HTTPException(
            status_code=400,
            detail="tipo_eleccion debe ser: presidencial, regional o distrital"
        )
    
    try:
        # Usar función de PostgreSQL
        result = supabase_client.rpc('obtener_estadisticas_votos', {
            'p_tipo_eleccion': tipo_eleccion
        }).execute()
        
        return {
            "success": True,
            "tipo": tipo_eleccion,
            "data": result.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))