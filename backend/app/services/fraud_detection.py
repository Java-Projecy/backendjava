# app/services/fraud_detection.py
from typing import Dict, List
from datetime import datetime, timedelta
from app.config.settings import supabase_client
import pandas as pd
from collections import Counter
import numpy as np


class FraudDetectionService:
    """
    Servicio de Detección de Fraudes Electorales
    Implementa múltiples algoritmos para detectar anomalías y patrones sospechosos
    """
    
    @staticmethod
    async def analizar_fraudes() -> Dict:
        """
        Ejecuta todos los análisis de fraude y retorna un reporte completo
        """
        try:
            print("🔍 Iniciando análisis de fraudes...")
            
            # Cargar datos
            votantes = supabase_client.table("votantes").select("*").execute()
            votos_pres = supabase_client.table("votos_presidenciales").select("*").execute()
            votos_reg = supabase_client.table("votos_regionales").select("*").execute()
            votos_dist = supabase_client.table("votos_distritales").select("*").execute()
            
            df_votantes = pd.DataFrame(votantes.data)
            
            # Combinar todos los votos
            all_votes = []
            if votos_pres.data:
                all_votes.extend([{**v, 'tipo': 'presidencial'} for v in votos_pres.data])
            if votos_reg.data:
                all_votes.extend([{**v, 'tipo': 'regional'} for v in votos_reg.data])
            if votos_dist.data:
                all_votes.extend([{**v, 'tipo': 'distrital'} for v in votos_dist.data])
            
            df_votes = pd.DataFrame(all_votes)
            
            if df_votes.empty:
                return {
                    "success": True,
                    "message": "No hay votos para analizar",
                    "total_votos": 0,
                    "fraudes_detectados": 0,
                    "nivel_riesgo": "bajo",
                    "anomalias": []
                }
            
            # Ejecutar análisis
            anomalias = []
            
            # 1. Votos duplicados (mismo DNI, múltiples votos del mismo tipo)
            duplicados = await FraudDetectionService._detectar_votos_duplicados(df_votes)
            if duplicados:
                anomalias.extend(duplicados)
            
            # 2. Votantes inexistentes
            votantes_inexistentes = await FraudDetectionService._detectar_votantes_inexistentes(df_votes, df_votantes)
            if votantes_inexistentes:
                anomalias.extend(votantes_inexistentes)
            
            # 3. Patrones temporales sospechosos
            patrones_temporales = await FraudDetectionService._detectar_patrones_temporales(df_votes)
            if patrones_temporales:
                anomalias.extend(patrones_temporales)
            
            # 4. Concentración geográfica anormal
            concentracion_geografica = await FraudDetectionService._detectar_concentracion_geografica(df_votes)
            if concentracion_geografica:
                anomalias.extend(concentracion_geografica)
            
            # 5. DNIs inválidos
            dnis_invalidos = await FraudDetectionService._detectar_dnis_invalidos(df_votes)
            if dnis_invalidos:
                anomalias.extend(dnis_invalidos)
            
            # Calcular nivel de riesgo
            total_votos = len(df_votes)
            total_anomalias = len(anomalias)
            porcentaje_fraude = (total_anomalias / total_votos * 100) if total_votos > 0 else 0
            
            if porcentaje_fraude < 1:
                nivel_riesgo = "bajo"
            elif porcentaje_fraude < 5:
                nivel_riesgo = "medio"
            else:
                nivel_riesgo = "alto"
            
            # Guardar en log
            try:
                supabase_client.table("fraud_detection_log").insert({
                    "total_votos_analizados": total_votos,
                    "anomalias_detectadas": total_anomalias,
                    "porcentaje_fraude": round(porcentaje_fraude, 2),
                    "nivel_riesgo": nivel_riesgo,
                    "detalles": {
                        "tipos_anomalias": {
                            "votos_duplicados": len([a for a in anomalias if a['tipo'] == 'voto_duplicado']),
                            "votantes_inexistentes": len([a for a in anomalias if a['tipo'] == 'votante_inexistente']),
                            "patron_temporal": len([a for a in anomalias if a['tipo'] == 'patron_temporal']),
                            "concentracion_geografica": len([a for a in anomalias if a['tipo'] == 'concentracion_geografica']),
                            "dni_invalido": len([a for a in anomalias if a['tipo'] == 'dni_invalido'])
                        }
                    },
                    "analyzed_at": datetime.utcnow().isoformat()
                }).execute()
            except Exception as e:
                print(f"⚠️ Error guardando log: {e}")
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "total_votos": total_votos,
                "fraudes_detectados": total_anomalias,
                "porcentaje_fraude": round(porcentaje_fraude, 2),
                "nivel_riesgo": nivel_riesgo,
                "anomalias": anomalias[:100],  # Limitar a 100 para no saturar
                "resumen_por_tipo": {
                    "votos_duplicados": len([a for a in anomalias if a['tipo'] == 'voto_duplicado']),
                    "votantes_inexistentes": len([a for a in anomalias if a['tipo'] == 'votante_inexistente']),
                    "patrones_temporales": len([a for a in anomalias if a['tipo'] == 'patron_temporal']),
                    "concentracion_geografica": len([a for a in anomalias if a['tipo'] == 'concentracion_geografica']),
                    "dnis_invalidos": len([a for a in anomalias if a['tipo'] == 'dni_invalido'])
                }
            }
        
        except Exception as e:
            print(f"❌ Error en análisis de fraudes: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def _detectar_votos_duplicados(df_votes: pd.DataFrame) -> List[Dict]:
        """Detecta DNIs que votaron múltiples veces en la misma elección"""
        anomalias = []
        
        # Agrupar por DNI y tipo de elección
        duplicados = df_votes.groupby(['dni_votante', 'tipo']).size()
        duplicados = duplicados[duplicados > 1]
        
        for (dni, tipo), count in duplicados.items():
            anomalias.append({
                "tipo": "voto_duplicado",
                "severidad": "alta",
                "dni": dni,
                "descripcion": f"DNI {dni} votó {count} veces en elección {tipo}",
                "cantidad_votos": int(count),
                "tipo_eleccion": tipo
            })
        
        return anomalias
    
    @staticmethod
    async def _detectar_votantes_inexistentes(df_votes: pd.DataFrame, df_votantes: pd.DataFrame) -> List[Dict]:
        """Detecta votos de DNIs que no están registrados como votantes"""
        anomalias = []
        
        if df_votantes.empty:
            return anomalias
        
        dnis_votantes = set(df_votantes['dni'].values)
        dnis_votos = set(df_votes['dni_votante'].values)
        
        dnis_inexistentes = dnis_votos - dnis_votantes
        
        for dni in dnis_inexistentes:
            votos_dni = df_votes[df_votes['dni_votante'] == dni]
            anomalias.append({
                "tipo": "votante_inexistente",
                "severidad": "alta",
                "dni": dni,
                "descripcion": f"DNI {dni} no está registrado como votante pero tiene {len(votos_dni)} voto(s)",
                "cantidad_votos": len(votos_dni)
            })
        
        return anomalias
    
    @staticmethod
    async def _detectar_patrones_temporales(df_votes: pd.DataFrame) -> List[Dict]:
        """Detecta patrones temporales sospechosos (muchos votos en poco tiempo)"""
        anomalias = []
        
        if 'fecha_voto' not in df_votes.columns:
            return anomalias
        
        try:
            df_votes['fecha_voto_dt'] = pd.to_datetime(df_votes['fecha_voto'], errors='coerce')
            df_votes = df_votes.dropna(subset=['fecha_voto_dt'])
            
            if df_votes.empty:
                return anomalias
            
            # Agrupar por minuto
            df_votes['minuto'] = df_votes['fecha_voto_dt'].dt.floor('min')
            votos_por_minuto = df_votes.groupby('minuto').size()
            
            # Detectar picos (más de 50 votos por minuto es sospechoso)
            umbral = 50
            picos = votos_por_minuto[votos_por_minuto > umbral]
            
            for minuto, count in picos.items():
                anomalias.append({
                    "tipo": "patron_temporal",
                    "severidad": "media",
                    "descripcion": f"{count} votos registrados en 1 minuto ({minuto.strftime('%Y-%m-%d %H:%M')})",
                    "cantidad_votos": int(count),
                    "timestamp": minuto.isoformat()
                })
        
        except Exception as e:
            print(f"Error en detección temporal: {e}")
        
        return anomalias
    
    @staticmethod
    async def _detectar_concentracion_geografica(df_votes: pd.DataFrame) -> List[Dict]:
        """Detecta concentración anormal de votos en una ubicación"""
        anomalias = []
        
        if 'departamento' not in df_votes.columns:
            return anomalias
        
        # Analizar por departamento
        votos_por_dept = df_votes.groupby('departamento').size()
        total_votos = len(df_votes)
        
        for dept, count in votos_por_dept.items():
            porcentaje = (count / total_votos * 100) if total_votos > 0 else 0
            
            # Si un departamento tiene más del 60% de los votos, es sospechoso
            if porcentaje > 60:
                anomalias.append({
                    "tipo": "concentracion_geografica",
                    "severidad": "media",
                    "departamento": dept,
                    "descripcion": f"Concentración anormal: {porcentaje:.1f}% de votos en {dept}",
                    "porcentaje": round(porcentaje, 2),
                    "cantidad_votos": int(count)
                })
        
        return anomalias
    
    @staticmethod
    async def _detectar_dnis_invalidos(df_votes: pd.DataFrame) -> List[Dict]:
        """Detecta DNIs con formato inválido"""
        anomalias = []
        
        for _, row in df_votes.iterrows():
            dni = str(row.get('dni_votante', ''))
            
            # Validar longitud
            if len(dni) != 8:
                anomalias.append({
                    "tipo": "dni_invalido",
                    "severidad": "alta",
                    "dni": dni,
                    "descripcion": f"DNI con longitud inválida: {dni} (longitud: {len(dni)})"
                })
                continue
            
            # Validar que sean solo números
            if not dni.isdigit():
                anomalias.append({
                    "tipo": "dni_invalido",
                    "severidad": "alta",
                    "dni": dni,
                    "descripcion": f"DNI contiene caracteres no numéricos: {dni}"
                })
                continue
            
            # Detectar patrones sospechosos (todos los dígitos iguales)
            if len(set(dni)) == 1:
                anomalias.append({
                    "tipo": "dni_invalido",
                    "severidad": "media",
                    "dni": dni,
                    "descripcion": f"DNI con patrón sospechoso (todos los dígitos iguales): {dni}"
                })
        
        return anomalias
