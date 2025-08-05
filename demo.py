#!/usr/bin/env python3
"""
AI智能自动化测试平台演示脚本
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

# 服务地址
AI_ENGINE_URL = "http://localhost:8001"
BACKEND_URL = "http://localhost:8000"

class AITestPlatformDemo:
    def __init__(self):
        self.ai_engine_url = AI_ENGINE_URL
        self.backend_url = BACKEND_URL
    
    async def check_services(self):
        """检查服务状态"""
        print("🔍 检查服务状态...")
        
        services = [
            ("AI引擎", f"{self.ai_engine_url}/health"),
            ("后端API", f"{self.backend_url}/health"),
        ]
        
        for name, url in services:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        print(f"✅ {name}: 运行正常")
                    else:
                        print(f"❌ {name}: 状态异常 ({response.status_code})")
            except Exception as e:
                print(f"❌ {name}: 无法连接 ({e})")
    
    async def demo_requirement_analysis(self):
        """演示需求分析功能"""
        print("\n📋 演示需求分析功能...")
        
        requirement = {
            "requirement_text": """
            电商网站购物车功能：
            1. 用户可以将商品添加到购物车
            2. 用户可以修改购物车中商品数量
            3. 用户可以删除购物车中的商品
            4. 系统自动计算购物车总价
            5. 用户可以从购物车进入结算页面
            """,
            "project_context": "电商网站核心功能模块",
            "test_focus": ["functional", "performance", "security"]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engine_url}/analyze_requirement",
                    json=requirement,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                print("✅ 需求分析完成")
                print("📊 分析要点:")
                if 'analysis' in result:
                    analysis = result['analysis']
                    if isinstance(analysis, dict):
                        if 'functional_points' in analysis:
                            print(f"  - 功能点: {len(analysis['functional_points'])} 个")
                        if 'test_boundaries' in analysis:
                            print(f"  - 边界条件: {len(analysis['test_boundaries'])} 个")
                        if 'risk_points' in analysis:
                            print(f"  - 风险点: {len(analysis['risk_points'])} 个")
                    else:
                        print(f"  - 分析结果: {analysis[:200]}...")
                
                return True
        except Exception as e:
            print(f"❌ 需求分析失败: {e}")
            return False
    
    async def demo_test_case_generation(self):
        """演示测试用例生成功能"""
        print("\n🧪 演示测试用例生成功能...")
        
        test_case_request = {
            "requirement_text": "用户登录功能：用户输入用户名和密码，系统验证后允许登录或显示错误信息",
            "test_type": "functional",
            "test_scope": {"priority": "high", "coverage": "comprehensive"}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engine_url}/generate_test_cases",
                    json=test_case_request,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                print("✅ 测试用例生成完成")
                if 'test_cases' in result:
                    test_cases = result['test_cases']
                    print(f"📝 生成了 {len(test_cases)} 个测试用例")
                    for i, test_case in enumerate(test_cases[:3], 1):
                        if isinstance(test_case, dict) and 'title' in test_case:
                            print(f"  {i}. {test_case['title']}")
                
                return True
        except Exception as e:
            print(f"❌ 测试用例生成失败: {e}")
            return False
    
    async def demo_api_test_generation(self):
        """演示API测试生成功能"""
        print("\n🔧 演示API测试生成功能...")
        
        api_request = {
            "api_documentation": """
            # 用户管理API
            
            ## 用户登录
            POST /api/auth/login
            Content-Type: application/json
            
            请求体:
            {
                "username": "string",
                "password": "string"
            }
            
            响应:
            {
                "token": "string",
                "user": {
                    "id": 1,
                    "username": "string",
                    "email": "string"
                }
            }
            
            ## 用户注册
            POST /api/auth/register
            Content-Type: application/json
            
            请求体:
            {
                "username": "string",
                "email": "string",
                "password": "string"
            }
            """,
            "base_url": "https://api.example.com",
            "test_scenarios": ["normal", "error", "boundary", "security"]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engine_url}/generate_api_tests",
                    json=api_request,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                print("✅ API测试生成完成")
                if 'api_tests' in result:
                    api_tests = result['api_tests']
                    print(f"🔧 生成了 {len(api_tests)} 个API测试")
                    for i, test in enumerate(api_tests[:3], 1):
                        if isinstance(test, dict) and 'name' in test:
                            print(f"  {i}. {test['name']}")
                
                return True
        except Exception as e:
            print(f"❌ API测试生成失败: {e}")
            return False
    
    async def demo_ui_test_generation(self):
        """演示UI测试生成功能"""
        print("\n🎨 演示UI测试生成功能...")
        
        ui_request = {
            "page_url": "https://example.com/login",
            "user_actions": [
                "打开登录页面",
                "输入用户名",
                "输入密码", 
                "点击登录按钮",
                "验证登录结果"
            ],
            "test_scenarios": ["正常登录", "错误密码", "空用户名", "记住密码"]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engine_url}/generate_ui_tests",
                    json=ui_request,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                print("✅ UI测试生成完成")
                if 'ui_tests' in result:
                    ui_tests = result['ui_tests']
                    print(f"🎨 生成了 {len(ui_tests)} 个UI测试")
                    for i, test in enumerate(ui_tests[:3], 1):
                        if isinstance(test, dict) and 'name' in test:
                            print(f"  {i}. {test['name']}")
                
                return True
        except Exception as e:
            print(f"❌ UI测试生成失败: {e}")
            return False
    
    async def run_demo(self):
        """运行完整演示"""
        print("🚀 AI智能自动化测试平台演示")
        print("=" * 50)
        
        # 检查服务状态
        await self.check_services()
        
        # 等待用户确认
        print("\n按 Enter 键开始演示...")
        input()
        
        # 运行各项演示
        demos = [
            ("需求分析", self.demo_requirement_analysis),
            ("测试用例生成", self.demo_test_case_generation),
            ("API测试生成", self.demo_api_test_generation),
            ("UI测试生成", self.demo_ui_test_generation),
        ]
        
        results = []
        for name, demo_func in demos:
            print(f"\n{'='*20} {name} {'='*20}")
            result = await demo_func()
            results.append(result)
            time.sleep(1)  # 短暂延迟
        
        # 输出演示结果
        print("\n" + "=" * 50)
        print("📊 演示结果汇总:")
        passed = sum(results)
        total = len(results)
        print(f"✅ 成功: {passed}/{total}")
        print(f"❌ 失败: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 所有演示成功！AI测试平台功能正常")
        else:
            print("⚠️  部分演示失败，请检查服务配置")
        
        print("\n🌐 访问地址:")
        print("  前端应用: http://localhost:3000")
        print("  后端API: http://localhost:8000")
        print("  AI引擎: http://localhost:8001")
        print("  API文档: http://localhost:8000/docs")

async def main():
    """主函数"""
    demo = AITestPlatformDemo()
    await demo.run_demo()

if __name__ == "__main__":
    asyncio.run(main()) 