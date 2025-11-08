"""
k6 性能测试结果分析服务
使用 AI 分析性能测试结果并生成专业报告
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

AI_ENGINE_URL = "http://localhost:8001"


class K6AnalysisService:
    """k6 性能测试结果分析服务"""
    
    def __init__(self):
        self.ai_engine_url = AI_ENGINE_URL
    
    def _format_duration(self, value: float) -> float:
        """
        格式化持续时间值（用于显示，单位：毫秒）
        
        根据k6的JSON输出格式，http_req_duration的值单位是**毫秒**（不是秒）。
        k6控制台显示时会标注ms，JSON中的数值就是毫秒。
        
        所以直接返回原始值（已经是毫秒），不需要转换。
        """
        if value is None or value == 0:
            return 0.0
        
        # k6的JSON输出中，http_req_duration的值单位是毫秒，直接返回
        # 如果值小于1，可能是秒（不应该出现），转换为毫秒
        if value > 0 and value < 1:
            logger.debug(f"[K6分析] 持续时间值 {value} 很小，可能是秒，转换为毫秒: {value * 1000}")
            return value * 1000
        
        # 否则，直接返回（已经是毫秒）
        return value
    
    def _convert_to_seconds(self, value: float) -> float:
        """
        将持续时间值转换为秒（用于传给AI分析）
        
        根据k6的JSON输出格式，http_req_duration的值单位是**毫秒**（不是秒）。
        k6控制台显示时会标注ms，但JSON中的数值就是毫秒。
        
        所以需要将所有http_req_duration相关的值除以1000转换为秒。
        """
        if value is None or value == 0:
            return 0.0
        
        # k6的JSON输出中，http_req_duration的值单位是毫秒，需要除以1000转换为秒
        # 根据k6官方文档和实际输出，所有http_req_duration相关的值都是毫秒
        seconds_value = value / 1000.0
        print(f"[K6分析] 转换时间单位: {value} ms -> {seconds_value} 秒")
        logger.debug(f"[K6分析] 转换时间单位: {value} ms -> {seconds_value} 秒")
        return seconds_value
    
    def _format_as_markdown_table(self, data: Dict[str, Any], key_translator=None) -> list:
        """
        将字典数据格式化为Markdown表格格式（JMeter聚合报告样式）
        
        Args:
            data: 字典数据，键为指标名称，值为指标值
            key_translator: 可选的键名翻译函数，用于将英文键名转换为中文
        
        Returns:
            list: Markdown表格行的列表，每行是一个字符串（不包含换行符）
        """
        if not data or not isinstance(data, dict):
            return []
        
        # 准备数据：收集所有指标
        metrics_data = []
        for key, value in data.items():
            # 使用翻译函数转换键名（如果提供）
            if key_translator:
                display_name = key_translator(key)
            else:
                display_name = key
            
            # 格式化数值
            if isinstance(value, str):
                # 如果已经是格式化好的字符串，直接使用
                value_str = value
            elif isinstance(value, (int, float)):
                # 如果是数字，根据键名判断单位和格式
                if "response_time" in key.lower() or "响应时间" in key:
                    # 响应时间：转换为秒，格式为 "0.258 s"
                    if value > 1000:
                        # 可能是毫秒，转换为秒
                        value_str = f"{value / 1000:.3f} s"
                    elif value > 0:
                        # 可能是秒，直接使用
                        value_str = f"{value:.3f} s"
                    else:
                        value_str = f"{value:.3f} s"
                elif "rate" in key.lower() or "速率" in key:
                    if "error" in key.lower() or "failure" in key.lower() or "失败" in key or "错误" in key:
                        value_str = f"{value * 100:.1f}%"
                    else:
                        value_str = f"{value:.2f} req/s"
                elif "count" in key.lower() or "总数" in key or "次数" in key or "请求数" in key:
                    # 总请求数：添加千位分隔符，格式为 "1,054"
                    value_str = f"{int(value):,}"
                elif "用户数" in key or "vus" in key.lower() or "并发" in key:
                    # 并发用户数：直接显示数字，格式为 "100"
                    value_str = f"{int(value)}"
                else:
                    value_str = str(value)
            else:
                value_str = str(value)
            
            metrics_data.append((display_name, value_str))
        
        if not metrics_data:
            return []
        
        # 生成表格行
        table_rows = []
        # 第一行：指标名称（表头）
        header_row = "| " + " | ".join([name for name, _ in metrics_data]) + " |"
        table_rows.append(header_row)
        
        # 第二行：分隔线（格式：| -------- | ----------- |，每个单元格的横线长度与表头单元格内容长度一致）
        separator_cells = []
        for name, _ in metrics_data:
            # 计算表头单元格内容长度（不包括前后空格和管道符）
            cell_length = len(name)
            separator_cells.append("-" * cell_length)
        separator_row = "| " + " | ".join(separator_cells) + " |"
        table_rows.append(separator_row)
        
        # 第三行：数值（数据行）
        data_row = "| " + " | ".join([value for _, value in metrics_data]) + " |"
        table_rows.append(data_row)
        
        return table_rows
    
    async def analyze_performance_results(
        self,
        performance_test_id: int,
        test_name: str,
        test_description: str,
        test_requirement: str = "",
        project_name: str = "",
        project_description: str = "",
        k6_results: Dict[str, Any] = None,
        k6_metrics: Dict[str, Any] = None,
        k6_stdout: str = None
    ) -> Dict[str, Any]:
        """
        分析性能测试结果
        
        Args:
            performance_test_id: 性能测试ID
            test_name: 测试名称
            test_description: 测试描述
            test_requirement: 测试需求（AI生成脚本时的原始需求）
            project_name: 项目名称
            project_description: 项目描述
            k6_results: k6 执行结果
            k6_metrics: k6 指标数据
        
        Returns:
            分析结果字典
        """
        try:
            # 构建分析提示词（直接使用原始执行输出）
            prompt = self._build_analysis_prompt(
                test_name, test_description, test_requirement, 
                project_name, project_description, k6_results, k6_metrics, k6_stdout
            )
            
            # 调用 AI 引擎进行分析
            print(f"\n{'='*80}")
            print(f"[K6分析] 开始分析性能测试 {performance_test_id}")
            print(f"{'='*80}\n")
            logger.info(f"[K6分析] 开始分析性能测试 {performance_test_id}")
            
            print(f"\n{'='*80}")
            print(f"[K6分析] ========== 发送给AI的完整提示词 ==========")
            print(f"[K6分析] 提示词长度: {len(prompt)} 字符")
            print(f"[K6分析] 提示词内容:\n{prompt}")
            print(f"[K6分析] ==========================================")
            print(f"{'='*80}\n")
            logger.info(f"[K6分析] ========== 发送给AI的完整提示词 ==========")
            logger.info(f"[K6分析] 提示词长度: {len(prompt)} 字符")
            logger.info(f"[K6分析] 提示词内容:\n{prompt}")
            logger.info(f"[K6分析] ==========================================")
            logger.info(f"[K6分析] AI引擎URL: {self.ai_engine_url}")
            
            # 记录关键指标数据（用于调试）
            if k6_metrics:
                http_req_duration = k6_metrics.get("http_req_duration", {})
                if http_req_duration:
                    print(f"[K6分析] 原始响应时间数据:")
                    print(f"  - avg (原始值): {http_req_duration.get('avg', 0)}")
                    print(f"  - avg (转换为秒): {self._convert_to_seconds(http_req_duration.get('avg', 0))}")
                    print(f"  - p95 (原始值): {http_req_duration.get('p95', 0)}")
                    print(f"  - p95 (转换为秒): {self._convert_to_seconds(http_req_duration.get('p95', 0))}")
                    print(f"  - max (原始值): {http_req_duration.get('max', 0)}")
                    print(f"  - max (转换为秒): {self._convert_to_seconds(http_req_duration.get('max', 0))}")
                    logger.info(f"[K6分析] 原始响应时间数据:")
                    logger.info(f"  - avg (原始值): {http_req_duration.get('avg', 0)}")
                    logger.info(f"  - avg (转换为秒): {self._convert_to_seconds(http_req_duration.get('avg', 0))}")
                    logger.info(f"  - p95 (原始值): {http_req_duration.get('p95', 0)}")
                    logger.info(f"  - p95 (转换为秒): {self._convert_to_seconds(http_req_duration.get('p95', 0))}")
                    logger.info(f"  - max (原始值): {http_req_duration.get('max', 0)}")
                    logger.info(f"  - max (转换为秒): {self._convert_to_seconds(http_req_duration.get('max', 0))}")
            
            # AI引擎的正确端点是 /analyze_requirement（注意是下划线，不是连字符，且没有/api前缀）
            ai_endpoint = f"{self.ai_engine_url}/analyze_requirement"
            logger.info(f"[K6分析] 调用端点: {ai_endpoint}")
            
            async with httpx.AsyncClient() as client:
                try:
                    request_payload = {
                        "requirement_text": prompt,
                        "project_context": f"性能测试结果分析 - 测试ID: {performance_test_id}",
                        "test_focus": ["性能指标", "瓶颈分析", "优化建议"]
                    }
                    print(f"\n{'='*80}")
                    print(f"[K6分析] ========== 发送给AI的请求参数 ==========")
                    print(f"[K6分析] 请求URL: {ai_endpoint}")
                    print(f"[K6分析] requirement_text长度: {len(prompt)} 字符")
                    print(f"[K6分析] project_context: {request_payload['project_context']}")
                    print(f"[K6分析] test_focus: {request_payload['test_focus']}")
                    print(f"[K6分析] ==========================================")
                    print(f"{'='*80}\n")
                    logger.info(f"[K6分析] ========== 发送给AI的请求参数 ==========")
                    logger.info(f"[K6分析] 请求URL: {ai_endpoint}")
                    logger.info(f"[K6分析] requirement_text长度: {len(prompt)} 字符")
                    logger.info(f"[K6分析] project_context: {request_payload['project_context']}")
                    logger.info(f"[K6分析] test_focus: {request_payload['test_focus']}")
                    logger.info(f"[K6分析] ==========================================")
                    
                    response = await client.post(
                        ai_endpoint,
                        json=request_payload,
                        timeout=120.0
                    )
                    response.raise_for_status()
                    ai_result = response.json()
                    logger.info(f"[K6分析] AI引擎响应状态码: {response.status_code}")
                except httpx.HTTPStatusError as e:
                    logger.error(f"[K6分析] AI引擎HTTP错误: {e.response.status_code} - {e.response.text}")
                    raise
                except httpx.RequestError as e:
                    logger.error(f"[K6分析] AI引擎请求错误: {e}")
                    raise
                
                print(f"\n{'='*80}")
                print(f"[K6分析] ========== AI引擎返回的完整结果 ==========")
                print(f"[K6分析] 返回结果类型: {type(ai_result)}")
                print(f"[K6分析] 返回结果完整内容:\n{json.dumps(ai_result, ensure_ascii=False, indent=2)}")
                print(f"[K6分析] ==========================================")
                print(f"{'='*80}\n")
                logger.info(f"[K6分析] ========== AI引擎返回的完整结果 ==========")
                logger.info(f"[K6分析] 返回结果类型: {type(ai_result)}")
                logger.info(f"[K6分析] 返回结果完整内容:\n{json.dumps(ai_result, ensure_ascii=False, indent=2)}")
                logger.info(f"[K6分析] ==========================================")
                
                # 提取分析内容
                if isinstance(ai_result, dict):
                    # 尝试多种方式获取分析数据
                    analysis_data = ai_result.get("analysis") or ai_result.get("data") or ai_result
                    
                    # 如果analysis_data是字符串，尝试解析（可能是Python字典字符串或JSON字符串）
                    if isinstance(analysis_data, str):
                        logger.info(f"[K6分析] ========== 分析数据是字符串，开始解析 ==========")
                        logger.info(f"[K6分析] 字符串长度: {len(analysis_data)} 字符")
                        logger.info(f"[K6分析] 字符串前500字符:\n{analysis_data[:500]}")
                        logger.info(f"[K6分析] 字符串后500字符:\n{analysis_data[-500:]}")
                        logger.info(f"[K6分析] ==========================================")
                        
                        # 先尝试ast.literal_eval（适用于Python字典字符串，如 {'key': 'value'}）
                        try:
                            import ast
                            analysis_data = ast.literal_eval(analysis_data)
                            logger.info(f"[K6分析] ✅ 使用ast.literal_eval解析成功，类型: {type(analysis_data)}")
                            if isinstance(analysis_data, dict):
                                logger.info(f"[K6分析] 解析后的数据键: {list(analysis_data.keys())}")
                                # 检查关键指标摘要中的响应时间
                                key_metrics = analysis_data.get("关键指标摘要") or analysis_data.get("key_metrics_summary")
                                if key_metrics and isinstance(key_metrics, dict):
                                    logger.info(f"[K6分析] ⚠️ 关键指标摘要中的响应时间值:")
                                    logger.info(f"  - 平均响应时间: {key_metrics.get('平均响应时间')} (类型: {type(key_metrics.get('平均响应时间'))})")
                                    logger.info(f"  - P95响应时间: {key_metrics.get('P95响应时间')} (类型: {type(key_metrics.get('P95响应时间'))})")
                                    logger.info(f"  - 最大响应时间: {key_metrics.get('最大响应时间')} (类型: {type(key_metrics.get('最大响应时间'))})")
                        except (ValueError, SyntaxError) as e:
                            logger.warning(f"[K6分析] ast.literal_eval解析失败: {e}")
                            # 再尝试JSON解析（需要将单引号替换为双引号）
                            try:
                                # 替换单引号为双引号，但要注意字符串中的单引号
                                json_str = analysis_data.replace("'", '"')
                                # 处理布尔值和None
                                json_str = json_str.replace('True', 'true').replace('False', 'false').replace('None', 'null')
                                analysis_data = json.loads(json_str)
                                logger.info(f"[K6分析] ✅ 使用json.loads解析成功")
                                if isinstance(analysis_data, dict):
                                    logger.info(f"[K6分析] 解析后的数据键: {list(analysis_data.keys())}")
                                    # 检查关键指标摘要中的响应时间
                                    key_metrics = analysis_data.get("关键指标摘要") or analysis_data.get("key_metrics_summary")
                                    if key_metrics and isinstance(key_metrics, dict):
                                        logger.info(f"[K6分析] ⚠️ 关键指标摘要中的响应时间值:")
                                        logger.info(f"  - 平均响应时间: {key_metrics.get('平均响应时间')} (类型: {type(key_metrics.get('平均响应时间'))})")
                                        logger.info(f"  - P95响应时间: {key_metrics.get('P95响应时间')} (类型: {type(key_metrics.get('P95响应时间'))})")
                                        logger.info(f"  - 最大响应时间: {key_metrics.get('最大响应时间')} (类型: {type(key_metrics.get('最大响应时间'))})")
                            except (json.JSONDecodeError, AttributeError) as e2:
                                logger.warning(f"[K6分析] json.loads解析失败: {e2}")
                                # 如果都失败了，尝试更智能的解析
                                try:
                                    # 使用eval（不安全，但作为最后手段）
                                    import ast
                                    # 再次尝试ast.literal_eval，但先清理字符串
                                    cleaned = analysis_data.strip()
                                    if cleaned.startswith('{') and cleaned.endswith('}'):
                                        analysis_data = ast.literal_eval(cleaned)
                                        logger.info(f"[K6分析] ✅ 清理后使用ast.literal_eval解析成功")
                                    else:
                                        raise ValueError("不是有效的字典格式")
                                except Exception as e3:
                                    logger.error(f"[K6分析] 所有解析方法都失败: {e3}")
                                    analysis_data = {"raw_analysis": analysis_data}
                    
                    # 确保analysis_data是字典类型
                    if not isinstance(analysis_data, dict):
                        logger.warning(f"[K6分析] 分析数据不是字典类型: {type(analysis_data)}，转换为字典")
                        analysis_data = {"raw_analysis": str(analysis_data)}
                    
                    # 检查是否有嵌套的Analysis字段（AI引擎可能返回嵌套结构）
                    if isinstance(analysis_data, dict):
                        # 如果analysis_data中有"Analysis"字段，尝试提取它
                        if "Analysis" in analysis_data:
                            logger.info(f"[K6分析] 发现Analysis字段，尝试提取")
                            analysis_content = analysis_data.get("Analysis")
                            
                            # 如果Analysis是字符串，尝试解析其中的JSON
                            if isinstance(analysis_content, str):
                                # 尝试从字符串中提取JSON对象
                                import re
                                # 查找JSON对象（可能包含在代码块中）
                                json_match = re.search(r'```json\s*(\{.*?\})\s*```', analysis_content, re.DOTALL)
                                if json_match:
                                    try:
                                        parsed_json = json.loads(json_match.group(1))
                                        logger.info(f"[K6分析] ✅ 从Analysis字符串中提取JSON成功")
                                        # 将解析的JSON合并到analysis_data中
                                        analysis_data.update(parsed_json)
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"[K6分析] 解析Analysis中的JSON失败: {e}")
                                
                                # 尝试直接解析整个Analysis字符串为JSON
                                if isinstance(analysis_data.get("Analysis"), str):
                                    try:
                                        # 尝试解析为JSON（如果整个字符串是JSON）
                                        parsed = json.loads(analysis_content)
                                        if isinstance(parsed, dict):
                                            logger.info(f"[K6分析] ✅ Analysis字符串是JSON，解析成功")
                                            analysis_data.update(parsed)
                                    except json.JSONDecodeError:
                                        pass
                            
                            # 如果Analysis是字典，直接合并
                            elif isinstance(analysis_content, dict):
                                logger.info(f"[K6分析] Analysis字段是字典，直接合并")
                                analysis_data.update(analysis_content)
                        
                        # 尝试从Analysis文本中提取结构化数据
                        if "Analysis" in analysis_data and isinstance(analysis_data.get("Analysis"), str):
                            analysis_text = analysis_data.get("Analysis")
                            # 尝试解析文本中的结构化数据
                            parsed_data = self._parse_analysis_text(analysis_text)
                            if parsed_data:
                                logger.info(f"[K6分析] 从Analysis文本中提取到结构化数据，键: {list(parsed_data.keys())[:5]}")
                                # 合并解析的数据
                                analysis_data.update(parsed_data)
                                # 移除原始的Analysis字段（如果已经解析成功）
                                if parsed_data:
                                    del analysis_data["Analysis"]
                        
                        # 移除不应该显示在报告中的字段
                        excluded_fields = {
                            "requirement_text", "Requirement Text", "Status", "status",
                            "test_focus", "filename", "test_focus", "Test Focus", "Analysis"
                        }
                        for field in excluded_fields:
                            if field in analysis_data:
                                logger.info(f"[K6分析] 移除不应该显示的字段: {field}")
                                del analysis_data[field]
                    
                    # 检查分析数据是否为空
                    if not analysis_data or (isinstance(analysis_data, dict) and len(analysis_data) == 0):
                        logger.warning(f"[K6分析] 分析数据为空，使用原始AI结果")
                        analysis_data = ai_result if isinstance(ai_result, dict) else {"raw_analysis": str(ai_result)}
                    
                    logger.info(f"[K6分析] 分析数据类型: {type(analysis_data)}, 长度: {len(analysis_data) if isinstance(analysis_data, (dict, list, str)) else 'N/A'}")
                    if isinstance(analysis_data, dict):
                        logger.info(f"[K6分析] 分析数据顶层键: {list(analysis_data.keys())[:10]}")
                    elif isinstance(analysis_data, str):
                        logger.info(f"[K6分析] 分析数据是字符串，前200字符: {analysis_data[:200]}")
                    
                    # 格式化分析结果
                    logger.info(f"[K6分析] ========== 开始格式化分析结果 ==========")
                    logger.info(f"[K6分析] 分析数据类型: {type(analysis_data)}")
                    if isinstance(analysis_data, dict):
                        logger.info(f"[K6分析] 分析数据键: {list(analysis_data.keys())}")
                        # 检查关键指标摘要
                        key_metrics = analysis_data.get("关键指标摘要") or analysis_data.get("key_metrics_summary")
                        if key_metrics:
                            logger.info(f"[K6分析] ⚠️ 格式化前 - 关键指标摘要内容:")
                            logger.info(f"{json.dumps(key_metrics, ensure_ascii=False, indent=2)}")
                    formatted_analysis = self._format_analysis_result(
                        analysis_data, k6_metrics
                    )
                    
                    logger.info(f"[K6分析] 格式化后的分析结果类型: {type(formatted_analysis)}, 长度: {len(formatted_analysis) if isinstance(formatted_analysis, dict) else 'N/A'}")
                    if isinstance(formatted_analysis, dict):
                        logger.info(f"[K6分析] 格式化后的结果键: {list(formatted_analysis.keys())[:10]}")
                        if "markdown" in formatted_analysis:
                            logger.info(f"[K6分析] ✅ Markdown已生成，长度: {len(formatted_analysis['markdown'])} 字符")
                            logger.info(f"[K6分析] Markdown前1000字符:\n{formatted_analysis['markdown'][:1000]}")
                        else:
                            logger.warning(f"[K6分析] ⚠️ Markdown字段不存在")
                    logger.info(f"[K6分析] ==========================================")
                    
                    return {
                        "status": "success",
                        "analysis": formatted_analysis,
                        "generated_at": datetime.utcnow().isoformat()
                    }
                else:
                    logger.warning(f"[K6分析] AI结果不是字典类型，使用原始结果")
                    return {
                        "status": "success",
                        "analysis": {"raw_analysis": str(ai_result)},
                        "generated_at": datetime.utcnow().isoformat()
                    }
                    
        except httpx.RequestError as e:
            logger.error(f"[K6分析] AI引擎请求失败: {e}")
            return {
                "status": "error",
                "error": f"AI分析服务暂时不可用: {str(e)}。请检查AI引擎是否运行在 {self.ai_engine_url}",
                "generated_at": datetime.utcnow().isoformat()
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"[K6分析] AI引擎响应错误: {e.response.status_code} - {e.response.text}")
            error_detail = f"AI分析服务错误: {e.response.status_code}"
            try:
                error_body = e.response.json()
                if "detail" in error_body:
                    error_detail += f" - {error_body['detail']}"
            except:
                error_detail += f" - {e.response.text[:200]}"
            return {
                "status": "error",
                "error": error_detail,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"分析性能测试结果失败: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    def _parse_analysis_text(self, analysis_text: str) -> Dict[str, Any]:
        """从Analysis文本中提取结构化数据"""
        import re
        parsed_data = {}
        
        if not analysis_text or not isinstance(analysis_text, str):
            return parsed_data
        
        try:
            # 辅助函数：提取JSON对象（支持跨行和代码块）
            def extract_json(text, start_pos=0):
                """从文本中提取JSON对象"""
                text_slice = text[start_pos:]
                
                # 先尝试从代码块中提取（支持多行JSON）
                json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', text_slice, re.DOTALL)
                if json_block_match:
                    try:
                        json_str = json_block_match.group(1).strip()
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # 如果代码块中的JSON解析失败，继续尝试其他方法
                        pass
                
                # 尝试找到第一个 { 的位置，然后找到匹配的 }
                brace_start = text_slice.find('{')
                if brace_start == -1:
                    return None
                
                # 从第一个 { 开始，找到匹配的 }
                brace_count = 0
                brace_end = -1
                in_string = False
                escape_next = False
                
                for i in range(brace_start, len(text_slice)):
                    char = text_slice[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                brace_end = i + 1
                                break
                
                if brace_end > brace_start:
                    json_str = text_slice[brace_start:brace_end]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        logger.debug(f"[K6分析] JSON解析失败: {e}, 内容: {json_str[:100]}")
                        pass
                
                return None
            
            # 辅助函数：提取到下一个标题之前的内容
            def extract_until_next_section(text, start_pos):
                """提取到下一个主要标题之前的内容"""
                # 查找下一个主要标题（以大写字母开头，后面跟冒号或减号）
                next_section = re.search(r'\n\s*(?:-?\s*\*\*)?([A-Z][a-zA-Z\s]+?)[:\-]', text[start_pos:])
                if next_section:
                    return text[start_pos:start_pos + next_section.start()].strip()
                return text[start_pos:].strip()
            
            # 1. 提取Performance Rating（支持中英文）
            rating_match = re.search(r'(?:Performance Rating|性能评级)[:\-]?\s*([^\n]+)', analysis_text, re.IGNORECASE)
            if rating_match:
                rating_value = rating_match.group(1).strip()
                # 同时保存到两个键名，确保兼容性
                parsed_data["performance_rating"] = rating_value
                parsed_data["性能评级"] = rating_value
            
            # 2. 提取Key Metrics Summary（支持中英文）
            metrics_start = re.search(r'(?:Key Metrics Summary|关键指标摘要)[:\-]?\s*', analysis_text, re.IGNORECASE)
            if metrics_start:
                start_pos = metrics_start.end()
                # 尝试提取JSON（包括代码块中的JSON）
                json_data = extract_json(analysis_text, start_pos)
                if json_data:
                    # 同时保存到两个键名，确保兼容性
                    parsed_data["key_metrics_summary"] = json_data
                    parsed_data["关键指标摘要"] = json_data
                    logger.debug(f"[K6分析] 成功提取key_metrics_summary: {list(json_data.keys())}")
                else:
                    # 提取到下一个标题之前的内容
                    content = extract_until_next_section(analysis_text, start_pos)
                    if content:
                        # 清理内容，移除代码块标记
                        content_cleaned = content.strip()
                        # 如果包含代码块，提取其中的JSON
                        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', content_cleaned, re.DOTALL)
                        if json_block_match:
                            try:
                                parsed_json = json.loads(json_block_match.group(1))
                                parsed_data["key_metrics_summary"] = parsed_json
                                parsed_data["关键指标摘要"] = parsed_json
                                logger.debug(f"[K6分析] 从代码块中解析key_metrics_summary成功")
                            except json.JSONDecodeError:
                                # 如果代码块解析失败，尝试直接解析整个内容
                                if content_cleaned.startswith('{'):
                                    try:
                                        parsed_json = json.loads(content_cleaned)
                                        parsed_data["key_metrics_summary"] = parsed_json
                                        parsed_data["关键指标摘要"] = parsed_json
                                    except json.JSONDecodeError:
                                        parsed_data["key_metrics_summary"] = content
                                        parsed_data["关键指标摘要"] = content
                                else:
                                    parsed_data["key_metrics_summary"] = content
                                    parsed_data["关键指标摘要"] = content
                        elif content_cleaned.startswith('{'):
                            try:
                                parsed_json = json.loads(content_cleaned)
                                parsed_data["key_metrics_summary"] = parsed_json
                                parsed_data["关键指标摘要"] = parsed_json
                                logger.debug(f"[K6分析] 从字符串中解析key_metrics_summary成功")
                            except json.JSONDecodeError:
                                parsed_data["key_metrics_summary"] = content
                                parsed_data["关键指标摘要"] = content
                        else:
                            parsed_data["key_metrics_summary"] = content
                            parsed_data["关键指标摘要"] = content
            
            # 3. 提取Response Time Analysis（支持中英文）
            response_time_start = re.search(r'(?:-?\s*\*\*)?(?:Response Time Analysis|响应时间分析)[:\-]?\s*\*\*?[:\-]?\s*', analysis_text, re.IGNORECASE)
            if response_time_start:
                start_pos = response_time_start.end()
                # 尝试提取JSON
                json_data = extract_json(analysis_text, start_pos)
                if json_data:
                    parsed_data["response_time_analysis"] = json_data
                    parsed_data["响应时间分析"] = json_data
                    logger.debug(f"[K6分析] 成功提取response_time_analysis: {list(json_data.keys())}")
                else:
                    # 提取到下一个标题之前的内容
                    content = extract_until_next_section(analysis_text, start_pos)
                    if content:
                        # 如果内容包含JSON代码块，尝试提取
                        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                        if json_block_match:
                            try:
                                parsed_json = json.loads(json_block_match.group(1))
                                parsed_data["response_time_analysis"] = parsed_json
                                parsed_data["响应时间分析"] = parsed_json
                                logger.debug(f"[K6分析] 从代码块中解析response_time_analysis成功")
                            except json.JSONDecodeError:
                                parsed_data["response_time_analysis"] = content
                                parsed_data["响应时间分析"] = content
                        elif content.strip().startswith('{'):
                            try:
                                parsed_json = json.loads(content.strip())
                                parsed_data["response_time_analysis"] = parsed_json
                                parsed_data["响应时间分析"] = parsed_json
                                logger.debug(f"[K6分析] 从字符串中解析response_time_analysis成功")
                            except json.JSONDecodeError:
                                parsed_data["response_time_analysis"] = content
                                parsed_data["响应时间分析"] = content
                        else:
                            parsed_data["response_time_analysis"] = content
                            parsed_data["响应时间分析"] = content
            
            # 4. 提取Throughput Analysis（支持中英文）
            throughput_start = re.search(r'(?:Throughput Analysis|吞吐量分析)[:\-]?\s*', analysis_text, re.IGNORECASE)
            if throughput_start:
                start_pos = throughput_start.end()
                json_data = extract_json(analysis_text, start_pos)
                if json_data:
                    parsed_data["throughput_analysis"] = json_data
                    parsed_data["吞吐量分析"] = json_data
                else:
                    content = extract_until_next_section(analysis_text, start_pos)
                    if content:
                        parsed_data["throughput_analysis"] = content
                        parsed_data["吞吐量分析"] = content
            
            # 5. 提取Stability Analysis（支持中英文）
            stability_start = re.search(r'(?:-?\s*\*\*)?(?:Stability Analysis|稳定性分析)[:\-]?\s*\*\*?[:\-]?\s*', analysis_text, re.IGNORECASE)
            if stability_start:
                start_pos = stability_start.end()
                json_data = extract_json(analysis_text, start_pos)
                if json_data:
                    parsed_data["stability_analysis"] = json_data
                    parsed_data["稳定性分析"] = json_data
                    logger.debug(f"[K6分析] 成功提取stability_analysis: {list(json_data.keys())}")
                else:
                    content = extract_until_next_section(analysis_text, start_pos)
                    if content:
                        # 如果内容包含JSON代码块，尝试提取
                        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                        if json_block_match:
                            try:
                                parsed_json = json.loads(json_block_match.group(1))
                                parsed_data["stability_analysis"] = parsed_json
                                parsed_data["稳定性分析"] = parsed_json
                                logger.debug(f"[K6分析] 从代码块中解析stability_analysis成功")
                            except json.JSONDecodeError:
                                parsed_data["stability_analysis"] = content
                                parsed_data["稳定性分析"] = content
                        elif content.strip().startswith('{'):
                            try:
                                parsed_json = json.loads(content.strip())
                                parsed_data["stability_analysis"] = parsed_json
                                parsed_data["稳定性分析"] = parsed_json
                                logger.debug(f"[K6分析] 从字符串中解析stability_analysis成功")
                            except json.JSONDecodeError:
                                parsed_data["stability_analysis"] = content
                                parsed_data["稳定性分析"] = content
                        else:
                            parsed_data["stability_analysis"] = content
                            parsed_data["稳定性分析"] = content
            
            # 6. 提取Optimization Recommendations（支持中英文）
            opt_start = re.search(r'(?:Optimization Recommendations?|优化建议)[:\-]?\s*', analysis_text, re.IGNORECASE)
            if opt_start:
                start_pos = opt_start.end()
                # 尝试提取JSON数组
                array_match = re.search(r'\[\s*(\{.*?\})\s*\]', analysis_text[start_pos:], re.DOTALL)
                if array_match:
                    try:
                        # 尝试解析整个数组
                        full_array_match = re.search(r'\[.*?\]', analysis_text[start_pos:], re.DOTALL)
                        if full_array_match:
                            parsed_array = json.loads(full_array_match.group(0))
                            parsed_data["optimization_recommendations"] = parsed_array
                            parsed_data["优化建议"] = parsed_array
                    except json.JSONDecodeError:
                        # 如果解析失败，尝试逐项解析
                        items = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_text[start_pos:], re.DOTALL)
                        recommendations = []
                        for item in items:
                            try:
                                recommendations.append(json.loads(item))
                            except json.JSONDecodeError:
                                pass
                        if recommendations:
                            parsed_data["optimization_recommendations"] = recommendations
                            parsed_data["优化建议"] = recommendations
            
            # 7. 提取Risk Assessment（支持中英文）
            risk_start = re.search(r'(?:-?\s*\*\*)?(?:Risk Assessment|风险评估)[:\-]?\s*\*\*?[:\-]?\s*', analysis_text, re.IGNORECASE)
            if risk_start:
                start_pos = risk_start.end()
                json_data = extract_json(analysis_text, start_pos)
                if json_data:
                    parsed_data["risk_assessment"] = json_data
                    parsed_data["风险评估"] = json_data
                    logger.debug(f"[K6分析] 成功提取risk_assessment: {list(json_data.keys())}")
                else:
                    content = extract_until_next_section(analysis_text, start_pos)
                    if content:
                        # 如果内容包含JSON代码块，尝试提取
                        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                        if json_block_match:
                            try:
                                parsed_json = json.loads(json_block_match.group(1))
                                parsed_data["risk_assessment"] = parsed_json
                                parsed_data["风险评估"] = parsed_json
                                logger.debug(f"[K6分析] 从代码块中解析risk_assessment成功")
                            except json.JSONDecodeError:
                                parsed_data["risk_assessment"] = content
                                parsed_data["风险评估"] = content
                        elif content.strip().startswith('{'):
                            try:
                                parsed_json = json.loads(content.strip())
                                parsed_data["risk_assessment"] = parsed_json
                                parsed_data["风险评估"] = parsed_json
                                logger.debug(f"[K6分析] 从字符串中解析risk_assessment成功")
                            except json.JSONDecodeError:
                                parsed_data["risk_assessment"] = content
                                parsed_data["风险评估"] = content
                        else:
                            parsed_data["risk_assessment"] = content
                            parsed_data["风险评估"] = content
            
            # 8. 提取Capacity Planning（支持中英文）
            capacity_start = re.search(r'(?:Capacity Planning|容量规划)[:\-]?\s*', analysis_text, re.IGNORECASE)
            if capacity_start:
                start_pos = capacity_start.end()
                json_data = extract_json(analysis_text, start_pos)
                if json_data:
                    parsed_data["capacity_planning"] = json_data
                    parsed_data["容量规划"] = json_data
                else:
                    content = extract_until_next_section(analysis_text, start_pos)
                    if content:
                        parsed_data["capacity_planning"] = content
                        parsed_data["容量规划"] = content
            
            logger.info(f"[K6分析] 从Analysis文本中解析出 {len(parsed_data)} 个字段: {list(parsed_data.keys())}")
        except Exception as e:
            logger.warning(f"[K6分析] 解析Analysis文本时出错: {e}", exc_info=True)
        
        return parsed_data
    
    def _build_analysis_prompt(
        self,
        test_name: str,
        test_description: str,
        test_requirement: str = "",
        project_name: str = "",
        project_description: str = "",
        k6_results: Dict[str, Any] = None,
        k6_metrics: Dict[str, Any] = None,
        k6_stdout: str = None
    ) -> str:
        """构建分析提示词"""
        
        if k6_metrics is None:
            k6_metrics = {}
        if k6_results is None:
            k6_results = {}
        
        # 提取关键指标
        http_req_duration = k6_metrics.get("http_req_duration", {})
        http_req_failed = k6_metrics.get("http_req_failed", {})
        http_reqs = k6_metrics.get("http_reqs", {})
        iterations = k6_metrics.get("iterations", {})
        vus = k6_metrics.get("vus", {})
        
        # 如果有原始执行输出，直接使用原始输出
        if k6_stdout:
            prompt = f"""
请分析以下 k6 性能测试结果，并提供专业的性能分析报告：

## 项目信息
- 项目名称: {project_name if project_name else "未指定"}
{f"- 项目描述: {project_description}" if project_description else ""}

## 测试信息
- 测试名称: {test_name}
- 测试描述: {test_description}
{f"- 测试需求: {test_requirement}" if test_requirement else ""}

## k6 执行输出（原始数据）
以下是 k6 性能测试的完整执行输出，请直接基于这些原始数据进行分析：

```
{k6_stdout}
```

## 完整指标数据（JSON格式）
{json.dumps(k6_metrics, indent=2, ensure_ascii=False)}

## 分析要求
请提供以下分析内容(以JSON格式返回，便于程序解析)：

1. **性能评估**：
   - 整体性能评级（优秀/良好/一般/较差/差）
   - 关键指标是否达标
   - 性能瓶颈识别

2. **响应时间分析**：
   - 响应时间分布情况
   - 是否存在异常值
   - 响应时间趋势分析

3. **吞吐量分析**：
   - 系统吞吐量评估
   - 并发处理能力
   - 资源利用率

4. **稳定性分析**：
   - 错误率分析
   - 系统稳定性评估
   - 异常情况识别

5. **优化建议**：
   - 性能优化建议（按优先级排序）
   - 系统改进方向
   - 配置调优建议

6. **风险评估**：
   - 性能风险点
   - 潜在问题预警
   - 容量规划建议

请以结构化的JSON格式返回分析结果，**重要：所有JSON键名必须使用中文**，包含以下字段：

- **性能评级** (performance_rating): 性能评级（优秀/良好/一般/较差/差）
- **关键指标摘要** (key_metrics_summary): 包含总请求数、请求速率、错误率、平均响应时间、最大响应时间、P95响应时间、并发用户数等关键指标。**重要：所有数值必须带上单位，例如"总请求数: 1054 次"、"平均响应时间: 0.258 秒"、"请求速率: 36.53 req/s"、"并发用户数: 100 个"。响应时间使用秒为单位（如0.258秒），不要使用毫秒。**
- **响应时间分析** (response_time_analysis): 包含响应时间分布、异常值分析、趋势分析等
- **吞吐量分析** (throughput_analysis): 包含吞吐量评估、并发处理能力、资源利用率等
- **稳定性分析** (stability_analysis): 包含错误率、系统稳定性评估、异常情况等
- **优化建议** (optimization_recommendations): 优化建议列表，每个建议包含优先级（high/medium/low）和建议内容
- **风险评估** (risk_assessment): 包含性能风险、潜在问题、预警信息等
- **容量规划** (capacity_planning): 包含当前容量、推荐容量、扩展策略等

**JSON格式要求：**
1. 所有键名必须使用中文（如：性能评级、关键指标摘要、响应时间分析等）
2. 所有值的内容也必须是中文
3. 优化建议列表中的每个建议对象，键名也要使用中文（如：优先级、建议内容）
4. 确保返回的JSON格式正确，便于程序解析

示例JSON结构：
```json
{{
  "性能评级": "优秀",
  "关键指标摘要": {{
    "总请求数": "1054 次",
    "请求速率": "36.53 req/s",
    "错误率": "0.0%",
    "平均响应时间": "0.258 秒",
    "最大响应时间": "0.470 秒",
    "P95响应时间": "0.307 秒",
    "并发用户数": "100 个"
  }},
  "响应时间分析": {{
    "响应时间分布": "描述文本",
    "异常值分析": "描述文本",
    "趋势分析": "描述文本"
  }},
  "优化建议": [
    {{
      "优先级": "high",
      "建议内容": "优化建议文本"
    }}
  ]
}}
```

请严格按照上述要求返回JSON格式的分析结果。
"""
        else:
            # 如果没有原始输出，使用格式化后的数据
            prompt = f"""
请分析以下 k6 性能测试结果，并提供专业的性能分析报告：

## 项目信息
- 项目名称: {project_name if project_name else "未指定"}
{f"- 项目描述: {project_description}" if project_description else ""}

## 测试信息
- 测试名称: {test_name}
- 测试描述: {test_description}
{f"- 测试需求: {test_requirement}" if test_requirement else ""}

## 性能指标数据

### HTTP 请求指标
- 请求总数: {http_reqs.get('count', 0)} 次
- 请求速率: {http_reqs.get('rate', 0):.2f} req/s
- 请求失败数: {http_req_failed.get('count', 0)} 次
- 失败率: {http_req_failed.get('rate', 0) * 100:.2f}%

### 响应时间指标
- 平均响应时间: {self._convert_to_seconds(http_req_duration.get('avg', 0)):.3f} 秒
- 最小响应时间: {self._convert_to_seconds(http_req_duration.get('min', 0)):.3f} 秒
- 最大响应时间: {self._convert_to_seconds(http_req_duration.get('max', 0)):.3f} 秒
- 中位数响应时间: {self._convert_to_seconds(http_req_duration.get('med', 0)):.3f} 秒
- P90响应时间: {self._convert_to_seconds(http_req_duration.get('p90', 0)):.3f} 秒
- P95响应时间: {self._convert_to_seconds(http_req_duration.get('p95', 0)):.3f} 秒
- P99响应时间: {self._convert_to_seconds(http_req_duration.get('p99', 0)):.3f} 秒

### 负载指标
- 虚拟用户数: {vus.get('max', 0)} 个
- 迭代次数: {iterations.get('count', 0)} 次
- 迭代速率: {iterations.get('rate', 0):.2f} iter/s

## 完整指标数据（JSON格式）
{json.dumps(k6_metrics, indent=2, ensure_ascii=False)}

## 分析要求
请提供以下分析内容(以JSON格式返回，便于程序解析)：

1. **性能评估**：
   - 整体性能评级（优秀/良好/一般/较差/差）
   - 关键指标是否达标
   - 性能瓶颈识别

2. **响应时间分析**：
   - 响应时间分布情况
   - 是否存在异常值
   - 响应时间趋势分析

3. **吞吐量分析**：
   - 系统吞吐量评估
   - 并发处理能力
   - 资源利用率

4. **稳定性分析**：
   - 错误率分析
   - 系统稳定性评估
   - 异常情况识别

5. **优化建议**：
   - 性能优化建议（按优先级排序）
   - 系统改进方向
   - 配置调优建议

6. **风险评估**：
   - 性能风险点
   - 潜在问题预警
   - 容量规划建议

请以结构化的JSON格式返回分析结果，**重要：所有JSON键名必须使用中文**，包含以下字段：

- **性能评级** (performance_rating): 性能评级（优秀/良好/一般/较差/差）
- **关键指标摘要** (key_metrics_summary): 包含总请求数、请求速率、错误率、平均响应时间、最大响应时间、P95响应时间、并发用户数等关键指标。**重要：所有数值必须带上单位，例如"总请求数: 1054 次"、"平均响应时间: 0.258 秒"、"请求速率: 36.53 req/s"、"并发用户数: 100 个"。响应时间使用秒为单位（如0.258秒），不要使用毫秒。**
- **响应时间分析** (response_time_analysis): 包含响应时间分布、异常值分析、趋势分析等
- **吞吐量分析** (throughput_analysis): 包含吞吐量评估、并发处理能力、资源利用率等
- **稳定性分析** (stability_analysis): 包含错误率、系统稳定性评估、异常情况等
- **优化建议** (optimization_recommendations): 优化建议列表，每个建议包含优先级（high/medium/low）和建议内容
- **风险评估** (risk_assessment): 包含性能风险、潜在问题、预警信息等
- **容量规划** (capacity_planning): 包含当前容量、推荐容量、扩展策略等

**JSON格式要求：**
1. 所有键名必须使用中文（如：性能评级、关键指标摘要、响应时间分析等）
2. 所有值的内容也必须是中文
3. 优化建议列表中的每个建议对象，键名也要使用中文（如：优先级、建议内容）
4. 确保返回的JSON格式正确，便于程序解析

示例JSON结构：
```json
{{
  "性能评级": "优秀",
  "关键指标摘要": {{
    "总请求数": "1054 次",
    "请求速率": "36.53 req/s",
    "错误率": "0.0%",
    "平均响应时间": "0.258 秒",
    "最大响应时间": "0.470 秒",
    "P95响应时间": "0.307 秒",
    "并发用户数": "100 个"
  }},
  "响应时间分析": {{
    "响应时间分布": "描述文本",
    "异常值分析": "描述文本",
    "趋势分析": "描述文本"
  }},
  "优化建议": [
    {{
      "优先级": "high",
      "建议内容": "优化建议文本"
    }}
  ]
}}
```

请严格按照上述要求返回JSON格式的分析结果。
"""
        return prompt
    
    def _format_analysis_result(
        self,
        analysis_data: Dict[str, Any],
        k6_metrics: Dict[str, Any],
        test_name: str = "",
        test_description: str = "",
        test_requirement: str = "",
        project_name: str = "",
        project_description: str = ""
    ) -> Dict[str, Any]:
        """格式化分析结果"""
        
        logger.info(f"[K6分析] 格式化分析结果，输入数据类型: {type(analysis_data)}")
        
        # 如果analysis_data是空字典，返回一个默认结构
        if not analysis_data or (isinstance(analysis_data, dict) and len(analysis_data) == 0):
            logger.warning(f"[K6分析] 分析数据为空，返回默认结构")
            return {
                "error": "AI分析结果为空，可能是AI引擎未返回有效数据",
                "test_name": test_name,
                "test_description": test_description,
                "test_requirement": test_requirement,
                "project_name": project_name,
                "project_description": project_description,
                "key_metrics": {
                    "http_req_duration": k6_metrics.get("http_req_duration", {}),
                    "http_req_failed": k6_metrics.get("http_req_failed", {}),
                    "http_reqs": k6_metrics.get("http_reqs", {}),
                    "iterations": k6_metrics.get("iterations", {}),
                    "vus": k6_metrics.get("vus", {}),
                },
                "formatted_at": datetime.utcnow().isoformat()
            }
        
        formatted = {
            "test_name": test_name,
            "test_description": test_description,
            "test_requirement": test_requirement,
            "project_name": project_name,
            "project_description": project_description,
            "key_metrics": {
                "http_req_duration": k6_metrics.get("http_req_duration", {}),
                "http_req_failed": k6_metrics.get("http_req_failed", {}),
                "http_reqs": k6_metrics.get("http_reqs", {}),
                "iterations": k6_metrics.get("iterations", {}),
                "vus": k6_metrics.get("vus", {}),
            },
            "formatted_at": datetime.utcnow().isoformat()
        }
        
        # 如果分析数据是字符串，尝试解析为字典
        if isinstance(analysis_data, str):
            logger.info(f"[K6分析] 分析数据是字符串，尝试解析为字典")
            try:
                import ast
                parsed_data = ast.literal_eval(analysis_data)
                if isinstance(parsed_data, dict):
                    logger.info(f"[K6分析] ✅ 字符串解析为字典成功，键: {list(parsed_data.keys())[:5]}")
                    analysis_data = parsed_data
                else:
                    logger.warning(f"[K6分析] 解析后不是字典类型: {type(parsed_data)}")
            except Exception as e:
                logger.warning(f"[K6分析] 字符串解析失败: {e}，将作为原始文本处理")
        
        # 如果分析数据是字典，合并到formatted中
        if isinstance(analysis_data, dict):
            # 再次检查并解析Analysis字段（以防之前的解析没有成功）
            if "Analysis" in analysis_data and isinstance(analysis_data.get("Analysis"), str):
                logger.info(f"[K6分析] 在格式化阶段发现Analysis字段，尝试解析")
                analysis_text = analysis_data.get("Analysis")
                parsed_data = self._parse_analysis_text(analysis_text)
                if parsed_data:
                    logger.info(f"[K6分析] ✅ 成功解析Analysis字段，提取到 {len(parsed_data)} 个字段: {list(parsed_data.keys())}")
                    # 合并解析的数据到analysis_data
                    analysis_data.update(parsed_data)
                    # 删除Analysis字段
                    del analysis_data["Analysis"]
                else:
                    logger.warning(f"[K6分析] ⚠️ 解析Analysis字段失败，将保留原始字段")
            
            # 移除不应该显示在报告中的字段
            excluded_fields = {
                "requirement_text", "Requirement Text", "Status", "status",
                "test_focus", "filename", "Test Focus", "Analysis"
            }
            for field in excluded_fields:
                if field in analysis_data:
                    logger.info(f"[K6分析] 移除不应该显示的字段: {field}")
                    del analysis_data[field]
            
            # 先添加原始分析数据
            formatted["raw_analysis"] = analysis_data.copy()
            # 然后更新formatted，让分析数据覆盖默认值
            formatted.update(analysis_data)
            
            # 生成Markdown格式的分析报告
            logger.info(f"[K6分析] 开始生成Markdown，数据键: {list(analysis_data.keys())[:10]}")
            markdown_report = self._format_as_markdown(
                analysis_data, 
                k6_metrics,
                test_name=test_name,
                test_description=test_description,
                test_requirement=test_requirement,
                project_name=project_name,
                project_description=project_description
            )
            formatted["markdown"] = markdown_report
            logger.info(f"[K6分析] Markdown生成完成，长度: {len(markdown_report)}")
        elif isinstance(analysis_data, str):
            # 如果是字符串且无法解析，保存为raw_analysis
            formatted["raw_analysis"] = analysis_data
            # 尝试将字符串作为Markdown（可能是AI直接返回的Markdown）
            formatted["markdown"] = analysis_data
        else:
            # 其他类型，转换为字符串
            formatted["raw_analysis"] = str(analysis_data)
            formatted["markdown"] = str(analysis_data)
        
        logger.info(f"[K6分析] 格式化完成，结果键: {list(formatted.keys())}")
        
        return formatted
    
    def _format_as_markdown(
        self, 
        analysis_data: Dict[str, Any], 
        k6_metrics: Dict[str, Any],
        test_name: str = "",
        test_description: str = "",
        test_requirement: str = "",
        project_name: str = "",
        project_description: str = ""
    ) -> str:
        """将分析结果格式化为Markdown格式"""
        markdown_parts = []
        content_sections_added = 0  # 跟踪实际内容部分的数量
        
        logger.info(f"[K6分析-Markdown] 开始格式化，数据键: {list(analysis_data.keys())[:10]}")
        
        # 键名到中文的映射
        key_to_chinese = {
            # 关键指标摘要
            "total_requests": "总请求数",
            "request_rate": "请求速率 (req/s)",
            "error_rate": "错误率 (%)",
            "failure_rate": "失败率 (%)",
            "avg_response_time": "平均响应时间 (ms)",
            "max_response_time": "最大响应时间 (ms)",
            "p95_response_time": "P95响应时间 (ms)",
            "p90_response_time": "P90响应时间 (ms)",
            "concurrent_users": "并发用户数",
            "virtual_users": "虚拟用户数",
            "iterations": "迭代次数",
            # 响应时间分析
            "distribution": "响应时间分布",
            "outliers": "异常值分析",
            "trend": "趋势分析",
            "percentile_analysis": "百分位分析",
            "issues": "问题分析",
            # 吞吐量分析
            "throughput_evaluation": "吞吐量评估",
            "concurrent_capability": "并发处理能力",
            "concurrency_capability": "并发处理能力",
            "resource_utilization": "资源利用率",
            # 稳定性分析
            "error_rate": "错误率",
            "stability_evaluation": "稳定性评估",
            "system_stability": "系统稳定性",
            "abnormal_conditions": "异常情况",
            # 风险评估
            "performance_risks": "性能风险",
            "potential_issues": "潜在问题",
            "early_warnings": "预警信息",
            "capacity_warning": "容量警告",
            "critical_concerns": "关键关注点",
            # 容量规划
            "current_capacity": "当前容量",
            "recommended_capacity": "推荐容量",
            "scaling_recommendations": "扩展建议",
            "scaling_strategy": "扩展策略",
            "capacity_targets": "容量目标",
        }
        
        def get_chinese_key(key: str) -> str:
            """获取键名的中文翻译"""
            # 如果键名已经是中文，直接返回
            if any('\u4e00' <= char <= '\u9fff' for char in key):
                return key
            # 否则从映射表中查找，如果找不到则使用英文格式
            return key_to_chinese.get(key, key.replace("_", " ").title())
        
        def is_chinese_key(key: str) -> bool:
            """判断键名是否是中文"""
            return any('\u4e00' <= char <= '\u9fff' for char in key)
        
        # 添加报告头部信息
        markdown_parts.append("# 📊 性能测试分析报告\n")
        markdown_parts.append("\n")
        
        # 项目信息
        if project_name:
            markdown_parts.append("## 📁 项目信息\n")
            markdown_parts.append(f"- **项目名称**: {project_name}")
            if project_description:
                markdown_parts.append(f"- **项目描述**: {project_description}")
            markdown_parts.append("\n")
        
        # 测试信息
        markdown_parts.append("## 🧪 测试信息\n")
        if test_name:
            markdown_parts.append(f"- **测试名称**: {test_name}")
        if test_description:
            markdown_parts.append(f"- **测试描述**: {test_description}")
        if test_requirement:
            markdown_parts.append(f"- **测试需求**: {test_requirement}")
        markdown_parts.append("\n")
        
        markdown_parts.append("---\n")
        markdown_parts.append("\n")
        
        # 辅助函数：格式化值（处理嵌套结构）
        def format_value(value, indent=0):
            """递归格式化值"""
            indent_str = "  " * indent
            if isinstance(value, dict):
                result = []
                for k, v in value.items():
                    # 格式化键名（将下划线转换为空格，首字母大写）
                    key_display = k.replace("_", " ").title()
                    formatted_v = format_value(v, indent + 1)
                    result.append(f"{indent_str}- **{key_display}**: {formatted_v}")
                return "\n".join(result)
            elif isinstance(value, list):
                result = []
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        formatted_item = format_value(item, indent + 1)
                        result.append(f"{indent_str}{i}. {formatted_item}")
                    else:
                        result.append(f"{indent_str}{i}. {item}")
                return "\n".join(result)
            else:
                return str(value)
        
        # 1. 性能评估（支持中文和英文键名）
        rating = analysis_data.get("performance_rating") or analysis_data.get("性能评级")
        if rating:
            content_sections_added += 1
            # 根据评级添加表情符号
            rating_emoji = {
                "优秀": "🟢",
                "良好": "🟡",
                "一般": "🟠",
                "较差": "🔴",
                "差": "🔴"
            }.get(rating, "📊")
            markdown_parts.append(f"## {rating_emoji} 性能评估\n")
            markdown_parts.append(f"**整体评级**: {rating}\n")
            markdown_parts.append("\n")
        
        # 2. 关键指标摘要（支持中文和英文键名）- 使用JMeter聚合报告样式的表格格式（2行多列）
        summary = analysis_data.get("key_metrics_summary") or analysis_data.get("关键指标摘要")
        if summary:
            content_sections_added += 1
            markdown_parts.append("## 📈 关键指标摘要\n")
            if isinstance(summary, dict):
                # 使用公共方法生成表格
                table_rows = self._format_as_markdown_table(summary, key_translator=get_chinese_key)
                for row in table_rows:
                    markdown_parts.append(row)
            elif isinstance(summary, str):
                markdown_parts.append(summary)
            markdown_parts.append("\n")
        
        # 3. 响应时间分析（支持中文和英文键名）
        analysis = analysis_data.get("response_time_analysis") or analysis_data.get("响应时间分析")
        if analysis:
            content_sections_added += 1
            markdown_parts.append("## ⏱️ 响应时间分析\n")
            if isinstance(analysis, dict):
                for key, value in analysis.items():
                    display_name = get_chinese_key(key)
                    if isinstance(value, (dict, list)):
                        markdown_parts.append(f"- **{display_name}**:\n  {json.dumps(value, ensure_ascii=False, indent=2)}")
                    else:
                        markdown_parts.append(f"- **{display_name}**: {value}")
            elif isinstance(analysis, str):
                markdown_parts.append(analysis)
            markdown_parts.append("\n")
        
        # 4. 吞吐量分析（支持中文和英文键名）
        analysis = analysis_data.get("throughput_analysis") or analysis_data.get("吞吐量分析")
        if analysis:
            content_sections_added += 1
            markdown_parts.append("## 🚀 吞吐量分析\n")
            if isinstance(analysis, dict):
                for key, value in analysis.items():
                    display_name = get_chinese_key(key)
                    markdown_parts.append(f"- **{display_name}**: {value}")
            elif isinstance(analysis, str):
                markdown_parts.append(analysis)
            markdown_parts.append("\n")
        
        # 5. 稳定性分析（支持中文和英文键名）
        analysis = analysis_data.get("stability_analysis") or analysis_data.get("稳定性分析")
        if analysis:
            content_sections_added += 1
            markdown_parts.append("## 🔒 稳定性分析\n")
            if isinstance(analysis, dict):
                for key, value in analysis.items():
                    display_name = get_chinese_key(key)
                    if isinstance(value, (dict, list)):
                        markdown_parts.append(f"- **{display_name}**:\n  {json.dumps(value, ensure_ascii=False, indent=2)}")
                    else:
                        markdown_parts.append(f"- **{display_name}**: {value}")
            elif isinstance(analysis, str):
                markdown_parts.append(analysis)
            markdown_parts.append("\n")
        
        # 6. 优化建议（支持中文和英文键名）
        recommendations = analysis_data.get("optimization_recommendations") or analysis_data.get("优化建议")
        if recommendations:
            content_sections_added += 1
            markdown_parts.append("## 💡 优化建议\n")
            if isinstance(recommendations, list):
                for i, rec in enumerate(recommendations, 1):
                    if isinstance(rec, dict):
                        # 支持中文和英文键名
                        priority = rec.get("priority") or rec.get("优先级", "")
                        suggestion = rec.get("suggestion") or rec.get("recommendation") or rec.get("建议内容", "")
                        # 如果 suggestion 是字典字符串，尝试解析
                        if isinstance(suggestion, str) and suggestion.strip().startswith('{'):
                            try:
                                import ast
                                parsed_suggestion = ast.literal_eval(suggestion)
                                if isinstance(parsed_suggestion, dict):
                                    suggestion = parsed_suggestion.get("recommendation", parsed_suggestion.get("suggestion", suggestion))
                            except:
                                pass
                        # 优先级表情符号
                        priority_emoji = {
                            "high": "🔴",
                            "medium": "🟡",
                            "low": "🟢"
                        }.get(priority.lower(), "•")
                        markdown_parts.append(f"{i}. {priority_emoji} **{suggestion}**\n")
                        if priority:
                            priority_cn = {"high": "高", "medium": "中", "low": "低"}.get(priority.lower(), priority)
                            markdown_parts.append(f"   - 优先级: {priority_cn}\n")
                    elif isinstance(rec, str):
                        # 如果 rec 是字典字符串，尝试解析
                        if rec.strip().startswith('{'):
                            try:
                                import ast
                                parsed_rec = ast.literal_eval(rec)
                                if isinstance(parsed_rec, dict):
                                    # 支持中文和英文键名
                                    priority = parsed_rec.get("priority") or parsed_rec.get("优先级", "")
                                    suggestion = parsed_rec.get("recommendation") or parsed_rec.get("suggestion") or parsed_rec.get("建议内容", "")
                                    priority_emoji = {
                                        "high": "🔴",
                                        "medium": "🟡",
                                        "low": "🟢"
                                    }.get(priority.lower(), "•")
                                    markdown_parts.append(f"{i}. {priority_emoji} **{suggestion}**\n")
                                    if priority:
                                        priority_cn = {"high": "高", "medium": "中", "low": "低"}.get(priority.lower(), priority)
                                        markdown_parts.append(f"   - 优先级: {priority_cn}\n")
                                else:
                                    markdown_parts.append(f"{i}. {rec}\n")
                            except:
                                markdown_parts.append(f"{i}. {rec}\n")
                        else:
                            markdown_parts.append(f"{i}. {rec}\n")
            elif isinstance(recommendations, str):
                markdown_parts.append(recommendations)
            markdown_parts.append("\n")
        
        # 7. 风险评估（支持中文和英文键名）
        risks = analysis_data.get("risk_assessment") or analysis_data.get("风险评估")
        if risks:
            content_sections_added += 1
            markdown_parts.append("## ⚠️ 风险评估\n")
            if isinstance(risks, dict):
                for key, value in risks.items():
                    display_name = get_chinese_key(key)
                    if isinstance(value, list):
                        markdown_parts.append(f"### {display_name}\n")
                        for item in value:
                            markdown_parts.append(f"- {item}")
                    elif isinstance(value, (dict, list)):
                        markdown_parts.append(f"- **{display_name}**:\n  {json.dumps(value, ensure_ascii=False, indent=2)}")
                    else:
                        markdown_parts.append(f"- **{display_name}**: {value}")
            elif isinstance(risks, str):
                markdown_parts.append(risks)
            markdown_parts.append("\n")
        
        # 8. 容量规划建议（支持中文和英文键名）
        planning = analysis_data.get("capacity_planning") or analysis_data.get("容量规划")
        if planning:
            content_sections_added += 1
            markdown_parts.append("## 📋 容量规划建议\n")
            if isinstance(planning, dict):
                for key, value in planning.items():
                    display_name = get_chinese_key(key)
                    markdown_parts.append(f"- **{display_name}**: {value}")
            elif isinstance(planning, str):
                markdown_parts.append(planning)
            markdown_parts.append("\n")
        
        # 9. 如果没有找到结构化数据，尝试提取其他字段
        # 首先检查是否有"analysis"字段（可能是嵌套的分析数据）
        if content_sections_added == 0 and "analysis" in analysis_data:
            ai_analysis = analysis_data.get("analysis", "")
            # 如果analysis是字符串（可能是Python字典字符串），尝试解析
            if isinstance(ai_analysis, str) and ai_analysis.strip().startswith('{'):
                try:
                    import ast
                    parsed_analysis = ast.literal_eval(ai_analysis)
                    if isinstance(parsed_analysis, dict):
                        logger.info(f"[K6分析-Markdown] 从analysis字符串解析出字典，重新格式化")
                        # 递归调用_format_as_markdown，使用解析后的字典
                        return self._format_as_markdown(
                            parsed_analysis, k6_metrics, test_name, test_description,
                            test_requirement, project_name, project_description
                        )
                except Exception as e:
                    logger.warning(f"[K6分析-Markdown] 解析analysis字符串失败: {e}")
            
            # 如果analysis是字符串但不是字典格式，直接使用
            if isinstance(ai_analysis, str) and ai_analysis.strip():
                content_sections_added += 1
                markdown_parts.append("## 📝 AI分析结果\n")
                markdown_parts.append(ai_analysis)
                markdown_parts.append("\n")
        
        # 10. 如果仍然没有内容部分，尝试处理 Analysis 字段（如果存在）
        if content_sections_added == 0 and "Analysis" in analysis_data:
            analysis_content = analysis_data.get("Analysis")
            if isinstance(analysis_content, str):
                logger.info(f"[K6分析-Markdown] 尝试从Analysis字段中提取结构化数据")
                # 尝试解析 Analysis 文本
                parsed_from_analysis = self._parse_analysis_text(analysis_content)
                if parsed_from_analysis:
                    logger.info(f"[K6分析-Markdown] ✅ 从Analysis字段解析出 {len(parsed_from_analysis)} 个字段")
                    # 合并解析的数据
                    analysis_data.update(parsed_from_analysis)
                    # 删除 Analysis 字段
                    del analysis_data["Analysis"]
                    # 递归调用，使用解析后的数据重新格式化
                    return self._format_as_markdown(
                        analysis_data, k6_metrics, test_name, test_description,
                        test_requirement, project_name, project_description
                    )
                else:
                    # 如果解析失败，尝试直接格式化 Analysis 内容中的 JSON 代码块
                    logger.warning(f"[K6分析-Markdown] 解析Analysis字段失败，尝试直接格式化JSON代码块")
                    # 提取所有 JSON 代码块并格式化为 Markdown
                    json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', analysis_content, re.DOTALL)
                    if json_blocks:
                        content_sections_added += 1
                        # 提取 Performance Rating（支持中英文）
                        rating_match = re.search(r'(?:Performance Rating|性能评级)[:\-]?\s*([^\n]+)', analysis_content, re.IGNORECASE)
                        if rating_match:
                            rating = rating_match.group(1).strip()
                            markdown_parts.append(f"## 🔴 性能评估\n")
                            markdown_parts.append(f"**整体评级**: {rating}\n")
                            markdown_parts.append("\n")
                        
                        # 使用集合跟踪已添加的部分，避免重复
                        added_sections = set()
                        
                        # 处理每个 JSON 块
                        for json_str in json_blocks:
                            try:
                                json_data = json.loads(json_str)
                                # 根据 JSON 的键名判断应该放在哪个部分（支持中英文键名）
                                has_metrics_keys = any(k in json_data for k in ["total_requests", "request_rate", "总请求数", "请求速率"])
                                if has_metrics_keys and "key_metrics_summary" not in added_sections:
                                    added_sections.add("key_metrics_summary")
                                    markdown_parts.append("## 📈 关键指标摘要\n")
                                    # 使用JMeter聚合报告样式：收集所有指标数据
                                    metrics_data = []
                                    for key, value in json_data.items():
                                        key_display = get_chinese_key(key)
                                        # 格式化数值
                                        # 如果值已经是字符串（AI返回的格式，包含单位），直接使用
                                        if isinstance(value, str):
                                            value_str = value
                                        elif isinstance(value, (int, float)):
                                            if "response_time" in key.lower() or "响应时间" in key or "time" in key.lower():
                                                # 响应时间：转换为秒，格式为 "0.258 s"
                                                if value > 1000:
                                                    # 值太大，可能是毫秒，转换为秒显示
                                                    value_str = f"{value / 1000:.3f} s"
                                                elif value > 0:
                                                    # 可能是秒，直接使用
                                                    value_str = f"{value:.3f} s"
                                                else:
                                                    value_str = f"{value:.3f} s"
                                            elif "rate" in key.lower() or "速率" in key:
                                                if "error" in key.lower() or "failure" in key.lower() or "失败" in key or "错误" in key:
                                                    value_str = f"{value * 100:.1f}%"
                                                else:
                                                    value_str = f"{value:.2f} req/s"
                                            elif "count" in key.lower() or "总数" in key or "次数" in key or "请求数" in key:
                                                # 总请求数：添加千位分隔符，格式为 "1,054"
                                                value_str = f"{int(value):,}"
                                            elif "用户数" in key or "vus" in key.lower() or "并发" in key:
                                                # 并发用户数：直接显示数字，格式为 "100"
                                                value_str = f"{int(value)}"
                                            else:
                                                value_str = str(value)
                                        else:
                                            value_str = str(value)
                                        metrics_data.append((key_display, value_str))
                                    
                                    # 使用JMeter聚合报告样式：第一行是指标名称，第二行是数值
                                    if metrics_data:
                                        # 构建字典数据，使用公共方法生成表格
                                        metrics_dict = {name: value for name, value in metrics_data}
                                        table_rows = self._format_as_markdown_table(metrics_dict)
                                        for row in table_rows:
                                            markdown_parts.append(row)
                                    markdown_parts.append("\n")
                                elif any(k in json_data for k in ["distribution", "outliers", "trend", "响应时间分布", "异常值分析", "趋势分析"]) and "response_time_analysis" not in added_sections:
                                    added_sections.add("response_time_analysis")
                                    markdown_parts.append("## ⏱️ 响应时间分析\n")
                                    for key, value in json_data.items():
                                        key_display = get_chinese_key(key)
                                        markdown_parts.append(f"- **{key_display}**: {value}\n")
                                    markdown_parts.append("\n")
                                elif any(k in json_data for k in ["throughput_evaluation", "concurrent_capability", "concurrency_capability", "吞吐量评估", "并发处理能力"]) and "throughput_analysis" not in added_sections:
                                    added_sections.add("throughput_analysis")
                                    markdown_parts.append("## 🚀 吞吐量分析\n")
                                    for key, value in json_data.items():
                                        key_display = get_chinese_key(key)
                                        markdown_parts.append(f"- **{key_display}**: {value}\n")
                                    markdown_parts.append("\n")
                                elif any(k in json_data for k in ["error_rate", "stability_evaluation", "system_stability", "错误率", "稳定性评估", "系统稳定性"]) and "stability_analysis" not in added_sections:
                                    added_sections.add("stability_analysis")
                                    markdown_parts.append("## 🔒 稳定性分析\n")
                                    for key, value in json_data.items():
                                        key_display = get_chinese_key(key)
                                        markdown_parts.append(f"- **{key_display}**: {value}\n")
                                    markdown_parts.append("\n")
                                elif any(k in json_data for k in ["performance_risks", "potential_issues", "性能风险", "潜在问题"]) and "risk_assessment" not in added_sections:
                                    added_sections.add("risk_assessment")
                                    markdown_parts.append("## ⚠️ 风险评估\n")
                                    for key, value in json_data.items():
                                        key_display = get_chinese_key(key)
                                        if isinstance(value, list):
                                            markdown_parts.append(f"### {key_display}\n")
                                            for item in value:
                                                markdown_parts.append(f"- {item}\n")
                                        else:
                                            markdown_parts.append(f"- **{key_display}**: {value}\n")
                                    markdown_parts.append("\n")
                                elif any(k in json_data for k in ["current_capacity", "recommended_capacity", "scaling_strategy", "当前容量", "推荐容量", "扩展策略"]) and "capacity_planning" not in added_sections:
                                    added_sections.add("capacity_planning")
                                    markdown_parts.append("## 📋 容量规划建议\n")
                                    for key, value in json_data.items():
                                        key_display = get_chinese_key(key)
                                        markdown_parts.append(f"- **{key_display}**: {value}\n")
                                    markdown_parts.append("\n")
                            except json.JSONDecodeError:
                                continue
                        
                        # 处理优化建议（可能是数组格式，支持中英文）
                        opt_array_match = re.search(r'(?:Optimization Recommendations?|优化建议)[:\-]?\s*(\[.*?\])', analysis_content, re.DOTALL | re.IGNORECASE)
                        if opt_array_match and "optimization_recommendations" not in added_sections:
                            try:
                                opt_array_str = opt_array_match.group(1)
                                opt_array = json.loads(opt_array_str)
                                if isinstance(opt_array, list) and len(opt_array) > 0 and isinstance(opt_array[0], dict):
                                    added_sections.add("optimization_recommendations")
                                    markdown_parts.append("## 💡 优化建议\n")
                                    for i, rec in enumerate(opt_array, 1):
                                        if isinstance(rec, dict):
                                            # 支持中文和英文键名
                                            priority = rec.get("priority") or rec.get("优先级", "")
                                            suggestion = rec.get("recommendation") or rec.get("suggestion") or rec.get("建议内容", "")
                                            priority_emoji = {
                                                "high": "🔴",
                                                "medium": "🟡",
                                                "low": "🟢"
                                            }.get(priority.lower(), "•")
                                            markdown_parts.append(f"{i}. {priority_emoji} **{suggestion}**\n")
                                            if priority:
                                                priority_cn = {"high": "高", "medium": "中", "low": "低"}.get(priority.lower(), priority)
                                                markdown_parts.append(f"   - 优先级: {priority_cn}\n")
                                    markdown_parts.append("\n")
                            except (json.JSONDecodeError, AttributeError):
                                pass
        
        # 11. 如果仍然没有内容部分，提取所有可用数据
        if content_sections_added == 0:
            logger.warning(f"[K6分析-Markdown] ⚠️ 没有找到结构化数据，尝试提取所有字段。analysis_data键: {list(analysis_data.keys())[:20]}")
            
            # 排除元数据字段
            excluded_keys = {
                "raw_analysis", "test_name", "test_description", "test_requirement",
                "project_name", "project_description", "key_metrics", "formatted_at",
                "markdown", "Analysis"  # 避免递归
            }
            
            # 提取所有非元数据的字段
            data_to_display = {
                k: v for k, v in analysis_data.items() 
                if k not in excluded_keys and v is not None and v != ""
            }
            
            if data_to_display:
                content_sections_added += 1
                markdown_parts.append("## 📊 性能分析结果\n")
                markdown_parts.append("\n")
                
                # 添加关键指标（如果有）- 使用JMeter聚合报告样式的表格格式（2行多列）
                if k6_metrics:
                    markdown_parts.append("### 📈 关键指标\n")
                    
                    # 收集所有指标数据
                    metrics_names = []
                    metrics_values = []
                    
                    http_req_duration = k6_metrics.get("http_req_duration", {})
                    if http_req_duration:
                        # k6的JSON输出中，http_req_duration的值单位是毫秒
                        # 直接使用原始值（已经是毫秒），不需要转换
                        avg_duration_raw = http_req_duration.get("avg", 0)
                        p95_duration_raw = http_req_duration.get("p95", 0)
                        min_duration_raw = http_req_duration.get("min", 0)
                        max_duration_raw = http_req_duration.get("max", 0)
                        
                        print(f"[K6分析-关键指标] 原始值: avg={avg_duration_raw}, p95={p95_duration_raw}, min={min_duration_raw}, max={max_duration_raw}")
                        
                        # k6返回的值已经是毫秒，直接使用
                        # 如果值异常大（>100000），可能是被错误转换了，需要修复
                        avg_duration = avg_duration_raw
                        p95_duration = p95_duration_raw
                        min_duration = min_duration_raw
                        max_duration = max_duration_raw
                        
                        # 如果值异常大（>100000），可能是被错误转换了，除以1000修复
                        if avg_duration > 100000:
                            print(f"[K6分析-关键指标] ⚠️ avg值异常大({avg_duration})，除以1000修复")
                            avg_duration = avg_duration / 1000
                        if p95_duration > 100000:
                            print(f"[K6分析-关键指标] ⚠️ p95值异常大({p95_duration})，除以1000修复")
                            p95_duration = p95_duration / 1000
                        if min_duration > 100000:
                            print(f"[K6分析-关键指标] ⚠️ min值异常大({min_duration})，除以1000修复")
                            min_duration = min_duration / 1000
                        if max_duration > 100000:
                            print(f"[K6分析-关键指标] ⚠️ max值异常大({max_duration})，除以1000修复")
                            max_duration = max_duration / 1000
                        
                        print(f"[K6分析-关键指标] 最终值: avg={avg_duration:.2f} ms, p95={p95_duration:.2f} ms")
                        
                        # 响应时间转换为秒，格式为 "0.258 s"
                        metrics_names.extend(["平均响应时间", "最小响应时间", "最大响应时间", "P95响应时间"])
                        metrics_values.extend([
                            f"{avg_duration / 1000:.3f} s",
                            f"{min_duration / 1000:.3f} s",
                            f"{max_duration / 1000:.3f} s",
                            f"{p95_duration / 1000:.3f} s"
                        ])
                    
                    http_req_failed = k6_metrics.get("http_req_failed", {})
                    if http_req_failed:
                        failure_rate = http_req_failed.get("rate", 0) * 100
                        metrics_names.append("错误率")
                        metrics_values.append(f"{failure_rate:.1f}%")
                    
                    http_reqs = k6_metrics.get("http_reqs", {})
                    if http_reqs:
                        total_requests = http_reqs.get("count", 0)
                        req_rate = http_reqs.get("rate", 0)
                        metrics_names.extend(["总请求数", "请求速率"])
                        metrics_values.extend([
                            f"{total_requests:,}",  # 添加千位分隔符，格式为 "1,054"
                            f"{req_rate:.2f} req/s"
                        ])
                    
                    vus = k6_metrics.get("vus", {})
                    if vus:
                        max_vus = vus.get("max", 0)
                        metrics_names.append("并发用户数")
                        metrics_values.append(f"{max_vus}")  # 直接显示数字，格式为 "100"
                    
                    # 使用JMeter聚合报告样式：第一行是指标名称，第二行是数值
                    if metrics_names:
                        # 构建字典数据，使用公共方法生成表格
                        metrics_dict = dict(zip(metrics_names, metrics_values))
                        table_rows = self._format_as_markdown_table(metrics_dict)
                        for row in table_rows:
                            markdown_parts.append(row)
                    
                    markdown_parts.append("\n")
                
                # 格式化并显示所有可用数据
                markdown_parts.append("### 📋 详细分析\n")
                markdown_parts.append("\n")
                
                for key, value in data_to_display.items():
                    # 跳过包含提示词内容的字段
                    if isinstance(value, str):
                        # 检查是否包含不应该显示的内容
                        excluded_keywords = [
                            "完整指标数据", "分析要求", "请分析以下", "请提供以下",
                            "requirement_text", "Requirement Text", "完整指标数据"
                        ]
                        if any(keyword in value for keyword in excluded_keywords):
                            logger.info(f"[K6分析-Markdown] 跳过包含提示词的字段: {key}")
                            continue
                        
                        # 如果值是包含 JSON 代码块的字符串，尝试解析并格式化
                        if "```json" in value:
                            # 尝试从字符串中提取并解析 JSON，然后格式化为 Markdown
                            json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', value, re.DOTALL)
                            if json_blocks:
                                # 如果成功提取到 JSON，格式化显示
                                for json_str in json_blocks:
                                    try:
                                        json_data = json.loads(json_str)
                                        # 根据 JSON 结构格式化
                                        if isinstance(json_data, dict):
                                            for json_key, json_value in json_data.items():
                                                json_key_display = get_chinese_key(json_key)
                                                # 特殊处理"关键指标摘要"，使用表格格式
                                                if json_key in ["key_metrics_summary", "关键指标摘要"] and isinstance(json_value, dict):
                                                    markdown_parts.append("## 📈 关键指标摘要\n")
                                                    # 使用公共方法生成表格
                                                    table_rows = self._format_as_markdown_table(json_value, key_translator=get_chinese_key)
                                                    for row in table_rows:
                                                        markdown_parts.append(row)
                                                    markdown_parts.append("\n")
                                                    continue
                                                elif isinstance(json_value, (dict, list)):
                                                    markdown_parts.append(f"- **{json_key_display}**:\n")
                                                    if isinstance(json_value, dict):
                                                        for nested_key, nested_value in json_value.items():
                                                            nested_key_display = get_chinese_key(nested_key)
                                                            markdown_parts.append(f"  - **{nested_key_display}**: {nested_value}\n")
                                                    else:
                                                        for i, item in enumerate(json_value, 1):
                                                            markdown_parts.append(f"  {i}. {item}\n")
                                                else:
                                                    markdown_parts.append(f"- **{json_key_display}**: {json_value}\n")
                                        elif isinstance(json_data, list):
                                            # 检查是否是优化建议列表（支持中英文键名）
                                            has_opt_keys = len(json_data) > 0 and isinstance(json_data[0], dict) and any(k in json_data[0] for k in ["priority", "recommendation", "suggestion", "优先级", "建议内容"])
                                            if has_opt_keys:
                                                markdown_parts.append("## 💡 优化建议\n")
                                                for i, item in enumerate(json_data, 1):
                                                    if isinstance(item, dict):
                                                        # 支持中文和英文键名
                                                        priority = item.get("priority") or item.get("优先级", "")
                                                        suggestion = item.get("recommendation") or item.get("suggestion") or item.get("建议内容", "")
                                                        priority_emoji = {
                                                            "high": "🔴",
                                                            "medium": "🟡",
                                                            "low": "🟢"
                                                        }.get(priority.lower(), "•")
                                                        markdown_parts.append(f"{i}. {priority_emoji} **{suggestion}**\n")
                                                        if priority:
                                                            priority_cn = {"high": "高", "medium": "中", "low": "低"}.get(priority.lower(), priority)
                                                            markdown_parts.append(f"   - 优先级: {priority_cn}\n")
                                                markdown_parts.append("\n")
                                            else:
                                                for i, item in enumerate(json_data, 1):
                                                    if isinstance(item, dict):
                                                        for item_key, item_value in item.items():
                                                            item_key_display = get_chinese_key(item_key)
                                                            markdown_parts.append(f"{i}. **{item_key_display}**: {item_value}\n")
                                                    else:
                                                        markdown_parts.append(f"{i}. {item}\n")
                                    except json.JSONDecodeError:
                                        # 如果解析失败，跳过这个 JSON 块
                                        continue
                                continue
                    
                    # 格式化键名（使用中文）
                    key_display = get_chinese_key(key)
                    
                    # 特殊处理某些字段（支持中英文键名）
                    if key in ["optimization_recommendations", "优化建议"] and isinstance(value, list):
                        markdown_parts.append("## 💡 优化建议\n")
                        for i, item in enumerate(value, 1):
                            if isinstance(item, dict):
                                # 支持中文和英文键名
                                priority = item.get("priority") or item.get("优先级", "")
                                suggestion = item.get("recommendation") or item.get("suggestion") or item.get("建议内容", "")
                                priority_emoji = {
                                    "high": "🔴",
                                    "medium": "🟡",
                                    "low": "🟢"
                                }.get(priority.lower(), "•")
                                markdown_parts.append(f"{i}. {priority_emoji} **{suggestion}**\n")
                                if priority:
                                    priority_cn = {"high": "高", "medium": "中", "low": "低"}.get(priority.lower(), priority)
                                    markdown_parts.append(f"   - 优先级: {priority_cn}\n")
                        markdown_parts.append("\n")
                    elif isinstance(value, dict):
                        # 根据键名判断应该放在哪个部分（支持中英文键名）
                        if key in ["key_metrics_summary", "关键指标摘要"]:
                            markdown_parts.append("## 📈 关键指标摘要\n")
                            # 使用公共方法生成表格
                            table_rows = self._format_as_markdown_table(value, key_translator=get_chinese_key)
                            for row in table_rows:
                                markdown_parts.append(row)
                            markdown_parts.append("\n")
                            continue
                        elif key in ["response_time_analysis", "响应时间分析"]:
                            markdown_parts.append("## ⏱️ 响应时间分析\n")
                        elif key in ["throughput_analysis", "吞吐量分析"]:
                            markdown_parts.append("## 🚀 吞吐量分析\n")
                        elif key in ["stability_analysis", "稳定性分析"]:
                            markdown_parts.append("## 🔒 稳定性分析\n")
                        elif key in ["risk_assessment", "风险评估"]:
                            markdown_parts.append("## ⚠️ 风险评估\n")
                        elif key in ["capacity_planning", "容量规划"]:
                            markdown_parts.append("## 📋 容量规划建议\n")
                        else:
                            markdown_parts.append(f"#### {key_display}\n")
                        
                        for sub_key, sub_value in value.items():
                            # 也检查子值是否包含提示词
                            if isinstance(sub_value, str):
                                excluded_keywords = [
                                    "完整指标数据", "分析要求", "请分析以下", "请提供以下"
                                ]
                                if any(keyword in sub_value for keyword in excluded_keywords):
                                    continue
                            
                            sub_key_display = get_chinese_key(sub_key)
                            # 特殊处理"关键指标摘要"嵌套在字典中的情况
                            if sub_key in ["key_metrics_summary", "关键指标摘要"] and isinstance(sub_value, dict):
                                markdown_parts.append("## 📈 关键指标摘要\n")
                                # 使用公共方法生成表格
                                table_rows = self._format_as_markdown_table(sub_value, key_translator=get_chinese_key)
                                for row in table_rows:
                                    markdown_parts.append(row)
                                markdown_parts.append("\n")
                                continue
                            elif isinstance(sub_value, (dict, list)):
                                markdown_parts.append(f"- **{sub_key_display}**:\n")
                                # 格式化嵌套结构为可读的文本，而不是 JSON 代码块
                                if isinstance(sub_value, dict):
                                    for nested_key, nested_value in sub_value.items():
                                        nested_key_display = get_chinese_key(nested_key)
                                        markdown_parts.append(f"  - **{nested_key_display}**: {nested_value}\n")
                                else:
                                    for i, item in enumerate(sub_value, 1):
                                        markdown_parts.append(f"  {i}. {item}\n")
                            else:
                                markdown_parts.append(f"- **{sub_key_display}**: {sub_value}\n")
                        markdown_parts.append("\n")
                    elif isinstance(value, list):
                        # 检查是否是优化建议列表（支持中英文键名）
                        is_opt_rec = key in ["optimization_recommendations", "优化建议"]
                        has_opt_keys = len(value) > 0 and isinstance(value[0], dict) and any(k in value[0] for k in ["priority", "recommendation", "suggestion", "优先级", "建议内容"])
                        if is_opt_rec or has_opt_keys:
                            markdown_parts.append("## 💡 优化建议\n")
                            for i, item in enumerate(value, 1):
                                if isinstance(item, dict):
                                    # 支持中文和英文键名
                                    priority = item.get("priority") or item.get("优先级", "")
                                    suggestion = item.get("recommendation") or item.get("suggestion") or item.get("建议内容", "")
                                    priority_emoji = {
                                        "high": "🔴",
                                        "medium": "🟡",
                                        "low": "🟢"
                                    }.get(priority.lower(), "•")
                                    markdown_parts.append(f"{i}. {priority_emoji} **{suggestion}**\n")
                                    if priority:
                                        priority_cn = {"high": "高", "medium": "中", "low": "低"}.get(priority.lower(), priority)
                                        markdown_parts.append(f"   - 优先级: {priority_cn}\n")
                            markdown_parts.append("\n")
                        else:
                            markdown_parts.append(f"#### {key_display}\n")
                            for i, item in enumerate(value, 1):
                                if isinstance(item, dict):
                                    # 格式化字典项为可读的文本
                                    for item_key, item_value in item.items():
                                        item_key_display = get_chinese_key(item_key)
                                        markdown_parts.append(f"{i}. **{item_key_display}**: {item_value}\n")
                                else:
                                    # 检查列表项是否包含提示词
                                    if isinstance(item, str):
                                        excluded_keywords = [
                                            "完整指标数据", "分析要求", "请分析以下", "请提供以下"
                                        ]
                                        if any(keyword in item for keyword in excluded_keywords):
                                            continue
                                    markdown_parts.append(f"{i}. {item}\n")
                            markdown_parts.append("\n")
                    elif isinstance(value, str) and len(value) > 200:
                        # 检查长字符串是否包含提示词
                        excluded_keywords = [
                            "完整指标数据", "分析要求", "请分析以下", "请提供以下"
                        ]
                        if any(keyword in value for keyword in excluded_keywords):
                            logger.info(f"[K6分析-Markdown] 跳过包含提示词的长字符串字段: {key}")
                            continue
                        # 长字符串，使用代码块
                        markdown_parts.append(f"#### {key_display}\n")
                        markdown_parts.append(f"{value}\n")
                        markdown_parts.append("\n")
                    else:
                        markdown_parts.append(f"- **{key_display}**: {value}\n")
                
                # 如果还有raw_analysis，也显示
                if "raw_analysis" in analysis_data and analysis_data["raw_analysis"]:
                    markdown_parts.append("\n### 🔍 原始分析数据\n")
                    markdown_parts.append("\n```json\n")
                    raw_data = analysis_data["raw_analysis"]
                    if isinstance(raw_data, dict):
                        markdown_parts.append(json.dumps(raw_data, indent=2, ensure_ascii=False))
                    else:
                        markdown_parts.append(str(raw_data))
                    markdown_parts.append("\n```\n")
            else:
                # 如果完全没有数据，显示提示和原始数据
                logger.warning(f"[K6分析-Markdown] 分析数据完全为空或只有元数据")
                markdown_parts.append("## ⚠️ 分析数据不足\n\n")
                markdown_parts.append("AI分析返回的数据结构不完整或为空。以下是原始数据：\n\n")
                markdown_parts.append("```json\n")
                markdown_parts.append(json.dumps(analysis_data, indent=2, ensure_ascii=False))
                markdown_parts.append("\n```\n")
        
        result = "\n".join(markdown_parts)
        logger.info(f"[K6分析-Markdown] 格式化完成，Markdown长度: {len(result)}, 行数: {len(markdown_parts)}")
        logger.debug(f"[K6分析-Markdown] Markdown预览（前500字符）: {result[:500]}")
        return result

