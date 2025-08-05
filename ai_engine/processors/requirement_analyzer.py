import json
import logging
from typing import Dict, Any, List, AsyncGenerator
from ai_engine.models.ai_client import AIClient

logger = logging.getLogger(__name__)


class RequirementAnalyzer:
    """需求分析处理器"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def analyze(
        self, 
        requirement_text: str, 
        project_context: str = "", 
        test_focus: List[str] = None
    ) -> Dict[str, Any]:
        """分析需求并生成测试要点"""
        
        if test_focus is None:
            test_focus = []
        
        # 构建分析提示词
        prompt = self._build_analysis_prompt(requirement_text, project_context, test_focus)
        
        try:
            # 调用AI进行分析
            response = await self.ai_client.generate_response(prompt, temperature=0.3)
            
            # 解析分析结果
            analysis_result = self._parse_analysis_response(response)
            
            return {
                "status": "success",
                "requirement_text": requirement_text,
                "analysis": analysis_result,
                "test_focus": test_focus
            }
            
        except Exception as e:
            logger.error(f"需求分析失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "requirement_text": requirement_text
            }
    
    async def analyze_stream(
        self, 
        requirement_text: str, 
        project_context: str = "", 
        test_focus: List[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式分析需求"""
        
        if test_focus is None:
            test_focus = []
        
        # 构建分析提示词
        prompt = self._build_analysis_prompt(requirement_text, project_context, test_focus)
        
        try:
            # 流式输出分析结果
            async for chunk in self.ai_client.generate_response_stream(prompt, temperature=0.3):
                yield chunk
                
        except Exception as e:
            logger.error(f"需求分析失败: {e}")
            yield f"\n\n分析出错: {str(e)}"

    def _build_analysis_prompt(
        self, 
        requirement_text: str, 
        project_context: str, 
        test_focus: List[str]
    ) -> str:
        """构建分析提示词"""
        
        focus_text = ""
        if test_focus:
            focus_text = f"\n重点关注测试领域：{', '.join(test_focus)}"
        
        prompt = f"""
        作为专业的软件测试专家，请对以下需求进行详细分析：

        【需求描述】
        {requirement_text}

        【项目背景】
        {project_context}
        {focus_text}

        请提供以下分析结果（以JSON格式返回）：

        {{
            "functional_points": [
                {{
                    "point": "功能点描述",
                    "priority": "high/medium/low",
                    "complexity": "high/medium/low",
                    "risk_level": "high/medium/low"
                }}
            ],
            "test_boundaries": [
                {{
                    "boundary": "边界条件描述",
                    "test_type": "positive/negative/edge",
                    "priority": "high/medium/low"
                }}
            ],
            "risk_points": [
                {{
                    "risk": "风险点描述",
                    "impact": "high/medium/low",
                    "mitigation": "缓解措施"
                }}
            ],
            "test_strategy": {{
                "overall_approach": "整体测试策略",
                "test_levels": ["unit", "integration", "system", "acceptance"],
                "automation_scope": "自动化范围建议",
                "tools_recommendation": ["推荐工具列表"]
            }},
            "test_priorities": [
                {{
                    "area": "测试区域",
                    "priority": "high/medium/low",
                    "rationale": "优先级理由"
                }}
            ],
            "estimated_effort": {{
                "total_hours": "预估总工时",
                "breakdown": {{
                    "test_planning": "测试计划工时",
                    "test_design": "测试设计工时",
                    "test_execution": "测试执行工时",
                    "automation": "自动化开发工时"
                }}
            }}
        }}
        """
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析AI分析响应"""
        try:
            # 尝试解析JSON
            if response.strip().startswith('{'):
                return json.loads(response)
            else:
                # 如果不是标准JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # 返回原始响应
                    return {
                        "raw_response": response,
                        "parsing_error": "无法解析JSON格式"
                    }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            return {
                "raw_response": response,
                "parsing_error": str(e)
            }
        except Exception as e:
            logger.error(f"响应解析失败: {e}")
            return {
                "raw_response": response,
                "parsing_error": str(e)
            }