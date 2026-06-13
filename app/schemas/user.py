from pydantic import BaseModel
from typing import Optional

class UserSignup(BaseModel):
    user_id: str
    password: str
    company_name: str
    location: str
    industry: str
    tech_field: Optional[str] = ""

class UserLogin(BaseModel):
    user_id: str
    password: str