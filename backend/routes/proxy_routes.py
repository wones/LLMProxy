from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from config.database import get_db
from models.config_model import LLMConfig
from models.log_model import RequestLog
from proxy.token_counter import count_message_tokens, count_tokens
import httpx
import json
import time
import asyncio

router = APIRouter(prefix="/v1", tags=["proxy"])


@router.get("/models")
async def list_models(db: Session = Depends(get_db)):
    """获取可用的模型列表（OpenAI 兼容格式）"""
    configs = db.query(LLMConfig).filter(LLMConfig.is_active == True).all()
    
    models = []
    for config in configs:
        models.append({
            "id": config.name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "llm-proxy",
            "config_id": config.id
        })
    
    if not models:
        models.append({
            "id": "default-model",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "llm-proxy"
        })
    
    return {"object": "list", "data": models}


def get_config_by_id(db: Session, config_id: int = None, model_name: str = None) -> LLMConfig:
    if config_id:
        config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
        if config:
            return config
    
    if model_name:
        config = db.query(LLMConfig).filter(LLMConfig.is_active == True, LLMConfig.name == model_name).first()
        if config:
            return config
    
    config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
    if not config:
        config = db.query(LLMConfig).first()
    if not config:
        raise HTTPException(status_code=500, detail="没有可用的配置，请先在配置管理中添加配置")
    return config


async def log_request(
    db: Session,
    config_id: int,
    request_type: str,
    model_name: str,
    status_code: int,
    duration_ms: int,
    input_tokens: int,
    output_tokens: int,
    error_message: str = None,
    request_headers: str = None,
    request_body: str = None,
    response_body: str = None
):
    log = RequestLog(
        config_id=config_id,
        request_type=request_type,
        model_name=model_name,
        status_code=status_code,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        error_message=error_message,
        request_headers=request_headers,
        request_body=request_body,
        response_body=response_body
    )
    db.add(log)
    await asyncio.to_thread(db.commit)

async def build_custom_headers(config: LLMConfig, request_body: dict = None) -> dict:
    headers = {
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }
    
    if config.app_key:
        headers['App-Key'] = config.app_key
        headers['x-api-key'] = config.app_key
    if config.app_secret:
        headers['App-Sign'] = config.app_secret
        headers['Authorization'] = f'Bearer {config.app_secret}'
    
    headers['Detection-Type'] = config.detection_type or 'extract'
    if config.detection_id:
        headers['Detection-Id'] = config.detection_id
    
    return headers


def extract_tokens_from_usage(response_data: dict) -> tuple[int, int]:
    """从响应中提取 token 信息"""
    if not response_data or "usage" not in response_data:
        return 0, 0
    
    usage = response_data["usage"]
    prompt_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
    return prompt_tokens, completion_tokens


def extract_content_for_token_count(response_data: dict) -> str:
    """从响应中提取用于 token 计数的内容"""
    if not response_data:
        return ""
    
    if "choices" in response_data and len(response_data["choices"]) > 0:
        choice = response_data["choices"][0]
        if "message" in choice:
            msg = choice["message"]
            if isinstance(msg.get("content"), str):
                return msg["content"]
        elif "delta" in choice:
            delta = choice["delta"]
            if isinstance(delta.get("content"), str):
                return delta["content"]
    
    if "content" in response_data:
        content = response_data["content"]
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
    
    return ""


@router.post("/chat/completions")
async def openai_chat_completions(
    request: Request,
    db: Session = Depends(get_db)
):
    start_time = time.time()
    body = await request.json()
    config_id = body.get("config_id")
    model_name = body.get("model", "")
    config = get_config_by_id(db, config_id, model_name)
    messages = body.get("messages", [])
    # 如果请求中明确设置了 stream，使用请求中的值；否则使用配置中的值
    stream_mode = body.get("stream", None)
    if stream_mode is None:
        stream_mode = hasattr(config, 'stream') and config.stream
    
    # 计算输入 tokens
    input_tokens = count_message_tokens(messages, model_name)
    output_tokens = 0
    
    try:
        # 在进入流之前先提取所有需要的属性，避免 detached 问题
        target_url = config.target_url
        config_id_for_log = config.id
        headers = await build_custom_headers(config)
        headers_str = json.dumps(headers, ensure_ascii=False)
        
        target_body = body.copy()
        if "config_id" in target_body:
            del target_body["config_id"]
        payload = json.dumps(target_body)
        
        response_status = 200
        response_text = ""
        response_data = None
        
        if stream_mode:
            # 流式响应处理 - 将客户端放在生成器内部
            async def stream_generator():
                nonlocal response_text, response_data, output_tokens, response_status
                
                buffer = []
                # 在生成器内部创建客户端，确保生命周期正确
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        target_url,
                        headers=headers,
                        content=payload,
                        timeout=httpx.Timeout(120.0)
                    ) as response:
                        response.raise_for_status()
                        response_status = response.status_code
                        
                        async for line in response.aiter_lines():
                            line = line.strip()
                            if line:
                                buffer.append(line)
                                yield line + "\n\n"
                
                # 收集完整响应用于日志
                response_text = "\n".join(buffer)
                
                # 尝试从最后一个 chunk 提取 token 信息或计算
                try:
                    for line in buffer:
                        if line.startswith("data: ") and line != "data: [DONE]":
                            chunk_data = json.loads(line[6:])
                            if chunk_data and "usage" in chunk_data:
                                _, output_tokens = extract_tokens_from_usage(chunk_data)
                except:
                    pass
                
                if output_tokens == 0:
                    # 如果没有 usage 信息，提取内容进行计数
                    content_for_count = extract_content_for_token_count(response_data)
                    output_tokens = count_tokens(content_for_count, model_name)
                
                # 流式响应完成后记录日志
                end_time = time.time()
                await log_request(
                    db,
                    config_id_for_log,
                    "OpenAI",
                    model_name,
                    200,
                    int((end_time - start_time) * 1000),
                    input_tokens,
                    output_tokens,
                    request_headers=headers_str,
                    request_body=json.dumps(body, ensure_ascii=False),
                    response_body=response_text
                )
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        
        else:
            # 非流式响应处理
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    target_url,
                    headers=headers,
                    content=payload,
                    timeout=httpx.Timeout(120.0)
                )
                response.raise_for_status()
                response_status = response.status_code
                response_text = response.text
                
                try:
                    response_data = response.json()
                except:
                    pass
                
                # 提取 token 信息
                if response_data:
                    _, output_tokens = extract_tokens_from_usage(response_data)
                
                if output_tokens == 0:
                    content_for_count = extract_content_for_token_count(response_data)
                    output_tokens = count_tokens(content_for_count, model_name)
                
                end_time = time.time()
                await log_request(
                    db,
                    config_id_for_log,
                    "OpenAI",
                    model_name,
                    response_status,
                    int((end_time - start_time) * 1000),
                    input_tokens,
                    output_tokens,
                    request_headers=headers_str,
                    request_body=json.dumps(body, ensure_ascii=False),
                    response_body=response_text
                )
                
                # 直接返回原始响应
                return Response(
                    content=response_text,
                    status_code=response_status,
                    media_type="application/json"
                )
    
    except Exception as e:
        end_time = time.time()
        await log_request(
            db,
            config_id_for_log if 'config_id_for_log' in locals() else None,
            "OpenAI",
            model_name,
            500,
            int((end_time - start_time) * 1000),
            input_tokens,
            0,
            str(e),
            request_headers=headers_str if 'headers_str' in locals() else None,
            request_body=json.dumps(body, ensure_ascii=False) if 'body' in locals() else None,
            response_body=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages")
async def anthropic_messages(
    request: Request,
    db: Session = Depends(get_db),
    beta: Optional[str] = None
):
    start_time = time.time()
    body = await request.json()
    config_id = body.get("config_id")
    model_name = body.get("model", "")
    config = get_config_by_id(db, config_id, model_name)
    # 如果请求中明确设置了 stream，使用请求中的值；否则使用配置中的值
    stream_mode = body.get("stream", None)
    if stream_mode is None:
        stream_mode = hasattr(config, 'stream') and config.stream
    
    # 计算输入 tokens
    messages = body.get("messages", [])
    openai_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        tool_call_id = None
        
        if isinstance(content, list):
            text_content = ""
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
                    elif item.get("type") == "tool_result":
                        # 处理工具结果消息 - 转换为 OpenAI 格式
                        text_content = item.get("content", "")
                        tool_call_id = item.get("tool_use_id", "")
            content = text_content
        
        # 如果是工具结果，使用 tool 角色
        if role == "user" and tool_call_id:
            openai_messages.append({
                "role": "tool",
                "content": content,
                "tool_call_id": tool_call_id
            })
        else:
            openai_messages.append({"role": role, "content": content})
    
    input_tokens = count_message_tokens(openai_messages, model_name)
    output_tokens = 0
    response_text = ""
    response_status = 200
    
    try:
        # 在进入流之前先提取所有需要的属性，避免 detached 问题
        target_url = config.target_url
        config_id_for_log = config.id
        headers = await build_custom_headers(config)
        headers_str = json.dumps(headers, ensure_ascii=False)
        
        # 将 Anthropic 格式转换为 OpenAI 格式发送给后端
        openai_body = {
            "model": model_name,
            "messages": openai_messages,
            "max_tokens": body.get("max_tokens", 2000),
            "temperature": body.get("temperature", 0.7),
            "stream": stream_mode
        }
        
        # 处理工具调用 - 将 Anthropic 的 tools 转换为 OpenAI 的 tools
        anthropic_tools = body.get("tools", [])
        if anthropic_tools and len(anthropic_tools) > 0:
            tools = []
            for anthropic_tool in anthropic_tools:
                if "name" in anthropic_tool:
                    # 转换为 OpenAI 格式
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": anthropic_tool["name"],
                            "description": anthropic_tool.get("description", ""),
                            "parameters": anthropic_tool.get("input_schema", {})
                        }
                    }
                    tools.append(openai_tool)
            openai_body["tools"] = tools
        
        payload = json.dumps(openai_body)
        
        if stream_mode:
            # 流式响应处理 - 需要将 OpenAI 格式转换为 Anthropic 格式
            async def stream_generator():
                nonlocal response_text, output_tokens, response_status
                
                buffer = []
                message_id = "msg_" + str(int(time.time()))
                content_buffer = ""
                has_tool_use = False
                tool_use_id = None
                tool_use_name = None
                tool_use_args = ""
                content_block_started = False
                
                # 发送 message_start - 包含完整的 message 结构
                start_chunk = {
                    "type": "message_start",
                    "message": {
                        "id": message_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": model_name,
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {
                            "input_tokens": input_tokens if input_tokens else 0,
                            "output_tokens": 0
                        }
                    }
                }
                yield f"event: message_start\ndata: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"
                
                content_block_index = 0
                
                # 在生成器内部创建客户端，确保生命周期正确
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        target_url,
                        headers=headers,
                        content=payload,
                        timeout=httpx.Timeout(120.0)
                    ) as response:
                        response.raise_for_status()
                        response_status = response.status_code
                        
                        async for line in response.aiter_lines():
                            line = line.strip()
                            if line and line.startswith("data: "):
                                buffer.append(line)
                                try:
                                    chunk_data = json.loads(line[6:])
                                    if chunk_data == "[DONE]":
                                        continue
                                    # 解析 OpenAI 格式并转换为 Anthropic 格式
                                    if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                        choice = chunk_data["choices"][0]
                                        delta = choice.get("delta", {})
                                        content = delta.get("content", "")
                                        
                                        # 检查是否有工具调用
                                        tool_calls = delta.get("tool_calls")
                                        if tool_calls and len(tool_calls) > 0:
                                            # 处理工具调用响应
                                            tool_call = tool_calls[0]
                                            function = tool_call.get("function", {})
                                            tool_name = function.get("name", "")
                                            tool_args_chunk = function.get("arguments", "")
                                            
                                            if tool_name and not has_tool_use:
                                                # 如果之前有文本内容块，先关闭它
                                                if content_block_started and not has_tool_use:
                                                    block_stop = {
                                                        "type": "content_block_stop",
                                                        "index": content_block_index
                                                    }
                                                    yield f"event: content_block_stop\ndata: {json.dumps(block_stop, ensure_ascii=False)}\n\n"
                                                    content_block_index += 1
                                                    content_block_started = False
                                                
                                                # 开始工具调用，发送 content_block_start
                                                tool_use_id = "toolu_" + str(int(time.time()))
                                                tool_use_name = tool_name
                                                has_tool_use = True
                                                
                                                tool_block_start = {
                                                    "type": "content_block_start",
                                                    "index": content_block_index,
                                                    "content_block": {
                                                        "type": "tool_use",
                                                        "id": tool_use_id,
                                                        "name": tool_name,
                                                        "input": {}
                                                    }
                                                }
                                                yield f"event: content_block_start\ndata: {json.dumps(tool_block_start, ensure_ascii=False)}\n\n"
                                                content_block_started = True
                                            
                                            if has_tool_use and tool_args_chunk:
                                                # 流式发送工具调用参数
                                                tool_use_args += tool_args_chunk
                                                tool_block_delta = {
                                                    "type": "content_block_delta",
                                                    "index": content_block_index,
                                                    "delta": {
                                                        "type": "input_json_delta",
                                                        "partial_json": tool_args_chunk
                                                    }
                                                }
                                                yield f"event: content_block_delta\ndata: {json.dumps(tool_block_delta, ensure_ascii=False)}\n\n"
                                        elif content:
                                            # 文本内容
                                            # 如果还没有开始内容块，先发送 content_block_start
                                            if not content_block_started:
                                                text_block_start = {
                                                    "type": "content_block_start",
                                                    "index": content_block_index,
                                                    "content_block": {
                                                        "type": "text",
                                                        "text": ""
                                                    }
                                                }
                                                yield f"event: content_block_start\ndata: {json.dumps(text_block_start, ensure_ascii=False)}\n\n"
                                                content_block_started = True
                                            
                                            content_buffer += content
                                            # 发送 content_block_delta
                                            delta_chunk = {
                                                "type": "content_block_delta",
                                                "index": content_block_index,
                                                "delta": {
                                                    "type": "text_delta",
                                                    "text": content
                                                }
                                            }
                                            yield f"event: content_block_delta\ndata: {json.dumps(delta_chunk, ensure_ascii=False)}\n\n"
                                except Exception as e:
                                    # 如果解析失败，直接透传
                                    yield line + "\n\n"
                
                # 发送 content_block_stop
                if content_block_started:
                    block_stop_chunk = {
                        "type": "content_block_stop",
                        "index": content_block_index
                    }
                    yield f"event: content_block_stop\ndata: {json.dumps(block_stop_chunk, ensure_ascii=False)}\n\n"
                
                # 计算输出 tokens
                if has_tool_use:
                    output_tokens = count_tokens(tool_use_args, model_name)
                    final_stop_reason = "tool_use"
                else:
                    output_tokens = count_tokens(content_buffer, model_name)
                    final_stop_reason = "end_turn"
                
                # 发送 message_delta - 官方格式只包含 output_tokens
                message_delta_chunk = {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": final_stop_reason,
                        "stop_sequence": None
                    },
                    "usage": {
                        "output_tokens": output_tokens if output_tokens else 0
                    }
                }
                yield f"event: message_delta\ndata: {json.dumps(message_delta_chunk, ensure_ascii=False)}\n\n"
                
                # 发送 message_stop
                stop_chunk = {
                    "type": "message_stop"
                }
                yield f"event: message_stop\ndata: {json.dumps(stop_chunk, ensure_ascii=False)}\n\n"
                
                # 收集完整响应用于日志
                response_text = "\n".join(buffer)
                
                # 流式响应完成后记录日志
                end_time = time.time()
                await log_request(
                    db,
                    config_id_for_log,
                    "Anthropic",
                    model_name,
                    response_status,
                    int((end_time - start_time) * 1000),
                    input_tokens,
                    output_tokens,
                    request_headers=headers_str,
                    request_body=json.dumps(body, ensure_ascii=False),
                    response_body=response_text
                )
            
            # 启动流式响应
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        
        else:
            # 非流式响应处理 - 需要将 OpenAI 格式转换为 Anthropic 格式
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    target_url,
                    headers=headers,
                    content=payload,
                    timeout=httpx.Timeout(120.0)
                )
                response.raise_for_status()
                response_status = response.status_code
                response_text = response.text
            
                response_data = None
                try:
                    response_data = response.json()
                except:
                    pass
            
                # 提取内容并转换为 Anthropic 格式
                content = ""
                tool_use = None
                
                if response_data and "choices" in response_data and len(response_data["choices"]) > 0:
                    choice = response_data["choices"][0]
                    
                    # 检查是否有工具调用
                    if "message" in choice:
                        message = choice["message"]
                        tool_calls = message.get("tool_calls")
                        
                        if tool_calls and len(tool_calls) > 0:
                            # 处理工具调用响应
                            tool_call = tool_calls[0]
                            tool_name = tool_call.get("function", {}).get("name", "")
                            tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                            
                            if tool_name:
                                # 解析工具参数
                                try:
                                    tool_args = json.loads(tool_args_str)
                                except:
                                    tool_args = tool_args_str
                                
                                tool_use = {
                                    "type": "tool_use",
                                    "id": "toolu_" + str(int(time.time())),
                                    "name": tool_name,
                                    "input": tool_args
                                }
                        elif "content" in message:
                            content = message["content"]
            
                output_tokens = count_tokens(content, model_name)
            
                # 构建 Anthropic 格式响应
                anthropic_response = {
                    "id": "msg_" + str(int(time.time())),
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": model_name,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }
                }
                
                # 添加内容块（工具调用或文本）
                if tool_use:
                    anthropic_response["content"].append(tool_use)
                    anthropic_response["stop_reason"] = "tool_use"
                else:
                    anthropic_response["content"].append({"type": "text", "text": content})
                    anthropic_response["stop_reason"] = "end_turn"
            
                end_time = time.time()
                await log_request(
                    db,
                    config_id_for_log,
                    "Anthropic",
                    model_name,
                    response_status,
                    int((end_time - start_time) * 1000),
                    input_tokens,
                    output_tokens,
                    request_headers=headers_str,
                    request_body=json.dumps(body, ensure_ascii=False),
                    response_body=json.dumps(anthropic_response, ensure_ascii=False)
                )
            
                return anthropic_response
    
    except Exception as e:
        end_time = time.time()
        await log_request(
            db,
            config_id_for_log if 'config_id_for_log' in locals() else None,
            "Anthropic",
            model_name,
            500,
            int((end_time - start_time) * 1000),
            input_tokens,
            0,
            str(e),
            request_headers=headers_str if 'headers_str' in locals() else None,
            request_body=json.dumps(body, ensure_ascii=False) if 'body' in locals() else None,
            response_body=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/chat")
async def test_chat(
    request: Request,
    db: Session = Depends(get_db)
):
    body = await request.json()
    config_id = body.get("config_id")
    config = get_config_by_id(db, config_id)
    
    message = body.get("message", "")
    model = body.get("model", "default")
    
    test_body = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 2000,
        "stream": False
    }
    
    try:
        headers = await build_custom_headers(config)
        payload = json.dumps(test_body)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.target_url,
                headers=headers,
                content=payload,
                timeout=httpx.Timeout(120.0)
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
