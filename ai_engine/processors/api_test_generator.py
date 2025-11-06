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
        test_scenarios: List[str] = None
    ) -> List[Dict[str, Any]]:
        """生成API测试脚本"""
        
        if test_scenarios is None:
            test_scenarios = []
        
        # 构建生成提示词
        prompt = self._build_generation_prompt(api_documentation, base_url, test_scenarios)
        
        try:
            # 调用AI生成API测试
            response = await self.ai_client.generate_response(prompt, temperature=0.3)
            
            # 解析生成的API测试
            api_tests = self._parse_api_tests_response(response)
            
            return api_tests
            
        except Exception as e:
            logger.error(f"API测试生成失败: {e}")
            return [{
                "status": "error",
                "error": str(e),
                "api_doc": api_documentation
            }]
    
    def _build_generation_prompt(
        self, 
        api_documentation: str, 
        base_url: str, 
        test_scenarios: List[str]
    ) -> str:
        """构建生成提示词"""
        
        scenarios_text = ""
        if test_scenarios:
            scenarios_text = f"\n测试场景：{', '.join(test_scenarios)}"
        
        prompt = f"""
        作为专业的API测试专家，请基于以下API文档生成自动化测试脚本：

        【API文档】
        {api_documentation}

        【基础URL】
        {base_url}
        {scenarios_text}

        请生成以下内容（以JSON格式返回）：

        {{
            "api_tests": [
                {{
                    "name": "测试用例名称",
                    "description": "测试描述",
                    "endpoint": "/api/endpoint",
                    "method": "GET/POST/PUT/DELETE",
                    "headers": {{
                        "Content-Type": "application/json",
                        "Authorization": "Bearer token"
                    }},
                    "request_body": {{
                        "key": "value"
                    }},
                    "expected_status": 200,
                    "expected_response": {{
                        "key": "value"
                    }},
                    "test_data": {{
                        "input": "输入数据",
                        "expected": "预期结果"
                    }},
                    "assertions": [
                        {{
                            "type": "status_code/response_body/response_time",
                            "expected": "预期值",
                            "description": "断言描述"
                        }}
                    ],
                    "python_code": "import requests\\n\\ndef test_api():\\n    # 测试代码"
                }}
            ],
            "test_suite": {{
                "name": "API测试套件",
                "description": "测试套件描述",
                "setup_code": "import requests\\nimport pytest\\n\\n# 设置代码",
                "teardown_code": "# 清理代码",
                "config": {{
                    "base_url": "{base_url}",
                    "timeout": 30,
                    "retry_count": 3
                }}
            }},
            "data_driven_tests": [
                {{
                    "name": "数据驱动测试",
                    "description": "测试描述",
                    "test_data": [
                        {{
                            "input": "输入1",
                            "expected": "预期1"
                        }},
                        {{
                            "input": "输入2", 
                            "expected": "预期2"
                        }}
                    ],
                    "python_code": "def test_with_data(input, expected):\\n    # 测试代码"
                }}
            ],
            "performance_tests": [
                {{
                    "name": "性能测试",
                    "description": "性能测试描述",
                    "load_config": {{
                        "users": 100,
                        "duration": 60,
                        "ramp_up": 10
                    }},
                    "python_code": "import locust\\n\\n# 性能测试代码"
                }}
            ]
        }}
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