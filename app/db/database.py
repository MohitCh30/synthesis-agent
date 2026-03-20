from sqlalchemy import create_engine, Column, String, Text, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./logs/agent_logs.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class LogModel(Base):
    __tablename__ = "logs"

    task_id = Column(String(36), primary_key=True)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    latency_ms = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    valid = Column(Boolean, nullable=True)
    reason = Column(Text, nullable=True)
    trust_score = Column(Float, nullable=True)
    trust_explanation = Column(Text, nullable=True)
    max_lines = Column(Float, nullable=True)
    max_words = Column(Float, nullable=True)
    sentence_count = Column(Float, nullable=True)
    words_per_sentence = Column(Float, nullable=True)
    forbidden_chars = Column(Text, nullable=True)
    format_constraint = Column(String(20), nullable=True)
    execution_hash = Column(String(64), nullable=False)
    contradiction_detected = Column(Boolean, default=False)
    contradiction_reason = Column(Text, nullable=True)
    violations = Column(Text, nullable=True)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
