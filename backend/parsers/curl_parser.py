import re
import json

class CurlParser:
    @staticmethod
    def parse(curl_command):
        result = {
            "url": "",
            "method": "POST",
            "headers": {},
            "body": None
        }
        
        url_patterns = [
            r"(?:curl\s+)?(?:-X\s+(\w+)\s+)?(?:['\"])([^'\"]+)(?:['\"])",
            r"curl\s+(?:-X\s+(\w+)\s+)?([^\s]+)"
        ]
        
        for url_pattern in url_patterns:
            url_match = re.search(url_pattern, curl_command)
            if url_match:
                if url_match.group(1):
                    result["method"] = url_match.group(1).upper()
                result["url"] = url_match.group(2)
                if result["url"]:
                    break
        
        header_pattern = r"(?:-H|--header)\s+(?:'([^']+)'|\"([^\"]+)\"|([^\s]+))"
        header_matches = re.findall(header_pattern, curl_command)
        for groups in header_matches:
            header = groups[0] or groups[1] or groups[2]
            if header and ":" in header:
                key, value = header.split(":", 1)
                result["headers"][key.strip()] = value.strip()
        
        return result

    @staticmethod
    def extract_config(curl_command):
        parsed = CurlParser.parse(curl_command)
        
        # 简单可靠的方法：直接从整个字符串中查找 model 字段
        model_name = None
        
        # 方法1: 查找常见的模式
        # 首先去掉转义的反斜杠，方便查找
        clean_str = curl_command.replace('\\', '')
        
        # 在清理后的字符串中查找
        patterns = [
            r'"model":\s*"([^"]+)"',
            r'"model":\s*\'([^\']+)\'',
            r'model:\s*"([^"]+)"',
            r'model:\s*\'([^\']+)\'',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_str)
            if match:
                model_name = match.group(1)
                break
        
        # 方法2: 如果方法1没找到，尝试更简单的查找
        if not model_name:
            # 查找 "model" 关键词，然后找后面的值
            pos = curl_command.find('"model"')
            if pos == -1:
                pos = curl_command.find("'model'")
            
            if pos != -1:
                # 从 model 位置开始找后面的值
                after_model = curl_command[pos:]
                # 找第一个 :
                colon_pos = after_model.find(':')
                if colon_pos != -1:
                    after_colon = after_model[colon_pos+1:].strip()
                    # 看看是引号开头还是其他
                    if len(after_colon) > 0:
                        first_char = after_colon[0]
                        if first_char in ['"', "'"]:
                            # 找对应的结束引号
                            end_quote_pos = after_colon.find(first_char, 1)
                            if end_quote_pos != -1:
                                model_name = after_colon[1:end_quote_pos]
                                # 清理可能的转义字符
                                if model_name:
                                    model_name = model_name.replace('\\', '')
        
        return {
            "target_url": parsed.get("url"),
            "app_key": parsed["headers"].get("App-Key"),
            "app_sign": parsed["headers"].get("App-Sign"),
            "detection_type": parsed["headers"].get("Detection-Type"),
            "detection_id": parsed["headers"].get("Detection-Id"),
            "model_name": model_name
        }
