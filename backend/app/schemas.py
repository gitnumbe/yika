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
    model_config = {"from_attributes": True}


class ProjectIn(BaseModel):
    name: str
    customer_id: int


class ProjectOut(BaseModel):
    id: int
    name: str
    customer_id: int
    status: str
    model_config = {"from_attributes": True}


class RequirementIn(BaseModel):
    title: str
    description: str = ""
    source: str = "manual"
    source_ref: str = ""
    project_id: int | None = None
    customer_id: int | None = None
    priority: int = 0


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
