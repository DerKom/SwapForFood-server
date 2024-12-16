from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import websocket_routes
import uvicorn

app = FastAPI()

# Configuración de CORS si es necesario
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(websocket_routes.router)

if __name__ == "__main__":
    # Configuración para el servidor
    reload_mode = True  # Cambiar a False si no quieres el modo reload
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=reload_mode
    )

#uvicorn main:app --host 0.0.0.0 --port 8000 --reload