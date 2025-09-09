from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Run

def create_run(db: Session, agent_id: int, user_id: int, question: str, chat_session_id: int = None) -> Run:
    run = Run(agent_id=agent_id, user_id=user_id, question=question, chat_session_id=chat_session_id, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def update_run_status(db: Session, run_id: int, **kwargs) -> Run:
    run = db.query(Run).filter(Run.id == run_id).first()
    for k, v in kwargs.items():
        setattr(run, k, v)
    db.commit()
    db.refresh(run)
    return run

