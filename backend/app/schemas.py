from pydantic import BaseModel


class RegisterIn(BaseModel):
    username: str
    password: str
    role: str


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    refresh: str = ""
    role: str


class CustomerIn(BaseModel):
    name: str
    industry: str = ""
    scale: str = ""
    main_business: str = ""
    group_id: int | None = None


class CustomerOut(CustomerIn):
    id: int
    source: str = "manual"
    model_config = {"from_attributes": True}


class ProjectIn(BaseModel):
    name: str
    customer_id: int
    description: str = ""


class ProjectOut(ProjectIn):
    id: int
    group_id: int
    status: str = "planned"
    model_config = {"from_attributes": True}



class RequirementCreate(BaseModel):
    title: str
    description: str = ""
    project_id: int | None = None
    source: str = "manual"          # manual / ai_extract
    priority: str = "med"           # low/med/high
    source_note_id: int | None = None   # P3.4 溯源到候选需求来源记录
    ai_confidence: float | None = None  # A3 置信度


class RequirementOut(BaseModel):
    id: int
    title: str
    description: str = ""
    status: str = "draft"
    project_id: int
    group_id: int
    source: str = "manual"
    source_note_id: int | None = None
    priority: str = "med"
    infeasible_reason: str = ""
    review_conclusion: str = ""
    ai_confidence: float | None = None


class TransitionIn(BaseModel):
    to: str
    reason: str = ""


class KnowledgeIn(BaseModel):
    title: str
    body: str = ""
    tags: list[str] = []
    source_enum: str = "manual"


class KnowledgeOut(KnowledgeIn):
    id: int
    status: str = "published"
    reviewer_id: int | None = None
    model_config = {"from_attributes": True}


class QAAsk(BaseModel):
    question: str


class QAAnswerIn(BaseModel):
    answer: str


class CandidateRequirement(BaseModel):
    title: str
    description: str = ""
    source_ref: str = ""


class ConfirmRequirements(BaseModel):
    project_id: int | None = None
    customer_id: int | None = None
    candidates: list[CandidateRequirement]
