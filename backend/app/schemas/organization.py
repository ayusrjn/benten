import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict

class OrgStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    membersCount: int
    projectsCount: int
    apiKeysCount: int
    storageUsedGb: int
    storageLimitGb: int


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: str
    avatar: str


class MemberInvite(BaseModel):
    email: str
    role: Optional[str] = "Viewer"
