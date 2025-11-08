import json
import logging
from typing import Dict, Any, List, Union
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
        user_actions: Union[str, List[str]], 
        test_scenarios: List[str] = None,
        page_info: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """生成UI自动化测试脚本（支持页面分析和业务需求）"""
        
        if test_scenarios is None:
            test_scenarios = []
        
        # 构建生成提示词（包含页面分析结果）
        prompt = self._build_generation_prompt(page_url, user_actions, test_scenarios, page_info)
        
        try:
            # 调用AI生成UI测试
            response = await self.ai_client.generate_response(prompt, temperature=0.3)
            
            # 解析生成的UI测试
            ui_tests = self._parse_ui_tests_response(response)
            
            # 为每个测试添加智能定位器（如果有页面信息，使用实际元素信息）
            if page_info:
                ui_tests = await self._enhance_with_page_info(ui_tests, page_info)
            else:
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
        user_actions: Union[str, List[str]], 
        test_scenarios: List[str],
        page_info: Dict[str, Any] = None
    ) -> str:
        """构建生成提示词（支持页面分析结果和业务需求）"""
        
        # 处理用户需求（可能是文本描述或操作列表）
        if isinstance(user_actions, str):
            # 如果是字符串，作为业务需求描述
            user_requirement = user_actions.strip() if user_actions.strip() else "未指定具体业务需求，请根据页面结构和功能自动推断测试场景"
        elif isinstance(user_actions, list) and user_actions:
            # 如果是列表，转换为文本
            user_requirement = "\n".join([f"- {action}" for action in user_actions])
        else:
            user_requirement = "未指定具体业务需求，请根据页面结构和功能自动推断测试场景"
        
        scenarios_text = ""
        if test_scenarios:
            scenarios_text = f"\n测试场景类型：{', '.join(test_scenarios)}"
        
        # 如果有页面分析结果，添加页面结构信息
        page_structure_info = ""
        if page_info:
            structure = page_info.get("structure", {})
            element_count = page_info.get("element_count", {})
            
            page_structure_info = f"""
【页面结构分析】（已自动分析页面）
页面标题: {page_info.get('title', '无标题')}
页面描述: {page_info.get('description', '无描述')}

【页面元素统计】
- 标题: {element_count.get('headings', 0)} 个
- 链接: {element_count.get('links', 0)} 个
- 按钮: {element_count.get('buttons', 0)} 个
- 输入框: {element_count.get('inputs', 0)} 个
- 表单: {element_count.get('forms', 0)} 个

【主要按钮列表】
"""
            for btn in structure.get("buttons", [])[:20]:
                btn_text = btn.get("text") or btn.get("ariaLabel") or "无文本"
                btn_id = btn.get("id")
                btn_type = btn.get("type", "button")
                data_test_id = btn.get("dataTestId")
                page_structure_info += f"- {btn_text} (id: {btn_id}, type: {btn_type}, data-testid: {data_test_id})\n"
            
            page_structure_info += "\n【输入框列表】\n"
            for inp in structure.get("inputs", [])[:20]:
                inp_name = inp.get("name") or inp.get("id") or inp.get("placeholder") or "未命名"
                inp_type = inp.get("type", "text")
                inp_required = "必填" if inp.get("required") else "可选"
                page_structure_info += f"- {inp_type}: {inp_name} ({inp_required})\n"
            
            page_structure_info += "\n【页面主要内容】\n"
            text_content = page_info.get("text_content", "")[:1500]  # 限制长度
            page_structure_info += text_content
        
        # 处理用户需求（可能是文本描述或操作列表）
        user_requirement = ""
        if user_actions:
            if isinstance(user_actions, list):
                # 如果是列表，转换为文本
                user_requirement = "\n".join([f"- {action}" for action in user_actions])
            else:
                # 如果是字符串，直接使用
                user_requirement = user_actions
        else:
            user_requirement = "未指定具体业务需求，请根据页面结构和功能自动推断测试场景"
        
        prompt = f"""
作为专业的UI自动化测试专家，请基于以下页面信息和**业务需求**生成**工程化的、可直接运行的**自动化测试脚本。

【重要要求】
1. **必须结合业务需求生成测试**，不仅仅是简单的点击操作，要覆盖完整的业务流程
2. **必须基于实际的页面结构生成测试代码**（如果提供了页面分析结果，必须使用实际元素信息）
3. **代码必须可以直接运行**，包含所有必要的导入和配置
4. **使用工程化的代码结构**：类、方法、模块化设计
5. **提供完整的项目结构建议**：目录结构、文件组织
6. **生成完整的业务流程测试**，包括：
   - 正常流程测试（happy path）
   - 异常流程测试（错误处理）
   - 边界条件测试
   - 数据验证测试

【页面URL】
{page_url}
{page_structure_info}

【业务需求/测试场景】
{user_requirement}

【测试场景类型】
{scenarios_text}

【业务测试示例】
根据不同的业务需求，生成相应的测试：

1. **用户注册/登录场景**：
   - 测试注册流程：填写表单 → 验证输入 → 提交 → 验证成功
   - 测试登录流程：输入凭证 → 点击登录 → 验证跳转
   - 测试错误处理：错误密码、空字段、格式验证等

2. **电商购物场景**：
   - 测试商品搜索：输入关键词 → 筛选 → 查看结果
   - 测试添加到购物车：选择商品 → 选择规格 → 添加到购物车 → 验证数量
   - 测试下单流程：填写收货信息 → 选择支付方式 → 提交订单 → 验证订单号

3. **数据管理场景**：
   - 测试数据录入：填写表单 → 验证必填项 → 提交 → 验证保存成功
   - 测试数据查询：输入查询条件 → 点击搜索 → 验证结果列表
   - 测试数据编辑：打开编辑 → 修改数据 → 保存 → 验证更新

4. **审批流程场景**：
   - 测试提交审批：填写申请 → 上传附件 → 提交 → 验证状态
   - 测试审批操作：查看详情 → 填写意见 → 批准/拒绝 → 验证流程

5. **报表查看场景**：
   - 测试报表生成：选择时间范围 → 选择维度 → 生成报表 → 验证数据
   - 测试数据导出：生成报表 → 点击导出 → 验证文件下载

请根据上述业务需求，生成完整的业务流程测试代码。

【代码生成要求】
1. **必须覆盖完整的业务流程**，不仅仅是单个操作
2. **包含数据准备、操作执行、结果验证**的完整流程
3. **生成多个测试用例**：正常流程、异常流程、边界条件
4. **使用实际页面元素**（如果提供了页面分析结果）
5. **代码必须可以直接运行**

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
                ui_tests = parsed.get('ui_tests', [])
                
                if ui_tests:
                    # 为每个测试添加元数据
                    for test in ui_tests:
                        test['generated_by'] = 'ai'
                        test['test_type'] = 'ui'
                        if 'status' not in test:
                            test['status'] = 'draft'
                    logger.info(f"成功解析出 {len(ui_tests)} 个UI测试")
                    return ui_tests
            except json.JSONDecodeError:
                # 尝试提取JSON对象
                import re
                # 更精确的JSON提取，匹配完整的JSON对象
                json_match = re.search(r'\{[\s\S]*"ui_tests"[\s\S]*\}', cleaned_response)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        ui_tests = parsed.get('ui_tests', [])
                        if ui_tests:
                            for test in ui_tests:
                                test['generated_by'] = 'ai'
                                test['test_type'] = 'ui'
                                if 'status' not in test:
                                    test['status'] = 'draft'
                            logger.info(f"通过正则提取成功解析出 {len(ui_tests)} 个UI测试")
                            return ui_tests
                    except json.JSONDecodeError as e:
                        logger.warning(f"正则提取的JSON解析失败: {e}")
            
            # 如果JSON解析失败，尝试从原始响应中提取python_code
            # 即使JSON不完整，也可能包含有用的代码片段
            python_code_extracted = None
            try:
                import re
                # 方法1: 尝试从python_code对象中提取（处理转义字符）
                # 查找 "python_code": {"selenium": "..." 或 "python_code": {"playwright": "..."
                python_code_patterns = [
                    r'"python_code"\s*:\s*\{[^}]*"(?:selenium|playwright)"\s*:\s*"((?:[^"\\]|\\.)*)"',
                    r'"python_code"\s*:\s*"((?:[^"\\]|\\.)*)"',
                ]
                for pattern in python_code_patterns:
                    match = re.search(pattern, cleaned_response, re.DOTALL)
                    if match:
                        python_code_extracted = match.group(1)
                        # 处理转义字符
                        python_code_extracted = python_code_extracted.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t').replace('\\\\', '\\')
                        if python_code_extracted.strip():
                            break
                
                # 方法2: 如果没找到，尝试从原始响应中查找Python代码块
                if not python_code_extracted:
                    python_code_block = re.search(r'```(?:python)?\s*\n(.*?)\n```', response, re.DOTALL)
                    if python_code_block:
                        python_code_extracted = python_code_block.group(1).strip()
            except Exception as e:
                logger.warning(f"提取python_code失败: {e}")
            
            # 如果无法解析，记录原始响应用于调试
            result = {
                "name": "AI生成的UI测试",
                "description": "无法解析JSON格式，返回原始响应",
                "test_type": "ui",
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response[:10000]  # 增加长度限制
            }
            if python_code_extracted:
                result["python_code"] = python_code_extracted
                result["description"] = "JSON解析部分失败，但已提取Python代码"
            logger.warning(f"无法解析JSON，返回原始响应（包含{'代码' if python_code_extracted else '无代码'}）")
            return [result]
                    
        except Exception as e:
            logger.error(f"UI测试解析失败: {e}", exc_info=True)
            return [{
                "name": "AI生成的UI测试",
                "description": f"解析失败: {str(e)}",
                "test_type": "ui",
                "generated_by": "ai",
                "status": "draft",
                "raw_response": response[:5000] if response else "",
                "parsing_error": str(e)
            }] 