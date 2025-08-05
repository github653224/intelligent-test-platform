#!/usr/bin/env python3
"""
AI引擎功能测试脚本
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# AI引擎服务地址
AI_ENGINE_URL = "http://localhost:8001"

async def test_requirement_analysis():
    """测试需求分析功能"""
    print("🧪 测试需求分析功能...")
    
    test_data = {
        "requirement_text": "用户登录功能：用户可以通过用户名和密码登录系统，登录成功后跳转到主页，登录失败显示错误信息。",
        "project_context": "这是一个电商网站的用户认证模块",
        "test_focus": ["functional", "security"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/analyze_requirement",
                json=test_data,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            print("✅ 需求分析测试通过")
            print(f"📊 分析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True
    except Exception as e:
        print(f"❌ 需求分析测试失败: {e}")
        return False

async def test_test_case_generation():
    """测试测试用例生成功能"""
    print("\n🧪 测试测试用例生成功能...")
    
    test_data = {
        "requirement_text": "用户注册功能：用户填写邮箱、密码、确认密码进行注册，系统验证邮箱格式和密码强度。",
        "test_type": "functional",
        "test_scope": {"priority": "high"}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_test_cases",
                json=test_data,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            print("✅ 测试用例生成测试通过")
            print(f"📋 生成的测试用例: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True
    except Exception as e:
        print(f"❌ 测试用例生成测试失败: {e}")
        return False

async def test_api_test_generation():
    """测试API测试生成功能"""
    print("\n🧪 测试API测试生成功能...")
    
    test_data = {
        "api_documentation": """
        POST /api/users/login
        请求体: {"username": "string", "password": "string"}
        响应: {"token": "string", "user": {"id": 1, "username": "string"}}
        """,
        "base_url": "https://api.example.com",
        "test_scenarios": ["normal", "error"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_api_tests",
                json=test_data,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            print("✅ API测试生成测试通过")
            print(f"🔧 生成的API测试: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True
    except Exception as e:
        print(f"❌ API测试生成测试失败: {e}")
        return False

async def test_ui_test_generation():
    """测试UI测试生成功能"""
    print("\n🧪 测试UI测试生成功能...")
    
    test_data = {
        "page_url": "https://example.com/login",
        "user_actions": ["输入用户名", "输入密码", "点击登录按钮"],
        "test_scenarios": ["正常登录", "错误密码"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_ui_tests",
                json=test_data,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            print("✅ UI测试生成测试通过")
            print(f"🎨 生成的UI测试: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True
    except Exception as e:
        print(f"❌ UI测试生成测试失败: {e}")
        return False

async def test_health_check():
    """测试健康检查"""
    print("\n🧪 测试健康检查...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_ENGINE_URL}/health", timeout=10.0)
            response.raise_for_status()
            result = response.json()
            print("✅ 健康检查通过")
            print(f"💚 服务状态: {result}")
            return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始AI引擎功能测试...")
    print("=" * 50)
    
    # 测试健康检查
    health_ok = await test_health_check()
    if not health_ok:
        print("❌ AI引擎服务不可用，请检查服务是否启动")
        return
    
    # 测试各项功能
    tests = [
        test_requirement_analysis,
        test_test_case_generation,
        test_api_test_generation,
        test_ui_test_generation,
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    passed = sum(results)
    total = len(results)
    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！AI引擎功能正常")
    else:
        print("⚠️  部分测试失败，请检查AI引擎配置")

if __name__ == "__main__":
    asyncio.run(main()) 