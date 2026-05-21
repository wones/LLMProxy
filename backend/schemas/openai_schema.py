from pydantic import BaseModel
from typing import List, Optional, Union

class OpenAIMessage(BaseModel):
    role: str
    content: Union[str, List[dict]]

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIMessage
    finish_reason: Optional[str]

class OpenAICompletion(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage

class OpenAIStreamChoice(BaseModel):
    index: int
    delta: OpenAIMessage
    finish_reason: Optional[str]

class OpenAIStreamCompletion(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[OpenAIStreamChoice]

class OpenAIRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: Optional[bool] = False
