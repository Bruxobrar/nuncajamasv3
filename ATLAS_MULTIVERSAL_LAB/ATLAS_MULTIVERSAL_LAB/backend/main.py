from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI(title="Atlas Multiversal API")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar por dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerationParams(BaseModel):
    params: dict = {}

@app.get("/api/")
async def root():
    return {"status": "Atlas Multiversal API online", "version": "1.0.0"}

@app.post("/api/generate/{generator_name}")
async def generate(generator_name: str, data: dict):
    """
    Endpoint para llamar a los scripts del HDD.
    """
    print(f"Generando {generator_name} con parámetros: {data}")
    
    # Lógica de conexión con los scripts reales
    # 1. Importar el script desde /generators/ (ej: from generators.lampgen import generate_lamp)
    # 2. Ejecutar la función con los parámetros recibidos
    # 3. Devolver la ruta del archivo STL generado
    
    if generator_name not in ["lamp", "drone", "planet"]:
        raise HTTPException(status_code=404, detail="Generador no encontrado")
        
    return {
        "status": "success",
        "message": f"{generator_name} generado correctamente",
        "path": f"/outputs/{generator_name}_model_0001.stl"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
