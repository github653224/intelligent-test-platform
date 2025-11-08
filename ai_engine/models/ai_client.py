import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from openai import AsyncOpenAI
import httpx

logger = logging.getLogger(__name__)

class AIClient:
    """AI客户端，支持OpenAI和Ollama模型"""
    
    def __init__(self):
        self.openai_client = None
        self.deepseek_client = None
        self.ollama_base_url = "http://localhost:11434"
        self.default_ollama_model = "llama3.2:latest"
        self.current_model = "ollama"
        self.current_model_name = "llama3.2:latest"  # 当前使用的具体模型名称
        # self.default_ollama_model = "deepseek-chat"  # 使用已经确认安装的模型名
        # self.current_model = "deepseek"
        self.ollama_api_version = "v1"  # 添加API版本控制
        self.max_retries = 2  # 添加重试次数限制
        
        try:
            # 初始化所有可能的客户端
            deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
            if deepseek_api_key:
                self.deepseek_client = AsyncOpenAI(
                    api_key=deepseek_api_key,
                    base_url="https://api.deepseek.com"
                )
                logger.info("Deepseek客户端初始化成功")
                # 若可用，优先使用 deepseek 以获取更稳定的响应
                self.current_model = "deepseek"
                self.current_model_name = "deepseek-chat"

            # 测试Ollama是否可用（延迟测试，避免在已有事件循环中使用asyncio.run）
            # 注意：在FastAPI环境中，已经有运行中的事件循环，不能使用asyncio.run()
            # 这里只做标记，实际测试在首次使用时进行
            try:
                # 尝试同步检查（如果Ollama不可用会快速失败）
                import requests
                try:
                    response = requests.get(f"{self.ollama_base_url}/api/version", timeout=1.0)
                    if response.status_code == 200:
                        logger.info("Ollama客户端可用")
                except:
                    logger.debug("Ollama服务不可用（这是正常的，如果使用Deepseek）")
            except Exception as e:
                logger.debug(f"Ollama检查跳过: {e}")
            
            logger.info(f"AI客户端初始化完成，当前使用模型: {self.current_model}")
                
        except Exception as e:
            logger.error(f"AI客户端初始化失败: {e}")

    async def switch_model(self, model_type: str) -> bool:
        """动态切换AI模型"""
        if model_type not in ["ollama", "deepseek"]:
            logger.error(f"不支持的模型类型: {model_type}")
            return False

        if model_type == "ollama":
            # 验证Ollama可用性
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.ollama_base_url}/api/version")
                    if response.status_code == 200:
                        self.current_model = "ollama"
                        logger.info(f"已切换到Ollama模型")
                        return True
                    else:
                        logger.error("Ollama服务不可用")
                        return False
            except Exception as e:
                logger.error(f"Ollama服务检查失败: {e}")
                return False

        elif model_type == "deepseek":
            if self.deepseek_client:
                self.current_model = "deepseek"
                logger.info(f"已切换到Deepseek模型")
                return True
            else:
                logger.error("Deepseek客户端未初始化")
                return False

    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> str:
        """生成AI响应"""
        try:
            if self.current_model == "openai" and self.openai_client:
                return await self._generate_openai_response(
                    prompt, model or "gpt-4", max_tokens, temperature
                )
            elif self.current_model == "deepseek" and self.deepseek_client:
                return await self._generate_deepseek_response(
                    prompt, model or "deepseek-chat", max_tokens, temperature
                )
            else:
                result = await self._generate_ollama_response(
                    prompt, model or self.default_ollama_model, max_tokens, temperature
                )
                # 若Ollama返回空字符串，尝试备选模型
                if not result and self.deepseek_client:
                    logger.warning("Ollama返回空响应，回退到Deepseek")
                    return await self._generate_deepseek_response(
                        prompt, "deepseek-chat", max_tokens, temperature
                    )
                return result
        except Exception as e:
            logger.error(f"AI响应生成失败: {e}")
            raise
    
    async def _generate_openai_response(
        self, 
        prompt: str, 
        model: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """使用OpenAI生成响应"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的软件测试专家，擅长需求分析、测试用例设计和自动化测试。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI响应生成失败: {e}")
            raise
    
    async def _generate_deepseek_response(
        self, 
        prompt: str, 
        model: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """使用Deepseek生成响应"""
        try:
            response = await self.deepseek_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的软件测试专家，擅长需求分析、测试用例设计和自动化测试。请严格按照用户要求的JSON格式返回结果，不要添加任何解释性文字，只返回可解析的JSON对象。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Deepseek响应生成失败: {e}")
            raise

    async def _generate_ollama_response(
        self, 
        prompt: str, 
        model: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """使用Ollama生成响应"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature
                        }
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama响应生成失败: {e}")
            raise
    
    async def _generate_ollama_response_stream(
        self, 
        prompt: str, 
        model: str = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """使用Ollama生成流式响应"""
        model = model or self.default_ollama_model
        self.current_model_name = model  # 更新当前使用的模型名称
        logger.info(f"开始调用Ollama流式生成，模型: {model}, URL: {self.ollama_base_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的软件测试专家，擅长需求分析、测试用例设计和自动化测试。请严格按照用户要求的JSON格式返回结果，不要添加任何解释性文字，只返回可解析的JSON对象。"},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": True
                    },
                    timeout=None
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"Ollama响应错误: {response.status_code}")
                        raise httpx.HTTPError(f"Ollama API响应: {response.status_code}")
                    
                    current_chunk = ""
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    # 直接返回内容，不添加data:前缀
                                    yield content
                                    current_chunk = ""
                        except json.JSONDecodeError:
                            continue
                    
                    if current_chunk:  # 发送最后的数据块
                        yield current_chunk
                        
        except Exception as e:
            logger.error(f"Ollama流式响应失败: {e}", exc_info=True)
            raise

    async def generate_response_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """生成AI流式响应"""
        logger.info(f"开始生成流式响应，使用模型: {self.current_model}")
        
        try:
            if self.current_model == "ollama":
                try:
                    async for chunk in self._generate_ollama_response_stream(
                        prompt, model, max_tokens, temperature
                    ):
                        yield chunk
                except Exception as e:
                    logger.error(f"Ollama响应失败，尝试切换到Deepseek: {e}")
                    if self.deepseek_client:
                        self.current_model = "deepseek"
                        self.current_model_name = "deepseek-chat"
                        async for chunk in self._generate_deepseek_response_stream(
                            prompt, "deepseek-chat", max_tokens, temperature
                        ):
                            yield chunk
                    else:
                        raise Exception("Ollama服务不可用，且没有配置备用模型")
            
            elif self.current_model == "deepseek":
                if not self.deepseek_client:
                    # 如果Deepseek不可用，尝试切换到Ollama
                    logger.warning("Deepseek客户端未初始化，尝试切换到Ollama")
                    self.current_model = "ollama"
                    async for chunk in self._generate_ollama_response_stream(
                        prompt, model, max_tokens, temperature
                    ):
                        yield chunk
                else:
                    async for chunk in self._generate_deepseek_response_stream(
                        prompt, model or "deepseek-chat", max_tokens, temperature
                    ):
                        yield chunk
            else:
                raise Exception(f"不支持的模型类型: {self.current_model}")
                
        except Exception as e:
            logger.error(f"生成响应失败: {e}", exc_info=True)
            raise

    async def _generate_deepseek_response_stream(
        self, 
        prompt: str, 
        model: str = "deepseek-chat", 
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """使用Deepseek生成流式响应"""
        if not self.deepseek_client:
            raise Exception("Deepseek客户端未初始化")
        
        self.current_model_name = model  # 更新当前使用的模型名称
        logger.info(f"开始调用Deepseek流式生成，模型: {model}")
        try:
            response = await self.deepseek_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的软件测试专家，擅长需求分析、测试用例设计和自动化测试。请严格按照用户要求的JSON格式返回结果，不要添加任何解释性文字，只返回可解析的JSON对象。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Deepseek流式响应失败: {e}", exc_info=True)
            raise

    async def analyze_requirement(self, requirement_text: str, context: str = "") -> Dict[str, Any]:
        """分析需求"""
        prompt = f"""
        请分析以下软件需求，并提供详细的测试分析：

        需求描述：{requirement_text}
        
        项目背景：{context}
        
        请提供以下分析：
        1. 功能要点分析
        2. 测试边界条件
        3. 潜在风险点
        4. 测试策略建议
        5. 优先级建议
        
        请以JSON格式返回结果。
        """
        
        response = await self.generate_response(prompt)
        # 这里可以添加JSON解析逻辑
        return {
            "analysis": response,
            "requirement_text": requirement_text
        }
    
    async def generate_test_cases(self, requirement: str, test_type: str) -> List[Dict[str, Any]]:
        """生成测试用例"""
        prompt = f"""
        基于以下需求生成{test_type}测试用例：

        需求：{requirement}
        
        请生成以下类型的测试用例：
        1. 正向测试用例
        2. 异常测试用例
        3. 边界值测试用例
        
        每个测试用例包含：
        - 测试标题
        - 前置条件
        - 测试步骤
        - 预期结果
        - 优先级
        
        请以JSON格式返回结果。
        """
        
        response = await self.generate_response(prompt)
        # 这里可以添加JSON解析逻辑
        return [{"test_case": response}]
    
    async def generate_api_tests(self, api_doc: str, base_url: str) -> List[Dict[str, Any]]:
        """生成API测试脚本"""
        prompt = f"""
        基于以下API文档生成自动化测试脚本：

        API文档：{api_doc}
        基础URL：{base_url}
        
        请生成：
        1. 请求测试脚本
        2. 响应验证脚本
        3. 错误处理测试
        4. 性能测试建议
        
        使用Python requests库编写测试代码。
        """
        
        response = await self.generate_response(prompt)
        return [{"api_test": response}]
    
    async def generate_ui_tests(self, page_url: str, actions: List[str], test_type: str) -> List[Dict[str, Any]]:
        """生成UI自动化测试脚本"""
        prompt = f"""
        基于以下页面和操作生成UI自动化测试脚本：

        页面URL：{page_url}
        用户操作：{', '.join(actions)}
        
        请生成：
        1. Selenium测试脚本
        2. Playwright测试脚本
        3. 元素定位策略
        4. 等待策略
        5. 断言验证
        
        使用Python编写测试代码。
        """
        
        response = await self.generate_response(prompt)
        return [{"ui_test": response}]