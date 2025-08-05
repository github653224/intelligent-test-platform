```python
class AIClient:
    def __init__(self):
        self.openai_client = None
        self.deepseek_client = None
        self.ollama_base_url = "http://localhost:11434"
        self.current_model = "openai"  # openai, deepseek 或 ollama
        
        # 初始化OpenAI客户端
        try:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("OpenAI客户端初始化成功")
            else:
                deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
                if deepseek_api_key:
                    import openai as deepseek_client
                    deepseek_client.api_key = deepseek_api_key
                    deepseek_client.api_base = settings.DEEPSEEK_API_BASE
                    self.deepseek_client = deepseek_client
                    self.current_model = "deepseek"
                    logger.info("Deepseek客户端初始化成功")
                else:
                    logger.warning("未找到API密钥，将使用Ollama")
                    self.current_model = "ollama"
        except Exception as e:
            logger.warning(f"AI客户端初始化失败: {e}")
            self.current_model = "ollama"

    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> str:
        try:
            if self.current_model == "openai" and self.openai_client:
                return await self._generate_openai_response(
                    prompt, model or "gpt-4", max_tokens, temperature
                )
            elif self.current_model == "deepseek" and self.deepseek_client:
                return await self._generate_deepseek_response(
                    prompt, model or settings.DEEPSEEK_MODEL, max_tokens, temperature
                )
            else:
                return await self._generate_ollama_response(
                    prompt, model or "llama2", max_tokens, temperature
                )
        except Exception as e:
            logger.error(f"AI响应生成失败: {e}")
            raise

    async def _generate_deepseek_response(
        self, 
        prompt: str, 
        model: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        try:
            response = await self.deepseek_client.ChatCompletion.acreate(
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
            logger.error(f"Deepseek响应生成失败: {e}")
            raise

    # ...existing code...
```