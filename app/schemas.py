from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LinkCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    original_url: str

class LinkResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    access_count: int

class LinkStats(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    access_count: int
    last_accessed_at: Optional[datetime] = None

class ExpiredLinkResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    expired_at: datetime
    deletion_reason: str
