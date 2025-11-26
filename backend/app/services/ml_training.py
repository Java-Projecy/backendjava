# app/services/ml_training.py
from datetime import datetime
from app.config.settings import supabase_client
import pandas as pd
import numpy as np
from typing import Dict, Optional
import json

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

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
    Servicio para Machine Learning Electoral usando DATOS GEOGRÁFICOS:
    - Classification: Predice candidato ganador según departamento, provincia, distrito
    """
    
    @staticmethod
    async def train_model(
        model_type: str,
        algorithm: str,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict:
        """
        Entrena modelo de clasificación geográfica
        """
        try:
            return await MLTrainingService._train_classification(
                algorithm, test_size, random_state
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
    async def _train_classification(algorithm: str, test_size: float, random_state: int) -> Dict:
        """Predice CANDIDATO GANADOR según ubicación geográfica"""
        
        print("\n🎯 Entrenando modelo de CLASIFICACIÓN (predicción geográfica)...")
        
        # 1. CARGAR DATOS DE LAS TABLAS REALES
        print("📊 Cargando votantes...")
        voters_result = supabase_client.table("votantes").select("id, dni, departamento, provincia, distrito").execute()
        
        # Combinar votos de las 3 tablas
        print("📊 Cargando votos presidenciales...")
        votos_pres = supabase_client.table("votos_presidenciales").select("votante_id, candidato_id, dni_votante, departamento, provincia, distrito").execute()
        print("📊 Cargando votos regionales...")
        votos_reg = supabase_client.table("votos_regionales").select("votante_id, candidato_id, dni_votante, departamento, provincia, distrito").execute()
        print("📊 Cargando votos distritales...")
        votos_dist = supabase_client.table("votos_distritales").select("votante_id, candidato_id, dni_votante, departamento, provincia, distrito").execute()
        
        if not voters_result.data:
            return {"success": False, "error": "No hay votantes registrados"}
        
        # Combinar todos los votos
        all_votes = []
        if votos_pres.data:
            all_votes.extend(votos_pres.data)
        if votos_reg.data:
            all_votes.extend(votos_reg.data)
        if votos_dist.data:
            all_votes.extend(votos_dist.data)
        
        if not all_votes:
            return {"success": False, "error": "No hay votos registrados. Necesitas al menos 10 votos para entrenar un modelo."}
        
        print(f"✅ Votantes: {len(voters_result.data)}, Votos: {len(all_votes)}")
        
        df_votes = pd.DataFrame(all_votes)
        
        # 2. FILTRAR DATOS VÁLIDOS
        df_clean = df_votes[
            (df_votes['candidato_id'].notna()) &
            (df_votes['departamento'].notna()) &
            (df_votes['provincia'].notna()) &
            (df_votes['distrito'].notna())
        ].copy().reset_index(drop=True)
        
        print(f"✅ Registros válidos: {len(df_clean)}")
        
        if len(df_clean) < 4:
            return {
                "success": False, 
                "error": f"Insuficientes datos para entrenar: {len(df_clean)} votos válidos. Necesitas al menos 4 votos para entrenar un modelo. Por favor, registra más votos en el sistema."
            }
        
        # 3. FEATURE ENGINEERING - Codificar ubicaciones geográficas
        le_dept = LabelEncoder()
        le_prov = LabelEncoder()
        le_dist = LabelEncoder()
        
        df_clean['departamento_encoded'] = le_dept.fit_transform(df_clean['departamento'].astype(str))
        df_clean['provincia_encoded'] = le_prov.fit_transform(df_clean['provincia'].astype(str))
        df_clean['distrito_encoded'] = le_dist.fit_transform(df_clean['distrito'].astype(str))
        
        # 4. X e y
        X = df_clean[['departamento_encoded', 'provincia_encoded', 'distrito_encoded']].copy()
        y = df_clean['candidato_id'].copy()
        
        # 5. VALIDAR CLASES
        class_counts = y.value_counts()
        valid_classes = class_counts[class_counts >= 1].index  # Reducido a 1 para datasets pequeños
        
        if len(valid_classes) < 2:
            return {
                "success": False, 
                "error": f"Requiere al menos 2 candidatos diferentes con votos. Actual: {class_counts.to_dict()}. Por favor, registra votos para más candidatos."
            }
        
        mask = y.isin(valid_classes)
        X = X[mask].reset_index(drop=True)
        y = y[mask].reset_index(drop=True)
        
        print(f"📊 Candidatos válidos: {len(valid_classes)}")
        print(f"📊 Distribución de votos: {y.value_counts().to_dict()}")
        
        # 6. NORMALIZAR
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 7. SPLIT
        # Solo usar stratify si cada clase tiene al menos 2 muestras
        min_class_count = y.value_counts().min()
        use_stratify = y if min_class_count >= 2 else None
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=random_state, stratify=use_stratify
        )
        
        print(f"📊 Train: {len(X_train)}, Test: {len(X_test)}")
        
        # 8. MODELO
        if algorithm == "random_forest":
            model = RandomForestClassifier(n_estimators=100, random_state=random_state, max_depth=10)
        elif algorithm == "logistic_regression":
            model = LogisticRegression(max_iter=1000, random_state=random_state)
        elif algorithm == "gradient_boosting":
            model = GradientBoostingClassifier(n_estimators=100, random_state=random_state, max_depth=5)
        else:
            return {"success": False, "error": f"Algoritmo '{algorithm}' no soportado. Usa: random_forest, logistic_regression, gradient_boosting"}
        
        # 9. ENTRENAR
        session_start = datetime.utcnow()
        print(f"🤖 Entrenando {algorithm}...")
        
        model.fit(X_train, y_train)
        
        session_end = datetime.utcnow()
        duration = (session_end - session_start).total_seconds()
        
        # 10. EVALUAR
        y_pred = model.predict(X_test)
        
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist()
        }
        
        if hasattr(model, 'feature_importances_'):
            metrics["feature_importance"] = {
                'departamento': float(model.feature_importances_[0]),
                'provincia': float(model.feature_importances_[1]),
                'distrito': float(model.feature_importances_[2])
            }
        
        print(f"✅ Accuracy: {metrics['accuracy']:.2%}")
        print(f"✅ F1-Score: {metrics['f1_score']:.2%}")
        
        # 11. RETORNAR RESULTADOS (sin guardar en BD por ahora)
        log_action(
            action="TRAIN_MODEL_GEOGRAPHIC",
            table="ml_training",
            details={
                "algorithm": algorithm,
                "accuracy": metrics["accuracy"],
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "duration_seconds": duration
            }
        )
        
        return {
            "success": True,
            "metrics": metrics,
            "training_time": f"{duration:.1f}s",
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "features_used": ["departamento", "provincia", "distrito"],
            "message": f"✅ Modelo entrenado: predice candidato ganador por ubicación geográfica (accuracy: {metrics['accuracy']:.2%})"
        }
    
    # ==================== MÉTODOS AUXILIARES ====================
    @staticmethod
    async def get_all_models() -> Dict:
        """Retorna modelos simulados por ahora"""
        try:
            # Por ahora retornamos lista vacía ya que no guardamos en BD
            return {
                "success": True, 
                "data": [],
                "total": 0,
                "message": "Los modelos se entrenan pero no se persisten en BD aún"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_model_details(model_id: int) -> Optional[Dict]:
        return None
    
    @staticmethod
    async def get_model_metrics(model_id: int) -> Optional[Dict]:
        return None
    
    @staticmethod
    async def get_training_history(model_id: int) -> Dict:
        return {"success": True, "history": []}
    
    @staticmethod
    async def predict(model_id: int, features: Dict) -> Dict:
        return {"success": False, "error": "Predicción requiere modelo serializado"}
    
    @staticmethod
    async def delete_model(model_id: int) -> Dict:
        return {"success": False, "error": "No hay modelos persistidos aún"}