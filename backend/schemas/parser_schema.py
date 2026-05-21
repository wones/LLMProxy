from pydantic import BaseModel
from typing import Optional

class CurlParseRequest(BaseModel):
    curl_command: str

class CurlParseResponse(BaseModel):
    target_url: Optional[str]
    app_key: Optional[str]
    app_sign: Optional[str]
    detection_type: Optional[str]
    detection_id: Optional[str]
    model_name: Optional[str]
