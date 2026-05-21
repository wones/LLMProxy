from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from config.database import Base

class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, index=True)
    request_type = Column(String, index=True)
    model_name = Column(String)
    status_code = Column(Integer)
    duration_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    error_message = Column(String)
    request_headers = Column(Text)
    request_body = Column(Text)
    response_body = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
