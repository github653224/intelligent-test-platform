#!/usr/bin/env python3
"""
智能DOM元素定位演示脚本
"""

import asyncio
import json
from ai_engine.processors.smart_element_locator import SmartElementLocator, ElementLocator

def demo_smart_element_locator():
    """演示智能DOM元素定位功能"""
    print("🧠 智能DOM元素定位演示")
    print("=" * 50)
    
    # 创建智能定位器
    smart_locator = SmartElementLocator()
    
    # 模拟不同的DOM元素
    test_elements = [
        {
            "name": "login_button",
            "tag_name": "button",
            "id": "login-btn",
            "class_names": ["btn", "btn-primary", "login-button"],
            "name_attr": "login",
            "text_content": "登录",
            "aria_label": "用户登录按钮",
            "data_test_id": "login-button",
            "is_dynamic": False,
            "description": "登录按钮"
        },
        {
            "name": "username_input",
            "tag_name": "input",
            "id": "username",
            "class_names": ["form-control", "input-field"],
            "name_attr": "username",
            "text_content": "",
            "aria_label": "用户名输入框",
            "data_test_id": "username-input",
            "is_dynamic": False,
            "description": "用户名输入框"
        },
        {
            "name": "password_input",
            "tag_name": "input",
            "id": "password",
            "class_names": ["form-control", "password-field"],
            "name_attr": "password",
            "text_content": "",
            "aria_label": "密码输入框",
            "data_test_id": "password-input",
            "is_dynamic": False,
            "description": "密码输入框"
        },
        {
            "name": "submit_button",
            "tag_name": "button",
            "id": "",
            "class_names": ["btn", "btn-success"],
            "name_attr": "submit",
            "text_content": "提交",
            "aria_label": "提交表单",
            "data_test_id": "",
            "is_dynamic": False,
            "description": "提交按钮"
        },
        {
            "name": "error_message",
            "tag_name": "div",
            "id": "",
            "class_names": ["alert", "alert-danger"],
            "name_attr": "",
            "text_content": "用户名或密码错误",
            "aria_label": "错误信息",
            "data_test_id": "error-message",
            "is_dynamic": True,
            "description": "错误信息显示"
        }
    ]
    
    print("📋 分析DOM元素定位策略...")
    print()
    
    for i, element in enumerate(test_elements, 1):
        print(f"🔍 元素 {i}: {element['name']} ({element['description']})")
        print(f"   标签: {element['tag_name']}")
        print(f"   ID: {element['id'] or '无'}")
        print(f"   类名: {', '.join(element['class_names']) if element['class_names'] else '无'}")
        print(f"   文本: {element['text_content'] or '无'}")
        print(f"   测试ID: {element['data_test_id'] or '无'}")
        
        # 生成智能定位器
        locators = smart_locator.analyze_element(element)
        
        print("   📍 定位策略 (按优先级排序):")
        for j, locator in enumerate(locators, 1):
            confidence_percent = int(locator.confidence * 100)
            print(f"     {j}. {locator.type.value.upper()}: {locator.value}")
            print(f"        置信度: {confidence_percent}%")
            print(f"        描述: {locator.description}")
        
        # 生成等待策略
        wait_strategy = smart_locator.generate_wait_strategy(element)
        print(f"   ⏱️  等待策略: {wait_strategy['type']} (超时: {wait_strategy['timeout']}秒)")
        
        print()
    
    # 演示代码生成
    print("💻 生成测试代码示例...")
    print()
    
    # 选择最佳定位器生成代码
    best_locators = []
    for element in test_elements:
        locators = smart_locator.analyze_element(element)
        if locators:
            best_locators.append((element['name'], locators[0]))
    
    # 生成Selenium代码
    print("🐍 Selenium代码示例:")
    selenium_code = """
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_login_functionality():
    \"\"\"登录功能测试\"\"\"
    driver = webdriver.Chrome()
    driver.get("https://example.com/login")
    
    try:
"""
    
    for element_name, locator in best_locators:
        selenium_code += f"""
        # {locator.description}
        {element_name}_element = driver.find_element(By.{locator.type.value.upper()}, "{locator.value}")
"""
        
        if "input" in element_name:
            selenium_code += f"""
        {element_name}_element.clear()
        {element_name}_element.send_keys("test_user")
"""
        elif "button" in element_name:
            selenium_code += f"""
        {element_name}_element.click()
"""
    
    selenium_code += """
        # 验证登录成功
        assert "dashboard" in driver.current_url
        
    finally:
        driver.quit()
"""
    
    print(selenium_code)
    
    # 生成Playwright代码
    print("\n🎭 Playwright代码示例:")
    playwright_code = """
from playwright.sync_api import sync_playwright

def test_login_functionality():
    \"\"\"登录功能测试\"\"\"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://example.com/login")
        
        try:
"""
    
    for element_name, locator in best_locators:
        playwright_locator = smart_locator._convert_to_playwright_locator(locator)
        playwright_code += f"""
            # {locator.description}
            {element_name}_element = page.locator("{playwright_locator}")
"""
        
        if "input" in element_name:
            playwright_code += f"""
            {element_name}_element.fill("test_user")
"""
        elif "button" in element_name:
            playwright_code += f"""
            {element_name}_element.click()
"""
    
    playwright_code += """
            # 验证登录成功
            assert "dashboard" in page.url
            
        finally:
            browser.close()
"""
    
    print(playwright_code)
    
    # 演示定位策略优先级
    print("\n📊 定位策略优先级说明:")
    print("1. ID定位器 (置信度: 95%) - 最稳定，推荐使用")
    print("2. Test ID定位器 (置信度: 90%) - 专为测试设计")
    print("3. Accessibility ID定位器 (置信度: 85%) - 无障碍友好")
    print("4. Name属性定位器 (置信度: 80%) - 表单元素常用")
    print("5. 智能CSS选择器 (置信度: 75%) - 灵活且可读性好")
    print("6. 智能XPath (置信度: 70%) - 功能强大但复杂")
    print("7. 文本内容定位器 (置信度: 65%) - 基于可见文本")
    print("8. 类名定位器 (置信度: 55%) - 相对稳定")
    
    print("\n🎯 智能定位器特点:")
    print("✅ 自动选择最佳定位策略")
    print("✅ 支持多种定位方式")
    print("✅ 置信度评估机制")
    print("✅ 自动生成测试代码")
    print("✅ 等待策略优化")
    print("✅ 跨浏览器兼容")
    
    print("\n🚀 使用建议:")
    print("1. 优先使用ID和Test ID定位器")
    print("2. 避免使用动态生成的类名")
    print("3. 为重要元素添加data-testid属性")
    print("4. 使用语义化的aria-label属性")
    print("5. 定期更新定位策略以适应页面变化")

if __name__ == "__main__":
    demo_smart_element_locator() 