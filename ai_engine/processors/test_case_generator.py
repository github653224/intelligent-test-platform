import json
import logging
from typing import Dict, Any, List
from ai_engine.models.ai_client import AIClient

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """测试用例生成处理器"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def generate(
        self, 
        requirement_text: str, 
        test_type: str, 
        test_scope: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """生成测试用例"""
        
        if test_scope is None:
            test_scope = {}
        
        # 构建生成提示词
        prompt = self._build_generation_prompt(requirement_text, test_type, test_scope)
        
        try:
            # 调用AI生成测试用例
            response = await self.ai_client.generate_response(prompt, temperature=0.4)
            
            # 解析生成的测试用例
            test_cases = self._parse_test_cases_response(response, test_type)
            
            return test_cases
            
        except Exception as e:
            logger.error(f"测试用例生成失败: {e}")
            return [{
                "status": "error",
                "error": str(e),
                "requirement": requirement_text
            }]
    
    def _build_generation_prompt(
        self, 
        requirement_text: str, 
        test_type: str, 
        test_scope: Dict[str, Any]
    ) -> str:
        """构建生成提示词"""
        
        scope_text = ""
        if test_scope:
            scope_text = f"\n测试范围：{json.dumps(test_scope, ensure_ascii=False)}"
        
        prompt = f"""
        作为专业的软件测试专家，请基于以下需求生成{test_type}测试用例：

        【需求描述】
        {requirement_text}
        {scope_text}

        请生成以下类型的测试用例（以JSON格式返回）：

        {{
            "test_cases": [
                {{
                    "title": "测试用例标题",
                    "description": "测试用例描述",
                    "test_type": "{test_type}",
                    "priority": "high/medium/low",
                    "preconditions": ["前置条件列表"],
                    "test_steps": [
                        {{
                            "step_number": 1,
                            "action": "操作步骤",
                            "expected_result": "预期结果",
                            "test_data": {{"key": "value"}}
                        }}
                    ],
                    "expected_result": "整体预期结果",
                    "test_data": {{
                        "input_data": "输入数据",
                        "expected_output": "预期输出"
                    }},
                    "tags": ["标签1", "标签2"],
                    "automation_ready": true/false
                }}
            ],
            "test_data_sets": [
                {{
                    "name": "测试数据集名称",
                    "description": "数据集描述",
                    "data": [
                        {{
                            "input": "输入值",
                            "expected": "预期结果",
                            "type": "positive/negative/edge"
                        }}
                    ]
                }}
            ],
            "automation_script": {{
                "framework": "推荐框架",
                "code_template": "代码模板",
                "setup_instructions": "环境设置说明"
            }}
        }}
        """
        
        return prompt
    
    def _parse_test_cases_response(self, response: str, test_type: str) -> List[Dict[str, Any]]:
        """解析测试用例响应"""
        try:
            # 尝试解析JSON
            if response.strip().startswith('{'):
                parsed = json.loads(response)
                test_cases = parsed.get('test_cases', [])
                
                # 为每个测试用例添加元数据
                for test_case in test_cases:
                    test_case['generated_by'] = 'ai'
                    test_case['test_type'] = test_type
                    test_case['status'] = 'draft'
                
                return test_cases
            else:
                # 如果不是标准JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    test_cases = parsed.get('test_cases', [])
                    
                    for test_case in test_cases:
                        test_case['generated_by'] = 'ai'
                        test_case['test_type'] = test_type
                        test_case['status'] = 'draft'
                    
                    return test_cases
                else:
                    # 返回原始响应作为单个测试用例
                    return [{
                        "title": f"AI生成的{test_type}测试用例",
                        "description": response,
                        "test_type": test_type,
                        "generated_by": "ai",
                        "status": "draft",
                        "raw_response": response
                    }]
                    
        except json.JSONDecodeError as e:
            logger.warning(f"测试用例JSON解析失败: {e}")
            return [{
                "title": f"AI生成的{test_type}测试用例",
                "description": response,
                "test_type": test_type,
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response,
                "parsing_error": str(e)
            }]
        except Exception as e:
            logger.error(f"测试用例解析失败: {e}")
            return [{
                "title": f"AI生成的{test_type}测试用例",
                "description": response,
                "test_type": test_type,
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response,
                "parsing_error": str(e)
            }] 