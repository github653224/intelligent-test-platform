# 服务启动的顺序


## 1、启动后端

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2、启动AI服务

```bash
 python -m ai_engine.main
```

## 3、启动前端
```bash
cd frontend && npm start
```



测试执行模块功能已完成。以下为总结：
已完成的测试执行模块功能
1. Schemas（数据模型）
TestRunBase, TestRunCreate, TestRunUpdate, TestRunOut, TestRunDetail
TestResult 用于存储测试结果详情
2. 测试执行器（Test Executors）
APITestExecutor: 执行 API 测试，支持 Python 代码和 requests 请求
UITestExecutor: 执行 UI 测试，支持 Python 代码和 Selenium/Playwright
FunctionalTestExecutor: 功能测试执行器
TestExecutorFactory: 工厂类，根据测试类型创建对应执行器
3. 测试执行服务（Test Execution Service）
TestExecutionService: 管理测试运行的执行
异步执行测试用例
按测试类型分组执行
结果统计和存储
支持取消正在运行的测试
4. API 端点（CRUD + 执行控制）
GET /api/v1/test-runs/ - 获取测试运行列表（支持筛选）
GET /api/v1/test-runs/{id} - 获取测试运行详情
POST /api/v1/test-runs/ - 创建测试运行并开始执行
POST /api/v1/test-runs/{id}/execute - 手动触发执行
POST /api/v1/test-runs/{id}/cancel - 取消正在运行的测试
PUT /api/v1/test-runs/{id} - 更新测试运行
DELETE /api/v1/test-runs/{id} - 删除测试运行
5. 测试报告生成器（Test Report Generator）
generate_summary_report() - 摘要报告
generate_detailed_report() - 详细报告
generate_html_report() - HTML 格式报告
generate_json_report() - JSON 格式报告
generate_csv_report() - CSV 格式报告
报告 API 端点：
GET /api/v1/test-runs/{id}/report/summary - 摘要报告
GET /api/v1/test-runs/{id}/report/detailed - 详细报告
GET /api/v1/test-runs/{id}/report/html - HTML 报告
GET /api/v1/test-runs/{id}/report/json - JSON 报告
GET /api/v1/test-runs/{id}/report/csv - CSV 报告（可下载）
6. 依赖更新
添加了 aiohttp==3.9.1 到 requirements.txt（用于异步 HTTP 请求）
主要特性
支持多种测试类型：API、UI、功能测试
异步执行：后台执行，不阻塞 API
结果统计：通过、失败、跳过、错误统计
报告格式：HTML、JSON、CSV
执行控制：支持启动、取消测试运行
错误处理：异常捕获和错误信息记录
所有功能已实现并通过 lint 检查。可以开始使用测试执行模块。