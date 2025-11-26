# app/routes/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, List
import pandas as pd
import uuid
from datetime import datetime
from app.config.settings import supabase_client
import io
import re

router = APIRouter()

class CSVDetector:
    """Clase para detectar automáticamente el tipo de elección de un CSV"""
    
    # Palabras clave por tipo de elección
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
        """
        Detecta el tipo de elección analizando:
        1. Nombres de columnas
        2. Contenido de las primeras filas
        """
        # Convertir columnas a minúsculas
        columns_lower = [col.lower().strip() for col in df.columns]
        
        print(f"🔍 Columnas detectadas: {columns_lower}")
        
        # Obtener contenido de las primeras 5 filas
        sample_content = df.head(5).to_string().lower()
        
        print(f"📄 Muestra de contenido: {sample_content[:200]}...")
        
        # Contar coincidencias por tipo
        scores = {}
        
        for tipo, keywords in CSVDetector.KEYWORDS.items():
            # Coincidencias en columnas
            column_matches = sum(
                1 for col in columns_lower
                if any(keyword in col for keyword in keywords)
            )
            
            # Coincidencias en contenido
            content_matches = sum(
                1 for keyword in keywords
                if keyword in sample_content
            )
            
            total_score = column_matches + content_matches
            scores[tipo] = total_score
            
            print(f"📊 {tipo}: {total_score} coincidencias (cols: {column_matches}, contenido: {content_matches})")
        
        # Obtener tipo con mayor score
        if max(scores.values()) == 0:
            # Sin coincidencias claras, analizar estructura
            if 'region' in columns_lower or 'provincia' in columns_lower:
                return 'regional'
            elif 'distrito' in columns_lower or 'alcalde' in columns_lower:
                return 'distrital'
            else:
                return 'presidencial'  # Default
        
        detected_type = max(scores, key=scores.get)
        print(f"✅ Tipo detectado: {detected_type}")
        
        return detected_type


class CSVProcessor:
    """Procesa y guarda CSV en tablas temporales"""
    
    @staticmethod
    def limpiar_dni(dni_str) -> str:
        """Limpia y valida DNI"""
        if pd.isna(dni_str):
            return None
        
        # Extraer solo números
        dni_clean = re.sub(r'\D', '', str(dni_str))
        
        # Validar longitud
        if len(dni_clean) == 8:
            return dni_clean
        elif len(dni_clean) > 8:
            return dni_clean[:8]  # Tomar primeros 8
        else:
            return None  # DNI inválido
    
    @staticmethod
    def normalizar_nombre(nombre_str) -> str:
        """Normaliza nombres (capitalización)"""
        if pd.isna(nombre_str):
            return None
        
        return str(nombre_str).strip().title()
    
    @staticmethod
    def procesar_csv(df: pd.DataFrame, tipo_eleccion: str, batch_id: str) -> Dict:
        """
        Procesa el DataFrame y lo guarda en la tabla temporal correspondiente
        """
        print(f"\n📊 Procesando CSV tipo: {tipo_eleccion}")
        print(f"📋 Columnas disponibles: {list(df.columns)}")
        print(f"📏 Total de filas: {len(df)}")
        
        # Mapeo flexible de columnas
        column_mapping = CSVProcessor._detectar_columnas(df)
        
        print(f"🗺️ Mapeo de columnas: {column_mapping}")
        
        # Procesar registros
        registros_procesados = []
        registros_validos = 0
        registros_con_errores = 0
        
        for idx, row in df.iterrows():
            try:
                # Extraer datos con mapeo flexible
                dni = CSVProcessor.limpiar_dni(row.get(column_mapping.get('dni')))
                nombre_completo = CSVProcessor.normalizar_nombre(
                    row.get(column_mapping.get('nombre_completo', 'nombre'))
                )
                candidato_nombre = CSVProcessor.normalizar_nombre(
                    row.get(column_mapping.get('candidato_nombre', 'candidato'))
                )
                candidato_partido = CSVProcessor.normalizar_nombre(
                    row.get(column_mapping.get('candidato_partido', 'partido'))
                )
                
                # Ubicación
                departamento = CSVProcessor.normalizar_nombre(
                    row.get(column_mapping.get('departamento', 'departamento'))
                )
                provincia = CSVProcessor.normalizar_nombre(
                    row.get(column_mapping.get('provincia', 'provincia'))
                )
                distrito = CSVProcessor.normalizar_nombre(
                    row.get(column_mapping.get('distrito', 'distrito'))
                )
                
                # Fecha
                fecha_voto = row.get(column_mapping.get('fecha_voto'))
                if pd.notna(fecha_voto):
                    try:
                        fecha_voto = pd.to_datetime(fecha_voto).isoformat()
                    except:
                        fecha_voto = datetime.utcnow().isoformat()
                else:
                    fecha_voto = datetime.utcnow().isoformat()
                
                # Validar datos mínimos
                if not dni or len(dni) != 8:
                    registros_con_errores += 1
                    continue
                
                # Crear registro
                registro = {
                    "batch_id": batch_id,
                    "dni": dni,
                    "nombre_completo": nombre_completo or "Sin nombre",
                    "candidato_nombre": candidato_nombre or "Sin candidato",
                    "candidato_partido": candidato_partido or "Sin partido",
                    "departamento": departamento or "Sin departamento",
                    "provincia": provincia or "Sin provincia",
                    "distrito": distrito or "Sin distrito",
                    "fecha_voto": fecha_voto,
                    "estado_registro": "pendiente",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                registros_procesados.append(registro)
                registros_validos += 1
                
            except Exception as e:
                print(f"⚠️ Error procesando fila {idx}: {str(e)}")
                registros_con_errores += 1
                continue
        
        print(f"✅ Registros válidos: {registros_validos}")
        print(f"❌ Registros con errores: {registros_con_errores}")
        
        # Guardar en tabla temporal correspondiente
        if registros_procesados:
            tabla_temporal = f"datos_temp_{tipo_eleccion}es"
            
            try:
                # Insertar en lotes de 100
                batch_size = 100
                for i in range(0, len(registros_procesados), batch_size):
                    batch = registros_procesados[i:i + batch_size]
                    supabase_client.table(tabla_temporal).insert(batch).execute()
                    print(f"💾 Insertados {len(batch)} registros en {tabla_temporal}")
                
                print(f"✅ Total guardado en {tabla_temporal}: {len(registros_procesados)} registros")
                
            except Exception as e:
                print(f"❌ Error guardando en Supabase: {str(e)}")
                raise
        
        return {
            "total_procesados": len(df),
            "registros_validos": registros_validos,
            "registros_con_errores": registros_con_errores,
            "batch_id": batch_id,
            "tabla_destino": f"datos_temp_{tipo_eleccion}es"
        }
    
    @staticmethod
    def _detectar_columnas(df: pd.DataFrame) -> Dict[str, str]:
        """
        Detecta automáticamente qué columnas corresponden a qué campos
        AHORA CON BÚSQUEDA MÁS FLEXIBLE
        """
        columns = list(df.columns)
        columns_lower = {col.lower().strip(): col for col in columns}
        
        print(f"🔍 Columnas originales del CSV: {columns}")
        
        mapping = {}
        
        # Función auxiliar para buscar con contenido parcial
        def buscar_columna(palabras_clave):
            for palabra in palabras_clave:
                # Búsqueda exacta
                if palabra in columns_lower:
                    return columns_lower[palabra]
                # Búsqueda parcial (contiene)
                for col_lower, col_original in columns_lower.items():
                    if palabra in col_lower:
                        return col_original
            return None
        
        # DNI
        mapping['dni'] = buscar_columna([
            'dni', 'documento', 'cedula', 'numero_documento', 
            'doc', 'identificacion', 'id'
        ])
        
        # Nombre completo / Votante
        mapping['nombre_completo'] = buscar_columna([
            'nombre_completo', 'nombre', 'nombres', 'votante', 
            'persona', 'ciudadano', 'elector', 'voter'
        ])
        
        # Candidato nombre
        mapping['candidato_nombre'] = buscar_columna([
            'candidato_nombre', 'candidato', 'nombre_candidato', 
            'postulante', 'aspirante', 'candidate', 'electo'
        ])
        
        # Partido
        mapping['candidato_partido'] = buscar_columna([
            'candidato_partido', 'partido', 'partido_politico', 
            'organizacion', 'agrupacion', 'party', 'movimiento'
        ])
        
        # Ubicación
        mapping['departamento'] = buscar_columna([
            'departamento', 'region', 'estado', 'dept'
        ])
        
        mapping['provincia'] = buscar_columna([
            'provincia', 'county', 'prov'
        ])
        
        mapping['distrito'] = buscar_columna([
            'distrito', 'municipality', 'localidad', 'dist'
        ])
        
        # Fecha
        mapping['fecha_voto'] = buscar_columna([
            'fecha_voto', 'fecha', 'fecha_votacion', 
            'timestamp', 'date', 'hora'
        ])
        
        # Filtrar None values
        mapping = {k: v for k, v in mapping.items() if v is not None}
        
        print(f"✅ Mapeo detectado: {mapping}")
        
        return mapping


# ============================================
# ENDPOINTS
# ============================================

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)) -> Dict:
    """
    Endpoint para cargar CSV, detectar tipo automáticamente y guardar en tabla temporal
    
    Flujo:
    1. Lee el archivo CSV
    2. Detecta tipo de elección (presidencial, regional, distrital)
    3. Procesa y limpia datos
    4. Guarda en tabla temporal correspondiente
    5. Retorna estadísticas
    """
    try:
        # Validar formato
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos CSV"
            )
        
        print(f"📁 Procesando archivo: {file.filename}")
        
        # Leer CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="El archivo CSV está vacío"
            )
        
        print(f"📊 CSV cargado: {len(df)} filas, {len(df.columns)} columnas")
        
        # Generar batch_id único
        batch_id = str(uuid.uuid4())
        
        # 1. DETECTAR TIPO
        tipo_eleccion = CSVDetector.detectar_tipo(df)
        
        # 2. PROCESAR Y GUARDAR
        resultado = CSVProcessor.procesar_csv(df, tipo_eleccion, batch_id)
        
        # 3. REGISTRAR EN LOG
        supabase_client.table("log_limpieza_datos").insert({
            "batch_id": batch_id,
            "tipo_eleccion": tipo_eleccion,
            "total_registros": resultado["total_procesados"],
            "registros_validos": resultado["registros_validos"],
            "registros_con_nulos": 0,  # Se calculará en limpieza
            "registros_duplicados": 0,  # Se calculará en limpieza
            "registros_normalizados": 0,  # Se calculará en limpieza
            "fecha_inicio": datetime.utcnow().isoformat(),
            "fecha_fin": datetime.utcnow().isoformat(),
            "estado": "cargado",
            "detalles": {
                "archivo_nombre": file.filename,
                "columnas_detectadas": list(df.columns),
                "tabla_destino": resultado["tabla_destino"]
            }
        }).execute()
        
        return {
            "success": True,
            "message": f"CSV procesado y guardado en {resultado['tabla_destino']}",
            "tipo_detectado": tipo_eleccion,
            "batch_id": batch_id,
            "estadisticas": {
                "total_filas": resultado["total_procesados"],
                "registros_validos": resultado["registros_validos"],
                "registros_con_errores": resultado["registros_con_errores"],
                "porcentaje_exito": round(
                    (resultado["registros_validos"] / resultado["total_procesados"]) * 100, 2
                ) if resultado["total_procesados"] > 0 else 0
            },
            "tabla_destino": resultado["tabla_destino"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error procesando CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)}"
        )


@router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str) -> Dict:
    """Obtiene el estado de un batch procesado"""
    try:
        result = supabase_client.table("log_limpieza_datos") \
            .select("*") \
            .eq("batch_id", batch_id) \
            .single() \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        return {
            "success": True,
            "data": result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches/list")
async def list_batches() -> Dict:
    """Lista todos los batches procesados"""
    try:
        result = supabase_client.table("log_limpieza_datos") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()
        
        return {
            "success": True,
            "batches": result.data,
            "total": len(result.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch/{batch_id}")
async def delete_batch(batch_id: str) -> Dict:
    """
    Elimina un batch y todos sus registros de las tablas temporales
    """
    try:
        # Obtener info del batch
        batch_info = supabase_client.table("log_limpieza_datos") \
            .select("tipo_eleccion") \
            .eq("batch_id", batch_id) \
            .single() \
            .execute()
        
        if not batch_info.data:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        tipo = batch_info.data['tipo_eleccion']
        tabla_temporal = f"datos_temp_{tipo}es"
        
        # Eliminar registros de tabla temporal
        supabase_client.table(tabla_temporal) \
            .delete() \
            .eq("batch_id", batch_id) \
            .execute()
        
        # Eliminar del log
        supabase_client.table("log_limpieza_datos") \
            .delete() \
            .eq("batch_id", batch_id) \
            .execute()
        
        return {
            "success": True,
            "message": f"Batch {batch_id} eliminado correctamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/{batch_id}/move-to-final")
async def move_batch_to_final(batch_id: str, replace_all: bool = False) -> Dict:
    """
    Mueve datos limpios del batch a las tablas finales
    
    Parámetros:
    - batch_id: ID del batch a procesar
    - replace_all: Si True, ELIMINA todos los datos actuales y los reemplaza
                   Si False, solo agrega nuevos (evita duplicados por DNI)
    
    Flujo:
    1. Lee datos de tabla temporal (datos_temp_X)
    2. Crea/actualiza votantes
    3. Busca/crea candidatos
    4. Registra votos en tabla final (votos_X)
    5. Marca batch como procesado
    """
    try:
        # 1. OBTENER INFO DEL BATCH
        batch_info = supabase_client.table("log_limpieza_datos") \
            .select("*") \
            .eq("batch_id", batch_id) \
            .single() \
            .execute()
        
        if not batch_info.data:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        tipo_eleccion = batch_info.data['tipo_eleccion']
        tabla_temporal = f"datos_temp_{tipo_eleccion}es"
        tabla_votos_final = f"votos_{tipo_eleccion}es"
        
        print(f"\n🔄 Moviendo datos de {tabla_temporal} → {tabla_votos_final}")
        print(f"📋 Modo: {'REEMPLAZAR TODO' if replace_all else 'AGREGAR NUEVOS'}")
        
        # 2. LEER DATOS TEMPORALES
        datos_temp = supabase_client.table(tabla_temporal) \
            .select("*") \
            .eq("batch_id", batch_id) \
            .eq("estado_registro", "pendiente") \
            .execute()
        
        if not datos_temp.data:
            return {
                "success": False,
                "message": "No hay registros pendientes en este batch"
            }
        
        print(f"📊 Registros a procesar: {len(datos_temp.data)}")
        
        # 3. SI REPLACE_ALL = TRUE, ELIMINAR DATOS ACTUALES
        if replace_all:
            print(f"⚠️ ELIMINANDO todos los votos en {tabla_votos_final}...")
            
            # Eliminar todos los votos
            supabase_client.table(tabla_votos_final).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            
            print(f"✅ Tabla {tabla_votos_final} limpiada")
        
        # 4. PROCESAR REGISTROS
        votantes_creados = 0
        candidatos_creados = 0
        votos_registrados = 0
        errores = 0
        
        for registro in datos_temp.data:
            try:
                dni = registro['dni']
                
                # 4.1 CREAR/ACTUALIZAR VOTANTE
                votante_existe = supabase_client.table("votantes") \
                    .select("id") \
                    .eq("dni", dni) \
                    .execute()
                
                if votante_existe.data:
                    votante_id = votante_existe.data[0]['id']
                else:
                    # Dividir nombre completo
                    nombre_partes = registro['nombre_completo'].split()
                    nombres = nombre_partes[0] if len(nombre_partes) > 0 else "Sin nombre"
                    apellido_paterno = nombre_partes[1] if len(nombre_partes) > 1 else "Sin apellido"
                    apellido_materno = nombre_partes[2] if len(nombre_partes) > 2 else ""
                    
                    votante_nuevo = supabase_client.table("votantes").insert({
                        "dni": dni,
                        "nombres": nombres,
                        "apellido_paterno": apellido_paterno,
                        "apellido_materno": apellido_materno,
                        "departamento": registro['departamento'],
                        "provincia": registro['provincia'],
                        "distrito": registro['distrito']
                    }).execute()
                    
                    votante_id = votante_nuevo.data[0]['id']
                    votantes_creados += 1
                
                # 4.2 BUSCAR/CREAR CANDIDATO
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
                
                # 4.3 REGISTRAR VOTO (evitar duplicados si no es replace_all)
                if not replace_all:
                    voto_existe = supabase_client.table(tabla_votos_final) \
                        .select("id") \
                        .eq("dni_votante", dni) \
                        .execute()
                    
                    if voto_existe.data:
                        print(f"⏭️ Voto ya existe para DNI {dni}, omitiendo...")
                        continue
                
                # Insertar voto
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
                
                # Marcar registro como procesado
                supabase_client.table(tabla_temporal) \
                    .update({"estado_registro": "procesado"}) \
                    .eq("id", registro['id']) \
                    .execute()
                
            except Exception as e:
                print(f"❌ Error procesando registro {registro.get('id')}: {str(e)}")
                errores += 1
                continue
        
        # 5. ACTUALIZAR LOG
        supabase_client.table("log_limpieza_datos") \
            .update({
                "estado": "procesado",
                "fecha_fin": datetime.utcnow().isoformat(),
                "detalles": {
                    **batch_info.data.get('detalles', {}),
                    "votantes_creados": votantes_creados,
                    "candidatos_creados": candidatos_creados,
                    "votos_registrados": votos_registrados,
                    "errores": errores,
                    "modo": "reemplazar_todo" if replace_all else "agregar_nuevos"
                }
            }) \
            .eq("batch_id", batch_id) \
            .execute()
        
        print(f"\n✅ PROCESO COMPLETADO")
        print(f"   Votantes creados: {votantes_creados}")
        print(f"   Candidatos creados: {candidatos_creados}")
        print(f"   Votos registrados: {votos_registrados}")
        print(f"   Errores: {errores}")
        
        return {
            "success": True,
            "message": f"Datos movidos exitosamente a {tabla_votos_final}",
            "estadisticas": {
                "votantes_creados": votantes_creados,
                "candidatos_creados": candidatos_creados,
                "votos_registrados": votos_registrados,
                "errores": errores,
                "total_procesado": len(datos_temp.data),
                "modo": "reemplazar_todo" if replace_all else "agregar_nuevos"
            },
            "tabla_destino": tabla_votos_final
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error moviendo batch: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))