"""测试分析API - AI驱动的测试报告汇总分析"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import httpx
import logging
import json
import ast

from app.db.session import get_db
from app.models.project import TestRun, TestCase, Project

logger = logging.getLogger(__name__)
router = APIRouter()

AI_ENGINE_URL = "http://localhost:8001"


@router.get("/test-runs/analyze-summary-stream")
async def analyze_test_summary_stream(
    request: Request,
    days: int = 30,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    AI分析测试报告汇总（流式输出）
    """
    async def generate():
        try:
            # 1. 收集测试数据
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = db.query(TestRun)
            if project_id:
                query = query.filter(TestRun.project_id == project_id)
            query = query.filter(TestRun.created_at >= cutoff_date)
            
            test_runs = query.order_by(TestRun.id.desc()).all()
            
            if not test_runs:
                yield f"data: {json.dumps({'type': 'error', 'message': '暂无测试运行数据'}, ensure_ascii=False)}\n\n"
                return
            
            # 2. 构建汇总数据
            summary_data = {
                "total_runs": len(test_runs),
                "statistics": {
                    "total_cases": 0,
                    "passed_cases": 0,
                    "failed_cases": 0,
                    "skipped_cases": 0,
                    "error_cases": 0,
                },
                "overall_pass_rate": 0.0,
            }
            
            for tr in test_runs:
                if tr.results and isinstance(tr.results, dict):
                    total = tr.results.get("total_cases", 0) or 0
                    passed = tr.results.get("passed_cases", 0) or 0
                    failed = tr.results.get("failed_cases", 0) or 0
                    skipped = tr.results.get("skipped_cases", 0) or 0
                    error = tr.results.get("error_cases", 0) or 0
                    
                    summary_data["statistics"]["total_cases"] += total
                    summary_data["statistics"]["passed_cases"] += passed
                    summary_data["statistics"]["failed_cases"] += failed
                    summary_data["statistics"]["skipped_cases"] += skipped
                    summary_data["statistics"]["error_cases"] += error
            
            total = summary_data["statistics"]["total_cases"]
            passed = summary_data["statistics"]["passed_cases"]
            overall_pass_rate = (passed / total * 100) if total > 0 else 0
            summary_data["overall_pass_rate"] = round(overall_pass_rate, 2)
            
            # 发送初始数据
            yield f"data: {json.dumps({'type': 'summary', 'data': summary_data}, ensure_ascii=False)}\n\n"
            
            # 3. 调用AI引擎进行流式分析
            try:
                async with httpx.AsyncClient() as client:
                    ai_prompt = f"""
请分析以下测试执行汇总数据，并提供专业的测试洞察和建议：

## 测试执行概况
- 分析时间段：{days}天
- 测试运行总数：{summary_data['total_runs']}次
- 总测试用例数：{summary_data['statistics']['total_cases']}个
- 通过用例：{summary_data['statistics']['passed_cases']}个
- 失败用例：{summary_data['statistics']['failed_cases']}个
- 跳过用例：{summary_data['statistics']['skipped_cases']}个
- 错误用例：{summary_data['statistics']['error_cases']}个
- 总体通过率：{summary_data['overall_pass_rate']}%

请提供以下分析：
1. **执行趋势分析**：分析测试执行的趋势和模式
2. **质量评估**：评估整体测试质量，包括通过率、稳定性等
3. **问题识别**：识别常见失败模式、高风险区域
4. **改进建议**：提供具体的测试优化建议
5. **风险预警**：识别潜在的质量风险点

请以结构化的方式返回分析结果，包括关键指标、趋势、建议等。
"""
                    
                    # 使用流式接口
                    async with client.stream(
                        "POST",
                        f"{AI_ENGINE_URL}/api/analyze-requirement-stream",
                        json={
                            "requirement_text": ai_prompt,
                            "project_context": f"测试执行汇总分析报告 - 分析最近{days}天的测试数据",
                            "test_focus": ["测试质量", "失败模式", "改进建议"]
                        },
                        timeout=120.0
                    ) as response:
                        response.raise_for_status()
                        async for chunk_bytes in response.aiter_bytes():
                            if chunk_bytes:
                                chunk_text = chunk_bytes.decode('utf-8', errors='ignore')
                                # 处理SSE格式的数据
                                for line in chunk_text.split('\n'):
                                    line = line.strip()
                                    if line.startswith('data: '):
                                        content = line[6:].strip()
                                        if content and content != '[DONE]':
                                            # 如果内容已经是JSON，尝试解析
                                            try:
                                                parsed = json.loads(content)
                                                if isinstance(parsed, dict) and 'content' in parsed:
                                                    yield f"data: {json.dumps({'type': 'chunk', 'content': parsed['content']}, ensure_ascii=False)}\n\n"
                                                else:
                                                    yield f"data: {json.dumps({'type': 'chunk', 'content': content}, ensure_ascii=False)}\n\n"
                                            except json.JSONDecodeError:
                                                # 如果不是JSON，直接作为文本内容
                                                yield f"data: {json.dumps({'type': 'chunk', 'content': content}, ensure_ascii=False)}\n\n"
                                    elif line and not line.startswith(':'):
                                        # 非SSE格式的直接文本
                                        yield f"data: {json.dumps({'type': 'chunk', 'content': line}, ensure_ascii=False)}\n\n"
                
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"AI流式分析失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'AI分析服务暂时不可用: {str(e)}'}, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"流式分析失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/test-runs/analyze-summary")
async def analyze_test_summary(
    days: int = 30,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    AI分析测试报告汇总
    分析最近N天的测试运行数据，提供AI驱动的洞察和建议
    """
    try:
        # 1. 收集测试数据
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(TestRun)
        if project_id:
            query = query.filter(TestRun.project_id == project_id)
        
        # TestRun继承自Base，Base有created_at字段
        # 按时间过滤，只获取最近N天的数据
        query = query.filter(TestRun.created_at >= cutoff_date)
        
        test_runs = query.order_by(TestRun.id.desc()).all()
        
        if not test_runs:
            return {
                "summary": {
                    "total_runs": 0,
                    "date_range": {
                        "start": cutoff_date.isoformat(),
                        "end": datetime.utcnow().isoformat()
                    },
                    "statistics": {
                        "total_cases": 0,
                        "passed_cases": 0,
                        "failed_cases": 0,
                        "skipped_cases": 0,
                        "error_cases": 0,
                    },
                    "status_distribution": {
                        "completed": 0,
                        "failed": 0,
                        "running": 0,
                        "pending": 0,
                        "cancelled": 0
                    },
                    "overall_pass_rate": 0.0,
                    "test_runs": []
                },
                "analysis": "暂无测试运行数据，无法进行分析。请先执行一些测试运行。",
                "key_metrics": {
                    "overall_pass_rate": 0.0,
                    "total_test_runs": 0,
                    "total_test_cases": 0,
                    "failure_rate": 0.0,
                    "avg_pass_rate": 0.0
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # 2. 构建汇总数据
        summary_data = {
            "total_runs": len(test_runs),
            "date_range": {
                "start": cutoff_date.isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "statistics": {
                "total_cases": 0,
                "passed_cases": 0,
                "failed_cases": 0,
                "skipped_cases": 0,
                "error_cases": 0,
            },
            "status_distribution": {
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": 0,
                "cancelled": 0
            },
            "test_runs": []
        }
        
        # 3. 分析每个测试运行
        for tr in test_runs:
            # 确保results是字典类型
            if not tr.results:
                tr.results = {}
            if isinstance(tr.results, dict):
                total = tr.results.get("total_cases", 0) or 0
                passed = tr.results.get("passed_cases", 0) or 0
                failed = tr.results.get("failed_cases", 0) or 0
                skipped = tr.results.get("skipped_cases", 0) or 0
                error = tr.results.get("error_cases", 0) or 0
                
                summary_data["statistics"]["total_cases"] += total
                summary_data["statistics"]["passed_cases"] += passed
                summary_data["statistics"]["failed_cases"] += failed
                summary_data["statistics"]["skipped_cases"] += skipped
                summary_data["statistics"]["error_cases"] += error
                
                # 计算通过率
                pass_rate = (passed / total * 100) if total > 0 else 0
                
                summary_data["test_runs"].append({
                    "id": tr.id,
                    "name": tr.name,
                    "status": tr.status,
                    "total_cases": total,
                    "passed_cases": passed,
                    "failed_cases": failed,
                    "skipped_cases": skipped,
                    "error_cases": error,
                    "pass_rate": round(pass_rate, 2),
                    "start_time": tr.start_time if tr.start_time else None,
                    "end_time": tr.end_time if tr.end_time else None,
                    "duration": tr.results.get("duration", 0)
                })
            
            # 统计状态分布
            status = tr.status
            if status in summary_data["status_distribution"]:
                summary_data["status_distribution"][status] += 1
        
        # 计算总体通过率
        total = summary_data["statistics"]["total_cases"]
        passed = summary_data["statistics"]["passed_cases"]
        overall_pass_rate = (passed / total * 100) if total > 0 else 0
        summary_data["overall_pass_rate"] = round(overall_pass_rate, 2)
        
        # 4. 调用AI引擎进行分析
        try:
            async with httpx.AsyncClient() as client:
                ai_prompt = f"""
请分析以下测试执行汇总数据，并提供专业的测试洞察和建议：

## 测试执行概况
- 分析时间段：{days}天
- 测试运行总数：{summary_data['total_runs']}次
- 总测试用例数：{summary_data['statistics']['total_cases']}个
- 通过用例：{summary_data['statistics']['passed_cases']}个
- 失败用例：{summary_data['statistics']['failed_cases']}个
- 跳过用例：{summary_data['statistics']['skipped_cases']}个
- 错误用例：{summary_data['statistics']['error_cases']}个
- 总体通过率：{summary_data['overall_pass_rate']}%

## 测试运行状态分布
- 已完成：{summary_data['status_distribution']['completed']}次
- 已失败：{summary_data['status_distribution']['failed']}次
- 执行中：{summary_data['status_distribution']['running']}次
- 待执行：{summary_data['status_distribution']['pending']}次
- 已取消：{summary_data['status_distribution']['cancelled']}次

## 详细测试运行数据
{summary_data['test_runs'][:10]}  # 只取前10个作为样本

请提供以下分析：
1. **执行趋势分析**：分析测试执行的趋势和模式
2. **质量评估**：评估整体测试质量，包括通过率、稳定性等
3. **问题识别**：识别常见失败模式、高风险区域
4. **改进建议**：提供具体的测试优化建议
5. **风险预警**：识别潜在的质量风险点

请以结构化的方式返回分析结果，包括关键指标、趋势、建议等。
"""
                
                # 使用需求分析的端点模式，但传递测试分析prompt
                try:
                    response = await client.post(
                        f"{AI_ENGINE_URL}/analyze_requirement",
                        json={
                            "requirement_text": ai_prompt,
                            "project_context": f"测试执行汇总分析报告 - 分析最近{days}天的测试数据",
                            "test_focus": ["测试质量", "失败模式", "改进建议"]
                        },
                        timeout=120.0
                    )
                    response.raise_for_status()
                    ai_result = response.json()
                    # 提取分析内容 - AI引擎返回格式为 {"status": "success", "analysis": {...}}
                    if isinstance(ai_result, dict):
                        analysis_data = ai_result.get("analysis", {})
                        
                        # 如果analysis_data是字符串，尝试解析为字典
                        if isinstance(analysis_data, str):
                            try:
                                # 尝试使用ast.literal_eval解析Python字典字符串（安全）
                                analysis_data = ast.literal_eval(analysis_data)
                            except (ValueError, SyntaxError) as e:
                                logger.warning(f"ast.literal_eval解析失败: {e}")
                                try:
                                    # 如果ast.literal_eval失败，尝试JSON解析（需要将单引号替换为双引号）
                                    # 注意：这只能处理简单的JSON格式
                                    json_str = analysis_data.replace("'", '"')
                                    analysis_data = json.loads(json_str)
                                except (json.JSONDecodeError, AttributeError) as e:
                                    logger.warning(f"JSON解析也失败: {e}")
                                    # 如果都失败，直接使用字符串
                                    ai_analysis = analysis_data
                                    analysis_data = None
                        
                        # 如果analysis_data是字典，格式化
                        if analysis_data and isinstance(analysis_data, dict):
                            # 将结构化数据转换为Markdown格式
                            ai_analysis = _format_analysis_as_markdown(analysis_data)
                        elif analysis_data:
                            ai_analysis = str(analysis_data) if analysis_data else "分析完成，但未返回详细内容"
                        elif not isinstance(analysis_data, dict) and analysis_data is None:
                            # 如果解析失败但没有设置ai_analysis，使用默认值
                            ai_analysis = "分析完成，但无法解析详细内容"
                    else:
                        ai_analysis = str(ai_result)
                except httpx.RequestError as e:
                    logger.error(f"AI引擎请求失败: {e}")
                    ai_analysis = "AI分析服务暂时不可用，但已提供基础统计数据。"
                except httpx.HTTPStatusError as e:
                    logger.error(f"AI引擎响应错误: {e.response.status_code} - {e.response.text}")
                    ai_analysis = "AI分析服务暂时不可用，但已提供基础统计数据。"
                
        except Exception as e:
            logger.error(f"AI分析失败: {e}", exc_info=True)
            ai_analysis = "AI分析服务暂时不可用，但已提供基础统计数据。"
        
        # 5. 返回结果
        return {
            "summary": summary_data,
            "analysis": ai_analysis,
            "key_metrics": {
                "overall_pass_rate": summary_data["overall_pass_rate"],
                "total_test_runs": summary_data["total_runs"],
                "total_test_cases": summary_data["statistics"]["total_cases"],
                "failure_rate": round((summary_data["statistics"]["failed_cases"] / total * 100) if total > 0 else 0, 2),
                "avg_pass_rate": _calculate_avg_pass_rate(summary_data["test_runs"])
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"分析测试汇总失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def _calculate_avg_pass_rate(test_runs: list) -> float:
    """计算平均通过率"""
    if not test_runs:
        return 0.0
    
    total_pass_rate = sum(run.get("pass_rate", 0) for run in test_runs)
    return round(total_pass_rate / len(test_runs), 2)


def _format_analysis_as_markdown(analysis_data: dict) -> str:
    """将AI分析结果格式化为Markdown格式"""
    markdown_parts = []
    
    # 1. 功能要点分析
    if "functional_points" in analysis_data and analysis_data["functional_points"]:
        markdown_parts.append("## 📋 功能要点分析\n")
        func_points = analysis_data["functional_points"]
        if isinstance(func_points, list):
            for i, point in enumerate(func_points, 1):
                if isinstance(point, dict):
                    point_name = point.get("point", "")
                    priority = point.get("priority", "")
                    complexity = point.get("complexity", "")
                    risk_level = point.get("risk_level", "")
                    markdown_parts.append(f"{i}. **{point_name}**")
                    if priority:
                        markdown_parts.append(f"   - 优先级: {priority}")
                    if complexity:
                        markdown_parts.append(f"   - 复杂度: {complexity}")
                    if risk_level:
                        markdown_parts.append(f"   - 风险级别: {risk_level}")
                    markdown_parts.append("")
        markdown_parts.append("\n")
    
    # 2. 测试边界条件
    if "test_boundaries" in analysis_data and analysis_data["test_boundaries"]:
        markdown_parts.append("## 🔲 测试边界条件\n")
        boundaries = analysis_data["test_boundaries"]
        if isinstance(boundaries, list):
            for i, boundary in enumerate(boundaries, 1):
                if isinstance(boundary, dict):
                    boundary_desc = boundary.get("boundary", "")
                    test_type = boundary.get("test_type", "")
                    priority = boundary.get("priority", "")
                    markdown_parts.append(f"{i}. **{boundary_desc}**")
                    if test_type:
                        markdown_parts.append(f"   - 测试类型: {test_type}")
                    if priority:
                        markdown_parts.append(f"   - 优先级: {priority}")
                    markdown_parts.append("")
        markdown_parts.append("\n")
    
    # 3. 潜在风险点
    if "risk_points" in analysis_data and analysis_data["risk_points"]:
        markdown_parts.append("## ⚠️ 潜在风险点\n")
        risks = analysis_data["risk_points"]
        if isinstance(risks, list):
            for i, risk in enumerate(risks, 1):
                if isinstance(risk, dict):
                    risk_desc = risk.get("risk", "")
                    impact = risk.get("impact", "")
                    mitigation = risk.get("mitigation", "")
                    markdown_parts.append(f"### 风险 {i}: {risk_desc}\n")
                    if impact:
                        markdown_parts.append(f"- **影响程度**: {impact}")
                    if mitigation:
                        markdown_parts.append(f"- **缓解措施**: {mitigation}")
                    markdown_parts.append("")
        markdown_parts.append("\n")
    
    # 4. 测试策略建议
    if "test_strategy" in analysis_data and analysis_data["test_strategy"]:
        markdown_parts.append("## 🎯 测试策略建议\n")
        strategy = analysis_data["test_strategy"]
        if isinstance(strategy, dict):
            overall = strategy.get("overall_approach", "")
            if overall:
                markdown_parts.append(f"### 整体策略\n{overall}\n")
            
            test_levels = strategy.get("test_levels", [])
            if test_levels:
                markdown_parts.append(f"### 测试层级\n- " + "\n- ".join(test_levels) + "\n")
            
            automation = strategy.get("automation_scope", "")
            if automation:
                markdown_parts.append(f"### 自动化范围\n{automation}\n")
            
            tools = strategy.get("tools_recommendation", [])
            if tools:
                markdown_parts.append(f"### 推荐工具\n- " + "\n- ".join(tools) + "\n")
        markdown_parts.append("\n")
    
    # 5. 测试优先级
    if "test_priorities" in analysis_data and analysis_data["test_priorities"]:
        markdown_parts.append("## 📊 测试优先级\n")
        priorities = analysis_data["test_priorities"]
        if isinstance(priorities, list):
            for i, priority_item in enumerate(priorities, 1):
                if isinstance(priority_item, dict):
                    area = priority_item.get("area", "")
                    priority_level = priority_item.get("priority", "")
                    rationale = priority_item.get("rationale", "")
                    markdown_parts.append(f"{i}. **{area}** (优先级: {priority_level})")
                    if rationale:
                        markdown_parts.append(f"   - 理由: {rationale}")
                    markdown_parts.append("")
        markdown_parts.append("\n")
    
    # 6. 预估工作量
    if "estimated_effort" in analysis_data and analysis_data["estimated_effort"]:
        markdown_parts.append("## ⏱️ 预估工作量\n")
        effort = analysis_data["estimated_effort"]
        if isinstance(effort, dict):
            total = effort.get("total_hours", 0)
            if total:
                markdown_parts.append(f"**总工作量**: {total} 小时\n")
            
            breakdown = effort.get("breakdown", {})
            if breakdown:
                markdown_parts.append("### 工作量分解\n")
                for key, value in breakdown.items():
                    key_name_map = {
                        "test_planning": "测试规划",
                        "test_design": "测试设计",
                        "test_execution": "测试执行",
                        "automation": "自动化"
                    }
                    key_display = key_name_map.get(key, key)
                    markdown_parts.append(f"- {key_display}: {value} 小时")
                markdown_parts.append("")
        markdown_parts.append("\n")
    
    # 如果没有找到任何结构化数据，尝试提取其他字段
    if not markdown_parts:
        if "analysis" in analysis_data:
            ai_analysis = str(analysis_data.get("analysis", ""))
            return ai_analysis
        else:
            # 如果都没有，将整个对象格式化为JSON
            return json.dumps(analysis_data, ensure_ascii=False, indent=2)
    
    return "\n".join(markdown_parts)

