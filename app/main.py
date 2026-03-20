import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.agent import router as agent_router
from app.models import HealthResponse
from app.services.llm import llm_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Transparent AI Agent",
    description="An AI agent system that executes tasks and logs every step for transparency",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    ollama_connected = llm_service.is_connected()
    return HealthResponse(
        status="healthy" if ollama_connected else "degraded",
        ollama_connected=ollama_connected,
        model="mistral"
    )


@app.get("/")
async def root():
    return {
        "name": "Transparent AI Agent",
        "version": "1.0.0",
        "description": "AI agent with full execution logging"
    }
