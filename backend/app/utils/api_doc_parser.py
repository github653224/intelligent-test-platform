"""
API文档解析器
支持OpenAPI/Swagger、Postman Collection等格式
"""
import json
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class APIDocParser:
    """API文档解析器"""
    
    @staticmethod
    def parse(file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        解析API文档文件
        
        Args:
            file_content: 文件二进制内容
            filename: 文件名
            
        Returns:
            解析后的API文档结构
        """
        file_ext = Path(filename).suffix.lower()
        
        try:
            # 根据文件扩展名判断格式
            if file_ext in ['.json']:
                return APIDocParser._parse_json(file_content, filename)
            elif file_ext in ['.yaml', '.yml']:
                return APIDocParser._parse_yaml(file_content, filename)
            else:
                # 尝试自动检测格式
                return APIDocParser._auto_detect_and_parse(file_content, filename)
        except Exception as e:
            logger.error(f"解析API文档 {filename} 失败: {e}")
            raise ValueError(f"API文档解析失败: {str(e)}")
    
    @staticmethod
    def _parse_json(file_content: bytes, filename: str) -> Dict[str, Any]:
        """解析JSON格式的API文档"""
        try:
            content = file_content.decode('utf-8')
            data = json.loads(content)
            
            # 检测文档类型
            if 'openapi' in data or 'swagger' in data:
                return APIDocParser._parse_openapi(data)
            elif 'info' in data and 'item' in data:
                return APIDocParser._parse_postman(data)
            else:
                # 尝试作为OpenAPI解析
                return APIDocParser._parse_openapi(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
    
    @staticmethod
    def _parse_yaml(file_content: bytes, filename: str) -> Dict[str, Any]:
        """解析YAML格式的API文档"""
        try:
            content = file_content.decode('utf-8')
            data = yaml.safe_load(content)
            
            if 'openapi' in data or 'swagger' in data:
                return APIDocParser._parse_openapi(data)
            else:
                raise ValueError("无法识别的YAML格式，仅支持OpenAPI/Swagger格式")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML格式错误: {str(e)}")
    
    @staticmethod
    def _auto_detect_and_parse(file_content: bytes, filename: str) -> Dict[str, Any]:
        """自动检测并解析文档格式"""
        content = file_content.decode('utf-8')
        
        # 尝试JSON
        try:
            data = json.loads(content)
            if 'openapi' in data or 'swagger' in data:
                return APIDocParser._parse_openapi(data)
            elif 'info' in data and 'item' in data:
                return APIDocParser._parse_postman(data)
        except:
            pass
        
        # 尝试YAML
        try:
            data = yaml.safe_load(content)
            if 'openapi' in data or 'swagger' in data:
                return APIDocParser._parse_openapi(data)
        except:
            pass
        
        raise ValueError("无法识别API文档格式，请确保是OpenAPI/Swagger或Postman Collection格式")
    
    @staticmethod
    def _parse_openapi(data: Dict[str, Any]) -> Dict[str, Any]:
        """解析OpenAPI/Swagger文档"""
        result = {
            "type": "openapi",
            "version": data.get("openapi") or data.get("swagger", "unknown"),
            "info": data.get("info", {}),
            "servers": data.get("servers", []),
            "base_url": "",
            "endpoints": []
        }
        
        # 提取基础URL
        if result["servers"]:
            result["base_url"] = result["servers"][0].get("url", "")
        elif "host" in data:
            scheme = data.get("schemes", ["http"])[0]
            host = data.get("host", "")
            base_path = data.get("basePath", "")
            result["base_url"] = f"{scheme}://{host}{base_path}"
        
        # 解析所有路径
        paths = data.get("paths", {})
        components = data.get("components", {})
        schemas = components.get("schemas", {})
        security_schemes = components.get("securitySchemes", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    endpoint = APIDocParser._parse_openapi_operation(
                        path, method.upper(), operation, schemas, security_schemes
                    )
                    result["endpoints"].append(endpoint)
        
        return result
    
    @staticmethod
    def _parse_openapi_operation(
        path: str,
        method: str,
        operation: Dict[str, Any],
        schemas: Dict[str, Any],
        security_schemes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析OpenAPI操作"""
        endpoint = {
            "path": path,
            "method": method,
            "operation_id": operation.get("operationId", ""),
            "summary": operation.get("summary", ""),
            "description": operation.get("description", ""),
            "tags": operation.get("tags", []),
            "parameters": [],
            "request_body": None,
            "responses": {},
            "security": operation.get("security", [])
        }
        
        # 解析参数
        for param in operation.get("parameters", []):
            endpoint["parameters"].append({
                "name": param.get("name", ""),
                "in": param.get("in", "query"),  # query, path, header, cookie
                "required": param.get("required", False),
                "schema": param.get("schema", {}),
                "description": param.get("description", "")
            })
        
        # 解析请求体
        request_body = operation.get("requestBody")
        if request_body:
            content = request_body.get("content", {})
            for content_type, schema_ref in content.items():
                if "application/json" in content_type:
                    endpoint["request_body"] = {
                        "content_type": content_type,
                        "schema": schema_ref.get("schema", {}),
                        "required": request_body.get("required", False)
                    }
                    break
        
        # 解析响应
        for status_code, response in operation.get("responses", {}).items():
            endpoint["responses"][status_code] = {
                "description": response.get("description", ""),
                "schema": response.get("content", {}).get("application/json", {}).get("schema", {})
            }
        
        return endpoint
    
    @staticmethod
    def _parse_postman(data: Dict[str, Any]) -> Dict[str, Any]:
        """解析Postman Collection文档"""
        result = {
            "type": "postman",
            "info": data.get("info", {}),
            "base_url": "",
            "endpoints": []
        }
        
        # 提取变量（可能包含base_url）
        variables = data.get("variable", [])
        for var in variables:
            if var.get("key") in ["base_url", "baseUrl", "url"]:
                result["base_url"] = var.get("value", "")
                break
        
        # 递归解析所有请求
        def parse_item(item: Dict[str, Any], base_url: str = ""):
            if "request" in item:
                # 这是一个请求
                request = item["request"]
                url_info = request.get("url", {})
                
                # 构建完整URL
                if isinstance(url_info, str):
                    full_url = url_info
                else:
                    protocol = url_info.get("protocol", "https")
                    host = url_info.get("host", [])
                    path = url_info.get("path", [])
                    
                    if host:
                        host_str = ".".join(host)
                        path_str = "/".join(path) if path else ""
                        full_url = f"{protocol}://{host_str}/{path_str}".rstrip("/")
                    else:
                        full_url = url_info.get("raw", "")
                
                # 提取基础URL（第一次遇到时）
                if not result["base_url"] and full_url:
                    from urllib.parse import urlparse
                    parsed = urlparse(full_url)
                    result["base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                
                endpoint = {
                    "path": url_info.get("path", []) if isinstance(url_info, dict) else full_url.split("?")[0],
                    "method": request.get("method", "GET"),
                    "name": item.get("name", ""),
                    "description": request.get("description", ""),
                    "headers": {},
                    "body": None,
                    "responses": []
                }
                
                # 解析请求头
                for header in request.get("header", []):
                    endpoint["headers"][header.get("key", "")] = header.get("value", "")
                
                # 解析请求体
                body = request.get("body")
                if body:
                    body_mode = body.get("mode", "raw")
                    if body_mode == "raw":
                        endpoint["body"] = {
                            "mode": "raw",
                            "content": body.get("raw", "")
                        }
                    elif body_mode == "formdata":
                        endpoint["body"] = {
                            "mode": "formdata",
                            "content": body.get("formdata", [])
                        }
                    elif body_mode == "urlencoded":
                        endpoint["body"] = {
                            "mode": "urlencoded",
                            "content": body.get("urlencoded", [])
                        }
                
                result["endpoints"].append(endpoint)
            
            # 递归处理子项
            for sub_item in item.get("item", []):
                parse_item(sub_item, base_url)
        
        # 开始解析
        for item in data.get("item", []):
            parse_item(item)
        
        return result
    
    @staticmethod
    def extract_endpoints_summary(parsed_doc: Dict[str, Any]) -> str:
        """提取API文档摘要，用于AI生成"""
        summary_parts = []
        
        if parsed_doc["type"] == "openapi":
            summary_parts.append(f"OpenAPI {parsed_doc['version']} 文档")
            if parsed_doc.get("info"):
                info = parsed_doc["info"]
                summary_parts.append(f"标题: {info.get('title', '')}")
                summary_parts.append(f"版本: {info.get('version', '')}")
                summary_parts.append(f"描述: {info.get('description', '')}")
        else:
            summary_parts.append("Postman Collection 文档")
            if parsed_doc.get("info"):
                info = parsed_doc["info"]
                summary_parts.append(f"名称: {info.get('name', '')}")
                summary_parts.append(f"描述: {info.get('description', '')}")
        
        summary_parts.append(f"\n基础URL: {parsed_doc.get('base_url', '未指定')}")
        summary_parts.append(f"\n共 {len(parsed_doc.get('endpoints', []))} 个接口:\n")
        
        for idx, endpoint in enumerate(parsed_doc.get("endpoints", [])[:50], 1):  # 限制前50个
            if parsed_doc["type"] == "openapi":
                method = endpoint.get("method", "")
                path = endpoint.get("path", "")
                summary = endpoint.get("summary", "")
                summary_parts.append(f"{idx}. {method} {path} - {summary}")
            else:
                method = endpoint.get("method", "")
                path = endpoint.get("path", "")
                name = endpoint.get("name", "")
                summary_parts.append(f"{idx}. {method} {path} - {name}")
        
        if len(parsed_doc.get("endpoints", [])) > 50:
            summary_parts.append(f"\n... 还有 {len(parsed_doc.get('endpoints', [])) - 50} 个接口")
        
        return "\n".join(summary_parts)

