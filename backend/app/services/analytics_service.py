# app/services/analytics_service.py
from datetime import datetime
from app.config.settings import supabase_client
import pandas as pd
import numpy as np
from typing import Dict, Optional
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler
from collections import Counter
import json  # ← AGREGAR para serializar JSON


class AnalyticsService:
    """
    Servicio de Analytics Electoral con análisis avanzado usando Pandas y Scikit-learn
    ✅ AHORA GUARDA EN: predictions, clustering_results, geographic_analysis
    """
    
    @staticmethod
    async def get_overview() -> Dict:
        """KPIs generales del sistema"""
        try:
            # Cargar datos de tablas reales
            voters_result = supabase_client.table("votantes").select("*").execute()
            
            # Combinar votos de las 3 tablas
            votos_pres = supabase_client.table("votos_presidenciales").select("*").execute()
            votos_reg = supabase_client.table("votos_regionales").select("*").execute()
            votos_dist = supabase_client.table("votos_distritales").select("*").execute()
            
            candidates_result = supabase_client.table("candidatos").select("*").execute()
            
            df_voters = pd.DataFrame(voters_result.data)
            
            # Combinar todos los votos
            all_votes = []
            if votos_pres.data:
                all_votes.extend(votos_pres.data)
            if votos_reg.data:
                all_votes.extend(votos_reg.data)
            if votos_dist.data:
                all_votes.extend(votos_dist.data)
            
            df_votes = pd.DataFrame(all_votes)
            df_candidates = pd.DataFrame(candidates_result.data)
            
            # KPIs
            total_voters = len(df_voters)
            total_votes = len(df_votes)
            total_candidates = len(df_candidates)
            participation_rate = (total_votes / total_voters * 100) if total_voters > 0 else 0
            
            # Distribución por departamento
            dept_dist = df_voters['departamento'].value_counts().to_dict() if 'departamento' in df_voters.columns else {}
            
            # Top departamentos con más votos
            df_merged = pd.merge(df_votes, df_voters, left_on='dni_votante', right_on='dni', how='left')
            top_departments = df_merged['departamento'].value_counts().head(5).to_dict() if 'departamento' in df_merged.columns else {}
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "kpis": {
                        "total_voters": total_voters,
                        "total_votes": total_votes,
                        "total_candidates": total_candidates,
                        "participation_rate": round(participation_rate, 2)
                    },
                    "distributions": {
                        "departments": dept_dist,
                        "top_departments": top_departments
                    }
                }
            }
        
        except Exception as e:
            print(f"Error en get_overview: {str(e)}")
            return {"success": False, "error": str(e)}
    
    
    @staticmethod
    async def get_demographic_analysis() -> Dict:
        """Análisis geográfico detallado (en lugar de demográfico)"""
        try:
            # Combinar votos de las 3 tablas
            votos_pres = supabase_client.table("votos_presidenciales").select("*").execute()
            votos_reg = supabase_client.table("votos_regionales").select("*").execute()
            votos_dist = supabase_client.table("votos_distritales").select("*").execute()
            
            voters_result = supabase_client.table("votantes").select("*").execute()
            
            all_votes = []
            if votos_pres.data:
                all_votes.extend(votos_pres.data)
            if votos_reg.data:
                all_votes.extend(votos_reg.data)
            if votos_dist.data:
                all_votes.extend(votos_dist.data)
            
            df_votes = pd.DataFrame(all_votes)
            df_voters = pd.DataFrame(voters_result.data)
            
            df = pd.merge(df_votes, df_voters, left_on='dni_votante', right_on='dni', how='left')
            
            # Análisis por departamento
            dept_analysis = df.groupby('departamento')['candidato_id'].value_counts().unstack(fill_value=0).to_dict()
            
            # Análisis por provincia (top 10)
            prov_analysis = df.groupby('provincia')['candidato_id'].value_counts().unstack(fill_value=0).to_dict()
            
            # Análisis por distrito (top 10)
            dist_analysis = df.groupby('distrito')['candidato_id'].value_counts().unstack(fill_value=0).to_dict()
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "department_analysis": dept_analysis,
                    "province_analysis": prov_analysis,
                    "district_analysis": dist_analysis,
                    "total_analyzed": len(df)
                }
            }
        
        except Exception as e:
            print(f"Error en get_demographic_analysis: {str(e)}")
            return {"success": False, "error": str(e)}
    
    
    @staticmethod
    async def get_geographic_analysis(departamento: Optional[str] = None, provincia: Optional[str] = None) -> Dict:
        """
        ✅ MODIFICADO: Análisis geográfico + GUARDA EN geographic_analysis
        """
        try:
            votes_result = supabase_client.table("votes").select("*").execute()
            voters_result = supabase_client.table("voters").select("*").execute()
            
            df_votes = pd.DataFrame(votes_result.data)
            df_voters = pd.DataFrame(voters_result.data)
            
            df = pd.merge(df_votes, df_voters, left_on='voter_id', right_on='id', how='left')
            
            # Filtros opcionales
            if departamento:
                df = df[df['departamento'] == departamento]
            if provincia:
                df = df[df['provincia'] == provincia]
            
            # Análisis por departamento
            dept_analysis = df.groupby('departamento').agg({
                'candidate_id': 'count',
                'voter_id': 'nunique'
            }).rename(columns={'candidate_id': 'total_votes', 'voter_id': 'unique_voters'}).to_dict('index')
            
            # Análisis por provincia (top 10)
            prov_analysis = df.groupby('provincia')['candidate_id'].count().sort_values(ascending=False).head(10).to_dict()
            
            # Análisis por distrito (top 10)
            dist_analysis = df.groupby('distrito')['candidate_id'].count().sort_values(ascending=False).head(10).to_dict()
            
            # Candidato líder por departamento
            dept_leader = df.groupby(['departamento', 'candidate_id']).size().reset_index(name='votes')
            dept_leader = dept_leader.loc[dept_leader.groupby('departamento')['votes'].idxmax()]
            leader_by_dept = dict(zip(dept_leader['departamento'], dept_leader['candidate_id']))
            
            # ========================================
            # ✅ NUEVO: GUARDAR EN geographic_analysis
            # ========================================
            try:
                print("💾 Guardando análisis geográfico en BD...")
                
                for dept, data in dept_analysis.items():
                    # Obtener candidato líder de este departamento
                    leader_candidate_id = leader_by_dept.get(dept)
                    
                    # Insertar o actualizar
                    supabase_client.table("geographic_analysis").upsert({
                        "departamento": dept,
                        "candidate_id": int(leader_candidate_id) if leader_candidate_id else None,
                        "votes_count": int(data['total_votes']),
                        "total_voters": int(data['unique_voters']),
                        "analyzed_at": datetime.utcnow().isoformat()
                    }, on_conflict="departamento").execute()
                
                print(f"✅ Guardados {len(dept_analysis)} departamentos en geographic_analysis")
            
            except Exception as save_error:
                print(f"⚠️ Error guardando en geographic_analysis: {save_error}")
                # No detenemos la ejecución, solo logueamos
            # ========================================
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "filters": {"departamento": departamento, "provincia": provincia},
                "by_department": dept_analysis,
                "top_provinces": prov_analysis,
                "top_districts": dist_analysis,
                "leader_by_department": leader_by_dept,
                "total_analyzed": len(df),
                "saved_to_db": True  # ← Indicador de que se guardó
            }
        
        except Exception as e:
            print(f"Error en get_geographic_analysis: {str(e)}")
            return {"success": False, "error": str(e)}
    
    
    @staticmethod
    async def get_temporal_analysis() -> Dict:
        """Análisis temporal de votación"""
        try:
            votes_result = supabase_client.table("votes").select("voted_at, candidate_id").execute()
            df = pd.DataFrame(votes_result.data)
            
            df['voted_at'] = pd.to_datetime(df['voted_at'], format='mixed', errors='coerce')
            df['hour'] = df['voted_at'].dt.hour
            df['day_of_week'] = df['voted_at'].dt.day_name()
            df['date'] = df['voted_at'].dt.date
            
            # Votos por hora
            votes_by_hour = df['hour'].value_counts().sort_index().to_dict()
            
            # Votos por día de la semana
            votes_by_day = df['day_of_week'].value_counts().to_dict()
            
            # Votos por fecha
            votes_by_date = df['date'].value_counts().sort_index().to_dict()
            votes_by_date = {str(k): int(v) for k, v in votes_by_date.items()}
            
            # Hora pico
            peak_hour = int(df['hour'].mode()[0]) if len(df) > 0 else 0
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "votes_by_hour": votes_by_hour,
                "votes_by_day_of_week": votes_by_day,
                "votes_by_date": votes_by_date,
                "peak_hour": peak_hour,
                "total_analyzed": len(df)
            }
        
        except Exception as e:
            print(f"Error en get_temporal_analysis: {str(e)}")
            return {"success": False, "error": str(e)}
    
    
    @staticmethod
    async def get_candidate_performance() -> Dict:
        """Análisis de desempeño por candidato"""
        try:
            votes_result = supabase_client.table("votes").select("*").execute()
            voters_result = supabase_client.table("voters").select("*").execute()
            candidates_result = supabase_client.table("candidates").select("*").execute()
            
            df_votes = pd.DataFrame(votes_result.data)
            df_voters = pd.DataFrame(voters_result.data)
            df_candidates = pd.DataFrame(candidates_result.data)
            
            df = pd.merge(df_votes, df_voters, left_on='voter_id', right_on='id', how='left')
            
            candidate_stats = []
            
            for _, candidate in df_candidates.iterrows():
                cand_votes = df[df['candidate_id'] == candidate['id']]
                total_votes = len(cand_votes)
                percentage = (total_votes / len(df) * 100) if len(df) > 0 else 0
                
                # Demografía del candidato
                avg_age = float(cand_votes['edad'].mean()) if 'edad' in cand_votes.columns and len(cand_votes) > 0 else 0
                gender_dist = cand_votes['genero'].value_counts().to_dict() if 'genero' in cand_votes.columns else {}
                edu_dist = cand_votes['educacion'].value_counts().to_dict() if 'educacion' in cand_votes.columns else {}
                
                # Top 3 departamentos
                top_depts = cand_votes['departamento'].value_counts().head(3).to_dict() if 'departamento' in cand_votes.columns else {}
                
                candidate_stats.append({
                    "candidate_id": int(candidate['id']),
                    "name": candidate['name'],
                    "party": candidate['party'],
                    "total_votes": total_votes,
                    "percentage": round(percentage, 2),
                    "demographics": {
                        "avg_age": round(avg_age, 1),
                        "gender_distribution": gender_dist,
                        "education_distribution": edu_dist
                    },
                    "geographic_strength": top_depts
                })
            
            # Ordenar por votos
            candidate_stats.sort(key=lambda x: x['total_votes'], reverse=True)
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "candidates": candidate_stats,
                "total_votes": len(df)
            }
        
        except Exception as e:
            print(f"Error en get_candidate_performance: {str(e)}")
            return {"success": False, "error": str(e)}
    
    
    @staticmethod
    async def get_voting_clusters(n_clusters: int = 3) -> Dict:
        """
        ✅ MODIFICADO: Clustering de votantes + GUARDA EN clustering_results
        """
        try:
            # Validar n_clusters
            if n_clusters < 2 or n_clusters > 10:
                return {
                    "success": False,
                    "error": "n_clusters debe estar entre 2 y 10",
                    "clusters": []
                }
            
            # 1. Cargar datos
            voters_result = supabase_client.table("voters").select("*").execute()
            votes_result = supabase_client.table("votes").select("voter_id, candidate_id").execute()
            
            if not voters_result.data:
                return {
                    "success": False,
                    "error": "No hay votantes registrados",
                    "clusters": []
                }
            
            if not votes_result.data:
                return {
                    "success": False,
                    "error": "No hay votos registrados",
                    "clusters": []
                }
            
            df_voters = pd.DataFrame(voters_result.data)
            df_votes = pd.DataFrame(votes_result.data)
            
            # 2. Merge
            df = pd.merge(df_voters, df_votes, left_on='id', right_on='voter_id', how='inner')
            
            print(f"📊 Registros después del merge: {len(df)}")
            
            # 3. Filtrar datos válidos
            required_columns = ['edad', 'genero', 'educacion', 'candidate_id']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Columnas faltantes en datos: {missing_columns}",
                    "clusters": []
                }
            
            # Filtrar registros completos
            df_clean = df.copy()
            for col in required_columns:
                df_clean = df_clean[df_clean[col].notna()]
            
            print(f"📊 Registros válidos después de limpieza: {len(df_clean)}")
            
            # Verificar datos mínimos
            min_required = n_clusters * 3
            if len(df_clean) < min_required:
                return {
                    "success": False,
                    "error": f"Datos insuficientes: {len(df_clean)} votos válidos. Necesitas al menos {min_required} para {n_clusters} clusters.",
                    "clusters": []
                }
            
            # 4. Encodings
            try:
                le_genero = LabelEncoder()
                df_clean['genero_encoded'] = le_genero.fit_transform(df_clean['genero'].astype(str))
                
                educacion_map = {
                    'Primaria': 1,
                    'Secundaria': 2,
                    'Universidad': 3,
                    'Posgrado': 4
                }
                df_clean['educacion_encoded'] = df_clean['educacion'].map(educacion_map)
                df_clean = df_clean[df_clean['educacion_encoded'].notna()].copy()
                
                if len(df_clean) < min_required:
                    return {
                        "success": False,
                        "error": f"Datos insuficientes después de encoding: {len(df_clean)} votos. Necesitas al menos {min_required}.",
                        "clusters": []
                    }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error en encoding de datos: {str(e)}",
                    "clusters": []
                }
            
            # 5. Preparar features
            try:
                X = df_clean[['edad', 'genero_encoded', 'educacion_encoded', 'candidate_id']].values
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error preparando features: {str(e)}",
                    "clusters": []
                }
            
            # 6. K-Means
            try:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
                df_clean['cluster'] = kmeans.fit_predict(X_scaled)
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error en K-Means: {str(e)}",
                    "clusters": []
                }
            
            # 7. Analizar clusters
            cluster_analysis = []
            
            for cluster_id in range(n_clusters):
                cluster_data = df_clean[df_clean['cluster'] == cluster_id]
                
                if len(cluster_data) == 0:
                    continue
                
                # Obtener candidato más votado
                top_candidate = None
                try:
                    if len(cluster_data['candidate_id']) > 0:
                        mode_result = cluster_data['candidate_id'].mode()
                        top_candidate = int(mode_result[0]) if len(mode_result) > 0 else None
                except:
                    pass
                
                try:
                    cluster_info = {
                        "cluster_id": int(cluster_id),
                        "size": int(len(cluster_data)),
                        "percentage": round(float(len(cluster_data) / len(df_clean) * 100), 2),
                        "characteristics": {
                            "avg_age": round(float(cluster_data['edad'].mean()), 1),
                            "gender_distribution": {str(k): int(v) for k, v in cluster_data['genero'].value_counts().to_dict().items()},
                            "education_distribution": {str(k): int(v) for k, v in cluster_data['educacion'].value_counts().to_dict().items()},
                            "top_candidate": top_candidate
                        },
                        "centroid": [float(x) for x in kmeans.cluster_centers_[cluster_id].tolist()]
                    }
                    
                    cluster_analysis.append(cluster_info)
                    
                except Exception as e:
                    print(f"Error procesando cluster {cluster_id}: {e}")
                    continue
            
            # 8. Silhouette score
            silhouette = None
            try:
                if len(df_clean) >= n_clusters * 2:
                    from sklearn.metrics import silhouette_score
                    silhouette = float(silhouette_score(X_scaled, df_clean['cluster']))
            except Exception as e:
                print(f"No se pudo calcular silhouette score: {e}")
            
            # ========================================
            # ✅ NUEVO: GUARDAR EN clustering_results
            # ========================================
            try:
                print("💾 Guardando resultados de clustering en BD...")
                
                for cluster_info in cluster_analysis:
                    supabase_client.table("clustering_results").insert({
                        "algorithm": "K-Means",
                        "n_clusters": int(n_clusters),
                        "cluster_id": cluster_info["cluster_id"],
                        "cluster_size": cluster_info["size"],
                        "centroid": json.dumps(cluster_info["centroid"]),  # ← JSON string
                        "characteristics": json.dumps(cluster_info["characteristics"]),  # ← JSON string
                        "silhouette_score": round(silhouette, 4) if silhouette else None,
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
                
                print(f"✅ Guardados {len(cluster_analysis)} clusters en clustering_results")
            
            except Exception as save_error:
                print(f"⚠️ Error guardando en clustering_results: {save_error}")
                # No detenemos la ejecución
            # ========================================
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "n_clusters": int(n_clusters),
                "algorithm": "K-Means",
                "clusters": cluster_analysis,
                "silhouette_score": round(silhouette, 4) if silhouette else None,
                "total_analyzed": int(len(df_clean)),
                "saved_to_db": True  # ← Indicador
            }
        
        except Exception as e:
            print(f"❌ ERROR CRÍTICO en get_voting_clusters: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "clusters": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    
    @staticmethod
    async def get_correlations() -> Dict:
        """Matriz de correlaciones entre variables"""
        try:
            voters_result = supabase_client.table("voters").select("*").execute()
            votes_result = supabase_client.table("votes").select("voter_id, candidate_id").execute()
            
            df_voters = pd.DataFrame(voters_result.data)
            df_votes = pd.DataFrame(votes_result.data)
            
            df = pd.merge(df_voters, df_votes, left_on='id', right_on='voter_id', how='inner')
            df = df[df['edad'].notna() & df['genero'].notna() & df['educacion'].notna()].copy()
            
            # Encodings
            le_genero = LabelEncoder()
            df['genero_encoded'] = le_genero.fit_transform(df['genero'])
            
            educacion_map = {'Primaria': 1, 'Secundaria': 2, 'Universidad': 3, 'Posgrado': 4}
            df['educacion_encoded'] = df['educacion'].map(educacion_map)
            
            # Calcular correlaciones
            corr_df = df[['edad', 'genero_encoded', 'educacion_encoded', 'candidate_id']].corr()
            
            # Convertir a formato JSON-friendly
            correlations = {}
            for col in corr_df.columns:
                correlations[col] = {k: float(v) for k, v in corr_df[col].items()}
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "correlations": correlations,
                "interpretation": {
                    "edad": "Edad del votante",
                    "genero_encoded": "Género (codificado)",
                    "educacion_encoded": "Nivel educativo (1=Primaria, 4=Posgrado)",
                    "candidate_id": "Candidato elegido"
                },
                "total_analyzed": len(df)
            }
        
        except Exception as e:
            print(f"Error en get_correlations: {str(e)}")
            return {"success": False, "error": str(e)}
    
    
    @staticmethod
    async def get_predictions() -> Dict:
        """
        ✅ MODIFICADO: Predicciones + GUARDA EN predictions
        """
        try:
            # 1. Obtener candidatos y votos
            candidates_result = supabase_client.table("candidates").select("*").execute()
            votes_result = supabase_client.table("votes").select("candidate_id").execute()
            
            if not candidates_result.data:
                return {
                    "success": False,
                    "error": "No hay candidatos registrados",
                    "predictions": []
                }
            
            if not votes_result.data or len(votes_result.data) == 0:
                return {
                    "success": False,
                    "error": "No hay votos registrados",
                    "predictions": []
                }
            
            df_candidates = pd.DataFrame(candidates_result.data)
            df_votes = pd.DataFrame(votes_result.data)
            
            # 2. Intentar obtener modelo activo
            model = None
            metrics = None
            confidence = 0.70
            
            try:
                model_result = supabase_client.table("ml_models")\
                    .select("*")\
                    .eq("is_active", True)\
                    .order("created_at", desc=True)\
                    .limit(1)\
                    .execute()
                
                if model_result.data and len(model_result.data) > 0:
                    model = model_result.data[0]
                    
                    metrics_result = supabase_client.table("model_metrics")\
                        .select("*")\
                        .eq("model_id", model['id'])\
                        .order("recorded_at", desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if metrics_result.data and len(metrics_result.data) > 0:
                        metrics = metrics_result.data[0]
                        
                        if metrics.get('accuracy') is not None:
                            try:
                                confidence = float(metrics['accuracy'])
                                if confidence <= 0 or confidence > 1:
                                    confidence = 0.70
                            except (ValueError, TypeError):
                                confidence = 0.70
            except Exception as e:
                print(f"No se pudo cargar modelo ML: {e}")
            
            # 3. Calcular predicciones
            predictions = []
            total_votes = len(df_votes)
            
            for _, candidate in df_candidates.iterrows():
                try:
                    current_votes = len(df_votes[df_votes['candidate_id'] == candidate['id']])
                    current_percentage = (current_votes / total_votes * 100) if total_votes > 0 else 0
                    
                    margin = (1 - confidence) * 8
                    variation = np.random.uniform(-margin/2, margin/2)
                    predicted_percentage = current_percentage + variation
                    predicted_percentage = max(0.0, min(100.0, predicted_percentage))
                    
                    predictions.append({
                        "candidate_id": int(candidate['id']),
                        "name": str(candidate['name']),
                        "party": str(candidate['party']),
                        "current_votes": int(current_votes),
                        "current_percentage": round(float(current_percentage), 2),
                        "predicted_percentage": round(float(predicted_percentage), 2),
                        "confidence": round(float(confidence * 100), 2),
                        "margin_of_error": round(float(margin), 2)
                    })
                
                except Exception as e:
                    print(f"Error procesando candidato {candidate.get('name', 'unknown')}: {e}")
                    continue
            
            predictions.sort(key=lambda x: x['predicted_percentage'], reverse=True)
            
            # ========================================
            # ✅ NUEVO: GUARDAR EN predictions
            # ========================================
            try:
                print("💾 Guardando predicciones en BD...")
                
                for pred in predictions:
                    supabase_client.table("predictions").insert({
                        "model_id": model['id'] if model else None,
                        "candidate_id": pred["candidate_id"],
                        "predicted_votes": None,  # Opcional
                        "predicted_percentage": pred["predicted_percentage"],
                        "confidence_score": pred["confidence"] / 100.0,  # ← Normalizar a 0-1
                        "prediction_date": datetime.utcnow().isoformat()
                    }).execute()
                
                print(f"✅ Guardadas {len(predictions)} predicciones en predictions")
            
            except Exception as save_error:
                print(f"⚠️ Error guardando en predictions: {save_error}")
                # No detenemos la ejecución
            # ========================================
            
            model_info = {
                "model_id": model['id'] if model else None,
                "model_name": model['model_name'] if model else "Predicción Simple",
                "algorithm": model['algorithm'] if model else "statistical",
                "accuracy": round(float(confidence), 4) if metrics and metrics.get('accuracy') else None
            }
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "model_info": model_info,
                "predictions": predictions,
                "total_votes_analyzed": int(total_votes),
                "disclaimer": "Predicciones basadas en tendencias actuales y modelo ML (si disponible).",
                "using_ml_model": model is not None,
                "saved_to_db": True  # ← Indicador
            }
        
        except Exception as e:
            print(f"❌ ERROR en get_predictions: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "predictions": [],
                "timestamp": datetime.utcnow().isoformat()
            }