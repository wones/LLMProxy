from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ConfigCreate(BaseModel):
    name: str
    target_url: str
    app_key: str
    app_secret: str
    detection_type: str
    detection_id: str
    stream: bool = False

class ConfigUpdate(BaseModel):
    name: Optional[str] = None
    target_url: Optional[str] = None
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    detection_type: Optional[str] = None
    detection_id: Optional[str] = None
    stream: Optional[bool] = None

class ConfigResponse(BaseModel):
    id: int
    name: str
    target_url: str
    app_key: str
    app_secret: str
    detection_type: str
    detection_id: str
    is_active: bool
    stream: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
