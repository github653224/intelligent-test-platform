"""
页面分析服务
使用Playwright自动访问URL并分析页面结构
"""
import logging
import json
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class PageAnalyzer:
    """页面分析器，用于分析网页结构"""
    
    def __init__(self):
        self.timeout = 30000  # 30秒超时
    
    def analyze(self, url: str, wait_time: int = 2000) -> Dict[str, Any]:
        """
        分析页面结构
        
        Args:
            url: 要分析的页面URL
            wait_time: 等待页面加载的时间（毫秒）
            
        Returns:
            页面结构信息
        """
        try:
            with sync_playwright() as p:
                # 启动浏览器（无头模式）
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                try:
                    # 访问页面
                    logger.info(f"正在访问页面: {url}")
                    page.goto(url, wait_until='networkidle', timeout=self.timeout)
                    
                    # 等待页面完全加载
                    page.wait_for_timeout(wait_time)
                    
                    # 提取页面信息
                    page_info = self._extract_page_info(page, url)
                    
                    browser.close()
                    return page_info
                    
                except PlaywrightTimeoutError:
                    logger.warning(f"页面加载超时: {url}")
                    # 即使超时，也尝试提取已有信息
                    try:
                        page_info = self._extract_page_info(page, url)
                        page_info['warning'] = '页面加载可能未完全完成'
                        browser.close()
                        return page_info
                    except Exception as e:
                        browser.close()
                        raise Exception(f"页面分析失败: {str(e)}")
                        
        except Exception as e:
            logger.error(f"页面分析失败: {e}")
            raise Exception(f"无法访问或分析页面 {url}: {str(e)}")
    
    def _extract_page_info(self, page, url: str) -> Dict[str, Any]:
        """提取页面信息"""
        
        # 执行JavaScript提取页面结构
        page_structure = page.evaluate("""
        () => {
            const result = {
                title: document.title,
                url: window.location.href,
                description: document.querySelector('meta[name="description"]')?.content || '',
                keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                headings: [],
                links: [],
                buttons: [],
                inputs: [],
                forms: [],
                images: [],
                interactive_elements: []
            };
            
            // 提取标题
            ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].forEach(tag => {
                document.querySelectorAll(tag).forEach(el => {
                    result.headings.push({
                        level: tag,
                        text: el.textContent.trim(),
                        id: el.id || null,
                        className: el.className || null
                    });
                });
            });
            
            // 提取链接
            document.querySelectorAll('a[href]').forEach(link => {
                if (link.textContent.trim() && link.href) {
                    result.links.push({
                        text: link.textContent.trim(),
                        href: link.href,
                        id: link.id || null,
                        className: link.className || null,
                        ariaLabel: link.getAttribute('aria-label') || null
                    });
                }
            });
            
            // 提取按钮
            document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"]').forEach(btn => {
                result.buttons.push({
                    text: btn.textContent?.trim() || btn.value || btn.getAttribute('aria-label') || '',
                    id: btn.id || null,
                    className: btn.className || null,
                    type: btn.type || btn.tagName.toLowerCase(),
                    ariaLabel: btn.getAttribute('aria-label') || null,
                    dataTestId: btn.getAttribute('data-testid') || null
                });
            });
            
            // 提取输入框
            document.querySelectorAll('input, textarea, select').forEach(input => {
                result.inputs.push({
                    type: input.type || input.tagName.toLowerCase(),
                    name: input.name || null,
                    id: input.id || null,
                    className: input.className || null,
                    placeholder: input.placeholder || null,
                    label: input.labels?.[0]?.textContent?.trim() || null,
                    required: input.required || false,
                    ariaLabel: input.getAttribute('aria-label') || null,
                    dataTestId: input.getAttribute('data-testid') || null
                });
            });
            
            // 提取表单
            document.querySelectorAll('form').forEach(form => {
                const formInputs = Array.from(form.querySelectorAll('input, textarea, select')).map(inp => ({
                    type: inp.type || inp.tagName.toLowerCase(),
                    name: inp.name || null,
                    id: inp.id || null
                }));
                result.forms.push({
                    id: form.id || null,
                    className: form.className || null,
                    action: form.action || null,
                    method: form.method || 'get',
                    inputs: formInputs
                });
            });
            
            // 提取图片
            document.querySelectorAll('img[src]').forEach(img => {
                result.images.push({
                    src: img.src,
                    alt: img.alt || null,
                    title: img.title || null
                });
            });
            
            // 提取交互元素（可点击、可输入的元素）
            document.querySelectorAll('[onclick], [data-action], [role="button"], [role="link"], [tabindex="0"]').forEach(el => {
                if (!result.buttons.some(b => b.id === el.id) && !result.links.some(l => l.id === el.id)) {
                    result.interactive_elements.push({
                        tag: el.tagName.toLowerCase(),
                        text: el.textContent?.trim() || '',
                        id: el.id || null,
                        className: el.className || null,
                        role: el.getAttribute('role') || null,
                        dataTestId: el.getAttribute('data-testid') || null
                    });
                }
            });
            
            return result;
        }
        """)
        
        # 获取页面文本内容（用于AI理解页面功能）
        page_text = page.evaluate("""
        () => {
            // 移除script和style标签
            const scripts = document.querySelectorAll('script, style');
            scripts.forEach(el => el.remove());
            
            // 获取可见文本
            const bodyText = document.body.innerText || document.body.textContent || '';
            return bodyText.substring(0, 5000); // 限制长度
        }
        """)
        
        # 获取页面HTML结构（简化版，用于理解布局）
        page_html_structure = page.evaluate("""
        () => {
            const getElementInfo = (el) => {
                const info = {
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    className: el.className || null,
                    text: el.textContent?.trim().substring(0, 100) || null
                };
                return info;
            };
            
            // 提取主要结构元素
            const mainElements = [];
            ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer'].forEach(tag => {
                document.querySelectorAll(tag).forEach(el => {
                    mainElements.push(getElementInfo(el));
                });
            });
            
            return mainElements;
        }
        """)
        
        # 构建页面信息
        page_info = {
            "url": url,
            "title": page_structure.get("title", ""),
            "description": page_structure.get("description", ""),
            "keywords": page_structure.get("keywords", ""),
            "structure": {
                "headings": page_structure.get("headings", [])[:20],  # 限制数量
                "links": page_structure.get("links", [])[:30],
                "buttons": page_structure.get("buttons", []),
                "inputs": page_structure.get("inputs", []),
                "forms": page_structure.get("forms", []),
                "images": page_structure.get("images", [])[:10],
                "interactive_elements": page_structure.get("interactive_elements", [])[:20],
                "main_sections": page_html_structure
            },
            "text_content": page_text[:3000],  # 限制文本长度
            "element_count": {
                "headings": len(page_structure.get("headings", [])),
                "links": len(page_structure.get("links", [])),
                "buttons": len(page_structure.get("buttons", [])),
                "inputs": len(page_structure.get("inputs", [])),
                "forms": len(page_structure.get("forms", [])),
                "images": len(page_structure.get("images", []))
            }
        }
        
        return page_info
    
    def generate_page_summary(self, page_info: Dict[str, Any]) -> str:
        """生成页面摘要，用于AI理解页面"""
        summary_parts = []
        
        summary_parts.append(f"页面URL: {page_info['url']}")
        summary_parts.append(f"页面标题: {page_info.get('title', '无标题')}")
        
        if page_info.get('description'):
            summary_parts.append(f"页面描述: {page_info['description']}")
        
        summary_parts.append("\n【页面元素统计】")
        element_count = page_info.get('element_count', {})
        summary_parts.append(f"- 标题: {element_count.get('headings', 0)} 个")
        summary_parts.append(f"- 链接: {element_count.get('links', 0)} 个")
        summary_parts.append(f"- 按钮: {element_count.get('buttons', 0)} 个")
        summary_parts.append(f"- 输入框: {element_count.get('inputs', 0)} 个")
        summary_parts.append(f"- 表单: {element_count.get('forms', 0)} 个")
        summary_parts.append(f"- 图片: {element_count.get('images', 0)} 个")
        
        structure = page_info.get('structure', {})
        
        # 主要标题
        if structure.get('headings'):
            summary_parts.append("\n【页面标题结构】")
            for heading in structure['headings'][:10]:
                summary_parts.append(f"- {heading['level']}: {heading['text'][:50]}")
        
        # 主要按钮
        if structure.get('buttons'):
            summary_parts.append("\n【主要按钮】")
            for btn in structure['buttons'][:15]:
                btn_text = btn.get('text') or btn.get('ariaLabel') or '无文本'
                summary_parts.append(f"- {btn_text} (id: {btn.get('id')}, type: {btn.get('type')})")
        
        # 主要输入框
        if structure.get('inputs'):
            summary_parts.append("\n【输入框】")
            for inp in structure['inputs'][:15]:
                inp_name = inp.get('name') or inp.get('id') or inp.get('placeholder') or '未命名'
                summary_parts.append(f"- {inp.get('type')}: {inp_name} (required: {inp.get('required')})")
        
        # 主要链接
        if structure.get('links'):
            summary_parts.append("\n【主要链接】")
            for link in structure['links'][:15]:
                summary_parts.append(f"- {link['text'][:30]} -> {link['href'][:50]}")
        
        # 页面文本内容（用于理解页面功能）
        if page_info.get('text_content'):
            summary_parts.append("\n【页面主要内容】")
            text_content = page_info['text_content'][:1000]  # 限制长度
            summary_parts.append(text_content)
        
        return "\n".join(summary_parts)

