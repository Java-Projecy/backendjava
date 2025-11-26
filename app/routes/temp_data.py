# app/routes/temp_data.py
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.config.settings import supabase_client

router = APIRouter()

@router.get("/temp-data/presidenciales")
async def get_temp_presidenciales() -> Dict:
    """
    Obtiene todos los datos temporales de elecciones presidenciales
    """
    try:
        response = supabase_client.table("datos_temp_presidenciales").select("*").execute()
        
        return {
            "success": True,
            "data": response.data,
            "total": len(response.data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos temporales presidenciales: {str(e)}"
        )

@router.get("/temp-data/regionales")
async def get_temp_regionales() -> Dict:
    """
    Obtiene todos los datos temporales de elecciones regionales
    """
    try:
        response = supabase_client.table("datos_temp_regionales").select("*").execute()
        
        return {
            "success": True,
            "data": response.data,
            "total": len(response.data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos temporales regionales: {str(e)}"
        )

@router.get("/temp-data/distritales")
async def get_temp_distritales() -> Dict:
    """
    Obtiene todos los datos temporales de elecciones distritales
    """
    try:
        response = supabase_client.table("datos_temp_distritales").select("*").execute()
        
        return {
            "success": True,
            "data": response.data,
            "total": len(response.data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos temporales distritales: {str(e)}"
        )

@router.get("/temp-data/all")
async def get_all_temp_data() -> Dict:
    """
    Obtiene todos los datos temporales de todas las elecciones
    """
    try:
        pres = supabase_client.table("datos_temp_presidenciales").select("*").execute()
        reg = supabase_client.table("datos_temp_regionales").select("*").execute()
        dist = supabase_client.table("datos_temp_distritales").select("*").execute()
        
        return {
            "success": True,
            "data": {
                "presidenciales": pres.data,
                "regionales": reg.data,
                "distritales": dist.data
            },
            "totales": {
                "presidenciales": len(pres.data),
                "regionales": len(reg.data),
                "distritales": len(dist.data),
                "total": len(pres.data) + len(reg.data) + len(dist.data)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo datos temporales: {str(e)}"
        )
