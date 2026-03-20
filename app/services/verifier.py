import hashlib
from datetime import datetime
from typing import Optional

from app.db.database import SessionLocal, LogModel


def compute_execution_hash(input_text: str, output_text: str, timestamp: str) -> str:
    hash_input = f"{input_text}|{output_text}|{timestamp}"
    return hashlib.sha256(hash_input.encode()).hexdigest()


def verify_execution(task_id: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        log_entry = db.query(LogModel).filter(LogModel.task_id == task_id).first()
        if not log_entry:
            return None

        stored_hash = log_entry.execution_hash
        
        timestamp_str = log_entry.timestamp.isoformat()
        
        recomputed_hash = compute_execution_hash(
            input_text=log_entry.input,
            output_text=log_entry.output or "",
            timestamp=timestamp_str
        )

        tampered = stored_hash != recomputed_hash

        return {
            "valid": not tampered,
            "execution_hash": stored_hash,
            "recomputed_hash": recomputed_hash,
            "tampered": tampered
        }
    finally:
        db.close()
