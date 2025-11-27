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
@router.get("/votos-por-distrito")
async def get_votos_por_distrito():
    """Obtiene votos agrupados por distrito"""
    try:
        # Combinar votos de las 3 tablas
        votos_pres = supabase_client.table("votos_presidenciales").select("distrito").execute()
        votos_reg = supabase_client.table("votos_regionales").select("distrito").execute()
        votos_dist = supabase_client.table("votos_distritales").select("distrito").execute()
        
        # Combinar todos los votos
        all_votes = []
        if votos_pres.data:
            all_votes.extend(votos_pres.data)
        if votos_reg.data:
            all_votes.extend(votos_reg.data)
        if votos_dist.data:
            all_votes.extend(votos_dist.data)
        
        # Contar votos por distrito
        distrito_counts = {}
        for voto in all_votes:
            distrito = voto.get('distrito', 'Sin distrito')
            if distrito:
                distrito_counts[distrito] = distrito_counts.get(distrito, 0) + 1
        
        # Convertir a lista ordenada
        distritos_data = [
            {"distrito": distrito, "votos": count}
            for distrito, count in distrito_counts.items()
        ]
        
        # Ordenar por cantidad de votos (mayor a menor)
        distritos_data.sort(key=lambda x: x['votos'], reverse=True)
        
        return {
            "success": True,
            "data": distritos_data,
            "total_distritos": len(distritos_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/votos-por-distrito/{tipo_eleccion}")
async def get_votos_por_distrito_filtrado(tipo_eleccion: str):
    """Obtiene votos por distrito filtrados por tipo de elección"""
    if tipo_eleccion not in ['presidencial', 'regional', 'distrital', 'todos']:
        raise HTTPException(
            status_code=400,
            detail="tipo_eleccion debe ser: presidencial, regional, distrital o todos"
        )
    
    try:
        all_votes = []
        
        # Si es "todos", combinar todas las tablas
        if tipo_eleccion == 'todos':
            votos_pres = supabase_client.table("votos_presidenciales").select("distrito").execute()
            votos_reg = supabase_client.table("votos_regionales").select("distrito").execute()
            votos_dist = supabase_client.table("votos_distritales").select("distrito").execute()
            
            if votos_pres.data:
                all_votes.extend(votos_pres.data)
            if votos_reg.data:
                all_votes.extend(votos_reg.data)
            if votos_dist.data:
                all_votes.extend(votos_dist.data)
        else:
            # Solo una tabla específica
            tabla = f"votos_{tipo_eleccion}es"
            votos = supabase_client.table(tabla).select("distrito").execute()
            if votos.data:
                all_votes.extend(votos.data)
        
        # Contar votos por distrito
        distrito_counts = {}
        for voto in all_votes:
            distrito = voto.get('distrito', 'Sin distrito')
            if distrito and distrito.strip():
                distrito_counts[distrito] = distrito_counts.get(distrito, 0) + 1
        
        # Convertir a lista ordenada
        distritos_data = [
            {"distrito": distrito, "votos": count}
            for distrito, count in distrito_counts.items()
        ]
        
        distritos_data.sort(key=lambda x: x['votos'], reverse=True)
        
        return {
            "success": True,
            "tipo_eleccion": tipo_eleccion,
            "data": distritos_data,
            "total_distritos": len(distritos_data),
            "total_votos": sum(d['votos'] for d in distritos_data)
        }
    except Exception as e:
        print(f"❌ Error en votos-por-distrito/{tipo_eleccion}: {str(e)}")
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
