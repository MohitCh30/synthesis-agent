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
    model: str = Field(default="mistral", description="Ollama model to use")


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
    status: str
    ollama_connected: bool
    model: str


class ErrorResponse(BaseModel):
    error: str
    status: str
