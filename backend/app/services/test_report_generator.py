"""
测试报告生成器
生成测试执行的详细报告和摘要
"""
import json
from html import escape as html_escape
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.project import TestRun


class TestReportGenerator:
    """测试报告生成器"""
    
    @staticmethod
    def generate_summary_report(test_run: TestRun) -> Dict[str, Any]:
        """生成测试运行摘要报告"""
        results = test_run.results or {}
        
        summary = {
            "test_run_id": test_run.id,
            "test_run_name": test_run.name,
            "project_id": test_run.project_id,
            "test_suite_id": test_run.test_suite_id,
            "status": test_run.status,
            "start_time": test_run.start_time,
            "end_time": test_run.end_time,
            "duration": results.get("duration", 0),
            "statistics": {
                "total_cases": results.get("total_cases", 0),
                "passed_cases": results.get("passed_cases", 0),
                "failed_cases": results.get("failed_cases", 0),
                "skipped_cases": results.get("skipped_cases", 0),
                "error_cases": results.get("error_cases", 0),
            },
            "pass_rate": 0.0
        }
        
        # 计算通过率
        total = summary["statistics"]["total_cases"]
        if total > 0:
            passed = summary["statistics"]["passed_cases"]
            summary["pass_rate"] = round((passed / total) * 100, 2)
        
        return summary
    
    @staticmethod
    def generate_detailed_report(test_run: TestRun) -> Dict[str, Any]:
        """生成详细测试报告"""
        summary = TestReportGenerator.generate_summary_report(test_run)
        results = test_run.results or {}
        
        # 确保 test_results 是列表，并包含所有字段
        test_results = results.get("test_results", [])
        
        # 转换为 TestResult 格式，确保所有字段都包含
        formatted_test_results = []
        for result in test_results:
            formatted_result = {
                "test_case_id": result.get("test_case_id", 0),
                "test_case_title": result.get("test_case_title", "Unknown"),
                "status": result.get("status", "unknown"),
                "duration": result.get("duration", 0),
                "error_message": result.get("error_message"),
                "error_traceback": result.get("error_traceback"),
                "steps": result.get("steps", []),
                "actual_result": result.get("actual_result"),
                "screenshots": result.get("screenshots", []),
                "logs": result.get("logs", []),
                # 手动验证相关字段
                "manually_verified": result.get("manually_verified", False),
                "verified_by": result.get("verified_by"),
                "verified_at": result.get("verified_at"),
                "verification_notes": result.get("verification_notes"),
                "failure_reason": result.get("failure_reason"),
                "bug_id": result.get("bug_id"),
                "attachments": result.get("attachments", []),
            }
            formatted_test_results.append(formatted_result)
        
        detailed_report = {
            **summary,
            "test_results": formatted_test_results,
            "failed_tests": [],
            "error_tests": [],
            "skipped_tests": []
        }
        
        # 分类测试结果
        for result in formatted_test_results:
            status = result.get("status", "unknown")
            if status == "failed":
                detailed_report["failed_tests"].append(result)
            elif status == "error":
                detailed_report["error_tests"].append(result)
            elif status == "skipped":
                detailed_report["skipped_tests"].append(result)
        
        return detailed_report
    
    @staticmethod
    def generate_html_report(test_run: TestRun) -> str:
        """生成专业的HTML格式测试报告（包含图表）"""
        report = TestReportGenerator.generate_detailed_report(test_run)
        
        # 准备图表数据
        stats = report['statistics']
        total = stats['total_cases']
        passed = stats['passed_cases']
        failed = stats['failed_cases']
        skipped = stats['skipped_cases']
        error = stats['error_cases']
        
        # 计算百分比
        passed_pct = (passed / total * 100) if total > 0 else 0
        failed_pct = (failed / total * 100) if total > 0 else 0
        skipped_pct = (skipped / total * 100) if total > 0 else 0
        error_pct = (error / total * 100) if total > 0 else 0
        
        # 准备执行时间数据（用于图表）
        duration_data = []
        duration_labels = []
        status_data = []
        for result in report.get("test_results", []):
            duration_data.append(result.get("duration", 0))
            title = result.get("test_case_title", "Unknown")
            # 截取标题，避免过长
            if len(title) > 20:
                title = title[:17] + "..."
            duration_labels.append(title)
            status_data.append(result.get("status", "unknown"))
        
        # 按状态分组统计
        status_counts = {}
        for status in status_data:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 按执行时长排序（用于柱状图，只显示前10个）
        sorted_results = sorted(
            [(idx, result.get("duration", 0), duration_labels[idx]) 
             for idx, result in enumerate(report.get("test_results", []))],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        top_duration_data = [r[1] for r in sorted_results]
        top_duration_labels = [r[2] for r in sorted_results]
        
        # 准备时间序列数据（用于折线图，如果有多个测试结果）
        time_series_data = []
        if len(duration_data) > 1:
            time_series_data = duration_data
        
        # 将数据转换为JSON字符串用于JavaScript
        duration_labels_json = json.dumps(duration_labels, ensure_ascii=False)
        duration_data_json = json.dumps(duration_data)
        duration_data_length = len(duration_data)
        top_duration_labels_json = json.dumps(top_duration_labels, ensure_ascii=False)
        top_duration_data_json = json.dumps(top_duration_data)
        time_series_data_json = json.dumps(time_series_data)
        status_counts_json = json.dumps(status_counts, ensure_ascii=False)
        
        # 状态颜色映射
        status_color_map = {
            'completed': '#52c41a',
            'failed': '#ff4d4f',
            'running': '#1890ff',
            'pending': '#faad14',
            'cancelled': '#d9d9d9'
        }
        status_text_map = {
            'completed': '已完成',
            'failed': '失败',
            'running': '执行中',
            'pending': '待执行',
            'cancelled': '已取消'
        }
        
        # HTML转义报告名称
        report_name = html_escape(str(report['test_run_name']))
        
        # 格式化时间
        def format_datetime(dt):
            if dt is None:
                return 'N/A'
            if isinstance(dt, str):
                try:
                    # 尝试解析ISO格式字符串
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return dt
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return str(dt)
        
        start_time = html_escape(format_datetime(report['start_time']))
        end_time = html_escape(format_datetime(report['end_time']))
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {report_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .report-container {{
            max-width: 1400px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }}
        .report-header h1 {{
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .report-header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .report-header .download-buttons {{
            margin-top: 20px;
            display: flex;
            gap: 12px;
            justify-content: center;
        }}
        .download-btn {{
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }}
        .download-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}
        .download-btn:active {{
            transform: translateY(0);
        }}
        .report-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        .meta-item {{
            text-align: center;
        }}
        .meta-item .label {{
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        .meta-item .value {{
            font-size: 18px;
            font-weight: 600;
            color: #212529;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            background: {status_color_map.get(report['status'], '#6c757d')};
            color: white;
        }}
        .charts-section {{
            padding: 30px;
            background: #ffffff;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .chart-card h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #212529;
            margin-bottom: 20px;
            text-align: center;
        }}
        .chart-container {{
            position: relative;
            height: 350px;
            min-height: 350px;
        }}
        .stat-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }}
        .stat-card.total {{
            border-top: 4px solid #2196F3;
        }}
        .stat-card.passed {{
            border-top: 4px solid #52c41a;
        }}
        .stat-card.failed {{
            border-top: 4px solid #ff4d4f;
        }}
        .stat-card.skipped {{
            border-top: 4px solid #faad14;
        }}
        .stat-card.error {{
            border-top: 4px solid #722ed1;
        }}
        .stat-card .value {{
            font-size: 36px;
            font-weight: 700;
            margin: 8px 0;
            color: #212529;
        }}
        .stat-card .label {{
            font-size: 14px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-card .percentage {{
            font-size: 12px;
            color: #6c757d;
            margin-top: 4px;
        }}
        .test-results-section {{
            padding: 30px;
        }}
        .test-results-section h2 {{
            font-size: 24px;
            font-weight: 600;
            color: #212529;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        .test-result {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            transition: box-shadow 0.2s;
        }}
        .test-result:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .test-result.passed {{
            border-left: 4px solid #52c41a;
        }}
        .test-result.failed {{
            border-left: 4px solid #ff4d4f;
        }}
        .test-result.error {{
            border-left: 4px solid #722ed1;
        }}
        .test-result.skipped {{
            border-left: 4px solid #faad14;
        }}
        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .test-title {{
            font-size: 16px;
            font-weight: 600;
            color: #212529;
            flex: 1;
        }}
        .test-status {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}
        .test-status.passed {{
            background: #f6ffed;
            color: #52c41a;
            border: 1px solid #b7eb8f;
        }}
        .test-status.failed {{
            background: #fff2f0;
            color: #ff4d4f;
            border: 1px solid #ffccc7;
        }}
        .test-status.error {{
            background: #f9f0ff;
            color: #722ed1;
            border: 1px solid #d3adf7;
        }}
        .test-status.skipped {{
            background: #fffbe6;
            color: #faad14;
            border: 1px solid #ffe58f;
        }}
        .test-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            font-size: 14px;
            color: #6c757d;
        }}
        .test-detail-item {{
            display: flex;
            align-items: center;
        }}
        .test-detail-item .label {{
            font-weight: 500;
            margin-right: 8px;
            color: #495057;
        }}
        .error-message {{
            margin-top: 12px;
            padding: 12px;
            background: #fff2f0;
            border-left: 3px solid #ff4d4f;
            border-radius: 4px;
            font-size: 13px;
            color: #722ed1;
        }}
        .steps-list {{
            margin-top: 12px;
        }}
        .step-item {{
            padding: 8px 12px;
            margin: 4px 0;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 13px;
            border-left: 3px solid #dee2e6;
        }}
        .step-item.passed {{
            border-left-color: #52c41a;
            background: #f6ffed;
        }}
        .step-item.failed {{
            border-left-color: #ff4d4f;
            background: #fff2f0;
        }}
        .verification-badge {{
            display: inline-block;
            padding: 2px 8px;
            background: #e6f7ff;
            color: #1890ff;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 8px;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #52c41a 0%, #73d13d 100%);
            transition: width 0.3s ease;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .report-container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1>📊 测试执行报告</h1>
            <div class="subtitle">{report_name}</div>
            <div class="download-buttons">
                <a href="#" class="download-btn" onclick="downloadCSV(event); return false;">
                    📥 下载CSV报告
                </a>
                <a href="#" class="download-btn" onclick="downloadJSON(event); return false;">
                    📥 下载JSON报告
                </a>
            </div>
        </div>
        
        <div class="report-meta">
            <div class="meta-item">
                <div class="label">测试运行ID</div>
                <div class="value">#{report['test_run_id']}</div>
            </div>
            <div class="meta-item">
                <div class="label">执行状态</div>
                <div class="value">
                    <span class="status-badge">{status_text_map.get(report['status'], report['status'])}</span>
                </div>
            </div>
            <div class="meta-item">
                <div class="label">开始时间</div>
                <div class="value">{start_time}</div>
            </div>
            <div class="meta-item">
                <div class="label">结束时间</div>
                <div class="value">{end_time}</div>
            </div>
            <div class="meta-item">
                <div class="label">执行时长</div>
                <div class="value">{report['duration']:.2f} 秒</div>
            </div>
            <div class="meta-item">
                <div class="label">通过率</div>
                <div class="value">{report['pass_rate']}%</div>
            </div>
        </div>
        
        <div class="stat-cards">
            <div class="stat-card total">
                <div class="label">总测试用例</div>
                <div class="value">{total}</div>
                <div class="percentage">100%</div>
            </div>
            <div class="stat-card passed">
                <div class="label">通过</div>
                <div class="value">{passed}</div>
                <div class="percentage">{passed_pct:.1f}%</div>
            </div>
            <div class="stat-card failed">
                <div class="label">失败</div>
                <div class="value">{failed}</div>
                <div class="percentage">{failed_pct:.1f}%</div>
            </div>
            <div class="stat-card skipped">
                <div class="label">跳过</div>
                <div class="value">{skipped}</div>
                <div class="percentage">{skipped_pct:.1f}%</div>
            </div>
            <div class="stat-card error">
                <div class="label">错误</div>
                <div class="value">{error}</div>
                <div class="percentage">{error_pct:.1f}%</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="charts-grid">
                <div class="chart-card">
                    <h3>📊 测试结果分布（饼图）</h3>
                    <div class="chart-container">
                        <div id="pieChart" style="width: 100%; height: 100%;"></div>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>📈 用例执行时长对比（柱状图）</h3>
                    <div class="chart-container">
                        <div id="barChart" style="width: 100%; height: 100%;"></div>
                    </div>
                </div>
            </div>
            <div class="charts-grid" style="margin-top: 20px;">
                <div class="chart-card">
                    <h3>📉 执行时长趋势（折线图）</h3>
                    <div class="chart-container">
                        <div id="lineChart" style="width: 100%; height: 100%;"></div>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>📊 执行时长分布（散点图）</h3>
                    <div class="chart-container">
                        <div id="scatterChart" style="width: 100%; height: 100%;"></div>
                    </div>
                </div>
            </div>
            <div class="chart-card" style="margin-top: 20px;">
                <h3>🎯 通过率可视化</h3>
                <div style="padding: 20px;">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {report['pass_rate']}%"></div>
                    </div>
                    <div style="text-align: center; margin-top: 12px; font-size: 24px; font-weight: 600; color: #52c41a;">
                        {report['pass_rate']}%
                    </div>
                    <div style="margin-top: 20px; text-align: center;">
                        <div style="display: inline-block; margin: 0 10px;">
                            <div style="font-size: 20px; font-weight: 600; color: #52c41a;">{passed}</div>
                            <div style="font-size: 12px; color: #6c757d;">通过</div>
                        </div>
                        <div style="display: inline-block; margin: 0 10px;">
                            <div style="font-size: 20px; font-weight: 600; color: #ff4d4f;">{failed}</div>
                            <div style="font-size: 12px; color: #6c757d;">失败</div>
                        </div>
                        <div style="display: inline-block; margin: 0 10px;">
                            <div style="font-size: 20px; font-weight: 600; color: #faad14;">{skipped}</div>
                            <div style="font-size: 12px; color: #6c757d;">跳过</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="test-results-section">
            <h2>📋 测试结果详情</h2>
"""
        
        # 添加每个测试用例的结果
        for idx, result in enumerate(report.get("test_results", []), 1):
            status = result.get("status", "unknown")
            title = html_escape(str(result.get("test_case_title", "Unknown")))
            duration = result.get("duration", 0)
            error_msg = html_escape(str(result.get("error_message", ""))) if result.get("error_message") else ""
            steps = result.get("steps", [])
            actual_result = html_escape(str(result.get("actual_result", ""))) if result.get("actual_result") else ""
            manually_verified = result.get("manually_verified", False)
            verified_by = html_escape(str(result.get("verified_by", ""))) if result.get("verified_by") else ""
            failure_reason = html_escape(str(result.get("failure_reason", ""))) if result.get("failure_reason") else ""
            bug_id = html_escape(str(result.get("bug_id", ""))) if result.get("bug_id") else ""
            
            status_upper = status.upper()
            
            html += f"""
            <div class="test-result {status}">
                <div class="test-header">
                    <div class="test-title">
                        #{idx}. {title}
                        {f'<span class="verification-badge">✓ 已手动验证</span>' if manually_verified else ''}
                    </div>
                    <span class="test-status {status}">{status_upper}</span>
                </div>
                <div class="test-details">
                    <div class="test-detail-item">
                        <span class="label">用例ID:</span>
                        <span>{result.get('test_case_id', 'N/A')}</span>
                    </div>
                    <div class="test-detail-item">
                        <span class="label">执行时长:</span>
                        <span>{duration:.2f} 秒</span>
                    </div>
                    {f'<div class="test-detail-item"><span class="label">验证人:</span><span>{verified_by}</span></div>' if verified_by else ''}
                    {f'<div class="test-detail-item"><span class="label">缺陷ID:</span><span>{bug_id}</span></div>' if bug_id else ''}
                </div>
"""
            
            if actual_result:
                html += f"""
                <div style="margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 4px;">
                    <strong style="color: #495057;">实际结果:</strong>
                    <div style="margin-top: 4px; color: #6c757d; white-space: pre-wrap;">{actual_result}</div>
                </div>
"""
            
            if steps:
                html += '<div class="steps-list"><strong style="color: #495057; display: block; margin-bottom: 8px;">测试步骤:</strong>'
                for step_idx, step in enumerate(steps, 1):
                    step_status = step.get("status", "unknown")
                    step_action = html_escape(str(step.get("action", "")))
                    step_result = html_escape(str(step.get("result", "")))
                    html += f'<div class="step-item {step_status}"><strong>步骤 {step_idx}:</strong> {step_action} - {step_result}</div>'
                html += '</div>'
            
            if error_msg:
                html += f'<div class="error-message"><strong>错误信息:</strong> {error_msg}</div>'
            
            if failure_reason:
                html += f'<div class="error-message"><strong>失败原因:</strong> {failure_reason}</div>'
            
            html += """
            </div>
"""
        
        html += f"""
        </div>
    </div>
    
    <script>
        // 饼图 - 测试结果分布
        const pieChart = echarts.init(document.getElementById('pieChart'));
        const pieOption = {{
            tooltip: {{
                trigger: 'item',
                formatter: '{{b}}: {{c}} ({{d}}%)'
            }},
            legend: {{
                orient: 'vertical',
                left: 'left',
                top: 'middle'
            }},
            series: [{{
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {{
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                }},
                label: {{
                    show: true,
                    formatter: '{{b}}\\n{{c}} ({{d}}%)'
                }},
                emphasis: {{
                    label: {{
                        show: true,
                        fontSize: 16,
                        fontWeight: 'bold'
                    }}
                }},
                data: [
                    {{ value: {passed}, name: '通过', itemStyle: {{ color: '#52c41a' }} }},
                    {{ value: {failed}, name: '失败', itemStyle: {{ color: '#ff4d4f' }} }},
                    {{ value: {skipped}, name: '跳过', itemStyle: {{ color: '#faad14' }} }},
                    {{ value: {error}, name: '错误', itemStyle: {{ color: '#722ed1' }} }}
                ]
            }}]
        }};
        pieChart.setOption(pieOption);
        
        // 柱状图 - 执行时长对比（前10个最慢的）
        const barChart = echarts.init(document.getElementById('barChart'));
        const barOption = {{
            tooltip: {{
                trigger: 'axis',
                axisPointer: {{
                    type: 'shadow'
                }},
                formatter: function(params) {{
                    return params[0].name + '<br/>' + 
                           params[0].seriesName + ': ' + params[0].value.toFixed(2) + ' 秒';
                }}
            }},
            grid: {{
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            }},
            xAxis: {{
                type: 'category',
                data: {top_duration_labels_json},
                axisLabel: {{
                    rotate: 45,
                    fontSize: 10
                }}
            }},
            yAxis: {{
                type: 'value',
                name: '执行时长(秒)',
                axisLabel: {{
                    formatter: '{{value}}s'
                }}
            }},
            series: [{{
                name: '执行时长',
                type: 'bar',
                data: {top_duration_data_json},
                itemStyle: {{
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: '#83bff6' }},
                        {{ offset: 0.5, color: '#188df0' }},
                        {{ offset: 1, color: '#188df0' }}
                    ])
                }},
                emphasis: {{
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: '#2378f7' }},
                            {{ offset: 0.7, color: '#2378f7' }},
                            {{ offset: 1, color: '#83bff6' }}
                        ])
                    }}
                }},
                animationDelay: function (idx) {{
                    return idx * 10;
                }}
            }}],
            animationEasing: 'elasticOut',
            animationDelayUpdate: function (idx) {{
                return idx * 5;
            }}
        }};
        barChart.setOption(barOption);
        
        // 折线图 - 执行时长趋势
        const lineChart = echarts.init(document.getElementById('lineChart'));
        const lineOption = {{
            tooltip: {{
                trigger: 'axis',
                formatter: function(params) {{
                    return '用例 #' + (params[0].dataIndex + 1) + '<br/>' +
                           '执行时长: ' + params[0].value.toFixed(2) + ' 秒';
                }}
            }},
            grid: {{
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            }},
            xAxis: {{
                type: 'category',
                boundaryGap: false,
                data: Array.from({{duration_data_length}}, (_, i) => '用例 ' + (i + 1))
            }},
            yAxis: {{
                type: 'value',
                name: '执行时长(秒)',
                axisLabel: {{
                    formatter: '{{value}}s'
                }}
            }},
            series: [{{
                name: '执行时长',
                type: 'line',
                smooth: true,
                data: {duration_data_json},
                areaStyle: {{
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: 'rgba(102, 126, 234, 0.3)' }},
                        {{ offset: 1, color: 'rgba(102, 126, 234, 0.1)' }}
                    ])
                }},
                lineStyle: {{
                    color: '#667eea',
                    width: 3
                }},
                itemStyle: {{
                    color: '#667eea'
                }},
                markPoint: {{
                    data: [
                        {{ type: 'max', name: '最大值' }},
                        {{ type: 'min', name: '最小值' }}
                    ]
                }},
                markLine: {{
                    data: [
                        {{ type: 'average', name: '平均值' }}
                    ]
                }}
            }}]
        }};
        lineChart.setOption(lineOption);
        
        // 散点图 - 执行时长分布
        const scatterChart = echarts.init(document.getElementById('scatterChart'));
        const scatterData = {duration_data_json}.map((value, index) => {{
            return [index, value];
        }});
        const scatterOption = {{
            tooltip: {{
                trigger: 'item',
                formatter: function(params) {{
                    return '用例 #' + (params.value[0] + 1) + '<br/>' +
                           '执行时长: ' + params.value[1].toFixed(2) + ' 秒';
                }}
            }},
            grid: {{
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            }},
            xAxis: {{
                type: 'value',
                name: '用例序号',
                nameLocation: 'middle',
                nameGap: 30
            }},
            yAxis: {{
                type: 'value',
                name: '执行时长(秒)',
                nameLocation: 'middle',
                nameGap: 50,
                axisLabel: {{
                    formatter: '{{value}}s'
                }}
            }},
            series: [{{
                name: '执行时长',
                type: 'scatter',
                data: scatterData,
                symbolSize: function(data) {{
                    return Math.sqrt(data[1]) * 2 + 5;
                }},
                itemStyle: {{
                    color: function(params) {{
                        const value = params.value[1];
                        const max = Math.max(...{duration_data_json});
                        const ratio = value / max;
                        if (ratio > 0.7) return '#ff4d4f';
                        if (ratio > 0.4) return '#faad14';
                        return '#52c41a';
                    }},
                    opacity: 0.7
                }},
                emphasis: {{
                    itemStyle: {{
                        opacity: 1,
                        borderColor: '#333',
                        borderWidth: 2
                    }}
                }}
            }}]
        }};
        scatterChart.setOption(scatterOption);
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            pieChart.resize();
            barChart.resize();
            lineChart.resize();
            scatterChart.resize();
        }});
        
        // 下载CSV报告
        function downloadCSV(event) {{
            event.preventDefault();
            const testRunId = {report['test_run_id']};
            const url = `/api/v1/test-runs/${{testRunId}}/report/csv`;
            const link = document.createElement('a');
            link.href = url;
            link.download = `test-run-${{testRunId}}-report.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
        
        // 下载JSON报告
        function downloadJSON(event) {{
            event.preventDefault();
            const testRunId = {report['test_run_id']};
            fetch(`/api/v1/test-runs/${{testRunId}}/report/json`)
                .then(response => response.json())
                .then(data => {{
                    const jsonStr = JSON.stringify(data, null, 2);
                    const blob = new Blob([jsonStr], {{ type: 'application/json' }});
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `test-run-${{testRunId}}-report.json`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }})
                .catch(error => {{
                    console.error('下载JSON报告失败:', error);
                    alert('下载JSON报告失败，请稍后重试');
                }});
        }}
    </script>
</body>
</html>
"""
        return html
    
    @staticmethod
    def generate_json_report(test_run: TestRun) -> str:
        """生成JSON格式的测试报告"""
        report = TestReportGenerator.generate_detailed_report(test_run)
        return json.dumps(report, ensure_ascii=False, indent=2, default=str)
    
    @staticmethod
    def generate_csv_report(test_run: TestRun) -> str:
        """生成CSV格式的测试报告"""
        import csv
        import io
        
        results = test_run.results or {}
        test_results = results.get("test_results", [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow([
            "测试用例ID", "测试用例标题", "状态", "执行时长(秒)", 
            "错误信息", "步骤数"
        ])
        
        # 写入数据行
        for result in test_results:
            writer.writerow([
                result.get("test_case_id", ""),
                result.get("test_case_title", ""),
                result.get("status", ""),
                result.get("duration", 0),
                result.get("error_message", ""),
                len(result.get("steps", []))
            ])
        
        return output.getvalue()


