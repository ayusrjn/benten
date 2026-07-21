import uuid
from pydantic import BaseModel, ConfigDict

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    agentsCount: int
    conversationsCount: int
    avgHealth: int


class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: str
