# app/routes/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict
import pandas as pd
import uuid
from datetime import datetime
from app.config.settings import supabase_client
import io
import re

router = APIRouter()

class CSVDetector:
    """Clase para detectar automáticamente el tipo de elección de un CSV"""
    
    KEYWORDS = {
        'presidencial': [
            'presidente', 'vicepresidente', 'nacional',
            'presidencial', 'voto_presidencial', 'candidato_presidencial',
            'presidente_id', 'vicepresidente_id', 'partido_nacional'
        ],
        'regional': [
            'region', 'gobernador', 'regional',
            'voto_regional', 'candidato_regional', 'provincia',
            'gobernador_regional', 'consejo_regional', 'region_id'
        ],
        'distrital': [
            'distrito', 'alcalde', 'distrital',
            'voto_distrital', 'candidato_distrital', 'municipal',
            'alcalde_distrital', 'regidor', 'concejo_municipal', 'distrito_id'
        ]
    }
    
    @staticmethod
    def detectar_tipo(df: pd.DataFrame) -> str:
        columns_lower = [col.lower().strip() for col in df.columns]
        sample_content = df.head(5).to_string().lower()
        
        scores = {}
        for tipo, keywords in CSVDetector.KEYWORDS.items():
            column_matches = sum(1 for col in columns_lower if any(keyword in col for keyword in keywords))
            content_matches = sum(1 for keyword in keywords if keyword in sample_content)
            scores[tipo] = column_matches + content_matches
        
        if max(scores.values()) == 0:
            if 'region' in columns_lower or 'provincia' in columns_lower:
                return 'regional'
            elif 'distrito' in columns_lower or 'alcalde' in columns_lower:
                return 'distrital'
            else:
                return 'presidencial'
        
        return max(scores, key=scores.get)


class CSVProcessor:
    """Procesa y guarda CSV directamente en tablas temporales de Supabase"""
    
    @staticmethod
    def limpiar_dni(dni_str) -> str:
        if pd.isna(dni_str):
            return None
        dni_clean = re.sub(r'\D', '', str(dni_str))
        if len(dni_clean) == 8:
            return dni_clean
        elif len(dni_clean) > 8:
            return dni_clean[:8]
        return None
    
    @staticmethod
    def normalizar_nombre(nombre_str) -> str:
        if pd.isna(nombre_str):
            return None
        return str(nombre_str).strip().title()
    
    @staticmethod
    def detectar_columnas(df: pd.DataFrame) -> Dict[str, str]:
        """Detecta automáticamente qué columnas corresponden a qué campos"""
        columns = list(df.columns)
        columns_lower = {col.lower().strip(): col for col in columns}
        
        mapping = {}
        
        def buscar_columna(palabras_clave):
            for palabra in palabras_clave:
                if palabra in columns_lower:
                    return columns_lower[palabra]
                for col_lower, col_original in columns_lower.items():
                    if palabra in col_lower:
                        return col_original
            return None
        
        mapping['dni'] = buscar_columna(['dni', 'documento', 'cedula', 'numero_documento', 'doc', 'identificacion', 'id'])
        mapping['nombre_completo'] = buscar_columna(['nombre_completo', 'nombre', 'nombres', 'votante', 'persona', 'ciudadano', 'elector', 'voter'])
        mapping['candidato_nombre'] = buscar_columna(['candidato_nombre', 'candidato', 'nombre_candidato', 'postulante', 'aspirante', 'candidate', 'electo', 'presidente', 'alcalde', 'gobernador'])
        mapping['candidato_partido'] = buscar_columna(['candidato_partido', 'partido', 'partido_politico', 'organizacion', 'agrupacion', 'party', 'movimiento', 'sigla'])
        mapping['departamento'] = buscar_columna(['departamento', 'region', 'estado', 'dept'])
        mapping['provincia'] = buscar_columna(['provincia', 'county', 'prov'])
        mapping['distrito'] = buscar_columna(['distrito', 'municipality', 'localidad', 'dist', 'ubigeo'])
        mapping['fecha_voto'] = buscar_columna(['fecha_voto', 'fecha', 'fecha_votacion', 'timestamp', 'date', 'hora'])
        
        return {k: v for k, v in mapping.items() if v is not None}
    
    @staticmethod
    def procesar_csv(df: pd.DataFrame, tipo_eleccion: str, batch_id: str) -> Dict:
        """Procesa el DataFrame y lo guarda DIRECTAMENTE en Supabase"""
        
        column_mapping = CSVProcessor.detectar_columnas(df)
        
        registros_procesados = []
        registros_validos = 0
        registros_con_errores = 0
        
        for idx, row in df.iterrows():
            try:
                # ← AQUÍ ESTABA EL ERROR: usabas .get('nombre') que no existía
                dni_col = column_mapping.get('dni')
                nombre_col = column_mapping.get('nombre_completo')
                candidato_col = column_mapping.get('candidato_nombre')
                partido_col = column_mapping.get('candidato_partido')
                distrito_col = column_mapping.get('distrito')
                fecha_col = column_mapping.get('fecha_voto')

                dni = CSVProcessor.limpiar_dni(row[dni_col]) if dni_col else None
                nombre_completo = CSVProcessor.normalizar_nombre(row[nombre_col]) if nombre_col else "Sin nombre"
                candidato_nombre = CSVProcessor.normalizar_nombre(row[candidato_col]) if candidato_col else "Sin candidato"
                candidato_partido = row[partido_col].strip().upper() if partido_col and pd.notna(row.get(partido_col)) else "SIN PARTIDO"
                distrito = CSVProcessor.normalizar_nombre(row[distrito_col]) if distrito_col else "Sin distrito"

                fecha_voto = row[fecha_col] if fecha_col else None
                if pd.notna(fecha_voto):
                    try:
                        fecha_voto = pd.to_datetime(fecha_voto).isoformat()
                    except:
                        fecha_voto = datetime.utcnow().isoformat()
                else:
                    fecha_voto = datetime.utcnow().isoformat()
                
                if not dni or len(dni) != 8:
                    registros_con_errores += 1
                    continue
                
                registro = {
                    "batch_id": batch_id,
                    "dni": dni,
                    "nombre_completo": nombre_completo,
                    "candidato_nombre": candidato_nombre,
                    "candidato_partido": candidato_partido,
                    "departamento": "Sin departamento",
                    "provincia": "Sin provincia",
                    "distrito": distrito,
                    "fecha_voto": fecha_voto,
                    "estado_registro": "pendiente",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                registros_procesados.append(registro)
                registros_validos += 1
                
            except Exception as e:
                print(f"Error procesando fila {idx}: {str(e)}")
                registros_con_errores += 1
                continue
        
        # GUARDAR DIRECTAMENTE EN SUPABASE
        if registros_procesados:
            tabla_temporal = f"datos_temp_{tipo_eleccion}es"
            
            try:
                batch_size = 100
                for i in range(0, len(registros_procesados), batch_size):
                    batch = registros_procesados[i:i + batch_size]
                    supabase_client.table(tabla_temporal).insert(batch).execute()
                
            except Exception as e:
                print(f"Error guardando en Supabase: {str(e)}")
                raise
        
        return {
            "total_procesados": len(df),
            "registros_validos": registros_validos,
            "registros_con_errores": registros_con_errores,
            "batch_id": batch_id,
            "tabla_destino": f"datos_temp_{tipo_eleccion}es"
        }


# ==================== TUS ENDPOINTS (INTACTOS) ====================

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)) -> Dict:
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos CSV")
        
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="El archivo CSV está vacío")
        
        batch_id = str(uuid.uuid4())
        tipo_eleccion = CSVDetector.detectar_tipo(df).lower()
        
        resultado = CSVProcessor.procesar_csv(df, tipo_eleccion, batch_id)
        
        supabase_client.table("log_limpieza_datos").insert({
            "batch_id": batch_id,
            "tipo_eleccion": tipo_eleccion,
            "total_registros": resultado["total_procesados"],
            "registros_validos": resultado["registros_validos"],
            "estado": "cargado",
            "detalles": {
                "archivo_nombre": file.filename,
                "columnas_detectadas": list(df.columns),
                "tabla_destino": resultado["tabla_destino"]
            }
        }).execute()
        
        return {
            "success": True,
            "message": f"CSV guardado exitosamente en Supabase",
            "tipo_detectado": tipo_eleccion,
            "batch_id": batch_id,
            "estadisticas": {
                "total_filas": resultado["total_procesados"],
                "registros_validos": resultado["registros_validos"],
                "registros_con_errores": resultado["registros_con_errores"],
            },
            "tabla_destino": resultado["tabla_destino"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")


@router.get("/batches/list")
async def list_batches() -> Dict:
    result = supabase_client.table("log_limpieza_datos").select("*").order("created_at", desc=True).execute()
    return {"success": True, "batches": result.data, "total": len(result.data)}


@router.get("/batch/{batch_id}/data/{tipo}")
async def get_batch_data(batch_id: str, tipo: str) -> Dict:
    tipo = tipo.lower()
    tabla = f"datos_temp_{tipo}es"
    result = supabase_client.table(tabla).select("*").eq("batch_id", batch_id).execute()
    return {"success": True, "data": result.data, "total": len(result.data)}


@router.post("/batch/{batch_id}/move-to-final")
async def move_batch_to_final(batch_id: str, replace_all: bool = False) -> Dict:
    try:
        batch_info = supabase_client.table("log_limpieza_datos").select("*").eq("batch_id", batch_id).single().execute()
        if not batch_info.data:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        tipo_eleccion = batch_info.data['tipo_eleccion']
        tabla_temporal = f"datos_temp_{tipo_eleccion}es"
        tabla_votos_final = f"votos_{tipo_eleccion}es"
        
        datos_temp = supabase_client.table(tabla_temporal).select("*").eq("batch_id", batch_id).eq("estado_registro", "pendiente").execute()
        if not datos_temp.data:
            return {"success": False, "message": "No hay registros pendientes"}
        
        if replace_all:
            supabase_client.table(tabla_votos_final).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        votantes_creados = candidatos_creados = votos_registrados = 0
        
        for registro in datos_temp.data:
            try:
                dni = registro['dni']
                votante_existe = supabase_client.table("votantes").select("id").eq("dni", dni).execute()
                
                if votante_existe.data:
                    votante_id = votante_existe.data[0]['id']
                else:
                    nombre_partes = registro['nombre_completo'].split()
                    votante_nuevo = supabase_client.table("votantes").insert({
                        "dni": dni,
                        "nombres": nombre_partes[0] if len(nombre_partes) > 0 else "Sin nombre",
                        "apellido_paterno": nombre_partes[1] if len(nombre_partes) > 1 else "Sin apellido",
                        "apellido_materno": nombre_partes[2] if len(nombre_partes) > 2 else "",
                        "departamento": registro['departamento'],
                        "provincia": registro['provincia'],
                        "distrito": registro['distrito']
                    }).execute()
                    votante_id = votante_nuevo.data[0]['id']
                    votantes_creados += 1
                
                candidato_existe = supabase_client.table("candidatos") \
                    .select("id") \
                    .eq("nombre", registro['candidato_nombre']) \
                    .eq("partido", registro['candidato_partido']) \
                    .eq("tipo_eleccion", tipo_eleccion) \
                    .execute()
                
                if candidato_existe.data:
                    candidato_id = candidato_existe.data[0]['id']
                else:
                    candidato_nuevo = supabase_client.table("candidatos").insert({
                        "nombre": registro['candidato_nombre'],
                        "partido": registro['candidato_partido'],
                        "tipo_eleccion": tipo_eleccion,
                        "propuestas": []
                    }).execute()
                    candidato_id = candidato_nuevo.data[0]['id']
                    candidatos_creados += 1
                
                if not replace_all:
                    voto_existe = supabase_client.table(tabla_votos_final).select("id").eq("dni_votante", dni).execute()
                    if voto_existe.data:
                        continue
                
                supabase_client.table(tabla_votos_final).insert({
                    "votante_id": votante_id,
                    "candidato_id": candidato_id,
                    "dni_votante": dni,
                    "departamento": registro['departamento'],
                    "provincia": registro['provincia'],
                    "distrito": registro['distrito'],
                    "fecha_voto": registro['fecha_voto']
                }).execute()
                
                votos_registrados += 1
                
                supabase_client.table(tabla_temporal) \
                    .update({"estado_registro": "procesado"}) \
                    .eq("id", registro['id']) \
                    .execute()
                
            except Exception as e:
                print(f"Error procesando registro: {str(e)}")
                continue
        
        supabase_client.table("log_limpieza_datos") \
            .update({"estado": "procesado", "fecha_fin": datetime.utcnow().isoformat()}) \
            .eq("batch_id", batch_id) \
            .execute()
        
        return {
            "success": True,
            "message": f"Datos movidos exitosamente",
            "estadisticas": {
                "votantes_creados": votantes_creados,
                "candidatos_creados": candidatos_creados,
                "votos_registrados": votos_registrados,
                "total_procesado": len(datos_temp.data)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))