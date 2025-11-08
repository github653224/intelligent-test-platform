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
    
    def __init__(self, k6_binary_path: str = "k6"):
        """
        初始化 k6 执行器
        
        Args:
            k6_binary_path: k6 可执行文件路径，默认为 "k6"（需要在 PATH 中）
        """
        self.k6_binary_path = k6_binary_path
        self._check_k6_installation()
    
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
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as script_file:
            script_file.write(script_content)
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
            cmd.extend(additional_args)
            
            logger.info(f"执行 k6 命令: {' '.join(cmd)}")
            
            # 执行 k6
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            # 解析结果
            # k6返回非0退出码可能有两种情况：
            # 1. 脚本执行错误（真正的失败）- exit_code = 1
            # 2. 阈值检查失败（测试执行成功，但未达到阈值）- exit_code = 99
            # 3. 其他错误 - exit_code = 其他值
            
            # 判断状态
            if result.returncode == 0:
                status = "success"
            elif result.returncode == 99:
                # k6的阈值检查失败，但测试执行成功
                status = "completed"  # 标记为完成，但阈值未通过
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
                    logger.warning(f"k6 阈值检查失败（退出码: 99）- 测试执行成功但未达到性能阈值")
                else:
                    logger.error(f"k6 执行失败（退出码: {result.returncode}）")
                
                if result.stderr:
                    logger.error(f"k6 stderr: {result.stderr[:1000]}")
                if result.stdout:
                    logger.info(f"k6 stdout (最后1000字符): {result.stdout[-1000:]}")
                
                # 如果有stderr，将其作为错误信息
                if result.stderr and status == "failed":
                    execution_result["error"] = result.stderr[:500]  # 保存前500字符作为错误信息
            
            # 读取并解析汇总JSON文件
            if os.path.exists(summary_json_path):
                try:
                    with open(summary_json_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                        execution_result["summary"] = summary_data
                        # 解析关键指标
                        execution_result["metrics"] = self._parse_k6_summary_json(summary_data)
                except Exception as e:
                    logger.warning(f"解析 k6 汇总JSON失败: {e}")
                    execution_result["summary"] = {"error": str(e)}
            
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

