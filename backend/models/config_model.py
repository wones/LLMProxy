from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from config.database import Base

class LLMConfig(Base):
    __tablename__ = "llm_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    target_url = Column(String)
    app_key = Column(String)
    app_secret = Column(String)
    detection_type = Column(String)
    detection_id = Column(String)
    is_active = Column(Boolean, default=False)
    stream = Column(Boolean, default=False)  # 是否使用流式响应
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
