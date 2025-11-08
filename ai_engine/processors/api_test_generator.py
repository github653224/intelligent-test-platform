import json
import logging
from typing import Dict, Any, List
from ai_engine.models.ai_client import AIClient

logger = logging.getLogger(__name__)


class APITestGenerator:
    """API测试生成处理器"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def generate(
        self, 
        api_documentation: str, 
        base_url: str, 
        test_scenarios: List[str] = None,
        parsed_doc: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成API测试脚本（工程化结构）"""
        
        if test_scenarios is None:
            test_scenarios = []
        
        # 构建生成提示词
        prompt = self._build_generation_prompt(api_documentation, base_url, test_scenarios, parsed_doc)
        
        try:
            # 调用AI生成API测试
            response = await self.ai_client.generate_response(prompt, temperature=0.3)
            
            # 解析生成的API测试（工程化结构）
            result = self._parse_structured_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"API测试生成失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "api_doc": api_documentation
            }
    
    def _build_generation_prompt(
        self, 
        api_documentation: str, 
        base_url: str, 
        test_scenarios: List[str],
        parsed_doc: Dict[str, Any] = None
    ) -> str:
        """构建生成提示词"""
        
        scenarios_text = ""
        if test_scenarios:
            scenarios_text = f"\n测试场景：{', '.join(test_scenarios)}"
        
        # 如果有解析后的文档，提供更详细的信息
        endpoints_info = ""
        if parsed_doc and parsed_doc.get("endpoints"):
            endpoints_info = "\n【接口列表】\n"
            for idx, endpoint in enumerate(parsed_doc["endpoints"][:20], 1):  # 限制前20个
                if parsed_doc["type"] == "openapi":
                    method = endpoint.get("method", "")
                    path = endpoint.get("path", "")
                    summary = endpoint.get("summary", "")
                    endpoints_info += f"{idx}. {method} {path} - {summary}\n"
                else:
                    method = endpoint.get("method", "")
                    path = endpoint.get("path", "")
                    name = endpoint.get("name", "")
                    endpoints_info += f"{idx}. {method} {path} - {name}\n"
            if len(parsed_doc["endpoints"]) > 20:
                endpoints_info += f"... 还有 {len(parsed_doc['endpoints']) - 20} 个接口\n"
        
        prompt = f"""
作为专业的API测试专家，请基于以下API文档生成**工程化的、可直接运行的**自动化测试代码。

【重要要求】
1. **必须为文档中的所有接口生成测试代码**（如果接口数量很多，至少生成前50个）
2. **代码必须可以直接运行**，包含所有必要的导入和配置
3. **使用工程化的代码结构**：类、方法、模块化设计
4. **提供完整的项目结构建议**：目录结构、文件组织

【API文档】
{api_documentation}
{endpoints_info}

【基础URL】
{base_url}
{scenarios_text}

【代码结构要求】
请生成以下工程化的代码结构（以JSON格式返回）：

{{
    "project_structure": {{
        "description": "项目结构说明",
        "directories": [
            "tests/ - 测试文件目录",
            "tests/api/ - API测试文件",
            "config/ - 配置文件",
            "utils/ - 工具类",
            "data/ - 测试数据"
        ],
        "files": [
            "tests/api/test_user_api.py - 用户相关接口测试",
            "tests/api/test_product_api.py - 产品相关接口测试",
            "config/settings.py - 配置文件",
            "utils/api_client.py - API客户端工具类",
            "conftest.py - pytest配置",
            "requirements.txt - 依赖包",
            "README.md - 项目说明"
        ]
    }},
    "api_client_class": {{
        "class_name": "APIClient",
        "description": "API客户端基类，封装通用请求方法",
        "code": "class APIClient:\\n    def __init__(self, base_url, timeout=30):\\n        # 初始化代码\\n    def request(self, method, endpoint, **kwargs):\\n        # 请求方法\\n    def get(self, endpoint, **kwargs):\\n        # GET方法\\n    def post(self, endpoint, **kwargs):\\n        # POST方法"
    }},
    "config_file": {{
        "file_name": "config/settings.py",
        "description": "配置文件",
        "code": "BASE_URL = '{base_url}'\\nTIMEOUT = 30\\n# 其他配置"
    }},
    "api_tests": [
        {{
            "file_name": "tests/api/test_example.py",
            "class_name": "TestExampleAPI",
            "description": "测试类描述",
            "endpoint": "/api/endpoint",
            "method": "GET/POST/PUT/DELETE",
            "test_methods": [
                {{
                    "method_name": "test_get_example_success",
                    "description": "测试成功场景",
                    "code": "def test_get_example_success(self):\\n    # 测试代码"
                }},
                {{
                    "method_name": "test_get_example_error",
                    "description": "测试错误场景",
                    "code": "def test_get_example_error(self):\\n    # 测试代码"
                }}
            ],
            "full_class_code": "import pytest\\nfrom utils.api_client import APIClient\\n\\nclass TestExampleAPI:\\n    def setup_method(self):\\n        # 设置方法\\n    def test_get_example_success(self):\\n        # 完整测试代码\\n    def test_get_example_error(self):\\n        # 完整测试代码"
        }}
    ],
    "conftest": {{
        "description": "pytest配置文件",
        "code": "import pytest\\nfrom utils.api_client import APIClient\\n\\n@pytest.fixture\\ndef api_client():\\n    # fixture代码"
    }},
    "requirements": {{
        "description": "依赖包列表",
        "packages": ["requests", "pytest", "pytest-html"]
    }},
    "readme": {{
        "description": "项目说明文档",
        "content": "# API测试项目\\n\\n## 安装依赖\\npip install -r requirements.txt\\n\\n## 运行测试\\npytest tests/"
    }}
}}

【代码生成规则】
1. 每个接口至少生成2个测试方法：成功场景和错误场景
2. 使用pytest框架，代码结构清晰
3. 使用类组织测试，每个类对应一个功能模块
4. 提供完整的断言验证：状态码、响应体、响应时间
5. 代码必须包含错误处理和日志记录
6. 使用配置文件管理base_url等配置
7. 提供清晰的注释和文档字符串

请严格按照以上要求生成代码，确保代码可以直接运行。
        """
        
        return prompt
    
    def _parse_api_tests_response(self, response: str) -> List[Dict[str, Any]]:
        """解析API测试响应"""
        try:
            if not response or not response.strip():
                logger.warning("AI响应为空")
                return []
            
            # 清理响应文本，移除可能的markdown代码块标记
            cleaned_response = response.strip()
            
            # 如果包含markdown代码块标记，提取JSON部分
            if "```json" in cleaned_response:
                import re
                match = re.search(r'```json\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
                    logger.info("从markdown代码块中提取JSON")
            elif "```" in cleaned_response:
                import re
                match = re.search(r'```\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
                    logger.info("从代码块中提取JSON")
            
            # 尝试直接解析JSON
            try:
                parsed = json.loads(cleaned_response)
                api_tests = parsed.get('api_tests', [])
                
                if api_tests:
                    # 为每个测试添加元数据
                    for test in api_tests:
                        test['generated_by'] = 'ai'
                        test['test_type'] = 'api'
                        if 'status' not in test:
                            test['status'] = 'draft'
                    logger.info(f"成功解析出 {len(api_tests)} 个API测试")
                    return api_tests
            except json.JSONDecodeError:
                # 尝试提取JSON对象
                import re
                # 更精确的JSON提取，匹配完整的JSON对象
                json_match = re.search(r'\{[\s\S]*"api_tests"[\s\S]*\}', cleaned_response)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        api_tests = parsed.get('api_tests', [])
                        if api_tests:
                            for test in api_tests:
                                test['generated_by'] = 'ai'
                                test['test_type'] = 'api'
                                if 'status' not in test:
                                    test['status'] = 'draft'
                            logger.info(f"通过正则提取成功解析出 {len(api_tests)} 个API测试")
                            return api_tests
                    except json.JSONDecodeError as e:
                        logger.warning(f"正则提取的JSON解析失败: {e}")
            
            # 如果无法解析，记录原始响应用于调试
            logger.warning(f"无法解析JSON，返回原始响应")
            return [{
                "name": "AI生成的API测试",
                "description": "无法解析JSON格式，返回原始响应",
                "test_type": "api",
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response[:5000]  # 限制长度
            }]
                    
        except Exception as e:
            logger.error(f"API测试解析失败: {e}", exc_info=True)
            return [{
                "name": "AI生成的API测试",
                "description": f"解析失败: {str(e)}",
                "test_type": "api",
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response[:5000] if response else "",
                "parsing_error": str(e)
            }]
    
    def _parse_structured_response(self, response: str) -> Dict[str, Any]:
        """解析工程化结构的响应"""
        try:
            if not response or not response.strip():
                logger.warning("AI响应为空")
                return {
                    "status": "error",
                    "error": "AI响应为空"
                }
            
            # 清理响应文本
            cleaned_response = response.strip()
            
            # 提取JSON部分
            if "```json" in cleaned_response:
                import re
                match = re.search(r'```json\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
            elif "```" in cleaned_response:
                import re
                match = re.search(r'```\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
            
            # 尝试解析JSON
            try:
                parsed = json.loads(cleaned_response)
                
                # 确保返回完整的工程化结构
                result = {
                    "status": "success",
                    "project_structure": parsed.get("project_structure", {}),
                    "api_client_class": parsed.get("api_client_class", {}),
                    "config_file": parsed.get("config_file", {}),
                    "api_tests": parsed.get("api_tests", []),
                    "conftest": parsed.get("conftest", {}),
                    "requirements": parsed.get("requirements", {}),
                    "readme": parsed.get("readme", {})
                }
                
                logger.info(f"成功解析工程化API测试结构，包含 {len(result.get('api_tests', []))} 个测试文件")
                return result
                
            except json.JSONDecodeError:
                # 尝试提取JSON对象
                import re
                json_match = re.search(r'\{[\s\S]*"api_tests"[\s\S]*\}', cleaned_response)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        result = {
                            "status": "success",
                            "project_structure": parsed.get("project_structure", {}),
                            "api_client_class": parsed.get("api_client_class", {}),
                            "config_file": parsed.get("config_file", {}),
                            "api_tests": parsed.get("api_tests", []),
                            "conftest": parsed.get("conftest", {}),
                            "requirements": parsed.get("requirements", {}),
                            "readme": parsed.get("readme", {})
                        }
                        logger.info(f"通过正则提取成功解析工程化结构")
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"正则提取的JSON解析失败: {e}")
            
            # 如果无法解析，返回原始响应
            logger.warning("无法解析JSON，返回原始响应")
            return {
                "status": "error",
                "error": "无法解析JSON格式",
                "raw_response": response[:10000]
            }
                    
        except Exception as e:
            logger.error(f"解析工程化结构失败: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "raw_response": response[:5000] if response else ""
            } 