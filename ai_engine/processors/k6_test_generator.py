"""
k6 性能测试脚本生成器
通过 AI 生成 k6 性能测试脚本
"""
import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class K6TestGenerator:
    """k6 性能测试脚本生成器"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
    
    def _clean_requirement_text(self, text: str) -> str:
        """清理需求文本（保护URL和数字）"""
        if not text:
            return ""
        
        # 先提取并保护URL和数字，避免被清理破坏
        url_pattern = r'https?://[^\s\)]+'
        number_pattern = r'\d+'
        
        # 保存URL和数字的位置和内容
        protected_items = []
        for match in re.finditer(url_pattern, text):
            protected_items.append((match.start(), match.end(), match.group(0), 'URL'))
        for match in re.finditer(number_pattern, text):
            # 只保护不在URL中的数字
            is_in_url = any(start <= match.start() < end for start, end, _, _ in protected_items)
            if not is_in_url:
                protected_items.append((match.start(), match.end(), match.group(0), 'NUMBER'))
        
        # 按位置排序
        protected_items.sort(key=lambda x: x[0])
        
        # 清理文本（只清理非保护区域）
        text = text.replace('\n', ' ').replace('\r', ' ').strip()
        
        # 只对非保护区域应用去重规则（避免破坏URL和数字）
        # 简化：对于k6脚本生成，我们不需要那么激进的去重，只去除明显的重复空格即可
        text = ' '.join(text.split())
        text = text.strip()
        
        return text
    
    async def generate(
        self,
        test_description: str,
        target_url: str = None,
        load_config: Dict[str, Any] = None,
        generation_mode: str = "regex"
    ) -> Dict[str, Any]:
        """
        生成 k6 性能测试脚本
        
        Args:
            test_description: 测试描述（一句话描述性能测试需求）
            target_url: 目标 URL（可选）
            load_config: 负载配置（可选，包含 VUs、duration 等）
            generation_mode: 生成模式，'ai' 或 'regex'，默认 'regex'
        """
        logger.info(f"[K6生成] ========== 开始生成k6脚本 ==========")
        logger.info(f"[K6生成] 生成模式: {generation_mode}")
        logger.info(f"[K6生成] 原始测试描述: {test_description}")
        
        # 根据生成模式选择不同的生成方法
        if generation_mode == "ai":
            return await self._generate_by_ai_direct(test_description)
        else:
            return await self._generate_by_regex(test_description, target_url, load_config)
    
    async def _generate_by_ai_direct(self, test_description: str) -> Dict[str, Any]:
        """AI直接生成模式：直接将需求给AI，要求只返回脚本代码"""
        logger.info(f"[K6生成-AI模式] 使用AI直接生成模式")
        
        # 构建简洁的提示词，要求只返回脚本代码
        prompt = self._build_ai_direct_prompt(test_description)
        logger.info(f"[K6生成-AI模式] 提示词长度: {len(prompt)}")
        logger.debug(f"[K6生成-AI模式] 提示词内容:\n{prompt}")
        
        try:
            # 调用 AI 生成 k6 脚本，使用较低的温度以获得更稳定的输出
            logger.info(f"[K6生成-AI模式] 开始调用AI生成脚本，temperature=0.2")
            response = await self.ai_client.generate_response(prompt, temperature=0.2, max_tokens=3000)
            logger.info(f"[K6生成-AI模式] AI响应长度: {len(response)}")
            logger.debug(f"[K6生成-AI模式] AI响应内容（前500字符）: {response[:500]}")
            
            # 提取脚本代码（去掉markdown标记和说明文字）
            k6_script = self._extract_script_from_response(response, test_description)
            
            if k6_script.get('status') == 'success':
                logger.info(f"[K6生成-AI模式] ✅ 脚本生成成功，长度: {k6_script.get('script_length', 0)}")
                # 清理脚本，移除重复定义的内置指标
                original_script = k6_script.get('script', '')
                cleaned_script = self._clean_k6_script(original_script)
                if cleaned_script != original_script:
                    logger.info(f"[K6生成-AI模式] 脚本已清理，移除了重复定义的内置指标")
                    k6_script['script'] = cleaned_script
                    k6_script['script_length'] = len(cleaned_script)
                # 验证脚本有效性
                if not self._validate_k6_script(k6_script.get('script', '')):
                    logger.warning(f"[K6生成-AI模式] ⚠️ 生成的脚本可能无效")
            else:
                logger.error(f"[K6生成-AI模式] ❌ 脚本生成失败: {k6_script.get('error')}")
            
            return k6_script
            
        except Exception as e:
            logger.error(f"[K6生成-AI模式] 生成失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "test_description": test_description
            }
    
    async def _generate_by_regex(self, test_description: str, target_url: str = None, load_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """正则匹配生成模式：使用正则提取参数，然后生成标准脚本"""
        original_description = test_description
        test_description = self._clean_requirement_text(test_description)
        logger.info(f"[K6生成-正则模式] 原始测试描述: {original_description}")
        logger.info(f"[K6生成-正则模式] 清理后的描述: {test_description}")
        
        if load_config is None:
            load_config = {}
        logger.info(f"[K6生成-正则模式] 传入的load_config: {load_config}")
        logger.info(f"[K6生成-正则模式] 传入的target_url: {target_url}")
        
        # 先用正则表达式提取参数
        extracted_params = self._extract_parameters_from_description(test_description)
        logger.info(f"[K6生成-正则模式] 正则提取的参数: {extracted_params}")
        
        # 如果正则提取不完整，使用 AI 补充提取
        if not extracted_params.get("vus") or not extracted_params.get("duration"):
            logger.warning(f"[K6生成-正则模式] ⚠️ 正则提取参数不完整，使用 AI 补充提取")
            ai_extracted = await self._extract_parameters_with_ai(test_description)
            logger.info(f"[K6生成-正则模式] AI提取的参数: {ai_extracted}")
            # 合并结果，AI 提取的优先级更高
            extracted_params = {**extracted_params, **ai_extracted}
            logger.info(f"[K6生成-正则模式] 合并后的参数: {extracted_params}")
        else:
            logger.info(f"[K6生成-正则模式] ✅ 正则提取完整，无需AI补充")
        
        # 构建生成提示词（传入提取的参数）
        prompt = self._build_generation_prompt(test_description, target_url, load_config, extracted_params)
        logger.info(f"[K6生成-正则模式] 生成的提示词长度: {len(prompt)}")
        logger.debug(f"[K6生成-正则模式] 提示词内容（前1000字符）:\n{prompt[:1000]}")
        
        try:
            # 调用 AI 生成 k6 脚本
            logger.info(f"[K6生成-正则模式] 开始调用AI生成脚本，temperature=0.3")
            response = await self.ai_client.generate_response(prompt, temperature=0.3)
            logger.info(f"[K6生成-正则模式] AI响应长度: {len(response)}")
            logger.debug(f"[K6生成-正则模式] AI响应内容（前500字符）: {response[:500]}")
            
            # 计算 final_vus 用于日志检查（从提取的参数或 load_config 获取）
            check_vus = extracted_params.get("vus") or (load_config.get("vus") if load_config else None) or 10
            
            # 解析生成的 k6 脚本
            k6_script = self._parse_k6_script_response(response, test_description)
            logger.info(f"[K6生成-正则模式] 解析后的脚本状态: {k6_script.get('status')}")
            if k6_script.get('status') == 'success':
                logger.info(f"[K6生成-正则模式] 生成的脚本长度: {k6_script.get('script_length', 0)}")
                # 清理脚本，移除重复定义的内置指标
                original_script = k6_script.get('script', '')
                cleaned_script = self._clean_k6_script(original_script)
                if cleaned_script != original_script:
                    logger.info(f"[K6生成-正则模式] 脚本已清理，移除了重复定义的内置指标")
                    k6_script['script'] = cleaned_script
                    k6_script['script_length'] = len(cleaned_script)
                # 检查脚本中是否包含正确的参数
                script_content = k6_script.get('script', '')
                # 检查是否错误地包含了vusMax字段（k6不支持此字段）
                if 'vusMax' in script_content:
                    logger.warning(f"[K6生成-正则模式] ⚠️ 脚本中包含 vusMax 字段（k6不支持此字段，应移除）")
                # 检查stages配置是否正确
                if f'target: {check_vus}' in script_content:
                    logger.info(f"[K6生成-正则模式] ✅ 脚本中包含正确的 target: {check_vus}")
                elif 'target: 10' in script_content:
                    logger.warning(f"[K6生成-正则模式] ⚠️ 脚本中包含 target: 10（可能使用了默认值，应该是 {check_vus}）")
            
            return k6_script
            
        except Exception as e:
            logger.error(f"[K6生成-正则模式] 生成失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "test_description": test_description
            }
    
    def _extract_parameters_from_description(self, test_description: str) -> Dict[str, Any]:
        """从测试描述中提取关键参数"""
        import re
        
        params = {}
        logger.info(f"[参数提取] ========== 开始参数提取 ==========")
        logger.info(f"[参数提取] 输入描述: {test_description}")
        
        # 提取并发用户数（支持多种表达方式）
        # 例如：100并发用户、100个用户、100 VUs、100虚拟用户、100用户并发
        vu_patterns = [
            r'(\d+)\s*并发用户',
            r'(\d+)\s*个用户',
            r'(\d+)\s*VUs?',
            r'(\d+)\s*虚拟用户',
            r'(\d+)\s*用户并发',
            r'(\d+)\s*并发',
            r'并发\s*(\d+)',
            r'(\d+)\s*用户',
            r'到\s*(\d+)\s*用户',  # 匹配"到100用户"
            r'加压到\s*(\d+)',      # 匹配"加压到100"
        ]
        for pattern in vu_patterns:
            match = re.search(pattern, test_description, re.IGNORECASE)
            if match:
                vus_value = int(match.group(1))
                params['vus'] = vus_value
                logger.info(f"[参数提取] 匹配到VUs模式: {pattern} -> {vus_value}")
                break
        
        if 'vus' not in params:
            logger.warning(f"[参数提取] 未找到并发用户数")
        
        # 提取加压时长和目标用户数（例如：3s加到100用户、3秒加到100）
        # 先尝试提取"X秒加到Y用户"的模式
        ramp_up_with_target_patterns = [
            r'(\d+)\s*s?\s*加到\s*(\d+)\s*用户',
            r'(\d+)\s*秒\s*加到\s*(\d+)\s*用户',
            r'(\d+)\s*s?\s*内\s*缓慢\s*加压\s*到\s*(\d+)',
            r'(\d+)\s*秒\s*内\s*缓慢\s*加压\s*到\s*(\d+)',
        ]
        ramp_up_found = False
        for pattern in ramp_up_with_target_patterns:
            match = re.search(pattern, test_description, re.IGNORECASE)
            if match:
                ramp_up_value = int(match.group(1))
                ramp_up_target = int(match.group(2))
                params['ramp_up_duration'] = f"{ramp_up_value}s"
                params['ramp_up_target'] = ramp_up_target  # 加压阶段的目标用户数
                logger.info(f"[参数提取] 匹配到RampUp模式（带目标）: {pattern} -> duration={params['ramp_up_duration']}, target={ramp_up_target}")
                ramp_up_found = True
                break
        
        # 如果没有找到带目标的模式，只提取加压时长
        if not ramp_up_found:
            ramp_up_patterns = [
                r'(\d+)\s*s?\s*加到\s*\d+',
                r'(\d+)\s*秒\s*加到\s*\d+',
                r'(\d+)\s*s?\s*内\s*缓慢\s*加压',
                r'(\d+)\s*秒\s*内\s*缓慢\s*加压',
                r'缓慢\s*加压.*?(\d+)\s*s',
                r'缓慢\s*加压.*?(\d+)\s*秒',
            ]
            for pattern in ramp_up_patterns:
                match = re.search(pattern, test_description, re.IGNORECASE)
                if match:
                    ramp_up_value = int(match.group(1))
                    params['ramp_up_duration'] = f"{ramp_up_value}s"
                    logger.info(f"[参数提取] 匹配到RampUp模式: {pattern} -> {params['ramp_up_duration']}")
                    break
        
        # 提取持续运行时长（例如：持续运行20s、持续20秒）
        duration_patterns = [
            r'持续\s*运行\s*(\d+)\s*秒',
            r'持续\s*运行\s*(\d+)\s*s',
            r'持续\s*(\d+)\s*秒',
            r'(\d+)\s*秒\s*持续',
            r'(\d+)\s*s\b',
            r'(\d+)\s*秒',
            r'持续\s*(\d+)\s*分钟',
            r'(\d+)\s*分钟',
            r'(\d+)\s*m\b',
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, test_description, re.IGNORECASE)
            if match:
                duration_value = int(match.group(1))
                # 判断单位
                if '分钟' in match.group(0) or 'm' in match.group(0).lower():
                    params['duration'] = f"{duration_value}m"
                else:
                    params['duration'] = f"{duration_value}s"
                logger.info(f"[参数提取] 匹配到Duration模式: {pattern} -> {params['duration']}")
                break
        
        # 提取减压时长（例如：3s内缓慢减少、3秒内减少到0）
        ramp_down_patterns = [
            r'(\d+)\s*s?\s*内\s*缓慢\s*减少',
            r'(\d+)\s*秒\s*内\s*缓慢\s*减少',
            r'(\d+)\s*s?\s*内\s*减少\s*到\s*0',
            r'(\d+)\s*秒\s*内\s*减少\s*到\s*0',
        ]
        for pattern in ramp_down_patterns:
            match = re.search(pattern, test_description, re.IGNORECASE)
            if match:
                ramp_down_value = int(match.group(1))
                params['ramp_down_duration'] = f"{ramp_down_value}s"
                logger.info(f"[参数提取] 匹配到RampDown模式: {pattern} -> {params['ramp_down_duration']}")
                break
        
        if 'duration' not in params:
            logger.warning(f"[参数提取] 未找到测试时长")
        
        # 提取 URL（改进正则，支持更多情况，并正确截断）
        url_patterns = [
            r'https?://[^\s\)\u4e00-\u9fff]+',  # 支持括号前的URL，但遇到中文字符停止
            r'https?://[^\s\)]+',     # 标准URL
        ]
        for url_pattern in url_patterns:
            url_match = re.search(url_pattern, test_description)
            if url_match:
                url = url_match.group(0)
                # 清理URL：移除尾部的标点符号和中文字符
                url = url.rstrip(')').rstrip('，').rstrip('。').rstrip(',').rstrip('。')
                # 如果URL后面紧跟着中文字符，需要截断
                # 找到URL在原文中的位置
                url_start = url_match.start()
                url_end = url_match.end()
                # 检查URL后面是否有中文字符，如果有则截断
                if url_end < len(test_description):
                    next_char = test_description[url_end]
                    # 如果下一个字符是中文字符，截断URL
                    if '\u4e00' <= next_char <= '\u9fff':
                        # 找到URL的最后一个有效字符位置
                        for i in range(len(url) - 1, -1, -1):
                            if url[i].isalnum() or url[i] in ['.', '/', '-', '_', ':', '?', '=', '&', '#']:
                                url = url[:i+1]
                                break
                params['url'] = url
                logger.info(f"[参数提取] 匹配到URL: {params['url']}")
                break
        else:
            logger.warning(f"[参数提取] 未找到URL，测试描述: {test_description[:100]}")
        
        logger.info(f"[参数提取] 最终提取结果: {params}")
        return params
    
    async def _extract_parameters_with_ai(self, test_description: str) -> Dict[str, Any]:
        """使用 AI 从测试描述中提取参数"""
        prompt = f"""
请从以下性能测试需求描述中提取关键参数，并以JSON格式返回：

测试需求：{test_description}

请提取以下参数（如果存在）：
1. 并发用户数（VUs）：数字，例如 100
2. 测试时长：格式为 "30s" 或 "5m"，例如 "30s" 表示30秒，"5m" 表示5分钟
3. 目标URL：完整的URL地址

请以JSON格式返回，例如：
{{
  "vus": 100,
  "duration": "30s",
  "url": "https://example.com"
}}

如果某个参数不存在，请省略该字段。只返回JSON，不要其他文字。
"""
        
        try:
            response = await self.ai_client.generate_response(prompt, temperature=0.1)
            # 尝试解析JSON
            import json
            # 清理响应，移除可能的markdown代码块标记
            cleaned_response = response.strip()
            if "```json" in cleaned_response:
                match = re.search(r'```json\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
            elif "```" in cleaned_response:
                match = re.search(r'```\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
            
            params = json.loads(cleaned_response)
            logger.info(f"AI提取的参数: {params}")
            return params
        except Exception as e:
            logger.warning(f"AI参数提取失败: {e}，使用正则提取的结果")
            return {}
    
    def _build_generation_prompt(
        self,
        test_description: str,
        target_url: str = None,
        load_config: Dict[str, Any] = None,
        extracted_params: Dict[str, Any] = None
    ) -> str:
        """构建 k6 脚本生成提示词"""
        
        if extracted_params is None:
            # 如果没有传入提取的参数，则使用正则表达式提取
            extracted_params = self._extract_parameters_from_description(test_description)
        
        # 优先使用提取的参数，其次使用 load_config，最后使用默认值
        final_vus = extracted_params.get("vus") or (load_config.get("vus") if load_config else None)
        final_duration = extracted_params.get("duration") or (load_config.get("duration") if load_config else None)
        final_url = extracted_params.get("url") or target_url
        
        logger.info(f"[提示词构建] 参数优先级选择:")
        logger.info(f"  - final_vus: {final_vus} (来源: extracted={extracted_params.get('vus')}, load_config={load_config.get('vus') if load_config else None})")
        logger.info(f"  - final_duration: {final_duration} (来源: extracted={extracted_params.get('duration')}, load_config={load_config.get('duration') if load_config else None})")
        logger.info(f"  - final_url: {final_url} (来源: extracted={extracted_params.get('url')}, target_url={target_url})")
        
        # 设置默认值
        if not final_vus:
            logger.warning(f"[提示词构建] ⚠️ VUs未找到，使用默认值10")
            final_vus = 10
        if not final_duration:
            logger.warning(f"[提示词构建] ⚠️ Duration未找到，使用默认值30s")
            final_duration = "30s"
        
        logger.info(f"[提示词构建] 最终使用的参数: VUs={final_vus}, Duration={final_duration}, URL={final_url}")
        
        # 检查是否需要缓慢加压（优先使用提取的参数）
        ramp_up_duration = extracted_params.get("ramp_up_duration")
        if not ramp_up_duration:
            # 如果没有提取到，从描述中判断
            if "缓慢" in test_description or "逐步" in test_description or "渐进" in test_description:
                # 缓慢加压：使用5秒或10%的测试时长（取较大值）
                if final_duration.endswith("s"):
                    duration_seconds = int(final_duration[:-1])
                    ramp_up_duration = f"{max(5, duration_seconds // 10)}s"
                elif final_duration.endswith("m"):
                    duration_minutes = int(final_duration[:-1])
                    ramp_up_duration = f"{max(5, duration_minutes * 6)}s"  # 分钟转秒
                else:
                    ramp_up_duration = "5s"
            else:
                ramp_up_duration = "1s"  # 默认快速升压
        
        # 检查减压时长（优先使用提取的参数）
        ramp_down_duration = extracted_params.get("ramp_down_duration") or "1s"  # 默认1秒降载
        
        # 构建 stages 配置
        # 检查是否有加压阶段的目标用户数（可能与最终目标不同）
        ramp_up_target = extracted_params.get("ramp_up_target")
        if ramp_up_target and ramp_up_target != final_vus:
            # 如果加压目标与最终目标不同，配置分阶段加压
            # 例如：3s加到100用户，然后持续30s保持121用户
            # stages应该是：
            # 1. 3s: 0 -> 100
            # 2. 30s: 100 -> 121 (k6会在30s内从100继续加压到121并保持)
            # 3. 3s: 121 -> 0
            stages_config = [
                {"duration": ramp_up_duration, "target": ramp_up_target},  # 升压阶段：3s内从0到100
                {"duration": final_duration, "target": final_vus},  # 保持阶段：30s内从100加压到121并保持
                {"duration": ramp_down_duration, "target": 0},  # 降载阶段：3s内从121到0
            ]
            logger.info(f"[提示词构建] 使用分阶段加压配置: 先加压到{ramp_up_target}，然后保持{final_vus}")
        else:
            # 标准配置：直接加压到最终目标
            stages_config = [
                {"duration": ramp_up_duration, "target": final_vus},  # 升压阶段（快速或缓慢）
                {"duration": final_duration, "target": final_vus},  # 保持目标并发数
                {"duration": ramp_down_duration, "target": 0},  # 平滑降载
            ]
            logger.info(f"[提示词构建] 使用标准配置: 直接加压到{final_vus}")
        
        logger.info(f"[提示词构建] 阶段配置: stages={stages_config}")
        
        prompt = f"""
你是一个专业的性能测试工程师，擅长使用 k6 进行性能测试。

请根据以下需求生成一个完整的 k6 性能测试脚本：

## 测试需求
{test_description}

## 从需求中提取的关键参数
"""
        
        if extracted_params:
            prompt += "已从测试需求中识别出以下参数：\n"
            if extracted_params.get("vus"):
                prompt += f"- 并发用户数: {extracted_params['vus']}\n"
            if extracted_params.get("duration"):
                prompt += f"- 测试时长: {extracted_params['duration']}\n"
            if extracted_params.get("url"):
                prompt += f"- 目标URL: {extracted_params['url']}\n"
            prompt += "\n"
        
        prompt += f"""
## 负载配置（请严格按照以下配置生成）
- 虚拟用户数 (VUs): {final_vus}
- 测试时长: {final_duration}
- 负载阶段配置 (stages): {json.dumps(stages_config, ensure_ascii=False)}

## 目标URL
"""
        
        if final_url:
            prompt += f"目标 URL: {final_url}\n"
        else:
            prompt += "目标 URL: 请从测试需求中提取或推断合适的测试目标\n"
        
        prompt += f"""
## 重要要求（请严格遵守）

1. **负载配置必须准确（这是最重要的，请严格遵守）**：
   - stages 配置必须完全按照上面提供的配置生成：{json.dumps(stages_config, ensure_ascii=False)}
   - **重要：stages 数组中的每个 stage 对象必须严格按照配置生成，不要修改 target 或 duration 值**
   - 第一阶段：{ramp_up_duration} 内将并发用户数从0提升到 {stages_config[0]['target']}（{"缓慢" if ramp_up_duration != "1s" else "快速"}加压）
   - 第二阶段：{"在 " + final_duration + " 内从 " + str(stages_config[0]['target']) + " 继续加压到 " + str(stages_config[1]['target']) + " 并保持" if len(stages_config) > 1 and stages_config[1]['target'] > stages_config[0]['target'] else "保持 " + str(stages_config[1]['target']) + " 个并发用户，持续 " + final_duration}
   - 第三阶段：{ramp_down_duration} 内将并发用户数从 {stages_config[-2]['target'] if len(stages_config) > 1 else final_vus} 降为0（平滑结束）
   - **重要：不要设置 vusMax 字段（k6不支持此字段，会根据stages自动确定最大VU数）**
   - **警告：不要使用默认值10，必须使用配置中的 target 值**

2. **脚本结构**：
   - 导入必要的 k6 模块：import http from 'k6/http'; import {{ check, sleep }} from 'k6';
   - options 配置必须包含 stages 和 thresholds
   - default function 中实现 HTTP 请求和检查

3. **性能阈值设置**（可根据实际情况调整，如果测试未达到阈值是正常的，说明需要优化性能）：
   - http_req_duration: ['p(95)<500']  # 95%请求响应时间<500ms（如果超过会显示警告但测试仍会完成）
   - http_req_failed: ['rate<0.01']    # 请求失败率<1%
   - checks: ['rate>0.99']            # 自定义校验通过率>99%

4. **请求逻辑**：
   - 使用 http.get() 或 http.post() 发送请求
   - 添加适当的 check() 验证响应
   - 包含 sleep() 模拟用户操作间隔（1-3秒随机）

5. **URL 处理**：
   - 如果测试需求中提到了具体的 URL，必须使用该 URL
   - URL 必须正确（注意拼写，如 quickpizza 不是 quickpiza）

## 输出格式
请直接输出 k6 JavaScript 代码，不要包含 markdown 代码块标记（不要使用 ```javascript 或 ``` 包裹）。
代码应该可以直接保存为 .js 文件并运行。

## 示例参考
如果需求是"对 https://example.com 接口进行100并发用户持续30秒的压力测试"，应该生成：

```javascript
export const options = {{
  stages: [
    {{ duration: '{ramp_up_duration}', target: {final_vus} }},  // 升压阶段：{ramp_up_duration}内从0到{final_vus}
    {{ duration: '{final_duration}', target: {final_vus} }}, // 保持阶段：保持{final_vus}用户{final_duration}
    {{ duration: '{ramp_down_duration}', target: 0 }},    // 降载阶段：{ramp_down_duration}内从{final_vus}到0
  ],
  thresholds: {{
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99']
  }}
}};

export default function() {{
  const url = '{final_url or "https://example.com"}';
  const response = http.get(url);
  check(response, {{
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500
  }});
  sleep(Math.random() * 2 + 1);
}}
```

## 关键提醒
- **必须使用提取的参数值 {final_vus}，不要使用默认值10**
- **URL必须是：{final_url or "从需求中提取"}**
- **stages配置必须完全匹配：{json.dumps(stages_config, ensure_ascii=False)}**

请严格按照以上要求生成 k6 脚本，确保所有数值都正确：
"""
        return prompt
    
    def _parse_k6_script_response(self, response: str, test_description: str) -> Dict[str, Any]:
        """解析 AI 生成的 k6 脚本"""
        try:
            # 清理响应文本
            cleaned_response = response.strip()
            
            # 如果包含 markdown 代码块标记，提取代码部分
            if "```javascript" in cleaned_response:
                match = re.search(r'```javascript\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
                    logger.info("从 markdown 代码块中提取 k6 脚本")
            elif "```js" in cleaned_response:
                match = re.search(r'```js\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
                    logger.info("从 markdown 代码块中提取 k6 脚本")
            elif "```" in cleaned_response:
                match = re.search(r'```\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
                    logger.info("从代码块中提取 k6 脚本")
            
            # 验证是否是有效的 k6 脚本
            if not self._validate_k6_script(cleaned_response):
                logger.warning("生成的脚本可能不是有效的 k6 脚本，使用原始响应")
                # 尝试修复或使用原始响应
                cleaned_response = response.strip()
            
            return {
                "status": "success",
                "script": cleaned_response,
                "test_description": test_description,
                "script_length": len(cleaned_response)
            }
            
        except Exception as e:
            logger.error(f"解析 k6 脚本失败: {e}")
            return {
                "status": "error",
                "error": f"解析失败: {str(e)}",
                "raw_response": response[:500] if response else "",
                "test_description": test_description
            }
    
    def _validate_k6_script(self, script: str) -> bool:
        """验证 k6 脚本的基本有效性"""
        if not script or len(script) < 50:
            return False
        
        # 检查是否包含 k6 的关键元素
        k6_keywords = ["import", "http", "check", "options", "export default function"]
        found_keywords = sum(1 for keyword in k6_keywords if keyword in script)
        
        # 至少应该包含 2 个关键词
        if found_keywords < 2:
            return False
        
        # 检查是否重复定义了内置指标
        import re
        builtin_metrics = ['data_sent', 'data_received', 'http_req_duration', 'http_reqs', 'iterations', 'vus']
        for metric in builtin_metrics:
            # 检查是否使用 new Counter/Trend/Rate/Gauge 创建了内置指标
            patterns = [
                rf"new\s+Counter\s*\(\s*['\"]{re.escape(metric)}['\"]",
                rf"new\s+Trend\s*\(\s*['\"]{re.escape(metric)}['\"]",
                rf"new\s+Rate\s*\(\s*['\"]{re.escape(metric)}['\"]",
                rf"new\s+Gauge\s*\(\s*['\"]{re.escape(metric)}['\"]",
                rf"new\s+Metric\s*\(\s*['\"]{re.escape(metric)}['\"]",
            ]
            for pattern in patterns:
                if re.search(pattern, script, re.IGNORECASE):
                    logger.warning(f"[脚本验证] 检测到重复定义的内置指标: {metric}")
                    # 不阻止，但记录警告（因为执行时会自动清理）
        
        return True
    
    def _clean_k6_script(self, script: str) -> str:
        """
        清理k6脚本，移除重复定义的内置指标及其使用
        
        Args:
            script: 原始脚本内容
            
        Returns:
            清理后的脚本内容
        """
        import re
        
        # k6内置指标列表
        builtin_metrics = [
            'data_sent', 'data_received', 'http_req_duration', 'http_reqs',
            'iterations', 'vus', 'http_req_failed', 'http_req_waiting',
            'http_req_connecting', 'http_req_tls_handshaking', 'http_req_sending',
            'http_req_receiving', 'http_req_blocked', 'iteration_duration',
            'vus_max'
        ]
        
        lines = script.split('\n')
        cleaned_lines = []
        
        # 跟踪需要移除的变量名
        variables_to_remove = set()
        
        # 第一遍：找出所有定义内置指标的变量
        for line in lines:
            for metric in builtin_metrics:
                # 匹配 const/let/var variableName = new Counter('data_sent')
                pattern = rf"(const|let|var)\s+(\w+)\s*=\s*new\s+(Counter|Trend|Rate|Gauge|Metric)\s*\(\s*['\"]{re.escape(metric)}['\"]"
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    var_name = match.group(2)
                    variables_to_remove.add(var_name)
                    logger.warning(f"[脚本清理] 检测到重复定义的内置指标: {metric} (变量名: {var_name})")
        
        # 第二遍：移除定义行和使用这些变量的代码行
        for line in lines:
            should_skip = False
            
            # 检查是否是定义内置指标的变量
            for metric in builtin_metrics:
                patterns = [
                    rf"(const|let|var)\s+\w+\s*=\s*new\s+(Counter|Trend|Rate|Gauge|Metric)\s*\(\s*['\"]{re.escape(metric)}['\"]",
                    rf"new\s+Counter\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"new\s+Trend\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"new\s+Rate\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"new\s+Gauge\s*\(\s*['\"]{re.escape(metric)}['\"]\s*\)",
                    rf"new\s+Metric\s*\(\s*['\"]{re.escape(metric)}['\"]",
                ]
                
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_skip = True
                        break
                
                if should_skip:
                    break
            
            # 检查是否使用了需要移除的变量
            if not should_skip and variables_to_remove:
                for var_name in variables_to_remove:
                    if re.search(rf"\b{re.escape(var_name)}\s*\.", line):
                        logger.warning(f"[脚本清理] 移除变量使用: {var_name}")
                        should_skip = True
                        break
            
            if not should_skip:
                cleaned_lines.append(line)
        
        cleaned_script = '\n'.join(cleaned_lines)
        
        if cleaned_script != script:
            logger.info(f"[脚本清理] 脚本已清理，移除了 {len(variables_to_remove)} 个变量的定义和使用")
            if variables_to_remove:
                logger.info(f"[脚本清理] 移除的变量: {', '.join(variables_to_remove)}")
        
        return cleaned_script
    
    def _build_ai_direct_prompt(self, test_description: str) -> str:
        """构建AI直接生成模式的提示词"""
        prompt = f"""你是一个专业的性能测试工程师，擅长使用 k6 进行性能测试。

请根据以下需求生成一个增强版的 k6 性能测试脚本：

## 测试需求
{test_description}

## 要求
1. **只返回 k6 JavaScript 代码，不要任何解释、说明或 markdown 标记**
2. **脚本必须是增强版本，包含更多监控指标**：
   - 响应时间分布（p50, p95, p99, p100）
   - 吞吐量（RPS）
   - 错误率
   - 数据发送/接收量
   - 迭代次数
3. **代码应该可以直接保存为 .js 文件并运行**
4. **不要使用 ```javascript 或 ``` 包裹代码**
5. **不要添加任何注释说明功能**
6. **脚本必须包含完整的 options 配置和 default function**
7. **重要：不要手动创建 k6 内置指标**：
   - k6 已经内置了以下指标，**不要使用 new Metric() 或 Counter/Rate/Trend/Gauge 创建这些指标**：
     - `data_sent` - 发送的数据量（自动统计）
     - `data_received` - 接收的数据量（自动统计）
     - `http_req_duration` - HTTP请求持续时间（自动统计）
     - `http_reqs` - HTTP请求总数（自动统计）
     - `iterations` - 迭代次数（自动统计）
     - `vus` - 虚拟用户数（自动统计）
   - **只使用 thresholds 配置来监控这些内置指标，不要重新定义它们**

## 脚本要求
- 使用 k6 的标准语法
- 包含 stages 配置（如果需要渐进式加压）
- 包含 thresholds 配置（性能阈值）- 使用内置指标名称，如 `http_req_duration`, `http_reqs`, `data_sent`, `data_received` 等
- **不要使用 new Trend(), new Counter(), new Rate(), new Gauge() 创建 k6 内置指标**
- 使用 check() 函数验证响应
- 添加适当的 sleep() 模拟用户行为
- 使用 k6 内置的 http 模块和指标，不要重复定义

## 输出格式
直接输出代码，不要任何其他文字。代码应该以 import 语句开始，以 export default function 结束。

直接输出代码："""
        return prompt
    
    def _extract_script_from_response(self, response: str, test_description: str = "") -> Dict[str, Any]:
        """从AI响应中提取脚本代码，去掉markdown标记和说明文字"""
        try:
            # 清理响应文本
            cleaned_response = response.strip()
            
            # 1. 尝试提取 markdown 代码块
            code_block_patterns = [
                r'```javascript\s*\n(.*?)\n```',  # ```javascript ... ```
                r'```js\s*\n(.*?)\n```',          # ```js ... ```
                r'```\s*\n(.*?)\n```',            # ``` ... ```
            ]
            
            for pattern in code_block_patterns:
                match = re.search(pattern, cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
                    logger.info(f"[脚本提取] 从 markdown 代码块中提取脚本（模式: {pattern[:20]}...）")
                    break
            
            # 2. 如果响应中包含代码块标记但没有匹配到，尝试更宽松的匹配
            if "```" in cleaned_response and not cleaned_response.strip().startswith("import"):
                # 尝试提取最后一个代码块
                code_blocks = re.findall(r'```(?:javascript|js)?\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if code_blocks:
                    cleaned_response = code_blocks[-1].strip()
                    logger.info(f"[脚本提取] 从最后一个代码块中提取脚本")
            
            # 3. 清理可能的前置说明文字
            # 如果响应以非代码内容开始，尝试找到第一个 import 或 export
            if not cleaned_response.strip().startswith("import") and not cleaned_response.strip().startswith("export"):
                # 查找第一个 import 或 export 语句的位置
                import_match = re.search(r'(import\s+.*?from)', cleaned_response, re.DOTALL)
                export_match = re.search(r'(export\s+.*?options)', cleaned_response, re.DOTALL)
                
                if import_match:
                    start_pos = import_match.start()
                    cleaned_response = cleaned_response[start_pos:].strip()
                    logger.info(f"[脚本提取] 从第一个 import 语句开始提取")
                elif export_match:
                    start_pos = export_match.start()
                    cleaned_response = cleaned_response[start_pos:].strip()
                    logger.info(f"[脚本提取] 从第一个 export 语句开始提取")
            
            # 4. 清理后置说明文字
            # 如果响应以非代码内容结束，尝试找到最后一个 }
            if cleaned_response.count('}') > cleaned_response.count('{'):
                # 可能有额外的说明文字，尝试找到最后一个完整的代码块
                lines = cleaned_response.split('\n')
                # 找到最后一个包含 export default function 或 } 的行
                last_code_line = -1
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    if line and (line.startswith('}') or line.startswith('export') or line.startswith('import')):
                        last_code_line = i
                        break
                
                if last_code_line >= 0:
                    cleaned_response = '\n'.join(lines[:last_code_line + 1]).strip()
                    logger.info(f"[脚本提取] 清理后置说明文字")
            
            # 5. 移除可能的行内注释说明（保留代码注释）
            # 这里只移除明显的非代码行，保留代码中的注释
            
            # 6. 最终清理：移除前后空白
            cleaned_response = cleaned_response.strip()
            
            # 7. 验证提取的脚本
            if not self._validate_k6_script(cleaned_response):
                logger.warning(f"[脚本提取] ⚠️ 提取的脚本可能无效，尝试使用原始响应")
                # 如果提取失败，尝试使用原始响应（去掉明显的说明文字）
                original_cleaned = response.strip()
                # 移除 markdown 标记
                original_cleaned = re.sub(r'```(?:javascript|js)?\s*\n?', '', original_cleaned)
                original_cleaned = re.sub(r'```\s*\n?', '', original_cleaned)
                original_cleaned = original_cleaned.strip()
                
                # 如果原始响应看起来更像代码，使用它
                if self._validate_k6_script(original_cleaned):
                    cleaned_response = original_cleaned
                    logger.info(f"[脚本提取] 使用清理后的原始响应")
                else:
                    logger.error(f"[脚本提取] ❌ 无法提取有效的脚本")
                    return {
                        "status": "error",
                        "error": "无法从AI响应中提取有效的k6脚本",
                        "test_description": test_description,
                        "raw_response": response[:500] if response else ""
                    }
            
            logger.info(f"[脚本提取] ✅ 脚本提取成功，长度: {len(cleaned_response)}")
            return {
                "status": "success",
                "script": cleaned_response,
                "test_description": test_description,
                "script_length": len(cleaned_response)
            }
            
        except Exception as e:
            logger.error(f"[脚本提取] 提取失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": f"脚本提取失败: {str(e)}",
                "test_description": test_description,
                "raw_response": response[:500] if response else ""
            }

