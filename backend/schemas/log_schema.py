from pydantic import BaseModel
from datetime import datetime

class LogResponse(BaseModel):
    id: int
    config_id: int
    request_type: str
    model_name: str
    status_code: int
    duration_ms: int
    input_tokens: int
    output_tokens: int
    error_message: str | None
    request_headers: str | None
    request_body: str | None
    response_body: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True

class LogListResponse(BaseModel):
    logs: list[LogResponse]
    total: int

class StatisticsResponse(BaseModel):
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_duration_ms: int
    success_rate: float
