
from fastapi import FastAPI
from app.routes.routes import router as router

from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Debenture AI", description=("API para processamento de contratos financeiros utilizando agentes de IA."), version="1.0.0")
app.include_router(router)


@app.get("/health", tags=["Monitoramento"])
def health():
    return {
        "status": "OK",
        "aplicacao": "Debenture AI"
    }