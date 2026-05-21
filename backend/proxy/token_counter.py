import tiktoken

def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    try:
        try:
            encoding = tiktoken.encoding_for_model(model_name)
        except (KeyError, ValueError):
            # 如果模型名不认识，使用默认编码
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # 如果 tiktoken 失败，使用简单的字符估算（作为后备方案）
        return len(text) // 4

def count_message_tokens(messages: list[dict], model_name: str = "gpt-3.5-turbo") -> int:
    total_tokens = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total_tokens += count_tokens(content, model_name)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    total_tokens += count_tokens(item["text"], model_name)
    return total_tokens
