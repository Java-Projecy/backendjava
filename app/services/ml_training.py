# app/services/ml_training.py - VERSIÓN MEJORADA INTEGRADA
from datetime import datetime
from app.config.settings import supabase_client
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
import json

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    confusion_matrix, classification_report
)
from collections import Counter


def log_action(action: str, table: str, details: dict = None):
    """Registra acción en audit_logs"""
    try:
        supabase_client.table("audit_logs").insert({
            "user_id": 1,
            "action": action,
            "table_name": table,
            "new_values": details,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        print(f"📝 Audit log: {action} en {table}")
    except Exception as e:
        print(f"⚠️ Error guardando audit log: {e}")


class MLTrainingService:
    """
    Servicio avanzado de Machine Learning Electoral
    - Predice candidato ganador con features geográficas, temporales y de popularidad
    - Soporta 3 tipos de elecciones: presidencial, regional, distrital
    - Incluye validación cruzada y análisis de importancia de features
    """
    
    # Configuración de encoders (se mantienen entre entrenamientos)
    _encoders = {
        'departamento': {},
        'provincia': {},
        'distrito': {},
        'partido': {}
    }
    _scalers = {}
    
    @staticmethod
    async def train_model(
        model_type: str,
        algorithm: str,
        test_size: float = 0.2,
        random_state: int = 42,
        use_enhanced_features: bool = True,
        election_type: Optional[str] = None  # 'presidencial', 'regional', 'distrital', None=todos
    ) -> Dict:
        """
        Entrena modelo de clasificación con features avanzadas
        
        Args:
            model_type: Tipo de modelo ('classification')
            algorithm: 'random_forest', 'logistic_regression', 'gradient_boosting'
            test_size: Proporción de datos para test (0-1)
            random_state: Semilla para reproducibilidad
            use_enhanced_features: Si True, usa features temporales y de popularidad
            election_type: Tipo específico de elección o None para todas
        """
        try:
            return await MLTrainingService._train_classification(
                algorithm, test_size, random_state, use_enhanced_features, election_type
            )
        except Exception as e:
            print(f"❌ Error en train_model: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Error interno: {str(e)}"
            }
    
    @staticmethod
    async def _load_voting_data(election_type: Optional[str] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Carga y combina datos de votación según el tipo de elección
        
        Returns:
            Tuple[DataFrame con votos, Dict con estadísticas]
        """
        print("📊 Cargando datos de votación...")
        
        # Cargar votantes
        voters_result = supabase_client.table("votantes").select(
            "id, dni, departamento, provincia, distrito, created_at"
        ).execute()
        
        # Cargar candidatos
        candidates_result = supabase_client.table("candidatos").select(
            "id, nombre, partido, tipo_eleccion"
        ).execute()
        
        # Cargar votos según tipo de elección
        all_votes = []
        stats = {
            "total_voters": len(voters_result.data) if voters_result.data else 0,
            "total_candidates": len(candidates_result.data) if candidates_result.data else 0,
            "votes_by_type": {}
        }
        
        # Función auxiliar para cargar votos de una tabla
        async def load_votes_from_table(table_name: str, tipo: str):
            try:
                result = supabase_client.table(table_name).select(
                    "id, votante_id, candidato_id, dni_votante, "
                    "departamento, provincia, distrito, fecha_voto"
                ).execute()
                
                if result.data:
                    for v in result.data:
                        v['tipo_eleccion'] = tipo
                    stats["votes_by_type"][tipo] = len(result.data)
                    return result.data
                return []
            except Exception as e:
                print(f"⚠️ Error cargando {table_name}: {e}")
                return []
        
        # Cargar según filtro de tipo
        if election_type is None or election_type == 'presidencial':
            votos_pres = await load_votes_from_table("votos_presidenciales", "presidencial")
            all_votes.extend(votos_pres)
        
        if election_type is None or election_type == 'regional':
            votos_reg = await load_votes_from_table("votos_regionales", "regional")
            all_votes.extend(votos_reg)
        
        if election_type is None or election_type == 'distrital':
            votos_dist = await load_votes_from_table("votos_distritales", "distrital")
            all_votes.extend(votos_dist)
        
        stats["total_votes"] = len(all_votes)
        
        if not all_votes:
            return None, stats
        
        df_votes = pd.DataFrame(all_votes)
        
        # Merge con candidatos para obtener partido
        if candidates_result.data:
            df_candidates = pd.DataFrame(candidates_result.data)
            df_votes = df_votes.merge(
                df_candidates[['id', 'partido', 'nombre']], 
                left_on='candidato_id', 
                right_on='id', 
                how='left',
                suffixes=('', '_candidato')
            )
        
        return df_votes, stats
    
    @staticmethod
    def _prepare_enhanced_features(df_votes: pd.DataFrame, use_enhanced: bool = True) -> Tuple[pd.DataFrame, List[str]]:
        """
        Prepara features para entrenamiento
        
        Args:
            df_votes: DataFrame con votos
            use_enhanced: Si incluir features avanzadas
            
        Returns:
            Tuple[DataFrame con features, lista de nombres de features]
        """
        df = df_votes.copy()
        feature_names = []
        
        # ===== 1. FEATURES GEOGRÁFICAS (siempre incluidas) =====
        for col, encoder_key in [('departamento', 'departamento'), 
                                  ('provincia', 'provincia'), 
                                  ('distrito', 'distrito')]:
            if col in df.columns:
                if encoder_key not in MLTrainingService._encoders or not MLTrainingService._encoders[encoder_key]:
                    MLTrainingService._encoders[encoder_key] = LabelEncoder()
                
                df[f'{col}_encoded'] = MLTrainingService._encoders[encoder_key].fit_transform(
                    df[col].fillna('UNKNOWN').astype(str)
                )
                feature_names.append(f'{col}_encoded')
        
        if not use_enhanced:
            return df, feature_names
        
        # ===== 2. FEATURES TEMPORALES =====
        if 'fecha_voto' in df.columns:
            df['fecha_voto_dt'] = pd.to_datetime(df['fecha_voto'], errors='coerce')
            
            # Hora del voto
            df['hour_of_vote'] = df['fecha_voto_dt'].dt.hour
            df['hour_of_vote'] = df['hour_of_vote'].fillna(df['hour_of_vote'].median())
            
            # Día de la semana
            df['day_of_week'] = df['fecha_voto_dt'].dt.dayofweek
            df['day_of_week'] = df['day_of_week'].fillna(0)
            
            # Fin de semana
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Periodo del día
            df['period_of_day'] = pd.cut(
                df['hour_of_vote'], 
                bins=[0, 6, 12, 18, 24], 
                labels=[0, 1, 2, 3],
                include_lowest=True
            ).astype(float)
            df['period_of_day'] = df['period_of_day'].fillna(1)
            
            feature_names.extend(['hour_of_vote', 'day_of_week', 'is_weekend', 'period_of_day'])
        
        # ===== 3. FEATURES DE POPULARIDAD GEOGRÁFICA =====
        # Votos totales por distrito
        df['votes_in_district'] = df.groupby('distrito')['candidato_id'].transform('count')
        
        # Votos del candidato en el distrito
        df['candidate_votes_in_district'] = df.groupby(
            ['distrito', 'candidato_id']
        )['candidato_id'].transform('count')
        
        # Popularidad relativa
        df['candidate_popularity'] = (
            df['candidate_votes_in_district'] / df['votes_in_district'].replace(0, 1)
        )
        
        # Ranking del candidato en el distrito
        df['candidate_rank_in_district'] = df.groupby('distrito')['candidate_votes_in_district'].rank(
            ascending=False, method='dense'
        )
        
        feature_names.extend([
            'votes_in_district', 
            'candidate_votes_in_district',
            'candidate_popularity',
            'candidate_rank_in_district'
        ])
        
        # ===== 4. FEATURES DE PARTIDO =====
        if 'partido' in df.columns:
            if 'partido' not in MLTrainingService._encoders or not MLTrainingService._encoders['partido']:
                MLTrainingService._encoders['partido'] = LabelEncoder()
            
            df['partido_encoded'] = MLTrainingService._encoders['partido'].fit_transform(
                df['partido'].fillna('INDEPENDIENTE').astype(str)
            )
            
            # Votos del partido en el departamento
            df['party_votes_in_dept'] = df.groupby(
                ['departamento', 'partido']
            )['candidato_id'].transform('count')
            
            feature_names.extend(['partido_encoded', 'party_votes_in_dept'])
        
        # ===== 5. FEATURES DE TIPO DE ELECCIÓN =====
        if 'tipo_eleccion' in df.columns:
            df['tipo_eleccion_encoded'] = LabelEncoder().fit_transform(
                df['tipo_eleccion'].fillna('presidencial')
            )
            feature_names.append('tipo_eleccion_encoded')
        
        # Rellenar NaNs
        for col in feature_names:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median() if df[col].dtype in ['float64', 'int64'] else 0)
        
        return df, feature_names
    
    @staticmethod
    async def _train_classification(
        algorithm: str, 
        test_size: float, 
        random_state: int,
        use_enhanced_features: bool,
        election_type: Optional[str]
    ) -> Dict:
        """Entrena modelo de clasificación con features avanzadas"""
        
        print(f"\n🎯 Entrenando modelo de CLASIFICACIÓN ({algorithm})...")
        print(f"   Tipo de elección: {election_type or 'TODAS'}")
        print(f"   Features mejoradas: {'✓' if use_enhanced_features else '✗'}")
        
        # 1. CARGAR DATOS
        df_votes, stats = await MLTrainingService._load_voting_data(election_type)
        
        if df_votes is None or len(df_votes) == 0:
            return {
                "success": False, 
                "error": "No hay votos registrados. Necesitas al menos 10 votos para entrenar."
            }
        
        print(f"✅ Votantes: {stats['total_voters']}, Votos: {stats['total_votes']}")
        print(f"   Distribución: {stats['votes_by_type']}")
        
        # 2. FILTRAR DATOS VÁLIDOS
        required_cols = ['candidato_id', 'departamento', 'provincia', 'distrito']
        df_clean = df_votes.copy()
        for col in required_cols:
            df_clean = df_clean[df_clean[col].notna()]
        
        df_clean = df_clean.reset_index(drop=True)
        
        print(f"✅ Registros válidos: {len(df_clean)}")
        
        if len(df_clean) < 4:
            return {
                "success": False, 
                "error": f"Datos insuficientes: {len(df_clean)} votos. Necesitas al menos 4 votos."
            }
        
        # 3. PREPARAR FEATURES
        df_featured, feature_names = MLTrainingService._prepare_enhanced_features(
            df_clean, use_enhanced_features
        )
        
        X = df_featured[feature_names].copy()
        y = df_clean['candidato_id'].copy()
        
        print(f"📊 Features utilizadas: {len(feature_names)}")
        print(f"   Top features: {', '.join(feature_names[:5])}{'...' if len(feature_names) > 5 else ''}")
        
        # 4. VALIDAR CLASES
        class_counts = y.value_counts()
        valid_classes = class_counts[class_counts >= 1].index
        
        if len(valid_classes) < 2:
            return {
                "success": False, 
                "error": f"Requiere al menos 2 candidatos diferentes. Actual: {class_counts.to_dict()}"
            }
        
        mask = y.isin(valid_classes)
        X = X[mask].reset_index(drop=True)
        y = y[mask].reset_index(drop=True)
        
        print(f"📊 Candidatos válidos: {len(valid_classes)}")
        print(f"📊 Distribución: {dict(list(y.value_counts().items())[:3])}")
        
        # 5. NORMALIZAR
        scaler_key = f"{algorithm}_{election_type or 'all'}"
        if scaler_key not in MLTrainingService._scalers:
            MLTrainingService._scalers[scaler_key] = StandardScaler()
        
        X_scaled = MLTrainingService._scalers[scaler_key].fit_transform(X)
        
        # 6. SPLIT
        min_class_count = y.value_counts().min()
        use_stratify = y if min_class_count >= 2 else None
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, 
            test_size=test_size, 
            random_state=random_state, 
            stratify=use_stratify
        )
        
        print(f"📊 Train: {len(X_train)}, Test: {len(X_test)}")
        
        # 7. SELECCIONAR MODELO
        model_params = {
            "random_forest": {
                "model": RandomForestClassifier(
                    n_estimators=100, 
                    max_depth=10, 
                    min_samples_split=5,
                    random_state=random_state
                ),
                "name": "Random Forest"
            },
            "logistic_regression": {
                "model": LogisticRegression(
                    max_iter=1000, 
                    random_state=random_state,
                    solver='lbfgs'
                ),
                "name": "Logistic Regression"
            },
            "gradient_boosting": {
                "model": GradientBoostingClassifier(
                    n_estimators=100, 
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=random_state
                ),
                "name": "Gradient Boosting"
            }
        }
        
        if algorithm not in model_params:
            return {
                "success": False, 
                "error": f"Algoritmo '{algorithm}' no soportado. Opciones: {list(model_params.keys())}"
            }
        
        model_info = model_params[algorithm]
        model = model_info["model"]
        
        # 8. ENTRENAR
        session_start = datetime.utcnow()
        print(f"🤖 Entrenando {model_info['name']}...")
        
        model.fit(X_train, y_train)
        
        session_end = datetime.utcnow()
        duration = (session_end - session_start).total_seconds()
        
        # 9. EVALUAR
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        metrics = {
            "train_accuracy": float(accuracy_score(y_train, y_pred_train)),
            "test_accuracy": float(accuracy_score(y_test, y_pred_test)),
            "precision": float(precision_score(y_test, y_pred_test, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_test, y_pred_test, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred_test, average='weighted', zero_division=0)),
            "confusion_matrix": confusion_matrix(y_test, y_pred_test).tolist()
        }
        
        # 10. CROSS-VALIDATION
        cv_scores = None
        if len(X_train) >= 10:
            try:
                cv_scores = cross_val_score(
                    model, X_train, y_train, 
                    cv=min(5, len(X_train) // 2),
                    scoring='accuracy'
                )
                metrics["cv_accuracy_mean"] = float(cv_scores.mean())
                metrics["cv_accuracy_std"] = float(cv_scores.std())
                print(f"   Cross-validation: {cv_scores.mean():.2%} ± {cv_scores.std():.2%}")
            except Exception as e:
                print(f"   ⚠️ No se pudo calcular CV: {e}")
        
        # 11. FEATURE IMPORTANCE
        if hasattr(model, 'feature_importances_'):
            importance_dict = {}
            for name, importance in zip(feature_names, model.feature_importances_):
                importance_dict[name] = float(importance)
            
            sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            metrics["feature_importance"] = dict(sorted_importance[:10])
            
            print("📊 Top 5 Features:")
            for feat, imp in sorted_importance[:5]:
                print(f"   {feat}: {imp:.3f}")
        
        # 12. DETECTAR OVERFITTING
        overfit_gap = metrics["train_accuracy"] - metrics["test_accuracy"]
        metrics["overfitting_detected"] = overfit_gap > 0.15
        
        if metrics["overfitting_detected"]:
            print(f"⚠️  Posible overfitting detectado (gap: {overfit_gap:.2%})")
        
        print(f"✅ Accuracy Train: {metrics['train_accuracy']:.2%}")
        print(f"✅ Accuracy Test: {metrics['test_accuracy']:.2%}")
        print(f"✅ F1-Score: {metrics['f1_score']:.2%}")
        
        # 13. LOGGING
        log_action(
            action="TRAIN_MODEL_ENHANCED",
            table="ml_training",
            details={
                "algorithm": algorithm,
                "election_type": election_type or "all",
                "test_accuracy": metrics["test_accuracy"],
                "f1_score": metrics["f1_score"],
                "features_count": len(feature_names),
                "enhanced_features": use_enhanced_features,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "duration_seconds": duration
            }
        )
        
        return {
            "success": True,
            "model_name": model_info["name"],
            "algorithm": algorithm,
            "election_type": election_type or "all",
            "metrics": metrics,
            "training_time": f"{duration:.2f}s",
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "features_count": len(feature_names),
            "features_used": feature_names,
            "enhanced_features_enabled": use_enhanced_features,
            "message": f"✅ Modelo entrenado exitosamente (Test Accuracy: {metrics['test_accuracy']:.2%}, F1: {metrics['f1_score']:.2%})"
        }
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    @staticmethod
    async def get_all_models() -> Dict:
        """Retorna modelos registrados"""
        try:
            return {
                "success": True, 
                "data": [],
                "total": 0,
                "message": "Modelos se entrenan pero no se persisten en BD (por implementar)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def compare_algorithms(
        test_size: float = 0.2, 
        random_state: int = 42,
        election_type: Optional[str] = None
    ) -> Dict:
        """Compara el rendimiento de todos los algoritmos disponibles"""
        
        print(f"\n🔬 Comparando algoritmos para: {election_type or 'TODAS las elecciones'}...")
        
        algorithms = ["random_forest", "logistic_regression", "gradient_boosting"]
        results = []
        
        for algo in algorithms:
            print(f"\n--- Entrenando {algo} ---")
            result = await MLTrainingService._train_classification(
                algo, test_size, random_state, 
                use_enhanced_features=True,
                election_type=election_type
            )
            
            if result["success"]:
                results.append({
                    "algorithm": algo,
                    "election_type": election_type or "all",
                    "test_accuracy": result["metrics"]["test_accuracy"],
                    "f1_score": result["metrics"]["f1_score"],
                    "training_time": result["training_time"],
                    "cv_score": result["metrics"].get("cv_accuracy_mean")
                })
        
        # Ordenar por f1_score
        results.sort(key=lambda x: x["f1_score"], reverse=True)
        
        return {
            "success": True,
            "election_type": election_type or "all",
            "comparison": results,
            "best_model": results[0]["algorithm"] if results else None,
            "message": f"✅ Mejor modelo: {results[0]['algorithm']} (F1: {results[0]['f1_score']:.2%})" if results else "No se pudo entrenar ningún modelo"
        }
    
    @staticmethod
    def reset_encoders():
        """Resetea encoders y scalers guardados"""
        MLTrainingService._encoders = {
            'departamento': {},
            'provincia': {},
            'distrito': {},
            'partido': {}
        }
        MLTrainingService._scalers = {}
        print("♻️  Encoders y scalers reseteados")
    
    @staticmethod
    async def get_model_details(model_id: int) -> Optional[Dict]:
        """Placeholder para obtener detalles de un modelo guardado"""
        return None
    
    @staticmethod
    async def get_model_metrics(model_id: int) -> Optional[Dict]:
        """Placeholder para obtener métricas de un modelo"""
        return None
    
    @staticmethod
    async def get_training_history(model_id: int) -> Dict:
        """Placeholder para obtener historial de entrenamiento"""
        return {"success": True, "history": []}
    
    @staticmethod
    async def predict(model_id: int, features: Dict) -> Dict:
        """Placeholder para hacer predicciones"""
        return {"success": False, "error": "Predicción requiere modelo serializado"}
    
    @staticmethod
    async def delete_model(model_id: int) -> Dict:
        """Placeholder para eliminar modelo"""
        return {"success": False, "error": "No hay modelos persistidos aún"}