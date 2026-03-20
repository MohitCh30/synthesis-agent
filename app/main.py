import os
import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.agent import router as agent_router
from app.models import HealthResponse
from app.services.llm import llm_service, DEFAULT_MODEL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(
    title="TrustAudit Agent",
    description="AI agent with constraint validation and on-chain verification",
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


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("TrustAudit Agent starting up...")
    logger.info(f"Port: {PORT}")
    logger.info(f"Groq Model: {DEFAULT_MODEL}")
    logger.info(f"Groq API: {'Configured' if os.getenv('GROQ_API_KEY') else 'NOT CONFIGURED'}")
    logger.info("=" * 50)


@app.get("/health")
async def health_check():
    groq_connected = llm_service.is_connected()
    return {
        "ok": True,
        "status": "healthy" if groq_connected else "degraded",
        "groq_connected": groq_connected,
        "model": DEFAULT_MODEL
    }


@app.get("/")
async def root():
    return {
        "name": "TrustAudit Agent",
        "version": "1.0.0",
        "description": "AI agent with constraint validation and on-chain verification"
    }
