# app/routes/fraud.py  (o cleaning.py)

from fastapi import APIRouter, HTTPException
from app.config.settings import supabase_client
from typing import Dict
from datetime import datetime

router = APIRouter(tags=["Limpieza de Datos"])  # ← sin prefix aquí

# ================================================================
# 1. QUITAR DUPLICADOS + LOG EN log_duplicados
# ================================================================
@router.post("/batch/{batch_id}/remove-duplicates")
async def remove_duplicates(batch_id: str) -> Dict:
    try:
        batch_info = supabase_client.table("log_limpieza_datos")\
            .select("tipo_eleccion")\
            .eq("batch_id", batch_id)\
            .single()\
            .execute()
        
        if not batch_info.data:
            raise HTTPException(404, "Batch no encontrado")
        
        tipo = batch_info.data['tipo_eleccion']
        tabla_temp = f"datos_temp_{tipo}es"

        # Obtener todos los registros con DNI
        datos = supabase_client.table(tabla_temp)\
            .select("id,dni,created_at,nombre_completo,candidato_nombre,candidato_partido,departamento,provincia,distrito")\
            .eq("batch_id", batch_id)\
            .not_.is_("dni", "null")\
            .execute()

        if not datos.data:
            return {"success": True, "duplicados_eliminados": 0, "message": "No hay datos con DNI"}

        # Agrupar por DNI
        dni_to_rows = {}
        for row in datos.data:
            dni = str(row['dni']).strip()
            dni_to_rows.setdefault(dni, []).append(row)

        eliminados = 0
        logs_duplicados = []

        for dni, registros in dni_to_rows.items():
            if len(registros) > 1:
                # Mantener el más antiguo
                registros.sort(key=lambda x: x['created_at'])
                original = registros[0]
                duplicados = registros[1:]

                # Registrar en log_duplicados
                logs_duplicados.append({
                    "batch_id": batch_id,
                    "tipo_eleccion": tipo,
                    "tabla_origen": tabla_temp,
                    "registro_id_1": original['id'],
                    "registro_id_2": duplicados[0]['id'] if len(duplicados) > 0 else None,
                    "campo_duplicado": "dni",
                    "valor_duplicado": dni,
                    "registros_duplicados": [d['id'] for d in duplicados],
                    "fecha_deteccion": datetime.utcnow().isoformat()
                })

                # Eliminar duplicados
                for dup in duplicados:
                    supabase_client.table(tabla_temp).delete().eq("id", dup['id']).execute()
                    eliminados += 1

        # Insertar logs si hubo duplicados
        if logs_duplicados:
            supabase_client.table("log_duplicados").insert(logs_duplicados).execute()

        # Actualizar log principal
        supabase_client.table("log_limpieza_datos")\
            .update({"registros_duplicados": eliminados})\
            .eq("batch_id", batch_id)\
            .execute()

        return {
            "success": True,
            "message": f"{eliminados} duplicados eliminados y registrados",
            "duplicados_eliminados": eliminados
        }

    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


# ================================================================
# 2. LIMPIAR NULOS + LOG EN log_valores_nulos
# ================================================================
@router.post("/batch/{batch_id}/clean-nulls")
async def clean_nulls(batch_id: str) -> Dict:
    try:
        batch_info = supabase_client.table("log_limpieza_datos")\
            .select("tipo_eleccion")\
            .eq("batch_id", batch_id)\
            .single()\
            .execute()
        
        if not batch_info.data:
            raise HTTPException(404, "Batch no encontrado")

        tipo = batch_info.data['tipo_eleccion']
        tabla_temp = f"datos_temp_{tipo}es"

        # Buscar registros con campos críticos nulos
        nulos = supabase_client.table(tabla_temp)\
            .select("*")\
            .eq("batch_id", batch_id)\
            .or_("dni.is.null,nombre_completo.is.null,candidato_nombre.is.null")\
            .execute()

        eliminados = len(nulos.data)
        logs_nulos = []

        for row in nulos.data:
            campos_faltantes = []
            if not row['dni']: campos_faltantes.append("dni")
            if not row['nombre_completo']: campos_faltantes.append("nombre_completo")
            if not row['candidato_nombre']: campos_faltantes.append("candidato_nombre")

            for campo in campos_faltantes:
                logs_nulos.append({
                    "batch_id": batch_id,
                    "tipo_eleccion": tipo,
                    "tabla_origen": tabla_temp,
                    "registro_id": row['id'],
                    "campo_nulo": campo,
                    "registro_completo": row,
                    "fecha_deteccion": datetime.utcnow().isoformat()
                })

            # Eliminar el registro
            supabase_client.table(tabla_temp).delete().eq("id", row['id']).execute()

        if logs_nulos:
            supabase_client.table("log_valores_nulos").insert(logs_nulos).execute()

        supabase_client.table("log_limpieza_datos")\
            .update({"registros_con_nulos": eliminados})\
            .eq("batch_id", batch_id)\
            .execute()

        return {
            "success": True,
            "message": f"{eliminados} registros con nulos eliminados y registrados",
            "nulos_eliminados": eliminados
        }

    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


# ================================================================
# 3. NORMALIZAR → AHORA PROTEGE LOS UUIDs
# ================================================================
@router.post("/batch/{batch_id}/normalize")
async def normalize_batch(batch_id: str) -> Dict:
    try:
        batch_info = supabase_client.table("log_limpieza_datos")\
            .select("tipo_eleccion")\
            .eq("batch_id", batch_id)\
            .single()\
            .execute()
        
        if not batch_info.data:
            raise HTTPException(404, "Batch no encontrado")

        tipo = batch_info.data['tipo_eleccion']
        tabla_temp = f"datos_temp_{tipo}es"

        datos = supabase_client.table(tabla_temp)\
            .select("id,nombre_completo,candidato_nombre,candidato_partido,distrito")\
            .eq("batch_id", batch_id)\
            .execute()

        normalizados = 0
        logs_normalizacion = []

        for row in datos.data:
            updates = {}
            cambios = []

            # Nombre completo
            if row.get('nombre_completo'):
                original = str(row['nombre_completo']).strip()
                nuevo = " ".join(original.title().split())
                if nuevo != original:
                    updates['nombre_completo'] = nuevo
                    cambios.append({"campo": "nombre_completo", "de": original, "a": nuevo})

            # CANDIDATO_NOMBRE → solo normalizar si NO es un UUID
            if row.get('candidato_nombre'):
                valor = str(row['candidato_nombre']).strip()
                # Si parece UUID (tiene guiones y longitud típica), NO TOCAR
                if '-' in valor and len(valor) >= 30:
                    pass  # es candidato_id → dejar intacto
                else:
                    nuevo = " ".join(valor.title().split())
                    if nuevo != valor:
                        updates['candidato_nombre'] = nuevo
                        cambios.append({"campo": "candidato_nombre", "de": valor, "a": nuevo})

            # Partido → siempre a MAYÚSCULAS
            if row.get('candidato_partido'):
                original = str(row['candidato_partido']).strip()
                nuevo = original.upper()
                if nuevo != original:
                    updates['candidato_partido'] = nuevo
                    cambios.append({"campo": "candidato_partido", "de": original, "a": nuevo})

            # Distrito
            if row.get('distrito'):
                original = str(row['distrito']).strip()
                nuevo = " ".join(original.title().split())
                if nuevo != original:
                    updates['distrito'] = nuevo
                    cambios.append({"campo": "distrito", "de": original, "a": nuevo})

            if updates:
                supabase_client.table(tabla_temp).update(updates).eq("id", row['id']).execute()
                normalizados += len(cambios)
                for c in cambios:
                    logs_normalizacion.append({
                        "batch_id": batch_id,
                        "tipo_eleccion": tipo,
                        "tabla_origen": tabla_temp,
                        "registro_id": row['id'],
                        "campo_normalizado": c['campo'],
                        "valor_original": c['de'],
                        "valor_normalizado": c['a'],
                        "tipo_normalizacion": "uppercase" if c['campo'] == "candidato_partido" else "title_case",
                        "fecha_normalizacion": datetime.utcnow().isoformat()
                    })

        if logs_normalizacion:
            supabase_client.table("log_normalizacion").insert(logs_normalizacion).execute()

        supabase_client.table("log_limpieza_datos")\
            .update({"registros_normalizados": normalizados})\
            .eq("batch_id", batch_id)\
            .execute()

        return {"success": True, "message": f"{normalizados} campos normalizados", "campos_normalizados": normalizados}

    except Exception as e:
        raise HTTPException(500, f"Error en normalización: {str(e)}")

