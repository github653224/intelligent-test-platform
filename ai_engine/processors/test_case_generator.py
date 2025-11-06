import json
import logging
from typing import Dict, Any, List
from ai_engine.models.ai_client import AIClient
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """测试用例生成处理器"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    def _clean_requirement_text(self, text: str) -> str:
        """清理需求文本，去除重复字符"""
        if not text:
            return ""
        import re
        # 去除换行符和多余空格
        text = text.replace('\n', ' ').replace('\r', ' ').strip()
        
        # 处理重复字符：检测连续重复的字符（如"系系统统"变成"系统"）
        # 方法1：处理每个字符重复2次的情况（如"系系统统课课"->"系统课"）
        result = []
        i = 0
        while i < len(text):
            if i < len(text) - 1 and text[i] == text[i + 1]:
                # 发现重复字符，只取一个
                result.append(text[i])
                i += 2  # 跳过重复的字符
            else:
                result.append(text[i])
                i += 1
        
        text = ''.join(result)
        
        # 方法2：处理连续重复的字符串模式（如"系统系统系统"->"系统"）
        text = re.sub(r'(.{1,10}?)\1{1,}', r'\1', text)
        
        # 去除多余空格
        text = ' '.join(text.split())
        return text.strip()
    
    async def generate(
        self, 
        requirement_text: str, 
        test_type: str, 
        test_scope: Dict[str, Any] = None,
        generate_script: bool = True
    ) -> List[Dict[str, Any]]:
        """生成测试用例"""
        
        # 清理需求文本，去除重复字符
        requirement_text = self._clean_requirement_text(requirement_text)
        
        if test_scope is None:
            test_scope = {}
        
        # 构建生成提示词
        prompt = self._build_generation_prompt(requirement_text, test_type, test_scope, generate_script)
        
        try:
            # 调用AI生成测试用例
            response = await self.ai_client.generate_response(prompt, temperature=0.4)
            
            # 解析生成的测试用例
            test_cases = self._parse_test_cases_response(response, test_type)

            # 若AI响应为空或未解析出用例，回退到基于需求文本的本地生成模板
            # 当解析不到或仅得到占位数据时，使用回退模板
            if not test_cases or self._looks_like_placeholder(test_cases):
                logger.warning("AI未返回有效测试用例，使用回退模板生成")
                test_cases = self._fallback_generate(requirement_text, test_type)
            
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
        test_scope: Dict[str, Any],
        generate_script: bool = True
    ) -> str:
        """构建生成提示词"""
        
        scope_text = ""
        if test_scope and isinstance(test_scope, dict):
            scope_items = [f"{k}: {v}" for k, v in test_scope.items() if v]
            if scope_items:
                scope_text = f"\n【测试范围】\n" + "\n".join(scope_items)
        
        test_type_map = {
            "functional": "功能测试",
            "api": "接口测试（API）",
            "ui": "UI测试"
        }
        test_type_cn = test_type_map.get(test_type, test_type)
        
        # 根据测试类型生成不同的提示词和格式要求
        if test_type == "api":
            format_example = """{
    "test_cases": [
        {
            "title": "API测试用例标题（如：验证用户登录接口）",
            "description": "测试用例的详细描述",
            "test_type": "api",
            "priority": "high/medium/low",
            "preconditions": ["前置条件1", "前置条件2"],
            "test_steps": [
                {
                    "step_number": 1,
                    "action": "发送POST请求到 /api/login",
                    "expected_result": "请求成功发送，返回状态码200",
                    "test_data": {
                        "method": "POST",
                        "url": "/api/login",
                        "headers": {"Content-Type": "application/json"},
                        "body": {"username": "testuser", "password": "123456"}
                    }
                },
                {
                    "step_number": 2,
                    "action": "验证响应状态码",
                    "expected_result": "状态码为200",
                    "test_data": {"expected_status": 200}
                },
                {
                    "step_number": 3,
                    "action": "验证响应体结构",
                    "expected_result": "响应包含token字段且不为空",
                    "test_data": {"expected_fields": ["token", "user_id"]}
                }
            ],
            "expected_result": "接口返回正确的token和用户信息",
            "test_data": {
                "request_method": "POST",
                "request_url": "/api/login",
                "request_headers": {"Content-Type": "application/json"},
                "request_body": {"username": "testuser", "password": "123456"},
                "expected_status_code": 200,
                "expected_response": {"token": "string", "user_id": "number"}
            },
            "tags": ["登录", "认证", "正向测试"],
            "automation_ready": true
        }
    ]
}"""
            if generate_script:
                format_example = format_example.replace(
                    '"automation_ready": true',
                    '"automation_ready": true,\n            "python_code": "import requests\\nimport json\\n\\ndef test_login_api():\\n    url = \\"http://localhost:8000/api/login\\"\\n    headers = {\\"Content-Type\\": \\"application/json\\"}\\n    data = {\\"username\\": \\"testuser\\", \\"password\\": \\"123456\\"}\\n    response = requests.post(url, headers=headers, json=data)\\n    assert response.status_code == 200\\n    result = response.json()\\n    assert \\"token\\" in result\\n    print(\\"Test passed\\")"'
                )
                specific_requirements = """【API测试特殊要求】
1. test_data中必须包含：request_method（请求方法：GET/POST/PUT/DELETE）、request_url（接口路径）、request_headers（请求头）、request_body（请求体，GET请求为空对象）
2. test_steps中每一步都要明确说明是发送请求还是验证响应
3. 必须包含状态码验证和响应体结构验证
4. 对于异常用例，要包含错误状态码（如400、401、500）和错误信息验证
5. **必须为每个测试用例生成完整的Python自动化测试脚本代码**，放在python_code字段中，使用requests库编写可执行的测试代码
6. **重要：生成的Python代码必须保持正确的格式和缩进，所有关键字、标识符和操作符之间必须有空格**，例如 `import requests` 和 `response = requests.post(...)` 而不是 `importrequests` 或 `response=requests.post(...)`"""
            else:
                specific_requirements = """【API测试特殊要求】
1. test_data中必须包含：request_method（请求方法：GET/POST/PUT/DELETE）、request_url（接口路径）、request_headers（请求头）、request_body（请求体，GET请求为空对象）
2. test_steps中每一步都要明确说明是发送请求还是验证响应
3. 必须包含状态码验证和响应体结构验证
4. 对于异常用例，要包含错误状态码（如400、401、500）和错误信息验证"""
        
        elif test_type == "ui":
            format_example = """{
    "test_cases": [
        {
            "title": "UI测试用例标题（如：验证登录页面功能）",
            "description": "测试用例的详细描述",
            "test_type": "ui",
            "priority": "high/medium/low",
            "preconditions": ["浏览器已打开", "访问登录页面"],
            "test_steps": [
                {
                    "step_number": 1,
                    "action": "在用户名输入框中输入'admin'",
                    "expected_result": "用户名输入框显示'admin'",
                    "test_data": {
                        "element": "用户名输入框",
                        "element_locator": "input[name='username']",
                        "action_type": "input",
                        "value": "admin"
                    }
                },
                {
                    "step_number": 2,
                    "action": "在密码输入框中输入'123456'",
                    "expected_result": "密码输入框显示密码（加密显示）",
                    "test_data": {
                        "element": "密码输入框",
                        "element_locator": "input[type='password']",
                        "action_type": "input",
                        "value": "123456"
                    }
                },
                {
                    "step_number": 3,
                    "action": "点击登录按钮",
                    "expected_result": "按钮可点击，页面开始跳转",
                    "test_data": {
                        "element": "登录按钮",
                        "element_locator": "button[type='submit']",
                        "action_type": "click"
                    }
                },
                {
                    "step_number": 4,
                    "action": "验证页面跳转到首页",
                    "expected_result": "URL变为首页地址，显示用户信息",
                    "test_data": {
                        "expected_url": "/dashboard",
                        "expected_elements": ["用户头像", "导航菜单"]
                    }
                }
            ],
            "expected_result": "成功登录并跳转到首页，显示用户信息",
            "test_data": {
                "page_url": "/login",
                "elements": [
                    {"name": "用户名输入框", "locator": "input[name='username']", "type": "input"},
                    {"name": "密码输入框", "locator": "input[type='password']", "type": "input"},
                    {"name": "登录按钮", "locator": "button[type='submit']", "type": "button"}
                ],
                "user_interactions": ["输入用户名", "输入密码", "点击登录"],
                "verification_points": ["页面跳转", "URL变化", "元素可见性"]
            },
            "tags": ["登录", "UI交互", "正向测试"],
            "automation_ready": true
        }
    ]
}"""
            if generate_script:
                format_example = format_example.replace(
                    '"automation_ready": true',
                    '"automation_ready": true,\n            "python_code": "from selenium import webdriver\\nfrom selenium.webdriver.common.by import By\\nfrom selenium.webdriver.support.ui import WebDriverWait\\nfrom selenium.webdriver.support import expected_conditions as EC\\n\\ndef test_login_ui():\\n    driver = webdriver.Chrome()\\n    try:\\n        driver.get(\\"http://localhost:3000/login\\")\\n        username_input = WebDriverWait(driver, 10).until(\\n            EC.presence_of_element_located((By.NAME, \\"username\\"))\\n        )\\n        username_input.send_keys(\\"admin\\")\\n        password_input = driver.find_element(By.NAME, \\"password\\")\\n        password_input.send_keys(\\"123456\\")\\n        login_btn = driver.find_element(By.CSS_SELECTOR, \\"button[type=\\\'submit\\\']\\")\\n        login_btn.click()\\n        WebDriverWait(driver, 10).until(EC.url_contains(\\"/dashboard\\"))\\n        print(\\"Test passed\\")\\n    finally:\\n        driver.quit()"'
                )
                specific_requirements = """【UI测试特殊要求】
1. test_steps中每一步都要明确描述具体的页面元素和操作（点击、输入、选择、滚动等）
2. test_data中必须包含：page_url（页面地址）、elements（页面元素列表，包含元素名称、定位器、类型）
3. test_steps的test_data中要包含element（元素名称）、element_locator（元素定位器，如CSS选择器或XPath）、action_type（操作类型：click/input/select/hover等）、value（操作值，如输入的内容）
4. 必须包含页面验证步骤，验证页面元素可见性、文本内容、URL变化等
5. **必须为每个测试用例生成完整的Python自动化测试脚本代码**，放在python_code字段中，使用selenium或playwright库编写可执行的测试代码
6. **重要：生成的Python代码必须保持正确的格式和缩进，所有关键字、标识符和操作符之间必须有空格**，例如 `from selenium import webdriver` 而不是 `fromseleniumimportwebdriver`"""
            else:
                specific_requirements = """【UI测试特殊要求】
1. test_steps中每一步都要明确描述具体的页面元素和操作（点击、输入、选择、滚动等）
2. test_data中必须包含：page_url（页面地址）、elements（页面元素列表，包含元素名称、定位器、类型）
3. test_steps的test_data中要包含element（元素名称）、element_locator（元素定位器，如CSS选择器或XPath）、action_type（操作类型：click/input/select/hover等）、value（操作值，如输入的内容）
4. 必须包含页面验证步骤，验证页面元素可见性、文本内容、URL变化等"""
        
        else:  # functional
            format_example = """{
    "test_cases": [
        {
            "title": "功能测试用例标题（如：验证用户登录功能）",
            "description": "测试用例的详细描述",
            "test_type": "functional",
            "priority": "high/medium/low",
            "preconditions": ["系统已部署", "测试账号已准备"],
            "test_steps": [
                {
                    "step_number": 1,
                    "action": "打开登录页面",
                    "expected_result": "登录页面正常显示，包含用户名和密码输入框",
                    "test_data": {}
                },
                {
                    "step_number": 2,
                    "action": "输入正确的用户名和密码",
                    "expected_result": "输入框正常接收输入内容",
                    "test_data": {"username": "testuser", "password": "123456"}
                },
                {
                    "step_number": 3,
                    "action": "点击登录按钮",
                    "expected_result": "系统开始验证用户信息",
                    "test_data": {}
                },
                {
                    "step_number": 4,
                    "action": "验证登录结果",
                    "expected_result": "登录成功，跳转到首页并显示用户信息",
                    "test_data": {"expected_page": "首页", "expected_info": "用户名显示"}
                }
            ],
            "expected_result": "用户成功登录系统，可以正常使用系统功能",
            "test_data": {
                "input_data": {
                    "username": "testuser",
                    "password": "123456"
                },
                "expected_output": "登录成功，进入系统首页",
                "business_rules": ["用户名和密码必须匹配", "登录后生成会话token"],
                "data_validation": ["验证用户身份", "检查账户状态"]
            },
            "tags": ["登录", "用户认证", "正向测试"],
            "automation_ready": true
        }
    ]
}"""
            specific_requirements = """【功能测试特殊要求】
1. test_steps要描述完整的业务流程步骤，从开始到结束
2. test_data中要包含input_data（输入数据）、expected_output（预期输出）、business_rules（业务规则）、data_validation（数据验证点）
3. 关注功能的完整性、正确性和业务流程的连贯性
4. 包含功能点验证、数据验证、业务逻辑验证"""
        
        prompt = f"""你是一个专业的软件测试专家。请根据以下需求生成{test_type_cn}测试用例。

【需求描述】
{requirement_text}
{scope_text}

【通用要求】
1. 必须生成5-10个测试用例，包括：正向用例（正常流程，2-3个）、异常用例（错误处理，2-3个）、边界值用例（边界条件，1-2个）、性能用例（如适用，1-2个）
2. 必须严格按照以下JSON格式返回，不要添加任何额外的解释文字
3. 每个测试用例必须包含完整的test_steps（至少3步，建议4-6步）
4. 测试用例应该覆盖需求的主要功能点，确保测试覆盖率
4. priority字段使用：high（高优先级，核心功能）、medium（中优先级，重要功能）、low（低优先级，次要功能）

{specific_requirements}

【返回格式（必须严格遵循）】
{format_example}

重要：只返回JSON对象，不要有任何其他文字说明。确保JSON格式完整且可解析。根据测试类型的不同，test_data和test_steps的结构要符合对应的要求。
"""
        
        return prompt
    
    def _parse_test_cases_response(self, response: str, test_type: str) -> List[Dict[str, Any]]:
        """解析测试用例响应"""
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
            if cleaned_response.strip().startswith('{'):
                parsed = json.loads(cleaned_response)
                test_cases = parsed.get('test_cases', [])
                
                if not test_cases:
                    logger.warning("解析成功但test_cases为空")
                    return []
                
                # 为每个测试用例添加元数据
                for test_case in test_cases:
                    test_case['generated_by'] = 'ai'
                    test_case['test_type'] = test_type
                    if 'status' not in test_case:
                        test_case['status'] = 'draft'
                
                logger.info(f"成功解析出 {len(test_cases)} 个测试用例")
                return test_cases
            else:
                # 尝试提取JSON对象
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_response, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        test_cases = parsed.get('test_cases', [])
                        
                        if test_cases:
                            for test_case in test_cases:
                                test_case['generated_by'] = 'ai'
                                test_case['test_type'] = test_type
                                if 'status' not in test_case:
                                    test_case['status'] = 'draft'
                            logger.info(f"通过正则提取成功解析出 {len(test_cases)} 个测试用例")
                            return test_cases
                    except json.JSONDecodeError as e:
                        logger.warning(f"正则提取的JSON解析失败: {e}")
                
                # 如果无法解析，记录原始响应用于调试
                logger.warning(f"无法解析JSON，响应前200字符: {response[:200]}")
                return []
                    
        except json.JSONDecodeError as e:
            logger.warning(f"测试用例JSON解析失败: {e}, 响应片段: {response[:200]}")
            return []
        except Exception as e:
            logger.error(f"测试用例解析失败: {e}", exc_info=True)
            return []

    def _looks_like_placeholder(self, cases: List[Dict[str, Any]]) -> bool:
        """判断是否为占位用例（例如只有一条，且包含 raw_response 或缺少关键结构）。"""
        if not cases:
            return True
        if len(cases) == 1:
            c = cases[0]
            # 空描述或包含原始响应字段，且没有步骤，视为占位
            if (not c.get("description")) or ("raw_response" in c) or (not c.get("test_steps")):
                return True
        return False

    def _fallback_generate(self, requirement_text: str, test_type: str) -> List[Dict[str, Any]]:
        """当AI不可用或响应不可解析时，基于需求文本生成基础用例模板"""
        # 使用统一的清理函数，由于requirement_text在generate中已经清理过，这里再清理一次确保安全
        cleaned_text = self._clean_requirement_text(requirement_text)
        title_base = cleaned_text[:50] if cleaned_text else "功能"
        cases: List[Dict[str, Any]] = []
        scenarios = [
            ("正常流程-基础场景", "positive", "high"),
            ("正常流程-完整流程", "positive", "medium"),
            ("异常输入-错误参数", "negative", "high"),
            ("异常输入-缺失必填", "negative", "high"),
            ("边界值-最小值", "edge", "medium"),
            ("边界值-最大值", "edge", "medium"),
            ("性能-并发场景", "performance", "low"),
        ]
        
        for idx, (name, kind, priority) in enumerate(scenarios, start=1):
            if test_type == "api":
                # API测试用例格式
                case = {
                    "title": f"{title_base}-{name}接口测试",
                    "description": f"针对 {title_base} 的{name} API接口测试",
                    "test_type": test_type,
                    "priority": priority,
                    "preconditions": ["接口文档已准备", "测试环境已部署"],
                    "test_steps": [
                        {
                            "step_number": 1,
                            "action": f"发送{'POST' if kind == 'positive' else 'GET'}请求到相关接口",
                            "expected_result": "请求成功发送",
                            "test_data": {
                                "method": "POST" if kind == "positive" else "GET",
                                "url": f"/api/{title_base.lower().replace(' ', '-')}",
                                "headers": {"Content-Type": "application/json"}
                            }
                        },
                        {
                            "step_number": 2,
                            "action": "验证响应状态码",
                            "expected_result": f"状态码为{'200' if kind == 'positive' else '400' if kind == 'negative' else '200'}",
                            "test_data": {"expected_status": 200 if kind != "negative" else 400}
                        },
                        {
                            "step_number": 3,
                            "action": "验证响应体结构",
                            "expected_result": "响应体符合预期格式",
                            "test_data": {"expected_fields": ["status", "data"]}
                        }
                    ],
                    "expected_result": "接口返回符合预期的响应",
                    "test_data": {
                        "request_method": "POST" if kind == "positive" else "GET",
                        "request_url": f"/api/{title_base.lower().replace(' ', '-')}",
                        "request_headers": {"Content-Type": "application/json"},
                        "request_body": {} if kind == "positive" else None,
                        "expected_status_code": 200 if kind != "negative" else 400,
                        "expected_response": {}
                    },
                    "tags": [test_type, kind, "API"],
                    "automation_ready": True,
                    "generated_by": "fallback",
                    "status": "draft",
                }
            elif test_type == "ui":
                # UI测试用例格式
                case = {
                    "title": f"{title_base}-{name}UI测试",
                    "description": f"针对 {title_base} 的{name} UI交互测试",
                    "test_type": test_type,
                    "priority": priority,
                    "preconditions": ["浏览器已打开", f"访问{title_base}相关页面"],
                    "test_steps": [
                        {
                            "step_number": 1,
                            "action": f"在页面中找到{title_base}相关的输入元素",
                            "expected_result": "元素可见且可交互",
                            "test_data": {
                                "element": f"{title_base}输入框",
                                "element_locator": "input[placeholder*='" + title_base[:10] + "']",
                                "action_type": "locate"
                            }
                        },
                        {
                            "step_number": 2,
                            "action": f"执行{name}操作",
                            "expected_result": "操作成功执行",
                            "test_data": {
                                "element": f"{title_base}按钮",
                                "element_locator": "button:contains('" + title_base[:10] + "')",
                                "action_type": "click" if kind == "positive" else "input",
                                "value": "test_value" if kind == "positive" else ""
                            }
                        },
                        {
                            "step_number": 3,
                            "action": "验证页面响应",
                            "expected_result": "页面状态符合预期",
                            "test_data": {
                                "expected_url": f"/{title_base.lower().replace(' ', '-')}",
                                "expected_elements": ["结果提示", "页面元素"]
                            }
                        }
                    ],
                    "expected_result": "UI交互符合预期，页面状态正确",
                    "test_data": {
                        "page_url": f"/{title_base.lower().replace(' ', '-')}",
                        "elements": [
                            {"name": f"{title_base}输入框", "locator": "input", "type": "input"},
                            {"name": f"{title_base}按钮", "locator": "button", "type": "button"}
                        ],
                        "user_interactions": ["定位元素", "执行操作", "验证结果"],
                        "verification_points": ["元素可见性", "页面状态", "交互反馈"]
                    },
                    "tags": [test_type, kind, "UI"],
                    "automation_ready": True,
                    "generated_by": "fallback",
                    "status": "draft",
                }
            else:
                # 功能测试用例格式
                case = {
                    "title": f"{title_base}-{name}功能测试",
                    "description": f"针对 {title_base} 的{name}功能测试",
                    "test_type": test_type,
                    "priority": priority,
                    "preconditions": ["系统已部署", "测试环境已准备"],
                    "test_steps": [
                        {
                            "step_number": 1,
                            "action": f"准备{title_base}的测试数据",
                            "expected_result": "测试数据准备完成",
                            "test_data": {"type": kind}
                        },
                        {
                            "step_number": 2,
                            "action": f"执行{title_base}的主要功能操作",
                            "expected_result": "功能执行成功",
                            "test_data": {"action": "execute", "type": kind}
                        },
                        {
                            "step_number": 3,
                            "action": "验证功能执行结果",
                            "expected_result": "结果符合预期",
                            "test_data": {"verification": "result", "type": kind}
                        },
                        {
                            "step_number": 4,
                            "action": "验证业务流程完整性",
                            "expected_result": "业务流程完整无缺失",
                            "test_data": {"verification": "business_flow"}
                        }
                    ],
                    "expected_result": f"{title_base}功能正常，满足需求预期",
                    "test_data": {
                        "input_data": {"scenario": kind},
                        "expected_output": "功能执行成功",
                        "business_rules": [f"{title_base}相关业务规则"],
                        "data_validation": ["数据完整性", "业务逻辑正确性"]
                    },
                    "tags": [test_type, kind, "功能"],
                    "automation_ready": True,
                    "generated_by": "fallback",
                    "status": "draft",
                }
            cases.append(case)
        return cases

    async def generate_stream(
        self,
        requirement_text: str,
        test_type: str,
        test_scope: Dict[str, Any] | None = None,
        generate_script: bool = True
    ) -> AsyncGenerator[str, None]:
        """流式生成测试用例，输出过程文本，结束时输出JSON标记的数据块"""
        # 清理需求文本，去除重复字符
        requirement_text = self._clean_requirement_text(requirement_text)
        
        if test_scope is None:
            test_scope = {}

        prompt = self._build_generation_prompt(requirement_text, test_type, test_scope, generate_script)

        try:
            accumulated = ""
            async for chunk in self.ai_client.generate_response_stream(prompt, temperature=0.4):
                accumulated += chunk
                yield chunk

            # 结束后解析或回退
            cases = self._parse_test_cases_response(accumulated, test_type)
            if not cases or self._looks_like_placeholder(cases):
                cases = self._fallback_generate(requirement_text, test_type)

            payload = {
                "status": "success",
                "test_cases": cases,
                "ai_model": {
                    "provider": self.ai_client.current_model,
                    "model_name": getattr(self.ai_client, 'current_model_name', self.ai_client.default_ollama_model if self.ai_client.current_model == "ollama" else "deepseek-chat")
                }
            }
            yield "\n\n#JSON_START#\n"
            import json as _json
            yield _json.dumps(payload, ensure_ascii=False, indent=2)
            yield "\n#JSON_END#\n"
        except Exception as e:
            yield f"\n\n生成出错: {str(e)}"