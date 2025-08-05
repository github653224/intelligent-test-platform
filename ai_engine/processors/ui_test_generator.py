import json
import logging
from typing import Dict, Any, List
from ai_engine.models.ai_client import AIClient
from ai_engine.processors.smart_element_locator import SmartElementLocator, ElementLocator

logger = logging.getLogger(__name__)


class UITestGenerator:
    """UI测试生成处理器"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.smart_locator = SmartElementLocator()
    
    async def generate(
        self, 
        page_url: str, 
        user_actions: List[str], 
        test_scenarios: List[str] = None
    ) -> List[Dict[str, Any]]:
        """生成UI自动化测试脚本"""
        
        if test_scenarios is None:
            test_scenarios = []
        
        # 构建生成提示词
        prompt = self._build_generation_prompt(page_url, user_actions, test_scenarios)
        
        try:
            # 调用AI生成UI测试
            response = await self.ai_client.generate_response(prompt, temperature=0.3)
            
            # 解析生成的UI测试
            ui_tests = self._parse_ui_tests_response(response)
            
            # 为每个测试添加智能定位器
            ui_tests = await self._enhance_with_smart_locators(ui_tests, user_actions)
            
            return ui_tests
            
        except Exception as e:
            logger.error(f"UI测试生成失败: {e}")
            return [{
                "status": "error",
                "error": str(e),
                "page_url": page_url
            }]
    
    def _build_generation_prompt(
        self, 
        page_url: str, 
        user_actions: List[str], 
        test_scenarios: List[str]
    ) -> str:
        """构建生成提示词"""
        
        actions_text = "\n".join([f"- {action}" for action in user_actions])
        scenarios_text = ""
        if test_scenarios:
            scenarios_text = f"\n测试场景：{', '.join(test_scenarios)}"
        
        prompt = f"""
        作为专业的UI自动化测试专家，请基于以下页面和用户操作生成自动化测试脚本：

        【页面URL】
        {page_url}

        【用户操作】
        {actions_text}
        {scenarios_text}

        请生成以下内容（以JSON格式返回）：

        {{
            "ui_tests": [
                {{
                    "name": "测试用例名称",
                    "description": "测试描述",
                    "page_url": "{page_url}",
                    "test_type": "ui_automation",
                    "framework": "selenium/playwright",
                    "elements": [
                        {{
                            "name": "元素名称",
                            "tag_name": "标签名",
                            "id": "元素ID",
                            "class_names": ["类名列表"],
                            "name_attr": "name属性",
                            "text_content": "文本内容",
                            "aria_label": "无障碍标签",
                            "data_test_id": "测试ID",
                            "is_dynamic": false,
                            "description": "元素描述"
                        }}
                    ],
                    "test_steps": [
                        {{
                            "step_number": 1,
                            "action": "操作类型",
                            "element_name": "目标元素名称",
                            "value": "输入值",
                            "wait_strategy": "等待策略",
                            "expected_result": "预期结果"
                        }}
                    ],
                    "assertions": [
                        {{
                            "type": "element_present/text_equals/url_contains",
                            "target": "目标元素或值",
                            "expected": "预期值",
                            "description": "断言描述"
                        }}
                    ],
                    "smart_locators": [
                        {{
                            "element_name": "元素名称",
                            "locators": [
                                {{
                                    "type": "id/css/xpath/name/test_id",
                                    "value": "定位值",
                                    "confidence": 0.95,
                                    "description": "定位描述"
                                }}
                            ],
                            "best_locator": {{
                                "type": "最佳定位类型",
                                "value": "最佳定位值",
                                "confidence": 0.95
                            }}
                        }}
                    ],
                    "wait_strategies": [
                        {{
                            "element_name": "元素名称",
                            "strategy": "等待策略",
                            "timeout": 10,
                            "description": "策略描述"
                        }}
                    ],
                    "python_code": {{
                        "selenium": "from selenium import webdriver\\n\\ndef test_ui():\\n    # Selenium代码",
                        "playwright": "from playwright.sync_api import sync_playwright\\n\\ndef test_ui():\\n    # Playwright代码"
                    }},
                    "page_object": {{
                        "class_name": "PageObject",
                        "elements": {{
                            "element_name": "locator_value"
                        }},
                        "methods": [
                            "def click_element(self):\\n    # 方法实现"
                        ]
                    }}
                }}
            ],
            "locator_strategies": [
                {{
                    "name": "定位策略名称",
                    "description": "策略描述",
                    "priority": 1,
                    "code_template": "代码模板"
                }}
            ],
            "test_data": [
                {{
                    "name": "测试数据名称",
                    "description": "数据描述",
                    "data": {{
                        "input": "输入数据",
                        "expected": "预期结果"
                    }}
                }}
            ],
            "browser_config": {{
                "browsers": ["chrome", "firefox", "safari"],
                "headless": true,
                "window_size": "1920x1080",
                "timeout": 30
            }}
        }}
        """
        
        return prompt
    
    async def _enhance_with_smart_locators(self, ui_tests: List[Dict[str, Any]], user_actions: List[str]) -> List[Dict[str, Any]]:
        """使用智能定位器增强UI测试"""
        enhanced_tests = []
        
        for test in ui_tests:
            enhanced_test = test.copy()
            
            # 为每个元素生成智能定位器
            if 'elements' in enhanced_test:
                smart_locators = []
                
                for element in enhanced_test['elements']:
                    # 使用智能定位器分析元素
                    locators = self.smart_locator.analyze_element(element)
                    
                    if locators:
                        smart_locator_info = {
                            "element_name": element.get('name', 'unknown'),
                            "locators": [
                                {
                                    "type": locator.type.value,
                                    "value": locator.value,
                                    "confidence": locator.confidence,
                                    "description": locator.description
                                }
                                for locator in locators
                            ],
                            "best_locator": {
                                "type": locators[0].type.value,
                                "value": locators[0].value,
                                "confidence": locators[0].confidence
                            }
                        }
                        smart_locators.append(smart_locator_info)
                
                enhanced_test['smart_locators'] = smart_locators
            
            # 生成等待策略
            if 'elements' in enhanced_test:
                wait_strategies = []
                
                for element in enhanced_test['elements']:
                    wait_strategy = self.smart_locator.generate_wait_strategy(element)
                    wait_strategies.append({
                        "element_name": element.get('name', 'unknown'),
                        "strategy": wait_strategy["type"],
                        "timeout": wait_strategy["timeout"],
                        "description": f"等待{element.get('name', 'unknown')}元素"
                    })
                
                enhanced_test['wait_strategies'] = wait_strategies
            
            # 生成代码模板
            if 'test_steps' in enhanced_test:
                selenium_code = self._generate_selenium_test_code(enhanced_test)
                playwright_code = self._generate_playwright_test_code(enhanced_test)
                
                enhanced_test['python_code'] = {
                    "selenium": selenium_code,
                    "playwright": playwright_code
                }
            
            enhanced_tests.append(enhanced_test)
        
        return enhanced_tests
    
    def _generate_selenium_test_code(self, test: Dict[str, Any]) -> str:
        """生成Selenium测试代码"""
        code = """
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def test_ui_automation():
    \"\"\"UI自动化测试\"\"\"
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 初始化WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    try:
        # 打开页面
        driver.get("{page_url}")
        
"""
        
        # 添加测试步骤
        if 'test_steps' in test:
            for step in test['test_steps']:
                element_name = step.get('element_name', 'element')
                action = step.get('action', 'click')
                value = step.get('value', '')
                
                # 获取最佳定位器
                best_locator = self._get_best_locator_for_element(test, element_name)
                
                if best_locator:
                    if action == 'click':
                        code += f"""
        # {step.get('description', f'点击{element_name}')}
        {element_name}_element = driver.find_element(By.{best_locator['type'].upper()}, "{best_locator['value']}")
        {element_name}_element.click()
"""
                    elif action == 'input':
                        code += f"""
        # {step.get('description', f'在{element_name}中输入文本')}
        {element_name}_element = driver.find_element(By.{best_locator['type'].upper()}, "{best_locator['value']}")
        {element_name}_element.clear()
        {element_name}_element.send_keys("{value}")
"""
                    elif action == 'wait':
                        code += f"""
        # {step.get('description', f'等待{element_name}元素')}
        wait = WebDriverWait(driver, 10)
        {element_name}_element = wait.until(EC.element_to_be_clickable((By.{best_locator['type'].upper()}, "{best_locator['value']}")))
"""
        
        code += """
        # 验证结果
        assert driver.current_url != "{page_url}", "页面未正确跳转"
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_ui_automation()
"""
        
        return code.format(page_url=test.get('page_url', ''))
    
    def _generate_playwright_test_code(self, test: Dict[str, Any]) -> str:
        """生成Playwright测试代码"""
        code = """
from playwright.sync_api import sync_playwright
import time

def test_ui_automation():
    \"\"\"UI自动化测试\"\"\"
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 打开页面
            page.goto("{page_url}")
            
"""
        
        # 添加测试步骤
        if 'test_steps' in test:
            for step in test['test_steps']:
                element_name = step.get('element_name', 'element')
                action = step.get('action', 'click')
                value = step.get('value', '')
                
                # 获取最佳定位器
                best_locator = self._get_best_locator_for_element(test, element_name)
                
                if best_locator:
                    playwright_locator = self._convert_to_playwright_locator(best_locator)
                    
                    if action == 'click':
                        code += f"""
            # {step.get('description', f'点击{element_name}')}
            page.locator("{playwright_locator}").click()
"""
                    elif action == 'input':
                        code += f"""
            # {step.get('description', f'在{element_name}中输入文本')}
            page.locator("{playwright_locator}").fill("{value}")
"""
                    elif action == 'wait':
                        code += f"""
            # {step.get('description', f'等待{element_name}元素')}
            page.locator("{playwright_locator}").wait_for(state="visible", timeout=10000)
"""
        
        code += """
            # 验证结果
            assert page.url != "{page_url}", "页面未正确跳转"
            
        finally:
            browser.close()

if __name__ == "__main__":
    test_ui_automation()
"""
        
        return code.format(page_url=test.get('page_url', ''))
    
    def _get_best_locator_for_element(self, test: Dict[str, Any], element_name: str) -> Dict[str, Any]:
        """获取元素的最佳定位器"""
        if 'smart_locators' in test:
            for locator_info in test['smart_locators']:
                if locator_info.get('element_name') == element_name:
                    return locator_info.get('best_locator', {})
        return {}
    
    def _convert_to_playwright_locator(self, locator: Dict[str, Any]) -> str:
        """将定位器转换为Playwright格式"""
        locator_type = locator.get('type', '')
        locator_value = locator.get('value', '')
        
        if locator_type == 'id':
            return f"#{locator_value}"
        elif locator_type == 'css_selector':
            return locator_value
        elif locator_type == 'xpath':
            return f"xpath={locator_value}"
        elif locator_type == 'test_id':
            return f"[data-testid='{locator_value}']"
        else:
            return locator_value
    
    def _parse_ui_tests_response(self, response: str) -> List[Dict[str, Any]]:
        """解析UI测试响应"""
        try:
            # 尝试解析JSON
            if response.strip().startswith('{'):
                parsed = json.loads(response)
                ui_tests = parsed.get('ui_tests', [])
                
                # 为每个测试添加元数据
                for test in ui_tests:
                    test['generated_by'] = 'ai'
                    test['test_type'] = 'ui'
                    test['status'] = 'draft'
                
                return ui_tests
            else:
                # 如果不是标准JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    ui_tests = parsed.get('ui_tests', [])
                    
                    for test in ui_tests:
                        test['generated_by'] = 'ai'
                        test['test_type'] = 'ui'
                        test['status'] = 'draft'
                    
                    return ui_tests
                else:
                    # 返回原始响应作为单个测试
                    return [{
                        "name": "AI生成的UI测试",
                        "description": response,
                        "test_type": "ui",
                        "generated_by": "ai",
                        "status": "draft",
                        "raw_response": response
                    }]
                    
        except json.JSONDecodeError as e:
            logger.warning(f"UI测试JSON解析失败: {e}")
            return [{
                "name": "AI生成的UI测试",
                "description": response,
                "test_type": "ui",
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response,
                "parsing_error": str(e)
            }]
        except Exception as e:
            logger.error(f"UI测试解析失败: {e}")
            return [{
                "name": "AI生成的UI测试",
                "description": response,
                "test_type": "ui",
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response,
                "parsing_error": str(e)
            }] 