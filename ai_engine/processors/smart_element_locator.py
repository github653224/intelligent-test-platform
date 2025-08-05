import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LocatorType(Enum):
    """定位器类型枚举"""
    ID = "id"
    NAME = "name"
    CLASS_NAME = "class_name"
    TAG_NAME = "tag_name"
    XPATH = "xpath"
    CSS_SELECTOR = "css_selector"
    LINK_TEXT = "link_text"
    PARTIAL_LINK_TEXT = "partial_link_text"
    ACCESSIBILITY_ID = "accessibility_id"
    TEST_ID = "test_id"
    SMART_XPATH = "smart_xpath"
    SMART_CSS = "smart_css"


@dataclass
class ElementLocator:
    """元素定位器"""
    type: LocatorType
    value: str
    description: str
    confidence: float
    fallback_locators: List['ElementLocator'] = None


class SmartElementLocator:
    """智能DOM元素定位器"""
    
    def __init__(self):
        self.locator_priorities = [
            LocatorType.ID,
            LocatorType.TEST_ID,
            LocatorType.ACCESSIBILITY_ID,
            LocatorType.NAME,
            LocatorType.CSS_SELECTOR,
            LocatorType.XPATH,
            LocatorType.CLASS_NAME,
            LocatorType.LINK_TEXT,
            LocatorType.PARTIAL_LINK_TEXT,
            LocatorType.TAG_NAME
        ]
    
    def analyze_element(self, element_info: Dict[str, Any]) -> List[ElementLocator]:
        """分析元素，生成多种定位策略"""
        locators = []
        
        # 基本信息
        tag_name = element_info.get('tag_name', '')
        element_id = element_info.get('id', '')
        class_names = element_info.get('class_names', [])
        name_attr = element_info.get('name', '')
        text_content = element_info.get('text_content', '')
        aria_label = element_info.get('aria_label', '')
        data_test_id = element_info.get('data_test_id', '')
        
        # 1. ID定位器 (最高优先级)
        if element_id:
            locators.append(ElementLocator(
                type=LocatorType.ID,
                value=element_id,
                description=f"通过ID定位元素: {element_id}",
                confidence=0.95
            ))
        
        # 2. Test ID定位器 (用于测试的专用属性)
        if data_test_id:
            locators.append(ElementLocator(
                type=LocatorType.TEST_ID,
                value=f'[data-testid="{data_test_id}"]',
                description=f"通过测试ID定位元素: {data_test_id}",
                confidence=0.90
            ))
        
        # 3. Accessibility ID定位器
        if aria_label:
            locators.append(ElementLocator(
                type=LocatorType.ACCESSIBILITY_ID,
                value=f'[aria-label="{aria_label}"]',
                description=f"通过无障碍标签定位元素: {aria_label}",
                confidence=0.85
            ))
        
        # 4. Name属性定位器
        if name_attr:
            locators.append(ElementLocator(
                type=LocatorType.NAME,
                value=name_attr,
                description=f"通过name属性定位元素: {name_attr}",
                confidence=0.80
            ))
        
        # 5. 智能CSS选择器
        css_selector = self._generate_smart_css_selector(element_info)
        if css_selector:
            locators.append(ElementLocator(
                type=LocatorType.CSS_SELECTOR,
                value=css_selector,
                description=f"智能CSS选择器: {css_selector}",
                confidence=0.75
            ))
        
        # 6. 智能XPath
        xpath = self._generate_smart_xpath(element_info)
        if xpath:
            locators.append(ElementLocator(
                type=LocatorType.XPATH,
                value=xpath,
                description=f"智能XPath: {xpath}",
                confidence=0.70
            ))
        
        # 7. 文本内容定位器
        if text_content and len(text_content.strip()) > 0:
            # 完整文本匹配
            if len(text_content.strip()) < 50:  # 避免过长的文本
                locators.append(ElementLocator(
                    type=LocatorType.LINK_TEXT,
                    value=text_content.strip(),
                    description=f"通过完整文本定位: {text_content.strip()}",
                    confidence=0.65
                ))
            
            # 部分文本匹配
            words = text_content.strip().split()
            if len(words) > 1:
                for word in words[:3]:  # 取前3个词
                    if len(word) > 2:  # 词长度大于2
                        locators.append(ElementLocator(
                            type=LocatorType.PARTIAL_LINK_TEXT,
                            value=word,
                            description=f"通过部分文本定位: {word}",
                            confidence=0.60
                        ))
        
        # 8. 类名定位器
        if class_names:
            # 选择最具体的类名
            specific_classes = [cls for cls in class_names if cls and not cls.startswith('ng-')]
            if specific_classes:
                class_selector = '.' + '.'.join(specific_classes[:2])  # 最多使用2个类名
                locators.append(ElementLocator(
                    type=LocatorType.CSS_SELECTOR,
                    value=class_selector,
                    description=f"通过类名定位: {class_selector}",
                    confidence=0.55
                ))
        
        # 按置信度排序
        locators.sort(key=lambda x: x.confidence, reverse=True)
        
        return locators
    
    def _generate_smart_css_selector(self, element_info: Dict[str, Any]) -> Optional[str]:
        """生成智能CSS选择器"""
        tag_name = element_info.get('tag_name', '')
        element_id = element_info.get('id', '')
        class_names = element_info.get('class_names', [])
        name_attr = element_info.get('name', '')
        data_test_id = element_info.get('data_test_id', '')
        
        # 构建CSS选择器
        selector_parts = []
        
        # 标签名
        if tag_name:
            selector_parts.append(tag_name)
        
        # ID选择器
        if element_id:
            selector_parts.append(f"#{element_id}")
            return ''.join(selector_parts)
        
        # Test ID选择器
        if data_test_id:
            selector_parts.append(f'[data-testid="{data_test_id}"]')
            return ''.join(selector_parts)
        
        # Name属性选择器
        if name_attr:
            selector_parts.append(f'[name="{name_attr}"]')
            return ''.join(selector_parts)
        
        # 类名选择器
        if class_names:
            specific_classes = [cls for cls in class_names if cls and not cls.startswith('ng-')]
            if specific_classes:
                class_selector = '.' + '.'.join(specific_classes[:2])
                selector_parts.append(class_selector)
        
        return ''.join(selector_parts) if selector_parts else None
    
    def _generate_smart_xpath(self, element_info: Dict[str, Any]) -> Optional[str]:
        """生成智能XPath"""
        tag_name = element_info.get('tag_name', '')
        element_id = element_info.get('id', '')
        name_attr = element_info.get('name', '')
        text_content = element_info.get('text_content', '')
        aria_label = element_info.get('aria_label', '')
        
        # 构建XPath
        xpath_parts = []
        
        # 标签名
        if tag_name:
            xpath_parts.append(tag_name)
        else:
            xpath_parts.append('*')
        
        # ID属性
        if element_id:
            xpath_parts.append(f'[@id="{element_id}"]')
            return '//' + ''.join(xpath_parts)
        
        # Name属性
        if name_attr:
            xpath_parts.append(f'[@name="{name_attr}"]')
            return '//' + ''.join(xpath_parts)
        
        # Aria-label属性
        if aria_label:
            xpath_parts.append(f'[@aria-label="{aria_label}"]')
            return '//' + ''.join(xpath_parts)
        
        # 文本内容
        if text_content and len(text_content.strip()) < 50:
            xpath_parts.append(f'[text()="{text_content.strip()}"]')
            return '//' + ''.join(xpath_parts)
        
        # 包含文本
        if text_content:
            words = text_content.strip().split()
            if words:
                xpath_parts.append(f'[contains(text(), "{words[0]}")]')
                return '//' + ''.join(xpath_parts)
        
        return None
    
    def generate_wait_strategy(self, element_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成等待策略"""
        element_type = element_info.get('tag_name', '')
        is_dynamic = element_info.get('is_dynamic', False)
        load_time = element_info.get('load_time', 0)
        
        wait_strategy = {
            "type": "explicit",
            "timeout": 10,
            "polling_interval": 0.5
        }
        
        # 根据元素类型调整等待策略
        if element_type in ['input', 'button', 'a']:
            wait_strategy["type"] = "element_to_be_clickable"
        elif element_type in ['img', 'video']:
            wait_strategy["type"] = "presence_of_element_located"
            wait_strategy["timeout"] = 15
        elif is_dynamic:
            wait_strategy["type"] = "visibility_of_element_located"
            wait_strategy["timeout"] = 20
        
        return wait_strategy
    
    def generate_page_object_code(self, locators: List[ElementLocator], element_name: str) -> str:
        """生成页面对象代码"""
        if not locators:
            return ""
        
        # 选择最佳定位器
        best_locator = locators[0]
        
        code = f"""
    @property
    def {element_name}(self):
        \"\"\"{best_locator.description}\"\"\"
        return self.driver.find_element(By.{best_locator.type.value.upper()}, "{best_locator.value}")
    
    def click_{element_name}(self):
        \"\"\"点击{element_name}元素\"\"\"
        self.{element_name}.click()
    
    def input_{element_name}(self, text):
        \"\"\"在{element_name}元素中输入文本\"\"\"
        self.{element_name}.clear()
        self.{element_name}.send_keys(text)
        """
        
        return code
    
    def generate_selenium_code(self, locators: List[ElementLocator], action: str, element_name: str, value: str = None) -> str:
        """生成Selenium代码"""
        if not locators:
            return f"# 无法找到{element_name}的定位器"
        
        best_locator = locators[0]
        
        code = f"""
        # {best_locator.description}
        {element_name}_element = driver.find_element(By.{best_locator.type.value.upper()}, "{best_locator.value}")
        """
        
        if action == "click":
            code += f"""
        {element_name}_element.click()
        """
        elif action == "input":
            code += f"""
        {element_name}_element.clear()
        {element_name}_element.send_keys("{value}")
        """
        elif action == "get_text":
            code += f"""
        text = {element_name}_element.text
        """
        elif action == "wait":
            code += f"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(driver, 10)
        {element_name}_element = wait.until(EC.element_to_be_clickable((By.{best_locator.type.value.upper()}, "{best_locator.value}")))
        """
        
        return code
    
    def generate_playwright_code(self, locators: List[ElementLocator], action: str, element_name: str, value: str = None) -> str:
        """生成Playwright代码"""
        if not locators:
            return f"# 无法找到{element_name}的定位器"
        
        best_locator = locators[0]
        
        # 转换定位器为Playwright格式
        playwright_locator = self._convert_to_playwright_locator(best_locator)
        
        code = f"""
        # {best_locator.description}
        {element_name}_element = page.locator("{playwright_locator}")
        """
        
        if action == "click":
            code += f"""
        {element_name}_element.click()
        """
        elif action == "input":
            code += f"""
        {element_name}_element.fill("{value}")
        """
        elif action == "get_text":
            code += f"""
        text = {element_name}_element.text_content()
        """
        elif action == "wait":
            code += f"""
        {element_name}_element.wait_for(state="visible", timeout=10000)
        """
        
        return code
    
    def _convert_to_playwright_locator(self, locator: ElementLocator) -> str:
        """将定位器转换为Playwright格式"""
        if locator.type == LocatorType.ID:
            return f"#{locator.value}"
        elif locator.type == LocatorType.CSS_SELECTOR:
            return locator.value
        elif locator.type == LocatorType.XPATH:
            return f"xpath={locator.value}"
        elif locator.type == LocatorType.TEST_ID:
            return f"[data-testid='{locator.value}']"
        else:
            return locator.value 