import time
import logging
import os
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.models import AgentRequest, AgentResponse, LogResponse, ConstraintsInfo, VerificationResponse, ErrorResponse, OnChainProof, ClassifyRequest, ClassifyResponse
from app.services.llm import llm_service
from app.services.logger import logger_service
from app.services.constraints import parse_constraints, detect_contradictions, validate_output, calculate_trust_score
from app.services.verifier import compute_execution_hash, verify_execution
from app.services.blockchain import store_execution_onchain
from app.services.classifier import classifier_service

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)


@router.post("/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    input_text = request.input.strip()

    if len(input_text) == 0:
        raise HTTPException(status_code=400, detail="Input cannot be empty")

    task_id = str(uuid4())
    combined_text = input_text + " " + (request.system_prompt or "")
    constraints = parse_constraints(combined_text)

    logger.info(f"Task started: task_id={task_id}, constraints={constraints}")

    contradiction_info = detect_contradictions(constraints, combined_text)
    contradiction_detected = contradiction_info["contradiction_detected"]
    contradiction_reason = contradiction_info["contradiction_reason"]

    if contradiction_detected:
        logger.warning(f"Contradiction detected: {contradiction_reason}")

    start_time = time.perf_counter()

    try:
        result = llm_service.generate(
            prompt=request.input,
            model=request.model,
            system_prompt=request.system_prompt
        )

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        output = result["response"]

        violations = validate_output(output, constraints)
        valid = len(violations) == 0 and not contradiction_detected

        trust_score, trust_explanation = calculate_trust_score(
            violations=violations,
            contradiction_detected=contradiction_detected,
            latency_ms=latency_ms
        )

        reason = "; ".join(violations) if violations else ""
        if contradiction_detected:
            reason = (reason + "; " if reason else "") + f"Contradiction: {contradiction_reason}"

        timestamp = datetime.utcnow()
        timestamp_str = timestamp.isoformat()
        execution_hash = compute_execution_hash(request.input, output, timestamp_str)

        onchain_result = store_execution_onchain(execution_hash)
        onchain = None
        if onchain_result:
            onchain = OnChainProof(
                tx_hash=onchain_result.get("tx_hash"),
                network=onchain_result.get("network", "base_sepolia"),
                contract=os.getenv("CONTRACT_ADDRESS", ""),
                status=onchain_result.get("status")
            )

        logger_service.append_log(
            task_id=task_id,
            input_text=request.input,
            output_text=output,
            latency_ms=latency_ms,
            status="success",
            valid=valid,
            reason=reason,
            trust_score=trust_score,
            trust_explanation=trust_explanation,
            max_lines=constraints.get("max_lines"),
            max_words=constraints.get("max_words"),
            sentence_count=constraints.get("sentence_count"),
            words_per_sentence=constraints.get("words_per_sentence"),
            forbidden_chars=constraints.get("forbidden_chars"),
            format_constraint=constraints.get("format"),
            contradiction_detected=contradiction_detected,
            contradiction_reason=contradiction_reason,
            violations=violations
        )

        logger.info(f"Task completed: task_id={task_id}, valid={valid}, trust_score={trust_score}")

        return AgentResponse(
            task_id=task_id,
            output=output,
            latency_ms=latency_ms,
            status="success",
            valid=valid,
            reason=reason,
            trust_score=trust_score,
            trust_explanation=trust_explanation,
            execution_hash=execution_hash,
            timestamp=timestamp_str,
            verification="onchain_anchored",
            constraints=ConstraintsInfo(**constraints),
            onchain=onchain,
            contradiction_detected=contradiction_detected,
            contradiction_reason=contradiction_reason,
            violations=violations
        )

    except Exception as e:
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        timestamp = datetime.utcnow()
        timestamp_str = timestamp.isoformat()
        execution_hash = compute_execution_hash(request.input, "", timestamp_str)

        logger_service.append_log(
            task_id=task_id,
            input_text=request.input,
            output_text=None,
            latency_ms=latency_ms,
            status="error",
            valid=False,
            reason=str(e),
            trust_score=0.0,
            trust_explanation="Execution failed",
            max_lines=constraints.get("max_lines"),
            max_words=constraints.get("max_words"),
            sentence_count=constraints.get("sentence_count"),
            words_per_sentence=constraints.get("words_per_sentence"),
            forbidden_chars=constraints.get("forbidden_chars"),
            format_constraint=constraints.get("format"),
            contradiction_detected=contradiction_detected,
            contradiction_reason=contradiction_reason,
            violations=["Execution failed: " + str(e)]
        )

        logger.error(f"Task failed: task_id={task_id}, error={str(e)}")

        raise HTTPException(status_code=500, detail=f"LLM execution failed: {str(e)}")


@router.post("/classify", response_model=ClassifyResponse)
async def classify_prompt(request: ClassifyRequest):
    prompt_raw = request.prompt
    if len(prompt_raw.strip()) == 0:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    task_id = str(uuid4())
    start_time = time.perf_counter()

    try:
        result = classifier_service.classify(prompt_raw)

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        logger_service.append_log(
            task_id=task_id,
            input_text=prompt_raw,
            output_text=(
                f"verdict={result['verdict']} confidence={result['confidence']:.6f} "
                f"embedding={result['signals']['embedding']:.6f} "
                f"base64={result['signals']['base64']:.6f} "
                f"persona={result['signals']['persona']:.6f} "
                f"length={result['signals']['length']:.6f}"
            ),
            latency_ms=latency_ms,
            status="success",
            valid=True,
            reason=None,
            trust_score=result["confidence"],
            trust_explanation=f"Prompt classified as {result['verdict']}",
            contradiction_detected=False,
            contradiction_reason=None,
            violations=[]
        )

        return ClassifyResponse(
            verdict=result["verdict"],
            confidence=result["confidence"],
            signals=result["signals"]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prompt classification failed: task_id={task_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.get("/verify/{task_id}", response_model=VerificationResponse)
async def verify_task(task_id: str):
    result = verify_execution(task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Log not found: {task_id}")
    return VerificationResponse(**result)


@router.get("/logs", response_model=list[LogResponse])
async def list_logs(limit: int = 50, offset: int = 0):
    logs = logger_service.list_logs(limit=limit, offset=offset)
    return [_log_to_response(log) for log in logs]


@router.get("/logs/{task_id}", response_model=LogResponse)
async def get_log(task_id: str):
    log = logger_service.get_log(task_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Log not found: {task_id}")
    return _log_to_response(log)


def _log_to_response(log) -> LogResponse:
    violations = log.violations.split("|") if log.violations else None
    forbidden_chars = log.forbidden_chars.split(",") if log.forbidden_chars else None

    return LogResponse(
        task_id=log.task_id,
        input=log.input,
        output=log.output,
        timestamp=log.timestamp,
        latency_ms=log.latency_ms,
        status=log.status,
        valid=log.valid,
        reason=log.reason,
        trust_score=log.trust_score,
        trust_explanation=log.trust_explanation,
        execution_hash=log.execution_hash,
        contradiction_detected=log.contradiction_detected,
        contradiction_reason=log.contradiction_reason,
        violations=violations
    )


@router.delete("/logs/{task_id}")
async def delete_log(task_id: str):
    deleted = logger_service.delete_log(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Log not found: {task_id}")
    return {"message": "Log deleted", "task_id": task_id}
