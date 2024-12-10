from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import websocket_routes

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

#uvicorn main:app --host 0.0.0.0 --port 8000 --reload

