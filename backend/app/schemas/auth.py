from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str
    org_name: str
    full_name: str | None = None
