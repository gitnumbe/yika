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
    role: str


class CustomerIn(BaseModel):
    name: str
    industry: str = ""
    contact: str = ""


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
    content: str
    source: str = "manual"


class KnowledgeOut(KnowledgeIn):
    id: int
    model_config = {"from_attributes": True}
