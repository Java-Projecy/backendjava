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

# app/routes/upload.py - REEMPLAZAR TODA LA CLASE CSVDetector

class CSVDetector:
    """
    ✅ DETECTOR INTELIGENTE v2.0
    
    Estrategia PRIORIZADA:
    1. Si encuentra candidato_id (UUID) → Busca en BD (100% preciso)
    2. Si no, analiza nombres de candidatos → Busca en BD
    3. Si no, usa análisis de columnas y contenido
    """
    
    @staticmethod
    def detectar_tipo(df: pd.DataFrame) -> str:
        """
        Detecta el tipo de elección con múltiples estrategias
        """
        print("\n🔍 ========================================")
        print("   INICIANDO DETECCIÓN DE TIPO DE ELECCIÓN")
        print("========================================")
        
        from app.config.settings import supabase_client
        
        # ====================================
        # ESTRATEGIA 1: BUSCAR POR UUID (candidato_id)
        # ====================================
        print("\n🆔 Estrategia 1: Buscando por candidato_id (UUID)...")
        
        # Detectar columna de candidato_id
        candidato_id_col = None
        for col in df.columns:
            if col.lower().strip() in ['candidato_id', 'candidatoid', 'candidate_id']:
                candidato_id_col = col
                break
        
        if candidato_id_col:
            print(f"   ✓ Columna UUID encontrada: '{candidato_id_col}'")
            
            # Obtener primer UUID válido
            for idx, row in df.head(10).iterrows():  # Revisar primeras 10 filas
                uuid_value = str(row[candidato_id_col]).strip()
                
                # Validar que parezca UUID (tiene guiones y longitud correcta)
                if len(uuid_value) >= 30 and '-' in uuid_value:
                    print(f"   → UUID detectado: {uuid_value}")
                    
                    try:
                        # Buscar en BD
                        result = supabase_client.table("candidatos")\
                            .select("tipo_eleccion, nombre")\
                            .eq("id", uuid_value.lower())\
                            .execute()
                        
                        if result.data and len(result.data) > 0:
                            tipo_detectado = result.data[0]['tipo_eleccion'].lower().strip()
                            nombre_candidato = result.data[0]['nombre']
                            
                            print(f"   ✅ CANDIDATO ENCONTRADO EN BD:")
                            print(f"      - Nombre: {nombre_candidato}")
                            print(f"      - Tipo: {tipo_detectado.upper()}")
                            print(f"\n✅ DETECCIÓN EXITOSA POR UUID")
                            print("========================================\n")
                            
                            return tipo_detectado
                        else:
                            print(f"   ⚠️ UUID no encontrado en BD: {uuid_value}")
                    
                    except Exception as e:
                        print(f"   ⚠️ Error buscando UUID: {e}")
                        continue
            
            print("   ⚠️ No se encontraron UUIDs válidos en candidato_id")
        else:
            print("   ⚠️ Columna 'candidato_id' no encontrada")
        
        # ====================================
        # ESTRATEGIA 2: BUSCAR POR NOMBRE DE CANDIDATO
        # ====================================
        print("\n👤 Estrategia 2: Buscando por nombre de candidato...")
        
        # Detectar columna de nombre de candidato
        candidato_nombre_col = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['candidato_nombre', 'candidato nombre', 'nombre_candidato', 
                            'candidato', 'nombre candidato', 'candidate_name']:
                candidato_nombre_col = col
                break
        
        if candidato_nombre_col:
            print(f"   ✓ Columna nombre encontrada: '{candidato_nombre_col}'")
            
            # Obtener primeros 5 nombres únicos
            nombres_unicos = df[candidato_nombre_col].dropna().unique()[:5]
            print(f"   → Nombres a buscar: {list(nombres_unicos)}")
            
            for nombre in nombres_unicos:
                nombre_str = str(nombre).strip()
                
                # Saltar si es UUID (no es nombre)
                if len(nombre_str) >= 30 and '-' in nombre_str:
                    continue
                
                if len(nombre_str) < 3:
                    continue
                
                try:
                    # Buscar en BD por nombre (fuzzy match)
                    result = supabase_client.table("candidatos")\
                        .select("tipo_eleccion, nombre")\
                        .ilike("nombre", f"%{nombre_str}%")\
                        .limit(1)\
                        .execute()
                    
                    if result.data and len(result.data) > 0:
                        tipo_detectado = result.data[0]['tipo_eleccion'].lower().strip()
                        nombre_completo = result.data[0]['nombre']
                        
                        print(f"   ✅ CANDIDATO ENCONTRADO:")
                        print(f"      - Buscado: {nombre_str}")
                        print(f"      - Encontrado: {nombre_completo}")
                        print(f"      - Tipo: {tipo_detectado.upper()}")
                        print(f"\n✅ DETECCIÓN EXITOSA POR NOMBRE")
                        print("========================================\n")
                        
                        return tipo_detectado
                
                except Exception as e:
                    print(f"   ⚠️ Error buscando '{nombre_str}': {e}")
                    continue
            
            print("   ⚠️ Ningún nombre encontrado en BD")
        else:
            print("   ⚠️ Columna de nombre de candidato no encontrada")
        
        # ====================================
        # ESTRATEGIA 3: ANÁLISIS DE CONTENIDO (FALLBACK)
        # ====================================
        print("\n📝 Estrategia 3: Análisis de contenido (fallback)...")
        
        keywords = {
            'presidencial': ['presidente', 'presidencial', 'vicepresidente', 'nacional'],
            'regional': ['gobernador', 'regional', 'region', 'provincia'],
            'distrital': ['alcalde', 'distrital', 'municipal', 'distrito']
        }
        
        scores = {'presidencial': 0, 'regional': 0, 'distrital': 0}
        
        # Analizar columnas
        columns_text = ' '.join(df.columns).lower()
        for tipo, words in keywords.items():
            for word in words:
                if word in columns_text:
                    scores[tipo] += 5
                    print(f"   → '{word}' en columnas (+5 {tipo})")
        
        # Analizar contenido (primeras 10 filas)
        sample_content = df.head(10).to_string().lower()
        for tipo, words in keywords.items():
            for word in words:
                count = sample_content.count(word)
                if count > 0:
                    scores[tipo] += count * 2
                    print(f"   → '{word}' en contenido x{count} (+{count*2} {tipo})")
        
        print(f"\n📊 Scores: {scores}")
        
        if max(scores.values()) > 0:
            tipo_detectado = max(scores, key=scores.get)
            print(f"\n⚠️ DETECCIÓN POR FALLBACK: {tipo_detectado.upper()}")
            print("========================================\n")
            return tipo_detectado
        
        # ====================================
        # ESTRATEGIA 4: DEFAULT (último recurso)
        # ====================================
        print("\n⚠️ NO SE PUDO DETECTAR AUTOMÁTICAMENTE")
        print("   Usando tipo por defecto: PRESIDENCIAL")
        print("========================================\n")
        
        return 'presidencial'  # Default seguro


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


# app/routes/upload.py - REEMPLAZAR el endpoint existente
@router.post("/batch/{batch_id}/move-to-final-replace")
async def move_batch_replace_all(batch_id: str) -> Dict:
    """
    ✅ MODO 1: REEMPLAZAR TODO
    
    1. BORRA todos los votos de la tabla final
    2. Migra datos limpios del batch
    """
    try:
        # 1️⃣ Obtener info del batch
        batch_info = supabase_client.table("log_limpieza_datos")\
            .select("*")\
            .eq("batch_id", batch_id)\
            .single()\
            .execute()
        
        if not batch_info.data:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        tipo_eleccion = batch_info.data['tipo_eleccion']
        tabla_temporal = f"datos_temp_{tipo_eleccion}es"
        tabla_votos_final = f"votos_{tipo_eleccion}es"
        
        print(f"🗑️ REEMPLAZAR TODO: Limpiando tabla {tabla_votos_final}...")
        
        # 2️⃣ BORRAR TODA LA TABLA FINAL
        supabase_client.table(tabla_votos_final)\
            .delete()\
            .neq("id", "00000000-0000-0000-0000-000000000000")\
            .execute()
        
        print(f"✅ Tabla {tabla_votos_final} limpiada")
        
        # 3️⃣ Obtener datos limpios
        datos_temp = supabase_client.table(tabla_temporal)\
            .select("*")\
            .eq("batch_id", batch_id)\
            .in_("estado_registro", ["pendiente", "limpio"])\
            .execute()
        
        if not datos_temp.data:
            return {
                "success": False, 
                "message": "No hay registros limpios para migrar"
            }
        
        print(f"📦 Migrando {len(datos_temp.data)} registros...")
        
        # 4️⃣ PROCESAR CADA REGISTRO (mismo código de antes)
        votantes_creados = 0
        votos_registrados = 0
        errores = []
        
        for idx, registro in enumerate(datos_temp.data, 1):
            try:
                # A. CREAR/OBTENER VOTANTE
                dni = registro['dni']
                if not dni or len(dni) != 8:
                    errores.append(f"DNI inválido: {dni}")
                    continue
                
                votante_existe = supabase_client.table("votantes")\
                    .select("id")\
                    .eq("dni", dni)\
                    .execute()
                
                if votante_existe.data:
                    votante_id = votante_existe.data[0]['id']
                else:
                    nombre_partes = registro['nombre_completo'].split()
                    votante_nuevo = supabase_client.table("votantes").insert({
                        "dni": dni,
                        "nombres": nombre_partes[0] if len(nombre_partes) > 0 else "Sin nombre",
                        "apellido_paterno": nombre_partes[1] if len(nombre_partes) > 1 else "Sin apellido",
                        "apellido_materno": nombre_partes[2] if len(nombre_partes) > 2 else "",
                        "departamento": registro.get('departamento', 'LIMA'),
                        "provincia": registro.get('provincia', 'LIMA'),
                        "distrito": registro.get('distrito', 'LIMA'),
                        "direccion": registro.get('direccion'),
                        "telefono": registro.get('telefono'),
                        "email": registro.get('email'),
                        "estado": "Activo"
                    }).execute()
                    
                    votante_id = votante_nuevo.data[0]['id']
                    votantes_creados += 1
                
                # B. OBTENER CANDIDATO POR UUID
                candidato_id = None
                candidato_uuid_raw = None

                for campo in ['candidato_id', 'candidato_nombre']:
                    if campo in registro and registro[campo]:
                        valor = str(registro[campo]).strip()
                        if len(valor) >= 30 and '-' in valor:
                            candidato_uuid_raw = valor
                            break

                if candidato_uuid_raw:
                    candidato_uuid = candidato_uuid_raw.lower()
                    result = supabase_client.table("candidatos")\
                        .select("id")\
                        .eq("id", candidato_uuid)\
                        .single()\
                        .execute()
                    
                    if result.data:
                        candidato_id = result.data['id']

                if not candidato_id:
                    errores.append(f"Candidato no encontrado: {candidato_uuid_raw}")
                    continue
                
                # C. INSERTAR VOTO (sin verificar duplicados)
                supabase_client.table(tabla_votos_final).insert({
                    "votante_id": votante_id,
                    "candidato_id": candidato_id,
                    "dni_votante": dni,
                    "departamento": registro.get('departamento', 'LIMA'),
                    "provincia": registro.get('provincia', 'LIMA'),
                    "distrito": registro.get('distrito', 'LIMA'),
                    "fecha_voto": registro.get('fecha_voto', datetime.utcnow().isoformat())
                }).execute()
                
                votos_registrados += 1
                
                # Marcar como procesado
                supabase_client.table(tabla_temporal)\
                    .update({"estado_registro": "procesado"})\
                    .eq("id", registro['id'])\
                    .execute()
                
            except Exception as e:
                error_msg = f"Error en registro {idx}: {str(e)}"
                print(f"   ❌ {error_msg}")
                errores.append(error_msg)
                continue
        
        # 5️⃣ Actualizar estado del batch
        supabase_client.table("log_limpieza_datos")\
            .update({
                "estado": "procesado",
                "fecha_fin": datetime.utcnow().isoformat(),
                "detalles": {
                    "votantes_creados": votantes_creados,
                    "votos_registrados": votos_registrados,
                    "errores": len(errores),
                    "modo": "REEMPLAZAR_TODO"
                }
            })\
            .eq("batch_id", batch_id)\
            .execute()
        
        print("\n" + "="*60)
        print(f"✅ REEMPLAZO COMPLETADO")
        print(f"   🗑️ Tabla limpiada: {tabla_votos_final}")
        print(f"   📊 Votantes creados: {votantes_creados}")
        print(f"   📊 Votos registrados: {votos_registrados}")
        print(f"   ⚠️ Errores: {len(errores)}")
        print("="*60)
        
        return {
            "success": True,
            "message": f"✅ Datos REEMPLAZADOS en {tabla_votos_final}",
            "modo": "REEMPLAZAR_TODO",
            "estadisticas": {
                "tabla_limpiada": tabla_votos_final,
                "votantes_creados": votantes_creados,
                "votos_registrados": votos_registrados,
                "total_procesado": len(datos_temp.data),
                "errores": len(errores),
                "errores_detalle": errores[:10] if errores else []
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en reemplazo: {str(e)}")

@router.post("/batch/{batch_id}/move-to-final-append")
async def move_batch_to_final(batch_id: str, replace_all: bool = False) -> Dict:
    """
    ✅ MIGRA DATOS LIMPIOS de tablas temporales a tablas finales
    
    Proceso:
    1. Lee datos limpios de datos_temp_{tipo}
    2. Crea/encuentra votantes en 'votantes'
    3. Crea/encuentra candidatos en 'candidatos'
    4. Inserta votos en votos_{tipo} con UUIDs correctos
    """
    try:
        # 1️⃣ Obtener info del batch
        batch_info = supabase_client.table("log_limpieza_datos")\
            .select("*")\
            .eq("batch_id", batch_id)\
            .single()\
            .execute()
        
        if not batch_info.data:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        tipo_eleccion = batch_info.data['tipo_eleccion']
        tabla_temporal = f"datos_temp_{tipo_eleccion}es"
        tabla_votos_final = f"votos_{tipo_eleccion}es"
        
        print(f"📦 Migrando batch {batch_id} → {tipo_eleccion}")
        
        # 2️⃣ Obtener datos LIMPIOS (estado='pendiente' o 'limpio')
        datos_temp = supabase_client.table(tabla_temporal)\
            .select("*")\
            .eq("batch_id", batch_id)\
            .in_("estado_registro", ["pendiente", "limpio"])\
            .execute()
        
        if not datos_temp.data:
            return {
                "success": False, 
                "message": "No hay registros limpios para migrar"
            }
        
        print(f"✅ Registros a migrar: {len(datos_temp.data)}")
        
        # 3️⃣ Opcional: Limpiar tabla final si replace_all=True
        if replace_all:
            print("🗑️ Limpiando tabla final...")
            supabase_client.table(tabla_votos_final)\
                .delete()\
                .neq("id", "00000000-0000-0000-0000-000000000000")\
                .execute()
        
        # 4️⃣ PROCESAR CADA REGISTRO
        votantes_creados = 0
        candidatos_creados = 0
        votos_registrados = 0
        errores = []
        
        for idx, registro in enumerate(datos_temp.data, 1):
            try:
                print(f"\n📝 Procesando {idx}/{len(datos_temp.data)}")
                
                # ==========================================
                # A. CREAR/OBTENER VOTANTE
                # ==========================================
                dni = registro['dni']
                if not dni or len(dni) != 8:
                    errores.append(f"DNI inválido: {dni}")
                    continue
                
                # Buscar votante existente
                votante_existe = supabase_client.table("votantes")\
                    .select("id")\
                    .eq("dni", dni)\
                    .execute()
                
                if votante_existe.data:
                    votante_id = votante_existe.data[0]['id']
                    print(f"   ✓ Votante encontrado: {votante_id}")
                else:
                    # Crear nuevo votante
                    nombre_partes = registro['nombre_completo'].split()
                    votante_nuevo = supabase_client.table("votantes").insert({
                        "dni": dni,
                        "nombres": nombre_partes[0] if len(nombre_partes) > 0 else "Sin nombre",
                        "apellido_paterno": nombre_partes[1] if len(nombre_partes) > 1 else "Sin apellido",
                        "apellido_materno": nombre_partes[2] if len(nombre_partes) > 2 else "",
                        "departamento": registro.get('departamento', 'LIMA'),
                        "provincia": registro.get('provincia', 'LIMA'),
                        "distrito": registro.get('distrito', 'LIMA'),
                        "direccion": registro.get('direccion'),
                        "telefono": registro.get('telefono'),
                        "email": registro.get('email'),
                        "estado": "Activo"
                    }).execute()
                    
                    votante_id = votante_nuevo.data[0]['id']
                    votantes_creados += 1
                    print(f"   ✓ Votante creado: {votante_id}")
                
                # ==========================================
                # B. OBTENER CANDIDATO POR UUID (en candidato_nombre o candidato_id)
                # ==========================================
                candidato_id = None
                candidato_uuid_raw = None

                # Buscar el UUID en cualquiera de estos campos (tu CSV lo pone en candidato_nombre)
                for campo in ['candidato_id', 'candidato_nombre']:
                    if campo in registro and registro[campo]:
                        valor = str(registro[campo]).strip()
                        if len(valor) >= 30 and '-' in valor:  # parece UUID
                            candidato_uuid_raw = valor
                            break

                if candidato_uuid_raw:
                    # Normalizar a minúsculas (Supabase guarda UUIDs en minúsculas)
                    candidato_uuid = candidato_uuid_raw.lower()
                    result = supabase_client.table("candidatos")\
                        .select("id")\
                        .eq("id", candidato_uuid)\
                        .single()\
                        .execute()
                    
                    if result.data:
                        candidato_id = result.data['id']
                        print(f"   CANDIDATO ENCONTRADO POR UUID: {candidato_id}")
                    else:
                        print(f"   UUID no encontrado en candidatos: {candidato_uuid_raw}")
                else:
                    # Solo si NO hay UUID → buscar por nombre + partido (fallback)
                    nombre = registro.get('candidato_nombre', '').strip()
                    partido = registro.get('candidato_partido', 'SIN PARTIDO').strip().upper()
                    
                    if nombre and nombre.upper() not in ['NO-ID', 'NULO', 'SIN CANDIDATO']:
                        result = supabase_client.table("candidatos")\
                            .select("id")\
                            .eq("nombre", nombre)\
                            .eq("partido", partido)\
                            .eq("tipo_eleccion", tipo_eleccion)\
                            .single()\
                            .execute()
                        
                        if result.data:
                            candidato_id = result.data[0]['id']
                            print(f"   Candidato encontrado por nombre: {nombre}")
                        else:
                            print(f"   CANDIDATO NO ENCONTRADO → VOTO SALTADO: {nombre} ({partido})")
                    else:
                        print("   Voto en blanco o sin candidato")

                if not candidato_id:
                    errores.append(f"Voto saltado - candidato no encontrado: {candidato_uuid_raw or registro.get('candidato_nombre')}")
                    continue
                
                # ==========================================
                # C. INSERTAR VOTO (si no existe ya)
                # ==========================================
                if not replace_all:
                    voto_existe = supabase_client.table(tabla_votos_final)\
                        .select("id")\
                        .eq("dni_votante", dni)\
                        .execute()
                    
                    if voto_existe.data:
                        print(f"   ⚠️ Voto ya existe, saltando...")
                        continue
                
                # Insertar voto con UUIDs correctos
                supabase_client.table(tabla_votos_final).insert({
                    "votante_id": votante_id,      # ✅ UUID
                    "candidato_id": candidato_id,  # ✅ UUID
                    "dni_votante": dni,
                    "departamento": registro.get('departamento', 'LIMA'),
                    "provincia": registro.get('provincia', 'LIMA'),
                    "distrito": registro.get('distrito', 'LIMA'),
                    "fecha_voto": registro.get('fecha_voto', datetime.utcnow().isoformat())
                }).execute()
                
                votos_registrados += 1
                print(f"   ✅ Voto registrado")
                
                # Marcar como procesado en tabla temporal
                supabase_client.table(tabla_temporal)\
                    .update({"estado_registro": "procesado"})\
                    .eq("id", registro['id'])\
                    .execute()
                
            except Exception as e:
                error_msg = f"Error en registro {idx}: {str(e)}"
                print(f"   ❌ {error_msg}")
                errores.append(error_msg)
                continue
        
        # 5️⃣ Actualizar estado del batch
        supabase_client.table("log_limpieza_datos")\
            .update({
                "estado": "procesado",
                "fecha_fin": datetime.utcnow().isoformat(),
                "detalles": {
                    "votantes_creados": votantes_creados,
                    "candidatos_creados": candidatos_creados,
                    "votos_registrados": votos_registrados,
                    "errores": len(errores)
                }
            })\
            .eq("batch_id", batch_id)\
            .execute()
        
        print("\n" + "="*60)
        print(f"✅ MIGRACIÓN COMPLETADA")
        print(f"   📊 Votantes creados: {votantes_creados}")
        print(f"   📊 Candidatos creados: {candidatos_creados}")
        print(f"   📊 Votos registrados: {votos_registrados}")
        print(f"   ⚠️ Errores: {len(errores)}")
        print("="*60)
        
        return {
            "success": True,
            "message": f"✅ Datos migrados exitosamente a {tabla_votos_final}",
            "estadisticas": {
                "votantes_creados": votantes_creados,
                "candidatos_creados": candidatos_creados,
                "votos_registrados": votos_registrados,
                "total_procesado": len(datos_temp.data),
                "errores": len(errores),
                "errores_detalle": errores[:10] if errores else []
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en migración: {str(e)}")