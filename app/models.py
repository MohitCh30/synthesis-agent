from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    input: str = Field(..., description="Task input prompt")
    system_prompt: Optional[str] = Field(
        default="You are a Trustworthy AI Agent. Execute the task and honor all constraints. Be precise and honest.",
        description="Optional system prompt"
    )
    model: str = Field(default="llama-3.1-8b-instant", description="Groq model to use")


class ConstraintsInfo(BaseModel):
    max_words: Optional[int] = None
    max_lines: Optional[int] = None
    sentence_count: Optional[int] = None
    words_per_sentence: Optional[int] = None
    forbidden_chars: Optional[list[str]] = None
    format: Optional[str] = None


class OnChainProof(BaseModel):
    tx_hash: Optional[str] = None
    network: str = "base_sepolia"
    contract: Optional[str] = None
    status: Optional[str] = None


class AgentResponse(BaseModel):
    task_id: str
    output: str
    latency_ms: float
    status: str
    valid: bool
    reason: str
    trust_score: float
    trust_explanation: str
    execution_hash: str
    timestamp: str
    verification: str = "onchain_anchored"
    constraints: ConstraintsInfo
    onchain: Optional[OnChainProof] = None
    contradiction_detected: bool = False
    contradiction_reason: Optional[str] = None
    violations: list[str] = Field(default_factory=list)


class VerificationResponse(BaseModel):
    valid: bool
    execution_hash: str
    recomputed_hash: str
    tampered: bool


class LogResponse(BaseModel):
    task_id: str
    input: str
    output: Optional[str]
    timestamp: datetime
    latency_ms: Optional[float]
    status: str
    valid: Optional[bool] = None
    reason: Optional[str] = None
    trust_score: Optional[float] = None
    trust_explanation: Optional[str] = None
    execution_hash: Optional[str] = None
    contradiction_detected: Optional[bool] = False
    contradiction_reason: Optional[str] = None
    violations: Optional[list[str]] = None


class HealthResponse(BaseModel):
    ok: bool
    status: str
    groq_connected: bool
    model: str


class ClassifyRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to classify")


class ClassifySignals(BaseModel):
    embedding: float = Field(..., ge=0.0, le=1.0)
    base64: float = Field(..., ge=0.0, le=1.0)
    persona: float = Field(..., ge=0.0, le=1.0)
    length: float = Field(..., ge=0.0, le=1.0)


class ClassifyResponse(BaseModel):
    verdict: str = Field(..., description="SAFE or ADVERSARIAL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    signals: ClassifySignals


class ErrorResponse(BaseModel):
    error: str
    status: str
