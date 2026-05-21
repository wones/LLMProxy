from pydantic import BaseModel
from typing import List, Optional, Union

class AnthropicMessage(BaseModel):
    role: str
    content: Union[str, List[dict]]

class AnthropicUsage(BaseModel):
    input_tokens: int
    output_tokens: int

class AnthropicMessageResponse(BaseModel):
    type: str = "message"
    role: str
    content: List[dict]
    model: str
    usage: AnthropicUsage
    stop_reason: Optional[str]

class AnthropicRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    max_tokens: int
    temperature: Optional[float] = None
    stream: Optional[bool] = False
