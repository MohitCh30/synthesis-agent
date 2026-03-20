import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Text
from sqlalchemy.orm import Session

from app.db.database import LogModel, SessionLocal
from app.services.verifier import compute_execution_hash

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoggerService:
    def __init__(self):
        self.db = SessionLocal()

    def append_log(
        self,
        task_id: str,
        input_text: str,
        output_text: Optional[str] = None,
        latency_ms: Optional[float] = None,
        status: str = "pending",
        valid: Optional[bool] = None,
        reason: Optional[str] = None,
        trust_score: Optional[float] = None,
        trust_explanation: Optional[str] = None,
        max_lines: Optional[int] = None,
        max_words: Optional[int] = None,
        sentence_count: Optional[int] = None,
        words_per_sentence: Optional[int] = None,
        forbidden_chars: Optional[List[str]] = None,
        format_constraint: Optional[str] = None,
        contradiction_detected: bool = False,
        contradiction_reason: Optional[str] = None,
        violations: Optional[List[str]] = None
    ) -> LogModel:
        timestamp = datetime.utcnow()
        execution_hash = compute_execution_hash(
            input_text=input_text,
            output_text=output_text or "",
            timestamp=timestamp.isoformat()
        )

        violations_str = "|".join(violations) if violations else None
        forbidden_str = ",".join(forbidden_chars) if forbidden_chars else None

        log_entry = LogModel(
            task_id=task_id,
            input=input_text,
            output=output_text,
            timestamp=timestamp,
            latency_ms=latency_ms,
            status=status,
            valid=valid,
            reason=reason,
            trust_score=trust_score,
            trust_explanation=trust_explanation,
            max_lines=max_lines,
            max_words=max_words,
            sentence_count=sentence_count,
            words_per_sentence=words_per_sentence,
            forbidden_chars=forbidden_str,
            format_constraint=format_constraint,
            execution_hash=execution_hash,
            contradiction_detected=contradiction_detected,
            contradiction_reason=contradiction_reason,
            violations=violations_str
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        logger.info(f"Log appended: task_id={task_id}, hash={execution_hash[:16]}..., valid={valid}")
        return log_entry

    def get_log(self, task_id: str) -> Optional[LogModel]:
        return self.db.query(LogModel).filter(LogModel.task_id == task_id).first()

    def list_logs(self, limit: int = 50, offset: int = 0) -> List[LogModel]:
        return (
            self.db.query(LogModel)
            .order_by(LogModel.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def delete_log(self, task_id: str) -> bool:
        log_entry = self.get_log(task_id)
        if log_entry:
            self.db.delete(log_entry)
            self.db.commit()
            logger.info(f"Log deleted: task_id={task_id}")
            return True
        return False


logger_service = LoggerService()
