"""
k6 性能测试执行器
执行 k6 脚本并收集结果
"""
import json
import logging
import subprocess
import tempfile
import os
import shutil
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class K6Executor:
    """k6 性能测试执行器"""
    
    def __init__(self, k6_binary_path: Optional[str] = None):
        """
        初始化 k6 执行器
        
        Args:
            k6_binary_path: k6 可执行文件路径，如果为None则自动查找
        """
        if k6_binary_path is None:
            k6_binary_path = self._find_k6_binary()
        self.k6_binary_path = k6_binary_path
        self._check_k6_installation()
    
    def _find_k6_binary(self) -> str:
        """自动查找k6二进制文件路径"""
        # 常见的k6安装路径
        common_paths = [
            "k6",  # 在PATH中
            "/opt/homebrew/bin/k6",  # macOS Homebrew (Apple Silicon)
            "/usr/local/bin/k6",  # macOS Homebrew (Intel) 或 Linux
            "/usr/bin/k6",  # Linux系统包管理器
            "C:\\Program Files\\k6\\k6.exe",  # Windows
        ]
        
        # 首先尝试从环境变量读取
        from app.core.config import settings
        if settings.K6_BINARY_PATH:
            if os.path.exists(settings.K6_BINARY_PATH) and os.access(settings.K6_BINARY_PATH, os.X_OK):
                logger.info(f"使用配置中的k6路径: {settings.K6_BINARY_PATH}")
                return settings.K6_BINARY_PATH
            else:
                logger.warning(f"配置的k6路径不存在或不可执行: {settings.K6_BINARY_PATH}")
        
        # 尝试每个常见路径
        for path in common_paths:
            try:
                # 如果路径是相对路径（如"k6"），使用which查找
                if path == "k6":
                    result = subprocess.run(
                        ["which", "k6"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        found_path = result.stdout.strip()
                        if found_path:
                            logger.info(f"在PATH中找到k6: {found_path}")
                            return found_path
                else:
                    # 检查绝对路径是否存在且可执行
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        logger.info(f"找到k6: {path}")
                        return path
            except Exception as e:
                logger.debug(f"检查路径 {path} 时出错: {e}")
                continue
        
        # 如果都找不到，返回默认值（让_check_k6_installation处理错误）
        logger.warning("未找到k6，将使用默认路径'k6'，请确保k6在PATH中")
        return "k6"
    
    def _check_k6_installation(self):
        """检查 k6 是否已安装"""
        try:
            result = subprocess.run(
                [self.k6_binary_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"k6 已安装: {result.stdout.strip()}")
            else:
                logger.warning(f"k6 版本检查失败: {result.stderr}")
        except FileNotFoundError:
            logger.error(f"k6 未找到，请确保 k6 已安装并在 PATH 中")
            raise RuntimeError("k6 未安装，请先安装 k6: https://k6.io/docs/getting-started/installation/")
        except Exception as e:
            logger.error(f"检查 k6 安装时出错: {e}")
            raise
    
    def _clean_k6_script(self, script_content: str) -> str:
        """
        清理k6脚本，移除重复定义的内置指标及其使用
        
        Args:
            script_content: 原始脚本内容
            
        Returns:
            清理后的脚本内容
        """
        import re
        
        # k6内置指标列表（这些指标k6会自动统计，不需要手动创建）
        builtin_metrics = [
            'data_sent', 'data_received', 'http_req_duration', 'http_reqs',
            'iterations', 'vus', 'http_req_failed', 'http_req_waiting',
            'http_req_connecting', 'http_req_tls_handshaking', 'http_req_sending',
            'http_req_receiving', 'http_req_blocked', 'iteration_duration',
            'vus_max'
        ]
        
        lines = script_content.split('\n')
        cleaned_lines = []
        
        # 跟踪需要移除的变量名（例如：dataSentCounter, dataReceivedCounter等）
        variables_to_remove = set()
        
        # 第一遍：找出所有定义内置指标的变量
        for i, line in enumerate(lines):
            for metric in builtin_metrics:
                # 匹配 const/let/var variableName = new Counter('data_sent')
                # 例如：const dataSentCounter = new Counter('data_sent');
                pattern = rf"(const|let|var)\s+(\w+)\s*=\s*new\s+(Counter|Trend|Rate|Gauge|Metric)\s*\(\s*['\"]{re.escape(metric)}['\"]"
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    var_name = match.group(2)
                    variables_to_remove.add(var_name)
                    logger.warning(f"[k6脚本清理] 检测到重复定义的内置指标: {metric} (变量名: {var_name})")
                    logger.warning(f"[k6脚本清理] 问题行 {i+1}: {line.strip()[:100]}")
        
        # 第二遍：移除定义行和使用这些变量的代码行
        i = 0
        while i < len(lines):
            line = lines[i]
            should_skip = False
            
            # 检查是否是定义内置指标的变量
            for metric in builtin_metrics:
                # 匹配各种创建指标的模式（更精确的匹配）
                patterns = [
                    # const/let/var variableName = new Counter('data_sent') 或 new Counter("data_sent")
                    rf"(const|let|var)\s+\w+\s*=\s*new\s+(Counter|Trend|Rate|Gauge|Metric)\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    # new Counter('data_sent') 单独使用（不在变量赋值中）
                    rf"^\s*new\s+Counter\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"^\s*new\s+Trend\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"^\s*new\s+Rate\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"^\s*new\s+Gauge\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"^\s*new\s+Metric\s*\(\s*['\"]{re.escape(metric)}['\"]",
                ]
                
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_skip = True
                        logger.debug(f"[k6脚本清理] 匹配到定义行模式: {pattern[:50]}")
                        break
                
                if should_skip:
                    break
            
            # 检查是否使用了需要移除的变量
            if not should_skip and variables_to_remove:
                for var_name in variables_to_remove:
                    # 匹配变量使用：variableName.add(...) 或 variableName.其他方法
                    # 使用单词边界 \b 确保精确匹配变量名
                    var_pattern = rf"\b{re.escape(var_name)}\s*\.\w+"
                    if re.search(var_pattern, line):
                        logger.warning(f"[k6脚本清理] 移除变量使用: {var_name}")
                        logger.warning(f"[k6脚本清理] 问题行 {i+1}: {line.strip()[:100]}")
                        should_skip = True
                        break
            
            if should_skip:
                i += 1
                continue
            
            cleaned_lines.append(line)
            i += 1
        
        cleaned_script = '\n'.join(cleaned_lines)
        
        # 如果脚本被修改了，记录日志
        if cleaned_script != script_content:
            removed_lines = len(script_content.split('\n')) - len(cleaned_script.split('\n'))
            logger.info(f"[k6脚本清理] 脚本已清理，移除了 {removed_lines} 行（包括 {len(variables_to_remove)} 个变量的定义和使用）")
            if variables_to_remove:
                logger.info(f"[k6脚本清理] 移除的变量: {', '.join(variables_to_remove)}")
        else:
            logger.debug(f"[k6脚本清理] 脚本无需清理，未发现重复定义的内置指标")
        
        return cleaned_script
    
    def execute(
        self,
        script_content: str,
        output_format: str = "summary",
        additional_args: list = None
    ) -> Dict[str, Any]:
        """
        执行 k6 脚本
        
        Args:
            script_content: k6 脚本内容
            output_format: 输出格式，支持 "summary"（汇总数据，推荐）, "json"（详细JSON，数据量大）
            additional_args: 额外的 k6 命令行参数
        
        Returns:
            包含执行结果的字典
        """
        if additional_args is None:
            additional_args = []
        
        # 清理脚本，移除重复定义的内置指标
        logger.info(f"[k6执行] 开始清理k6脚本，检查重复定义的内置指标")
        cleaned_script = self._clean_k6_script(script_content)
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as script_file:
            script_file.write(cleaned_script)
            script_path = script_file.name
        
        # 创建临时目录用于存储输出文件
        temp_dir = tempfile.mkdtemp()
        summary_json_path = os.path.join(temp_dir, "summary.json")
        
        try:
            # 构建 k6 命令
            cmd = [self.k6_binary_path, "run", script_path]
            
            # 使用 summary export 输出汇总数据（只包含聚合指标，不包含每次请求的详细数据）
            # 这样可以大大减少数据量
            if output_format == "summary" or output_format == "json":
                # 使用 --summary-export 输出汇总JSON（推荐，数据量小）
                cmd.extend(["--summary-export", summary_json_path])
            elif output_format == "full":
                # 如果需要详细数据，使用 json 输出到文件
                json_output_path = os.path.join(temp_dir, "output.json")
                cmd.extend(["--out", f"json={json_output_path}"])
            
            # 添加额外参数
            if additional_args:
                cmd.extend(additional_args)
            
            logger.info(f"[k6执行] ===== 开始执行k6测试 =====")
            logger.info(f"[k6执行] k6二进制路径: {self.k6_binary_path}")
            logger.info(f"[k6执行] 执行命令: {' '.join(cmd)}")
            logger.info(f"[k6执行] k6脚本路径: {script_path}")
            logger.info(f"[k6执行] 输出文件路径: {summary_json_path}")
            logger.info(f"[k6执行] 脚本内容长度: {len(script_content)} 字符")
            logger.info(f"[k6执行] 输出格式: {output_format}")
            logger.info(f"[k6执行] 额外参数: {additional_args}")
            
            # 执行 k6
            start_time = datetime.now()
            logger.info(f"[k6执行] 开始时间: {start_time}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"[k6执行] 结束时间: {end_time}")
            logger.info(f"[k6执行] 执行耗时: {duration:.2f} 秒")
            logger.info(f"[k6执行] 退出码: {result.returncode}")
            logger.info(f"[k6执行] stdout长度: {len(result.stdout)} 字符")
            logger.info(f"[k6执行] stderr长度: {len(result.stderr)} 字符")
            
            # 解析结果
            # k6返回非0退出码可能有两种情况：
            # 1. 脚本执行错误（真正的失败）- exit_code = 1
            # 2. 阈值检查失败（测试执行成功，但未达到阈值）- exit_code = 99
            # 3. 其他错误 - exit_code = 其他值
            
            # 判断状态
            # k6退出码说明：
            # 0: 测试成功完成，所有阈值通过
            # 99: 测试执行完成，但阈值检查失败（测试本身成功，只是性能未达标）
            # 1: 脚本执行错误（真正的失败）
            # 其他: 其他错误
            if result.returncode == 0:
                # 测试成功完成
                status = "completed"
            elif result.returncode == 99:
                # k6的阈值检查失败，但测试执行成功（标记为completed，但可以在results中标记阈值未通过）
                status = "completed"
            elif result.returncode == 1:
                # 脚本执行错误
                status = "failed"
            else:
                # 其他错误
                status = "failed"
            
            execution_result = {
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout,  # 保留标准输出用于日志
                "stderr": result.stderr,
                "script_path": script_path,
                "executed_at": datetime.utcnow().isoformat()
            }
            
            # 如果退出码非0，记录详细信息
            if result.returncode != 0:
                if result.returncode == 99:
                    logger.warning(f"[k6执行] k6 阈值检查失败（退出码: 99）- 测试执行成功但未达到性能阈值")
                else:
                    logger.error(f"[k6执行] k6 执行失败（退出码: {result.returncode}）")
                
                if result.stderr:
                    stderr_preview = result.stderr[:2000] if len(result.stderr) > 2000 else result.stderr
                    logger.error(f"[k6执行] k6 stderr (前2000字符): {stderr_preview}")
                if result.stdout:
                    stdout_preview = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
                    logger.info(f"[k6执行] k6 stdout (最后2000字符): {stdout_preview}")
                
                # 如果有stderr，将其作为错误信息
                if result.stderr and status == "failed":
                    execution_result["error"] = result.stderr[:1000]  # 保存前1000字符作为错误信息
                    logger.error(f"[k6执行] 错误信息已保存到结果中: {execution_result['error'][:200]}")
            else:
                logger.info(f"[k6执行] k6执行成功（退出码: 0）")
            
            # 读取并解析汇总JSON文件
            logger.info(f"[k6执行] 检查汇总JSON文件: {summary_json_path}")
            logger.info(f"[k6执行] 文件是否存在: {os.path.exists(summary_json_path)}")
            if os.path.exists(summary_json_path):
                try:
                    file_size = os.path.getsize(summary_json_path)
                    logger.info(f"[k6执行] 汇总JSON文件大小: {file_size} 字节")
                    with open(summary_json_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                        logger.info(f"[k6执行] 成功读取汇总JSON，keys: {list(summary_data.keys())}")
                        execution_result["summary"] = summary_data
                        # 解析关键指标
                        execution_result["metrics"] = self._parse_k6_summary_json(summary_data)
                        logger.info(f"[k6执行] 解析后的metrics keys: {list(execution_result['metrics'].keys()) if execution_result['metrics'] else 'None'}")
                except Exception as e:
                    error_msg = f"解析 k6 汇总JSON失败: {e}"
                    logger.warning(f"[k6执行] {error_msg}", exc_info=True)
                    execution_result["summary"] = {"error": str(e)}
            else:
                logger.warning(f"[k6执行] 汇总JSON文件不存在: {summary_json_path}")
                execution_result["summary"] = {"error": "汇总JSON文件不存在"}
            
            logger.info(f"[k6执行] 执行结果状态: {execution_result['status']}")
            logger.info(f"[k6执行] ===== k6测试执行完成 =====")
            
            # 如果需要详细JSON输出（通常不需要，数据量太大）
            if output_format == "full":
                json_output_path = os.path.join(temp_dir, "output.json")
                if os.path.exists(json_output_path):
                    # 只保存文件路径，不读取全部内容（文件可能很大）
                    execution_result["detailed_json_path"] = json_output_path
                    execution_result["note"] = "详细JSON数据已保存到文件，文件较大，建议使用summary格式"
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            logger.error("k6 执行超时")
            return {
                "status": "timeout",
                "error": "k6 执行超时（超过1小时）",
                "executed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"执行 k6 脚本失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }
        finally:
            # 清理临时文件
            try:
                os.unlink(script_path)
            except Exception as e:
                logger.warning(f"删除临时脚本文件失败: {e}")
            
            # 清理临时目录
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"删除临时目录失败: {e}")
    
    def _parse_k6_metrics(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 k6 JSON 输出中的指标"""
        metrics = {}
        
        try:
            if "metrics" in json_data:
                k6_metrics = json_data["metrics"]
                
                # 提取关键指标
                key_metrics = [
                    "http_req_duration",  # HTTP 请求时长
                    "http_req_failed",    # HTTP 请求失败数
                    "http_reqs",          # HTTP 请求总数
                    "iterations",         # 迭代次数
                    "vus",                # 虚拟用户数
                    "vus_max",            # 最大虚拟用户数
                    "data_received",      # 接收数据量
                    "data_sent",          # 发送数据量
                ]
                
                for metric_name in key_metrics:
                    if metric_name in k6_metrics:
                        metric_data = k6_metrics[metric_name]
                        metrics[metric_name] = {
                            "values": metric_data.get("values", {}),
                            "count": metric_data.get("count", 0),
                            "rate": metric_data.get("rate", 0),
                            "min": metric_data.get("min", 0),
                            "max": metric_data.get("max", 0),
                            "avg": metric_data.get("avg", 0),
                            "med": metric_data.get("med", 0),
                            "p90": metric_data.get("p(90)", 0),
                            "p95": metric_data.get("p(95)", 0),
                            "p99": metric_data.get("p(99)", 0),
                        }
            
            # 提取根级别指标
            if "root_group" in json_data:
                root_group = json_data["root_group"]
                metrics["root_group"] = {
                    "checks": root_group.get("checks", {}),
                    "http_reqs": root_group.get("http_reqs", {}),
                    "http_req_duration": root_group.get("http_req_duration", {}),
                }
            
        except Exception as e:
            logger.error(f"解析 k6 指标失败: {e}")
        
        return metrics
    
    def _parse_k6_summary_json(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 k6 汇总JSON数据，提取关键指标"""
        metrics = {}
        
        try:
            if "metrics" in summary_data:
                k6_metrics = summary_data["metrics"]
                
                # 提取关键指标
                key_metrics = [
                    "http_req_duration",  # HTTP 请求时长
                    "http_req_failed",    # HTTP 请求失败数
                    "http_reqs",          # HTTP 请求总数
                    "iterations",         # 迭代次数
                    "vus",                # 虚拟用户数
                    "vus_max",            # 最大虚拟用户数
                    "data_received",      # 接收数据量
                    "data_sent",          # 发送数据量
                    "http_req_waiting",   # HTTP 请求等待时间
                    "http_req_connecting", # HTTP 连接时间
                    "iteration_duration",  # 迭代时长
                ]
                
                for metric_name in key_metrics:
                    if metric_name in k6_metrics:
                        metric_data = k6_metrics[metric_name]
                        # 提取所有可用的聚合数据
                        parsed_metric = {}
                        
                        # 提取基本统计信息
                        if "count" in metric_data:
                            parsed_metric["count"] = metric_data["count"]
                        if "sum" in metric_data:
                            parsed_metric["sum"] = metric_data["sum"]
                        if "rate" in metric_data:
                            parsed_metric["rate"] = metric_data["rate"]
                        if "min" in metric_data:
                            parsed_metric["min"] = metric_data["min"]
                        if "max" in metric_data:
                            parsed_metric["max"] = metric_data["max"]
                        if "avg" in metric_data:
                            parsed_metric["avg"] = metric_data["avg"]
                        if "med" in metric_data:
                            parsed_metric["med"] = metric_data["med"]
                        if "p(90)" in metric_data:
                            parsed_metric["p90"] = metric_data["p(90)"]
                        if "p(95)" in metric_data:
                            parsed_metric["p95"] = metric_data["p(95)"]
                        if "p(99)" in metric_data:
                            parsed_metric["p99"] = metric_data["p(99)"]
                        
                        # 对于某些指标（如vus），保留values字段（但只保留最后几个值，避免数据过大）
                        if "values" in metric_data and isinstance(metric_data["values"], dict):
                            values_dict = metric_data["values"]
                            # 只保留最后10个值（如果太多）
                            if len(values_dict) > 10:
                                # 转换为列表并排序，取最后10个
                                sorted_items = sorted(values_dict.items(), key=lambda x: float(x[0]) if x[0].isdigit() else 0)
                                parsed_metric["values"] = dict(sorted_items[-10:])
                            else:
                                parsed_metric["values"] = values_dict
                        
                        metrics[metric_name] = parsed_metric
            
            # 提取根级别指标
            if "root_group" in summary_data:
                root_group = summary_data["root_group"]
                metrics["root_group"] = {
                    "checks": root_group.get("checks", {}),
                    "http_reqs": root_group.get("http_reqs", {}),
                    "http_req_duration": root_group.get("http_req_duration", {}),
                }
            
        except Exception as e:
            logger.error(f"解析 k6 汇总指标失败: {e}")
        
        return metrics
    
    def _parse_k6_summary(self, summary_text: str) -> Dict[str, Any]:
        """解析 k6 文本摘要输出（备用方法）"""
        summary = {
            "raw": summary_text
        }
        
        # 尝试提取关键信息
        # k6 摘要格式示例：
        # checks.........................: 100.00% ✓ 1000  ✗ 0
        # data_received..................: 1.2 MB  40 kB/s
        # data_sent......................: 120 kB  4.0 kB/s
        # http_req_duration..............: avg=200ms min=100ms med=180ms max=500ms p(90)=300ms p(95)=400ms
        # http_req_failed................: 0.00%   ✓ 0     ✗ 1000
        # http_reqs......................: 1000    33.333333/s
        # iteration_duration.............: avg=250ms min=150ms med=230ms max=600ms p(90)=350ms p(95)=450ms
        # iterations.....................: 1000    33.333333/s
        # vus............................: 10      min=10 max=10
        # vus_max........................: 10       min=10 max=10
        
        lines = summary_text.split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    metric_name = parts[0].strip().replace('.', '').replace(' ', '_')
                    metric_value = parts[1].strip()
                    summary[metric_name] = metric_value
        
        return summary

