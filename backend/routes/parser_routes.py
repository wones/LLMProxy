from fastapi import APIRouter, HTTPException
from parsers.curl_parser import CurlParser
from schemas.parser_schema import CurlParseRequest, CurlParseResponse

router = APIRouter(prefix="/api/parser", tags=["parser"])

@router.post("/curl", response_model=CurlParseResponse)
async def parse_curl(request: CurlParseRequest):
    try:
        result = CurlParser.extract_config(request.curl_command)
        return CurlParseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析curl指令失败: {str(e)}")
