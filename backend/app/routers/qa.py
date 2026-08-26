from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Knowledge, QA, User
from ..schemas import QAAnswerIn, QAAsk
from ..services import qa_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask")
def ask(body: QAAsk, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    result = qa_service.answer(db, body.question)
    qa = QA(question=body.question, answer=result["answer"], status="answered" if not result["needs_human"] else "pending", author_id=user.id)
    db.add(qa)
    db.commit()
    db.refresh(qa)
    return {"id": qa.id, **result}


@router.post("/{qa_id}/answer")
def answer_question(qa_id: int, body: QAAnswerIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech"))):
    qa = db.get(QA, qa_id)
    if not qa:
        raise HTTPException(404, "问题不存在")
    qa.answer = body.answer
    qa.status = "answered"
    # 回流知识库
    k = Knowledge(title=qa.question[:50], content=body.answer, source="qa")
    db.add(k)
    db.flush()
    qa.knowledge_id = k.id
    db.commit()
    return {"id": qa.id, "status": qa.status}
