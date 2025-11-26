# app/services/ml_data_preparation.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from app.config.settings import supabase_client

class MLDataPreparation:
    """
    Prepara datos desde Supabase para entrenar modelos de ML
    """
    
    @staticmethod
    async def get_classification_data(tipo_eleccion='presidencial'):
        """
        Obtiene datos para CLASIFICACIÓN (predecir candidato ganador)
        
        Args:
            tipo_eleccion: 'presidencial', 'regional' o 'distrital'
        
        Returns:
            X: DataFrame con features
            y: Serie con targets (candidato_id)
        """
        tabla = f"votos_{tipo_eleccion}es"
        
        # 1. Obtener votos con JOIN a candidatos
        query = f"""
            SELECT 
                v.id,
                v.dni_votante,
                v.departamento,
                v.provincia,
                v.distrito,
                v.fecha_voto,
                v.candidato_id,
                c.partido
            FROM {tabla} v
            JOIN candidatos c ON v.candidato_id = c.id
            WHERE v.dni_votante IS NOT NULL 
              AND v.candidato_id IS NOT NULL
        """
        
        result = supabase_client.rpc('execute_sql', {'query': query}).execute()
        
        if not result.data:
            raise ValueError(f"No hay datos en {tabla}")
        
        df = pd.DataFrame(result.data)
        
        # 2. Feature Engineering
        df['fecha_voto'] = pd.to_datetime(df['fecha_voto'])
        df['hora_voto'] = df['fecha_voto'].dt.hour
        df['dia_semana'] = df['fecha_voto'].dt.dayofweek
        df['mes'] = df['fecha_voto'].dt.month
        
        # 3. Codificación de variables categóricas
        le_dept = LabelEncoder()
        le_prov = LabelEncoder()
        le_dist = LabelEncoder()
        le_partido = LabelEncoder()
        
        df['departamento_encoded'] = le_dept.fit_transform(df['departamento'].fillna('UNKNOWN'))
        df['provincia_encoded'] = le_prov.fit_transform(df['provincia'].fillna('UNKNOWN'))
        df['distrito_encoded'] = le_dist.fit_transform(df['distrito'].fillna('UNKNOWN'))
        df['partido_encoded'] = le_partido.fit_transform(df['partido'].fillna('UNKNOWN'))
        
        # 4. Seleccionar features y target
        X = df[[
            'departamento_encoded',
            'provincia_encoded',
            'distrito_encoded',
            'hora_voto',
            'dia_semana',
            'mes',
            'partido_encoded'
        ]].copy()
        
        y = df['candidato_id'].copy()
        
        return X, y, {
            'label_encoders': {
                'departamento': le_dept,
                'provincia': le_prov,
                'distrito': le_dist,
                'partido': le_partido
            },
            'feature_names': list(X.columns)
        }
    
    
    @staticmethod
    async def get_regression_data(tipo_eleccion='presidencial'):
        """
        Obtiene datos para REGRESIÓN (predecir % de votos por región)
        
        Returns:
            X: DataFrame con features
            y: Serie con targets (porcentaje_votos)
        """
        tabla = f"votos_{tipo_eleccion}es"
        
        # 1. Query compleja para calcular porcentajes
        query = f"""
        WITH votos_por_region AS (
            SELECT 
                departamento,
                provincia,
                distrito,
                candidato_id,
                COUNT(*) AS votos_candidato
            FROM {tabla}
            WHERE candidato_id IS NOT NULL
            GROUP BY departamento, provincia, distrito, candidato_id
        ),
        total_votos_region AS (
            SELECT 
                departamento,
                provincia,
                distrito,
                COUNT(*) AS total_votos
            FROM {tabla}
            WHERE candidato_id IS NOT NULL
            GROUP BY departamento, provincia, distrito
        )
        SELECT 
            vr.departamento,
            vr.provincia,
            vr.distrito,
            vr.candidato_id,
            c.partido,
            vr.votos_candidato,
            tvr.total_votos,
            (vr.votos_candidato::FLOAT / tvr.total_votos * 100) AS porcentaje_votos
        FROM 
            votos_por_region vr
            JOIN total_votos_region tvr 
                ON vr.departamento = tvr.departamento 
                AND vr.provincia = tvr.provincia 
                AND vr.distrito = tvr.distrito
            JOIN candidatos c ON vr.candidato_id = c.id
        WHERE tvr.total_votos >= 5;  -- Solo regiones con al menos 5 votos
        """
        
        result = supabase_client.rpc('execute_sql', {'query': query}).execute()
        
        if not result.data:
            raise ValueError(f"No hay datos suficientes en {tabla}")
        
        df = pd.DataFrame(result.data)
        
        # 2. Codificación
        le_dept = LabelEncoder()
        le_prov = LabelEncoder()
        le_dist = LabelEncoder()
        le_partido = LabelEncoder()
        le_candidato = LabelEncoder()
        
        df['departamento_encoded'] = le_dept.fit_transform(df['departamento'])
        df['provincia_encoded'] = le_prov.fit_transform(df['provincia'])
        df['distrito_encoded'] = le_dist.fit_transform(df['distrito'])
        df['partido_encoded'] = le_partido.fit_transform(df['partido'])
        df['candidato_encoded'] = le_candidato.fit_transform(df['candidato_id'])
        
        # 3. Features y Target
        X = df[[
            'departamento_encoded',
            'provincia_encoded',
            'distrito_encoded',
            'partido_encoded',
            'candidato_encoded',
            'total_votos'  # Población de la región
        ]].copy()
        
        y = df['porcentaje_votos'].copy()
        
        return X, y, {
            'label_encoders': {
                'departamento': le_dept,
                'provincia': le_prov,
                'distrito': le_dist,
                'partido': le_partido,
                'candidato': le_candidato
            },
            'feature_names': list(X.columns)
        }
    
    
    @staticmethod
    async def get_combined_election_data():
        """
        Combina datos de los 3 tipos de elecciones para análisis comparativo
        """
        datasets = []
        
        for tipo in ['presidencial', 'regional', 'distrital']:
            try:
                X, y, metadata = await MLDataPreparation.get_classification_data(tipo)
                X['tipo_eleccion'] = tipo
                df_combined = X.copy()
                df_combined['candidato_id'] = y
                datasets.append(df_combined)
            except Exception as e:
                print(f"⚠️ No se pudo cargar {tipo}: {e}")
        
        if not datasets:
            raise ValueError("No hay datos disponibles en ninguna tabla de votos")
        
        df_final = pd.concat(datasets, ignore_index=True)
        
        # Codificar tipo_eleccion
        le_tipo = LabelEncoder()
        df_final['tipo_eleccion_encoded'] = le_tipo.fit_transform(df_final['tipo_eleccion'])
        
        X = df_final.drop(['candidato_id', 'tipo_eleccion'], axis=1)
        y = df_final['candidato_id']
        
        return X, y, {'tipo_eleccion_encoder': le_tipo}