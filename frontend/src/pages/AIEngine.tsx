import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Select,
  Space,
  message,
  Typography,
  Divider,
  Progress,
  Tooltip,
  Switch,
  Upload,
  Modal,
  theme,
} from 'antd';
import { Markmap } from 'markmap-view';
import { Transformer } from 'markmap-lib';
import {
  CodeOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  ApartmentOutlined,
  EyeOutlined,
  RobotOutlined,
  FileTextOutlined,
  BugOutlined,
  ApiOutlined,
  UploadOutlined,
  FileWordOutlined,
} from '@ant-design/icons';
import { analyzeRequirementStream, generateTestCases, generateTestCasesStream, generateAPITests, generateUITests, parseDocument, parseAPIDocument, analyzePage } from '../services/aiService';
import type { UploadProps } from 'antd';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface AnalysisJsonData {
  status: string;
  filename?: string;
  data?: any;
  message?: string;
}

const AIEngine: React.FC = () => {
  // 获取主题token
  const {
    token: { colorBgContainer, colorFillSecondary, colorBorder, colorInfoBg, colorInfoBorder },
  } = theme.useToken();
  
  // 添加loading状态声明
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<any>(null);
  const [streamAnalysis, setStreamAnalysis] = useState('');
  const [progress, setProgress] = useState(0);
  const [progressVisible, setProgressVisible] = useState(false);
  const [analysisJson, setAnalysisJson] = useState<AnalysisJsonData | null>(null);
  const [streamTestCases, setStreamTestCases] = useState('');
  // 思维导图预览相关状态
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewType, setPreviewType] = useState<'analysis' | 'testcase'>('testcase');
  const svgRef = useRef<SVGSVGElement>(null);
  const markmapRef = useRef<any>(null);
  const [testCasesJson, setTestCasesJson] = useState<any>(null);
  
  // 保存各Tab的表单数据，避免切换时清空
  const [requirementFormData, setRequirementFormData] = useState<any>({});
  const [testCaseFormData, setTestCaseFormData] = useState<any>({});
  const [apiTestFormData, setApiTestFormData] = useState<any>({});
  const [uiTestFormData, setUITestFormData] = useState<any>({});
  const [parsedAPIDoc, setParsedAPIDoc] = useState<any>(null);  // 解析后的API文档
  const [analyzedPageInfo, setAnalyzedPageInfo] = useState<any>(null);  // 页面分析结果
  
  // Form 实例
  const [requirementForm] = Form.useForm();
  const [testCaseForm] = Form.useForm();
  const [apiTestForm] = Form.useForm();
  const [uiTestForm] = Form.useForm();

  // 将分析结果转为 Markdown 字符串
  const buildMarkdownFromAnalysis = (data: any): string => {
    const lines: string[] = [];
    lines.push(`# 需求分析报告`);
    if (data?.functional_points?.length) {
      lines.push(`\n## 功能点`);
      data.functional_points.forEach((fp: any, idx: number) => {
        lines.push(`\n### 功能点 ${idx + 1}`);
        lines.push(`- 描述: ${fp.point ?? ''}`);
        lines.push(`- 优先级: ${fp.priority ?? ''}`);
        lines.push(`- 复杂度: ${fp.complexity ?? ''}`);
        lines.push(`- 风险等级: ${fp.risk_level ?? ''}`);
      });
    }
    if (data?.test_boundaries?.length) {
      lines.push(`\n## 测试边界`);
      data.test_boundaries.forEach((tb: any, idx: number) => {
        lines.push(`\n### 边界 ${idx + 1}`);
        lines.push(`- 描述: ${tb.boundary ?? ''}`);
        lines.push(`- 类型: ${tb.test_type ?? ''}`);
        lines.push(`- 优先级: ${tb.priority ?? ''}`);
      });
    }
    if (data?.risk_points?.length) {
      lines.push(`\n## 风险点`);
      data.risk_points.forEach((rp: any, idx: number) => {
        lines.push(`\n### 风险 ${idx + 1}`);
        lines.push(`- 风险: ${rp.risk ?? ''}`);
        lines.push(`- 影响: ${rp.impact ?? ''}`);
        lines.push(`- 缓解: ${rp.mitigation ?? ''}`);
      });
    }
    if (data?.test_strategy) {
      lines.push(`\n## 测试策略`);
      lines.push(`- 总体策略: ${data.test_strategy.overall_approach ?? ''}`);
      if (Array.isArray(data.test_strategy.test_levels)) {
        lines.push(`- 测试级别: ${data.test_strategy.test_levels.join(', ')}`);
      }
      lines.push(`- 自动化范围: ${data.test_strategy.automation_scope ?? ''}`);
      if (Array.isArray(data.test_strategy.tools_recommendation)) {
        lines.push(`- 推荐工具: ${data.test_strategy.tools_recommendation.join(', ')}`);
      }
    }
    if (data?.test_priorities?.length) {
      lines.push(`\n## 测试优先级`);
      data.test_priorities.forEach((tp: any, idx: number) => {
        lines.push(`\n### 区域 ${idx + 1}`);
        lines.push(`- 区域: ${tp.area ?? ''}`);
        lines.push(`- 优先级: ${tp.priority ?? ''}`);
        lines.push(`- 理由: ${tp.rationale ?? ''}`);
      });
    }
    if (data?.estimated_effort) {
      lines.push(`\n## 预估工时`);
      lines.push(`- 总工时: ${data.estimated_effort.total_hours ?? ''}`);
      const b = data.estimated_effort.breakdown ?? {};
      lines.push(`- 细分:`);
      lines.push(`  - 测试计划: ${b.test_planning ?? ''}`);
      lines.push(`  - 测试设计: ${b.test_design ?? ''}`);
      lines.push(`  - 测试执行: ${b.test_execution ?? ''}`);
      lines.push(`  - 自动化: ${b.automation ?? ''}`);
    }
    return lines.join('\n');
  };

  // 将分析结果转成 HTML（用于PDF渲染）
  const buildHtmlFromAnalysis = (data: any): string => {
    const escape = (s: any) => (s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'));
    const parts: string[] = [];
    if (data?.functional_points?.length) {
      parts.push('<h2>功能点</h2>');
      parts.push('<ol style="padding-left: 20px; margin: 0;">');
      data.functional_points.forEach((fp: any) => {
        parts.push('<li style="margin-bottom: 10px; line-height: 1.6;">');
        parts.push(`<div><strong>描述：</strong>${escape(fp.point ?? '')}</div>`);
        parts.push(`<div><strong>优先级：</strong>${escape(fp.priority ?? '')}</div>`);
        parts.push(`<div><strong>复杂度：</strong>${escape(fp.complexity ?? '')}</div>`);
        parts.push(`<div><strong>风险等级：</strong>${escape(fp.risk_level ?? '')}</div>`);
        parts.push('</li>');
      });
      parts.push('</ol>');
    }
    if (data?.test_boundaries?.length) {
      parts.push('<h2>测试边界</h2>');
      parts.push('<ol style="padding-left: 20px; margin: 0;">');
      data.test_boundaries.forEach((tb: any) => {
        parts.push('<li style="margin-bottom: 10px; line-height: 1.6;">');
        parts.push(`<div><strong>描述：</strong>${escape(tb.boundary ?? '')}</div>`);
        parts.push(`<div><strong>类型：</strong>${escape(tb.test_type ?? '')}</div>`);
        parts.push(`<div><strong>优先级：</strong>${escape(tb.priority ?? '')}</div>`);
        parts.push('</li>');
      });
      parts.push('</ol>');
    }
    if (data?.risk_points?.length) {
      parts.push('<h2>风险点</h2>');
      parts.push('<ol style="padding-left: 20px; margin: 0;">');
      data.risk_points.forEach((rp: any) => {
        parts.push('<li style="margin-bottom: 10px; line-height: 1.6;">');
        parts.push(`<div><strong>风险：</strong>${escape(rp.risk ?? '')}</div>`);
        parts.push(`<div><strong>影响：</strong>${escape(rp.impact ?? '')}</div>`);
        parts.push(`<div><strong>缓解：</strong>${escape(rp.mitigation ?? '')}</div>`);
        parts.push('</li>');
      });
      parts.push('</ol>');
    }
    if (data?.test_strategy) {
      const ts = data.test_strategy;
      parts.push('<h2>测试策略</h2>');
      parts.push(`<div><strong>总体策略：</strong>${escape(ts.overall_approach ?? '')}</div>`);
      if (Array.isArray(ts.test_levels)) {
        parts.push(`<div><strong>测试级别：</strong>${escape(ts.test_levels.join(', '))}</div>`);
      }
      parts.push(`<div><strong>自动化范围：</strong>${escape(ts.automation_scope ?? '')}</div>`);
      if (Array.isArray(ts.tools_recommendation)) {
        parts.push(`<div><strong>推荐工具：</strong>${escape(ts.tools_recommendation.join(', '))}</div>`);
      }
    }
    if (data?.test_priorities?.length) {
      parts.push('<h2>测试优先级</h2>');
      parts.push('<ol style="padding-left: 20px; margin: 0;">');
      data.test_priorities.forEach((tp: any) => {
        parts.push('<li style="margin-bottom: 10px; line-height: 1.6;">');
        parts.push(`<div><strong>区域：</strong>${escape(tp.area ?? '')}</div>`);
        parts.push(`<div><strong>优先级：</strong>${escape(tp.priority ?? '')}</div>`);
        parts.push(`<div><strong>理由：</strong>${escape(tp.rationale ?? '')}</div>`);
        parts.push('</li>');
      });
      parts.push('</ol>');
    }
    if (data?.estimated_effort) {
      const b = data.estimated_effort.breakdown ?? {};
      parts.push('<h2>预估工时</h2>');
      parts.push(`<div><strong>总工时：</strong>${escape(data.estimated_effort.total_hours ?? '')}</div>`);
      parts.push('<ul>');
      parts.push(`<li>测试计划：${escape(b.test_planning ?? '')}</li>`);
      parts.push(`<li>测试设计：${escape(b.test_design ?? '')}</li>`);
      parts.push(`<li>测试执行：${escape(b.test_execution ?? '')}</li>`);
      parts.push(`<li>自动化：${escape(b.automation ?? '')}</li>`);
      parts.push('</ul>');
    }
    return parts.join('');
  };

  // 生成 Freemind .mm XML
  // 使用 markmap 技术生成需求分析思维导图（Markdown 格式）
  const buildMarkmapMarkdownForAnalysis = (data: any): string => {
    const lines: string[] = [];
    lines.push('# 需求分析结果\n');
    
    if (data.summary) {
      lines.push(`## 需求概述\n`);
      lines.push(`${data.summary}\n`);
    }
    
    if (Array.isArray(data.test_points) && data.test_points.length) {
      lines.push(`\n## 测试点\n`);
      data.test_points.forEach((tp: any, idx: number) => {
        lines.push(`### ${idx + 1}. ${tp.point || '测试点'}\n`);
        if (tp.category) lines.push(`- **类别**: ${tp.category}`);
        if (tp.priority) lines.push(`- **优先级**: ${tp.priority}`);
        if (tp.description) lines.push(`- **描述**: ${tp.description}`);
        if (tp.scope) lines.push(`- **范围**: ${tp.scope}`);
        lines.push('');
      });
    }
    
    if (Array.isArray(data.key_scenarios) && data.key_scenarios.length) {
      lines.push(`\n## 关键场景\n`);
      data.key_scenarios.forEach((ks: any, idx: number) => {
        lines.push(`### 场景 ${idx + 1}: ${ks.scenario || '场景'}\n`);
        if (ks.description) lines.push(`- **描述**: ${ks.description}`);
        if (ks.steps && Array.isArray(ks.steps)) {
          lines.push(`- **步骤**:`);
          ks.steps.forEach((step: any, stepIdx: number) => {
            lines.push(`  ${stepIdx + 1}. ${step}`);
          });
        }
        lines.push('');
      });
    }
    
    if (Array.isArray(data.boundary_cases) && data.boundary_cases.length) {
      lines.push(`\n## 边界情况\n`);
      data.boundary_cases.forEach((bc: any, idx: number) => {
        lines.push(`### ${idx + 1}. ${bc.case || '边界情况'}\n`);
        if (bc.description) lines.push(`- **描述**: ${bc.description}`);
        if (bc.test_approach) lines.push(`- **测试方法**: ${bc.test_approach}`);
        lines.push('');
      });
    }
    
    if (Array.isArray(data.risk_points) && data.risk_points.length) {
      lines.push(`\n## 风险点\n`);
      data.risk_points.forEach((rp: any, idx: number) => {
        lines.push(`### ${idx + 1}. ${rp.risk || '风险'}\n`);
        if (rp.impact) lines.push(`- **影响**: ${rp.impact}`);
        if (rp.mitigation) lines.push(`- **缓解措施**: ${rp.mitigation}`);
        lines.push('');
      });
    }
    
    if (data.test_strategy) {
      lines.push(`\n## 测试策略\n`);
      if (data.test_strategy.overall_approach) {
        lines.push(`- **总体策略**: ${data.test_strategy.overall_approach}`);
      }
      if (Array.isArray(data.test_strategy.test_levels)) {
        lines.push(`- **测试级别**: ${data.test_strategy.test_levels.join(', ')}`);
      }
      if (data.test_strategy.automation_scope) {
        lines.push(`- **自动化范围**: ${data.test_strategy.automation_scope}`);
      }
      if (Array.isArray(data.test_strategy.tools_recommendation)) {
        lines.push(`- **推荐工具**: ${data.test_strategy.tools_recommendation.join(', ')}`);
      }
      lines.push('');
    }
    
    if (Array.isArray(data.test_priorities) && data.test_priorities.length) {
      lines.push(`\n## 测试优先级\n`);
      data.test_priorities.forEach((tp: any, idx: number) => {
        lines.push(`### ${idx + 1}. ${tp.area || '区域'}\n`);
        if (tp.priority) lines.push(`- **优先级**: ${tp.priority}`);
        if (tp.rationale) lines.push(`- **理由**: ${tp.rationale}`);
        lines.push('');
      });
    }
    
    if (data.estimated_effort) {
      lines.push(`\n## 预估工时\n`);
      lines.push(`- **总工时**: ${data.estimated_effort.total_hours || ''}`);
      if (data.estimated_effort.breakdown) {
        const b = data.estimated_effort.breakdown;
        if (b.test_planning) lines.push(`- **测试计划**: ${b.test_planning}`);
        if (b.test_design) lines.push(`- **测试设计**: ${b.test_design}`);
        if (b.test_execution) lines.push(`- **测试执行**: ${b.test_execution}`);
        if (b.automation) lines.push(`- **自动化**: ${b.automation}`);
      }
      lines.push('');
    }
    
    return lines.join('\n');
  };

  // 生成包含 markmap 渲染的需求分析 HTML 文件
  const buildMarkmapHtmlForAnalysis = (data: any): string => {
    const markdown = buildMarkmapMarkdownForAnalysis(data);
    // 使用 JSON.stringify 安全地嵌入 markdown 内容，避免转义问题
    const markdownJson = JSON.stringify(markdown);
    
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>需求分析思维导图</title>
  <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.18.12/dist/index.min.js" 
          onerror="console.error('markmap-lib 加载失败'); window._markmapLibError = true;"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/index.min.js"
          onerror="console.error('markmap-view 加载失败'); window._markmapViewError = true;"></script>
  <style>
    body {
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
      background: #f5f5f5;
    }
    #markmap {
      width: 100%;
      height: 100vh;
      background: white;
    }
    .toolbar {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 1000;
      background: white;
      padding: 10px;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .toolbar button {
      margin: 0 5px;
      padding: 5px 10px;
      cursor: pointer;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      background: white;
    }
    .toolbar button:hover {
      background: #f0f0f0;
    }
  </style>
</head>
<body>
  <div class="toolbar">
    <button onclick="fit()">适应视图</button>
    <button onclick="exportSVG()">导出 SVG</button>
    <button onclick="exportHTML()">导出 HTML</button>
  </div>
  <svg id="markmap"></svg>
  
  <script>
    // 等待 markmap 库加载完成
    function initMarkmap() {
      if (!window.markmap || !window.markmapLib) {
        console.error('Markmap 库未加载');
        document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图加载失败</h2><p>请检查网络连接，确保可以访问 CDN</p></div>';
        return;
      }
      
      const { Markmap } = window.markmap;
      const { Transformer } = window.markmapLib;
      
      const transformer = new Transformer();
      const mm = Markmap.create('#markmap', {
        color: (node) => {
          // 根据节点层级设置不同颜色
          const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];
          return colors[node.depth % colors.length] || '#666';
        },
        duration: 300,
        maxWidth: 300,
        initialExpandLevel: 2,
      });
      
      try {
        // 从 JSON 中解析 markdown 内容（安全方式）
        // markdownJson 已经是 JSON.stringify 的结果，直接使用
        const markdownContent = JSON.parse(${markdownJson});
        const { root } = transformer.transform(markdownContent);
        mm.setData(root);
        mm.fit();
      } catch (e) {
        console.error('解析或渲染失败:', e);
        document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图渲染失败</h2><p>' + e.message + '</p></div>';
      }
      
      window.fit = function() {
        mm.fit();
      };
      
      window.exportSVG = function() {
        const svg = document.getElementById('markmap');
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        const svgUrl = URL.createObjectURL(svgBlob);
        const downloadLink = document.createElement('a');
        downloadLink.href = svgUrl;
        downloadLink.download = '需求分析思维导图.svg';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        URL.revokeObjectURL(svgUrl);
      };
      
      window.exportHTML = function() {
        const html = document.documentElement.outerHTML;
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.download = '需求分析思维导图.html';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        URL.revokeObjectURL(url);
      };
    }
    
    // 等待脚本加载完成后初始化
    function initWhenReady() {
      // 检查是否有脚本加载错误
      if (window._markmapLibError || window._markmapViewError) {
        const errorMsg = window._markmapLibError ? 'markmap-lib' : 'markmap-view';
        document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图库加载失败</h2><p>' + errorMsg + ' 加载失败，请检查网络连接或尝试使用预览功能</p></div>';
        return;
      }
      
      if (window.markmap && window.markmapLib && window.markmap.Markmap && window.markmapLib.Transformer) {
        try {
          initMarkmap();
        } catch (e) {
          console.error('初始化失败:', e);
          const errorMsg = e instanceof Error ? e.message : String(e);
          document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图初始化失败</h2><p>' + errorMsg + '</p><p>请检查浏览器控制台获取详细错误信息</p></div>';
        }
      } else {
        // 等待最多 10 秒
        let tries = 0;
        const checkInterval = setInterval(() => {
          tries++;
          
          // 检查是否有加载错误
          if (window._markmapLibError || window._markmapViewError) {
            clearInterval(checkInterval);
            const errorMsg = window._markmapLibError ? 'markmap-lib' : 'markmap-view';
            document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图库加载失败</h2><p>' + errorMsg + ' 加载失败，请检查网络连接</p></div>';
            return;
          }
          
          if (window.markmap && window.markmapLib && window.markmap.Markmap && window.markmapLib.Transformer) {
            clearInterval(checkInterval);
            try {
              initMarkmap();
            } catch (e) {
              console.error('初始化失败:', e);
              const errorMsg = e instanceof Error ? e.message : String(e);
              document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图初始化失败</h2><p>' + errorMsg + '</p></div>';
            }
          } else if (tries > 100) {
            clearInterval(checkInterval);
            document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图加载超时</h2><p>库加载超时（10秒），请检查网络连接，确保可以访问 CDN</p><p>如果问题持续，请尝试使用预览功能</p></div>';
          }
        }, 100);
      }
    }
    
    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initWhenReady);
    } else {
      setTimeout(initWhenReady, 200);
    }
  </script>
</body>
</html>`;
  };

  // 保留旧的 Freemind XML 生成函数（向后兼容）
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const buildFreemindXml = (data: any): string => {
    const esc = (s: any) => (s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'));
    const lines: string[] = [];
    lines.push('<?xml version="1.0" encoding="UTF-8"?>');
    lines.push('<map version="0.9.0">');
    lines.push('<node TEXT="需求分析">');
    const addNode = (title: string) => { lines.push(`<node TEXT="${esc(title)}">`); };
    const endNode = () => { lines.push('</node>'); };

    if (Array.isArray(data.functional_points) && data.functional_points.length) {
      addNode('功能点');
      data.functional_points.forEach((fp: any) => {
        addNode(fp.point ?? '功能点');
        lines.push(`<node TEXT="优先级: ${esc(fp.priority ?? '')}"/>`);
        lines.push(`<node TEXT="复杂度: ${esc(fp.complexity ?? '')}"/>`);
        lines.push(`<node TEXT="风险等级: ${esc(fp.risk_level ?? '')}"/>`);
        endNode();
      });
      endNode();
    }

    if (Array.isArray(data.test_boundaries) && data.test_boundaries.length) {
      addNode('测试边界');
      data.test_boundaries.forEach((tb: any) => {
        addNode(tb.boundary ?? '边界');
        lines.push(`<node TEXT="类型: ${esc(tb.test_type ?? '')}"/>`);
        lines.push(`<node TEXT="优先级: ${esc(tb.priority ?? '')}"/>`);
        endNode();
      });
      endNode();
    }

    if (Array.isArray(data.risk_points) && data.risk_points.length) {
      addNode('风险点');
      data.risk_points.forEach((rp: any) => {
        addNode(rp.risk ?? '风险');
        lines.push(`<node TEXT="影响: ${esc(rp.impact ?? '')}"/>`);
        lines.push(`<node TEXT="缓解: ${esc(rp.mitigation ?? '')}"/>`);
        endNode();
      });
      endNode();
    }

    if (data.test_strategy) {
      addNode('测试策略');
      lines.push(`<node TEXT="总体策略: ${esc(data.test_strategy.overall_approach ?? '')}"/>`);
      if (Array.isArray(data.test_strategy.test_levels)) {
        lines.push(`<node TEXT="测试级别: ${esc(data.test_strategy.test_levels.join(', '))}"/>`);
      }
      lines.push(`<node TEXT="自动化范围: ${esc(data.test_strategy.automation_scope ?? '')}"/>`);
      if (Array.isArray(data.test_strategy.tools_recommendation)) {
        lines.push(`<node TEXT="推荐工具: ${esc(data.test_strategy.tools_recommendation.join(', '))}"/>`);
      }
      endNode();
    }

    if (Array.isArray(data.test_priorities) && data.test_priorities.length) {
      addNode('测试优先级');
      data.test_priorities.forEach((tp: any) => {
        addNode(tp.area ?? '区域');
        lines.push(`<node TEXT="优先级: ${esc(tp.priority ?? '')}"/>`);
        lines.push(`<node TEXT="理由: ${esc(tp.rationale ?? '')}"/>`);
        endNode();
      });
      endNode();
    }

    if (data.estimated_effort) {
      addNode('预估工时');
      lines.push(`<node TEXT="总工时: ${esc(data.estimated_effort.total_hours ?? '')}"/>`);
      const b = data.estimated_effort.breakdown ?? {};
      lines.push(`<node TEXT="测试计划: ${esc(b.test_planning ?? '')}"/>`);
      lines.push(`<node TEXT="测试设计: ${esc(b.test_design ?? '')}"/>`);
      lines.push(`<node TEXT="测试执行: ${esc(b.test_execution ?? '')}"/>`);
      lines.push(`<node TEXT="自动化: ${esc(b.automation ?? '')}"/>`);
      endNode();
    }

    lines.push('</node>');
    lines.push('</map>');
    return lines.join('');
  };

  // 预览思维导图（在 Modal 中打开）
  const handlePreviewMindmap = (data: any, type: 'analysis' | 'testcase') => {
    try {
      if (!data) {
        message.error('没有可预览的数据');
        return;
      }
      
      setPreviewData(data);
      setPreviewType(type);
      setPreviewModalVisible(true);
    } catch (e) {
      console.error(e);
      message.error('思维导图预览失败: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  // 将思维导图渲染为图片并下载
  const downloadMindmapAsImage = async (data: any, type: 'analysis' | 'testcase', filename: string) => {
    try {
      message.loading({ content: '正在生成思维导图...', key: 'mindmap' });
      
      // 创建隐藏的容器
      const container = document.createElement('div');
      container.style.position = 'fixed';
      container.style.left = '-9999px';
      container.style.top = '0';
      container.style.width = '1920px'; // 使用较大的宽度以确保完整显示
      container.style.height = '1080px';
      container.style.backgroundColor = 'white';
      document.body.appendChild(container);

      // 创建 SVG 元素
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('id', 'mindmap-temp');
      svg.setAttribute('width', '1920');
      svg.setAttribute('height', '1080');
      svg.style.width = '100%';
      svg.style.height = '100%';
      container.appendChild(svg);

      // 生成 Markdown
      const markdown = type === 'analysis' 
        ? buildMarkmapMarkdownForAnalysis(data)
        : buildMarkmapMarkdownForTestCases(data);

      // 转换并渲染
      const transformer = new Transformer();
      const { root } = transformer.transform(markdown);
      
      const mm = Markmap.create('#mindmap-temp', {
        color: (node: any) => {
          const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];
          return colors[(node.depth || 0) % colors.length] || '#666';
        },
        duration: 0, // 无动画，立即渲染
        maxWidth: 300,
        initialExpandLevel: 999, // 展开所有节点（使用很大的数字确保展开所有）
        pan: false,
        zoom: false,
      }, root);

      // 等待渲染完成
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 适应视图
      mm.fit();
      await new Promise(resolve => setTimeout(resolve, 300));

      // 使用 html2canvas 截图
      const canvas = await html2canvas(container, {
        backgroundColor: '#ffffff',
        useCORS: true,
        logging: false,
        width: 1920,
        height: 1080,
        scale: 2, // 提高清晰度
      });

      // 下载图片
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          message.success({ content: '思维导图下载成功', key: 'mindmap' });
        } else {
          message.error({ content: '生成图片失败', key: 'mindmap' });
        }
      }, 'image/png', 1.0);

      // 清理
      mm.destroy();
      document.body.removeChild(container);
    } catch (e) {
      console.error('思维导图图片生成失败:', e);
      message.error({ content: '思维导图图片生成失败: ' + (e instanceof Error ? e.message : String(e)), key: 'mindmap' });
    }
  };

  // 初始化思维导图
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!previewModalVisible || !previewData) {
      // Modal 关闭时清理
      if (markmapRef.current) {
        markmapRef.current.destroy();
        markmapRef.current = null;
      }
      return;
    }

    // 延迟初始化，确保 Modal 和 SVG 元素已经完全渲染
    const timer = setTimeout(() => {
      if (!svgRef.current) {
        console.error('SVG ref 不可用');
        return;
      }
      
      try {
        // 清理之前的实例
        if (markmapRef.current) {
          markmapRef.current.destroy();
          markmapRef.current = null;
        }

        // 生成 Markdown（直接在 useEffect 内部调用，避免依赖问题）
        const markdown = previewType === 'analysis' 
          ? buildMarkmapMarkdownForAnalysis(previewData)
          : buildMarkmapMarkdownForTestCases(previewData);
        
        console.log('生成的 Markdown 长度:', markdown.length);
        
        // 转换 Markdown 为思维导图数据
        const transformer = new Transformer();
        const { root } = transformer.transform(markdown);

        // 创建 Markmap 实例
        if (svgRef.current) {
          markmapRef.current = Markmap.create(svgRef.current, {
            color: (node: any) => {
              const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];
              return colors[(node.depth || 0) % colors.length] || '#666';
            },
            duration: 300,
            maxWidth: 300,
            initialExpandLevel: 2,
            pan: true,
            zoom: true,
          }, root);

          console.log('Markmap 实例创建成功');

          // 自动适应视图
          setTimeout(() => {
            if (markmapRef.current) {
              markmapRef.current.fit();
              console.log('Markmap 视图已适应');
            }
          }, 100);
        }
      } catch (e) {
        console.error('思维导图初始化失败:', e);
        message.error('思维导图初始化失败: ' + (e instanceof Error ? e.message : String(e)));
      }
    }, 500); // 增加延迟到 500ms，确保 Modal 动画完成

    return () => {
      clearTimeout(timer);
      if (markmapRef.current) {
        markmapRef.current.destroy();
        markmapRef.current = null;
      }
    };
  }, [previewModalVisible, previewData, previewType]);

  // 下载分析结果
  // 生成Word文档（使用HTML格式，确保格式正确）
  const generateWordDocument = async (data: any): Promise<Blob> => {
    const escapeHtml = (text: any): string => {
      if (!text) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    };

    const htmlParts: string[] = [];
    htmlParts.push('<!DOCTYPE html>');
    htmlParts.push('<html>');
    htmlParts.push('<head>');
    htmlParts.push('<meta charset="UTF-8">');
    htmlParts.push('<meta name="ProgId" content="Word.Document">');
    htmlParts.push('<meta name="Generator" content="Microsoft Word">');
    htmlParts.push('<meta name="Originator" content="Microsoft Word">');
    htmlParts.push('<style>');
    htmlParts.push('body { font-family: "Microsoft YaHei", Arial, sans-serif; padding: 20px; line-height: 1.6; }');
    htmlParts.push('h1 { border-bottom: 2px solid #333; padding-bottom: 10px; }');
    htmlParts.push('h2 { color: #666; margin-top: 20px; margin-bottom: 10px; }');
    htmlParts.push('ol { margin-left: 20px; padding-left: 20px; }');
    htmlParts.push('li { margin-bottom: 10px; line-height: 1.6; }');
    htmlParts.push('p { margin: 5px 0; }');
    htmlParts.push('</style>');
    htmlParts.push('</head>');
    htmlParts.push('<body>');
    
    htmlParts.push('<h1>需求分析报告</h1>');
    
    // 功能点
    if (data?.functional_points?.length) {
      htmlParts.push('<h2>功能点</h2>');
      htmlParts.push('<ol>');
      data.functional_points.forEach((fp: any) => {
        htmlParts.push('<li>');
        htmlParts.push(`<strong>描述：</strong>${escapeHtml(fp.point ?? '')} `);
        htmlParts.push(`<strong>优先级：</strong>${escapeHtml(fp.priority ?? '')} `);
        htmlParts.push(`<strong>复杂度：</strong>${escapeHtml(fp.complexity ?? '')} `);
        htmlParts.push(`<strong>风险等级：</strong>${escapeHtml(fp.risk_level ?? '')}`);
        htmlParts.push('</li>');
      });
      htmlParts.push('</ol>');
    }
    
    // 测试边界
    if (data?.test_boundaries?.length) {
      htmlParts.push('<h2>测试边界</h2>');
      htmlParts.push('<ol>');
      data.test_boundaries.forEach((tb: any) => {
        htmlParts.push('<li>');
        htmlParts.push(`<strong>描述：</strong>${escapeHtml(tb.boundary ?? '')} `);
        htmlParts.push(`<strong>类型：</strong>${escapeHtml(tb.test_type ?? '')} `);
        htmlParts.push(`<strong>优先级：</strong>${escapeHtml(tb.priority ?? '')}`);
        htmlParts.push('</li>');
      });
      htmlParts.push('</ol>');
    }
    
    // 风险点
    if (data?.risk_points?.length) {
      htmlParts.push('<h2>风险点</h2>');
      htmlParts.push('<ol>');
      data.risk_points.forEach((rp: any) => {
        htmlParts.push('<li>');
        htmlParts.push(`<strong>风险：</strong>${escapeHtml(rp.risk ?? '')} `);
        htmlParts.push(`<strong>影响：</strong>${escapeHtml(rp.impact ?? '')} `);
        htmlParts.push(`<strong>缓解：</strong>${escapeHtml(rp.mitigation ?? '')}`);
        htmlParts.push('</li>');
      });
      htmlParts.push('</ol>');
    }
    
    // 测试策略
    if (data?.test_strategy) {
      const ts = data.test_strategy;
      htmlParts.push('<h2>测试策略</h2>');
      htmlParts.push(`<p><strong>总体策略：</strong>${escapeHtml(ts.overall_approach ?? '')}</p>`);
      if (Array.isArray(ts.test_levels)) {
        htmlParts.push(`<p><strong>测试级别：</strong>${escapeHtml(ts.test_levels.join(', '))}</p>`);
      }
      htmlParts.push(`<p><strong>自动化范围：</strong>${escapeHtml(ts.automation_scope ?? '')}</p>`);
      if (Array.isArray(ts.tools_recommendation)) {
        htmlParts.push(`<p><strong>推荐工具：</strong>${escapeHtml(ts.tools_recommendation.join(', '))}</p>`);
      }
    }
    
    // 测试优先级
    if (data?.test_priorities?.length) {
      htmlParts.push('<h2>测试优先级</h2>');
      htmlParts.push('<ol style="padding-left: 20px; margin: 0;">');
      data.test_priorities.forEach((tp: any) => {
        htmlParts.push('<li style="margin-bottom: 10px; line-height: 1.6;">');
        htmlParts.push(`<div><strong>区域：</strong>${escapeHtml(tp.area ?? '')}</div>`);
        htmlParts.push(`<div><strong>优先级：</strong>${escapeHtml(tp.priority ?? '')}</div>`);
        htmlParts.push(`<div><strong>理由：</strong>${escapeHtml(tp.rationale ?? '')}</div>`);
        htmlParts.push('</li>');
      });
      htmlParts.push('</ol>');
    }
    
    // 预估工时
    if (data?.estimated_effort) {
      const b = data.estimated_effort.breakdown ?? {};
      htmlParts.push('<h2>预估工时</h2>');
      htmlParts.push(`<p><strong>总工时：</strong>${escapeHtml(data.estimated_effort.total_hours ?? '')}</p>`);
      htmlParts.push(`<p>测试计划：${escapeHtml(b.test_planning ?? '')}</p>`);
      htmlParts.push(`<p>测试设计：${escapeHtml(b.test_design ?? '')}</p>`);
      htmlParts.push(`<p>测试执行：${escapeHtml(b.test_execution ?? '')}</p>`);
      htmlParts.push(`<p>自动化：${escapeHtml(b.automation ?? '')}</p>`);
    }
    
    htmlParts.push('</body>');
    htmlParts.push('</html>');
    
    const htmlContent = htmlParts.join('\n');
    
    // 使用HTML格式，Word可以直接打开
    const blob = new Blob(['\ufeff', htmlContent], { 
      type: 'application/msword' 
    });
    return blob;
  };

  const handleDownload = (type: 'json' | 'markdown' | 'pdf' | 'excel' | 'mindmap' | 'word') => {
    if (!analysisJson) {
      message.warning('请先进行需求分析');
      return;
    }

    switch (type) {
      case 'json':
        if (analysisJson.status === 'success' && analysisJson.filename) {
          // 跨域时，直接 a[href] 可能在新标签页打开；改为 fetch Blob 再触发下载
          const downloadUrl = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
          fetch(downloadUrl)
            .then(async (res) => {
              if (!res.ok) throw new Error(`下载失败: ${res.status}`);
              const blob = await res.blob();
              const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
              link.href = url;
          link.download = analysisJson.filename || `需求分析结果_${new Date().toISOString().split('T')[0]}.json`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
              URL.revokeObjectURL(url);
          message.success('文件下载开始');
            })
            .catch((e) => {
              console.error(e);
              message.error('下载失败');
            });
        } else if (analysisJson.data) {
          // Fallback to downloading the current analysis data as JSON
          const dataStr = JSON.stringify(analysisJson.data, null, 2);
          const blob = new Blob([dataStr], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `需求分析结果_${new Date().toISOString().split('T')[0]}.json`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          message.success('文件下载开始');
        } else {
          message.error('没有可下载的数据');
        }
        break;
      case 'markdown':
        (async () => {
          try {
            let data: any = analysisJson.data;
            if (!data && analysisJson.filename) {
              const url = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
              const res = await fetch(url);
              if (!res.ok) throw new Error(`获取JSON失败: ${res.status}`);
              data = await res.json();
            }
            if (!data) {
              message.error('没有可转换为Markdown的数据');
              return;
            }
            const md = buildMarkdownFromAnalysis(data);
            const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `需求分析_${new Date().toISOString().split('T')[0]}.md`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            message.success('Markdown 下载开始');
          } catch (e) {
            console.error(e);
            message.error('Markdown 导出失败');
          }
        })();
        break;
      case 'pdf':
        (async () => {
          try {
            // 准备 HTML 内容（直接用分析数据构建简单 HTML）
            const ensureData = async () => {
              if (analysisJson.data) return analysisJson.data;
              if (analysisJson.filename) {
                const url = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error(`获取JSON失败: ${res.status}`);
                return await res.json();
              }
              return null;
            };
            const data = await ensureData();
            if (!data) {
              message.error('没有可导出的数据');
              return;
            }
            const container = document.createElement('div');
            container.style.width = '800px';
            container.style.padding = '24px';
            container.style.background = '#fff';
            container.style.fontFamily = '"Microsoft YaHei", Arial, sans-serif';
            container.style.lineHeight = '1.6';
            container.innerHTML = `
              <h1 style="margin:0 0 20px; border-bottom: 2px solid #333; padding-bottom: 10px;">需求分析报告</h1>
              ${buildHtmlFromAnalysis(data)}
            `;
            document.body.appendChild(container);
            const canvas = await html2canvas(container, { 
              scale: 2,
              useCORS: true,
              logging: false,
              backgroundColor: '#ffffff'
            });
            const imgData = canvas.toDataURL('image/png', 1.0);
            const pdf = new jsPDF({ orientation: 'p', unit: 'pt', format: 'a4' });
            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 40; // 页面边距
            const imgWidth = pageWidth - (margin * 2);
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            // 修复分页逻辑，避免空白页和重复内容
            let heightLeft = imgHeight;
            let position = -margin;
            
            // 添加第一页
            pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
            heightLeft -= (pageHeight - margin * 2);

            // 如果内容超过一页，继续添加页面
            while (heightLeft > 10) { // 10pt的容差，避免因小数导致的空白页
              pdf.addPage();
              position = -margin - (imgHeight - heightLeft); // 计算正确的Y位置偏移
              pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
              heightLeft -= (pageHeight - margin * 2);
            }
            
            pdf.save(`需求分析_${new Date().toISOString().split('T')[0]}.pdf`);
            document.body.removeChild(container);
            message.success('PDF 下载开始');
          } catch (e) {
            console.error(e);
            message.error('PDF 导出失败');
          }
        })();
        break;
      case 'excel':
        (async () => {
          try {
            let data: any = analysisJson.data;
            if (!data && analysisJson.filename) {
              const url = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
              const res = await fetch(url);
              if (!res.ok) throw new Error(`获取JSON失败: ${res.status}`);
              data = await res.json();
            }
            if (!data) {
              message.error('没有可导出的数据');
              return;
            }
            const wb = XLSX.utils.book_new();
            // 功能点
            if (Array.isArray(data.functional_points)) {
              const fpSheet = XLSX.utils.json_to_sheet(data.functional_points);
              XLSX.utils.book_append_sheet(wb, fpSheet, '功能点');
            }
            // 测试边界
            if (Array.isArray(data.test_boundaries)) {
              const tbSheet = XLSX.utils.json_to_sheet(data.test_boundaries);
              XLSX.utils.book_append_sheet(wb, tbSheet, '测试边界');
            }
            // 风险点
            if (Array.isArray(data.risk_points)) {
              const rpSheet = XLSX.utils.json_to_sheet(data.risk_points);
              XLSX.utils.book_append_sheet(wb, rpSheet, '风险点');
            }
            // 测试策略
            if (data.test_strategy) {
              const ts = data.test_strategy;
              const aoa = [
                ['overall_approach', ts.overall_approach ?? ''],
                ['test_levels', Array.isArray(ts.test_levels) ? ts.test_levels.join(', ') : ''],
                ['automation_scope', ts.automation_scope ?? ''],
                ['tools_recommendation', Array.isArray(ts.tools_recommendation) ? ts.tools_recommendation.join(', ') : ''],
              ];
              const tsSheet = XLSX.utils.aoa_to_sheet([['key', 'value'], ...aoa]);
              XLSX.utils.book_append_sheet(wb, tsSheet, '测试策略');
            }
            // 测试优先级
            if (Array.isArray(data.test_priorities)) {
              const tpSheet = XLSX.utils.json_to_sheet(data.test_priorities);
              XLSX.utils.book_append_sheet(wb, tpSheet, '测试优先级');
            }
            // 预估工时
            if (data.estimated_effort) {
              const ee = data.estimated_effort;
              const aoa = [
                ['total_hours', ee.total_hours ?? ''],
                ['test_planning', ee.breakdown?.test_planning ?? ''],
                ['test_design', ee.breakdown?.test_design ?? ''],
                ['test_execution', ee.breakdown?.test_execution ?? ''],
                ['automation', ee.breakdown?.automation ?? ''],
              ];
              const eeSheet = XLSX.utils.aoa_to_sheet([['key', 'value'], ...aoa]);
              XLSX.utils.book_append_sheet(wb, eeSheet, '预估工时');
            }
            const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
            const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `需求分析_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            message.success('Excel 下载开始');
          } catch (e) {
            console.error(e);
            message.error('Excel 导出失败');
          }
        })();
        break;
      case 'word':
        (async () => {
          try {
            let data: any = analysisJson.data;
            if (!data && analysisJson.filename) {
              const url = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
              const res = await fetch(url);
              if (!res.ok) throw new Error(`获取JSON失败: ${res.status}`);
              data = await res.json();
            }
            if (!data) {
              message.error('没有可导出的数据');
              return;
            }
            const blob = await generateWordDocument(data);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `需求分析_${new Date().toISOString().split('T')[0]}.doc`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            message.success('Word 文档下载开始');
          } catch (e) {
            console.error(e);
            message.error('Word 导出失败');
          }
        })();
        break;
      case 'mindmap':
        (async () => {
          try {
            let data: any = analysisJson.data;
            if (!data && analysisJson.filename) {
              const url = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
              const res = await fetch(url);
              if (!res.ok) throw new Error(`获取JSON失败: ${res.status}`);
              data = await res.json();
            }
            if (!data) {
              message.error('没有可导出的数据');
              return;
            }
            // 生成图片格式的思维导图
            const filename = `需求分析思维导图_${new Date().toISOString().split('T')[0]}.png`;
            await downloadMindmapAsImage(data, 'analysis', filename);
          } catch (e) {
            console.error(e);
            message.error('思维导图导出失败');
          }
        })();
        break;
      default:
        return;
    }
  };

  // 进度条动画
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (loading && progressVisible) {
      timer = setInterval(() => {
        setProgress((prevProgress) => {
          // 确保进度在0-95之间，保留最后5%给完成时使用
          const nextProgress = prevProgress + Math.random() * 3;
          return nextProgress < 95 ? nextProgress : 95;
        });
      }, 200);
    } else if (!loading && progressVisible) {
      // 当加载完成时，直接设置为100%
      setProgress(100);
      timer = setTimeout(() => {
        setProgress(0);
        setProgressVisible(false);
      }, 500);
    }

    return () => {
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [loading, progressVisible]);

  // 处理文档上传和解析
  const handleDocumentUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    const fileObj = file as File;
    
    // 验证文件类型
    const fileExt = fileObj.name.split('.').pop()?.toLowerCase();
    const allowedExts = ['doc', 'docx', 'pdf', 'xls', 'xlsx', 'xmind'];
    
    if (!fileExt || !allowedExts.includes(fileExt)) {
      message.error(`不支持的文件格式。仅支持: Word (.doc, .docx), PDF (.pdf), Excel (.xls, .xlsx), XMind (.xmind)`);
      onError?.(new Error('不支持的文件格式'));
      return;
    }
    
    // 验证文件大小（最大50MB）
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (fileObj.size > maxSize) {
      message.error('文件大小不能超过50MB');
      onError?.(new Error('文件大小超过限制'));
      return;
    }
    
    try {
      message.loading({ content: '正在解析文档...', key: 'parse-doc', duration: 0 });
      
      const result = await parseDocument(fileObj);
      
      if (result.success && result.text) {
        // 将解析的文本填入需求描述字段
        requirementForm.setFieldsValue({
          requirement_text: result.text
        });
        
        // 更新表单数据状态
        setRequirementFormData({
          ...requirementFormData,
          requirement_text: result.text
        });
        
        message.success({
          content: `文档解析成功！已提取 ${result.text_length} 个字符的内容。文件名: ${result.filename}`,
          key: 'parse-doc',
          duration: 4
        });
        
        onSuccess?.(result);
      } else {
        throw new Error('文档解析失败：未提取到文本内容');
      }
    } catch (error: any) {
      const errorMsg = error.message || '文档解析失败';
      message.error({
        content: errorMsg,
        key: 'parse-doc',
        duration: 4
      });
      onError?.(error);
    }
  };

  // 测试用例生成的文档上传处理
  const handleDocumentUploadForTestCase: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    const fileObj = file as File;
    
    // 验证文件类型
    const fileExt = fileObj.name.split('.').pop()?.toLowerCase();
    const allowedExts = ['doc', 'docx', 'pdf', 'xls', 'xlsx', 'xmind'];
    
    if (!fileExt || !allowedExts.includes(fileExt)) {
      message.error(`不支持的文件格式。仅支持: Word (.doc, .docx), PDF (.pdf), Excel (.xls, .xlsx), XMind (.xmind)`);
      onError?.(new Error('不支持的文件格式'));
      return;
    }
    
    // 验证文件大小（最大50MB）
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (fileObj.size > maxSize) {
      message.error('文件大小不能超过50MB');
      onError?.(new Error('文件大小超过限制'));
      return;
    }
    
    try {
      message.loading({ content: '正在解析文档...', key: 'parse-doc-testcase', duration: 0 });
      
      const result = await parseDocument(fileObj);
      
      if (result.success && result.text) {
        // 将解析的文本填入测试用例需求描述字段
        testCaseForm.setFieldsValue({
          requirement_text: result.text
        });
        
        // 更新表单数据状态
        setTestCaseFormData({
          ...testCaseFormData,
          requirement_text: result.text
        });
        
        message.success({
          content: `文档解析成功！已提取 ${result.text_length} 个字符的内容。文件名: ${result.filename}`,
          key: 'parse-doc-testcase',
          duration: 4
        });
        
        onSuccess?.(result);
      } else {
        throw new Error('文档解析失败：未提取到文本内容');
      }
    } catch (error: any) {
      const errorMsg = error.message || '文档解析失败';
      message.error({
        content: errorMsg,
        key: 'parse-doc-testcase',
        duration: 4
      });
      onError?.(error);
    }
  };

  const handleRequirementAnalysis = async (values: any) => {
    console.log('Starting requirement analysis...');  // 添加调试日志
    setLoading(true);
    setStreamAnalysis('');
    setProgressVisible(true);
    setProgress(0);
    setAnalysisJson(null);  // 重置JSON状态
    let isCollectingJson = false;
    let jsonContent = '';
    
    console.log('Starting analysis...');
    try {
      await analyzeRequirementStream(
        values,
        (chunk) => {
          console.log('Received chunk:', chunk);  // 调试：显示接收到的每个数据块
          
          // 检查是否包含JSON标记
          if (chunk.includes('#JSON_START#')) {
            console.log('Found JSON_START marker');  // 调试：JSON开始标记
            isCollectingJson = true;
            jsonContent = '';  // 重置JSON内容
            return;
          }
          
          if (chunk.includes('#JSON_END#')) {
            console.log('Found JSON_END marker');  // 调试：JSON结束标记
            console.log('Collected JSON content:', jsonContent);  // 调试：显示收集到的JSON内容
            isCollectingJson = false;
            try {
              // 解析和设置JSON数据
              const jsonData = JSON.parse(jsonContent.trim());
              console.log('Successfully parsed JSON:', jsonData);  // 调试：显示解析后的JSON
              
              // 设置分析结果
              setAnalysisJson(jsonData);
              message.success('分析完成，可以下载结果');
              console.log('Analysis JSON set:', jsonData); // 添加调试日志
            } catch (e) {
              console.error('JSON parse error:', e);  // 调试：显示解析错误
              console.error('Failed JSON content:', jsonContent);  // 调试：显示导致失败的内容
              message.error('JSON解析失败');
            }
            return;
          }
          
          // 收集JSON内容或更新分析结果显示
          if (isCollectingJson) {
            console.log('Collecting JSON chunk:', chunk);  // 调试：显示正在收集的JSON片段
            jsonContent += chunk;
          } else {
            setStreamAnalysis(prev => prev + chunk);
          }
        }
      );
    } catch (error) {
      message.error('分析失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 从流式内容中尝试提取JSON
  const tryExtractJsonFromStream = (streamContent: string): boolean => {
    try {
      // 方法1: 尝试找到 #JSON_START# 标记
      const startMarker = '#JSON_START#';
      const endMarker = '#JSON_END#';
      const startIndex = streamContent.indexOf(startMarker);
      
      if (startIndex >= 0) {
        let jsonStr = streamContent.substring(startIndex + startMarker.length);
        // 如果有结束标记，截取到结束标记
        const endIndex = jsonStr.indexOf(endMarker);
        if (endIndex >= 0) {
          jsonStr = jsonStr.substring(0, endIndex);
        }
        
        // 尝试解析JSON
        try {
          const jsonData = JSON.parse(jsonStr.trim());
          setResults({ type: 'test_case_generation', data: jsonData });
          setTestCasesJson({ ...jsonData, _rawStreamContent: streamContent }); // 保存原始流式内容
          message.success('测试用例生成完成！');
          return true;
        } catch (e) {
          console.warn('完整JSON解析失败，尝试修复:', e);
          // JSON可能被截断，尝试修复或提取部分内容
          return tryExtractPartialJson(jsonStr, streamContent);
        }
      } else {
        // 方法2: 尝试从流式内容中直接查找JSON对象
        const jsonMatch = streamContent.match(/\{[\s\S]*"test_cases"[\s\S]*\}/);
        if (jsonMatch) {
          try {
            const jsonData = JSON.parse(jsonMatch[0]);
            setResults({ type: 'test_case_generation', data: jsonData });
            setTestCasesJson({ ...jsonData, _rawStreamContent: streamContent }); // 保存原始流式内容
            message.success('测试用例生成完成！');
            return true;
          } catch (e) {
            return tryExtractPartialJson(jsonMatch[0], streamContent);
          }
        }
      }
    } catch (e) {
      console.error('提取JSON失败:', e);
    }
    return false;
  };
  
  // 尝试从部分/截断的JSON中提取内容
  const tryExtractPartialJson = (partialJson: string, streamContent?: string): boolean => {
    try {
      // 尝试找到最后一个完整的test_case对象
      const testCaseRegex = /"test_cases"\s*:\s*\[([\s\S]*?)\]/;
      const match = partialJson.match(testCaseRegex);
      
      if (match) {
        // 尝试提取每个test_case
        const testCasesMatch = match[1].match(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g);
        if (testCasesMatch && testCasesMatch.length > 0) {
          const testCases: any[] = [];
          testCasesMatch.forEach((testCaseStr, index) => {
            try {
              const testCase = JSON.parse(testCaseStr);
              testCase.generated_by = 'ai';
              testCase.status = 'draft';
              testCases.push(testCase);
            } catch (e) {
              // 解析单个test_case失败，尝试提取关键信息
              const titleMatch = testCaseStr.match(/"title"\s*:\s*"([^"]*)"/);
              const typeMatch = testCaseStr.match(/"test_type"\s*:\s*"([^"]*)"/);
              if (titleMatch || typeMatch) {
                testCases.push({
                  title: titleMatch ? titleMatch[1] : `Test Case ${index + 1}`,
                  test_type: typeMatch ? typeMatch[1] : 'functional',
                  description: 'JSON被截断，部分信息丢失',
                  raw_response: testCaseStr.substring(0, 5000),
                  generated_by: 'ai',
                  status: 'draft'
                });
              }
            }
          });
          
          if (testCases.length > 0) {
            const jsonData = { test_cases: testCases };
            setResults({ type: 'test_case_generation', data: jsonData });
            setTestCasesJson({ ...jsonData, _rawStreamContent: streamContent || partialJson }); // 保存原始流式内容
            message.warning('JSON响应被截断，已提取部分测试用例');
            return true;
          }
        }
      }
      
      // 如果无法提取test_cases，至少保存原始内容
      const jsonData = {
        test_cases: [{
          title: 'JSON响应被截断',
          description: '无法完整解析JSON，请查看原始响应',
          test_type: 'functional',
          raw_response: partialJson.substring(0, 10000),
          generated_by: 'ai',
          status: 'draft'
        }]
      };
      setResults({ type: 'test_case_generation', data: jsonData });
      setTestCasesJson({ ...jsonData, _rawStreamContent: streamContent || partialJson }); // 保存原始流式内容
      message.warning('JSON响应被截断，已保存原始内容');
      return true;
    } catch (e) {
      console.error('提取部分JSON失败:', e);
      return false;
    }
  };

  const handleTestCaseGeneration = async (values: any) => {
    setLoading(true);
    setProgressVisible(true);
    setProgress(0);
    setStreamTestCases('');
    let isCollectingJson = false;
    let jsonContent = '';
    let allStreamContent = ''; // 保存所有流式内容，用于后续提取
    let jsonParsed = false; // 跟踪JSON是否成功解析
    try {
      // 如果是功能测试，强制关闭generate_script
      const requestData = {
        ...values,
        generate_script: values.test_type === 'functional' ? false : (values.generate_script ?? true)
      };
      await generateTestCasesStream(
        requestData,
        (chunk) => {
          allStreamContent += chunk; // 保存所有内容，用于后续代码提取
          
          // 总是更新流式显示（包括JSON标记，让用户看到完整输出）
          setStreamTestCases((prev) => prev + chunk);
          
          // 同时处理JSON收集
          if (chunk.includes('#JSON_START#')) {
            isCollectingJson = true;
            jsonContent = '';
            // 提取 #JSON_START# 之后的内容
            const startIndex = chunk.indexOf('#JSON_START#');
            jsonContent = chunk.substring(startIndex + '#JSON_START#'.length);
            return;
          }
          if (chunk.includes('#JSON_END#')) {
            isCollectingJson = false;
            // 提取 #JSON_END# 之前的内容
            const endIndex = chunk.indexOf('#JSON_END#');
            jsonContent += chunk.substring(0, endIndex);
            try {
              const jsonData = JSON.parse(jsonContent.trim());
              setResults({ type: 'test_case_generation', data: jsonData });
              setTestCasesJson({ ...jsonData, _rawStreamContent: allStreamContent }); // 保存原始流式内容
              jsonParsed = true;
      message.success('测试用例生成完成！');
            } catch (e) {
              console.error('JSON解析失败，尝试从流式内容中提取:', e);
              // JSON解析失败，尝试从流式内容中提取
              if (tryExtractJsonFromStream(allStreamContent)) {
                jsonParsed = true;
              }
            }
            return;
          }
          if (isCollectingJson) {
            jsonContent += chunk;
          }
        }
      );
      
      // 流式完成后，如果没有成功解析JSON，尝试从流式内容中提取
      if (!jsonParsed) {
        tryExtractJsonFromStream(allStreamContent);
      }
    } catch (error) {
      // 如果流式失败，回退到一次性生成
    try {
      // 如果是功能测试，强制关闭generate_script
      const requestData = {
        ...values,
        generate_script: values.test_type === 'functional' ? false : (values.generate_script ?? true)
      };
      const response = await generateTestCases(requestData);
      setResults({ type: 'test_case_generation', data: response });
        setTestCasesJson(response);
      message.success('测试用例生成完成！');
      } catch (e) {
      message.error('测试用例生成失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const getTestCasesData = () => {
    const data = testCasesJson || results?.data;
    if (!data) return null;
    return data.test_cases ? data : { status: 'success', test_cases: [] };
  };

  const handleCopyTestCases = async () => {
    const data = getTestCasesData();
    if (!data) {
      message.warning('没有可复制的数据');
      return;
    }
    const text = JSON.stringify(data, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      message.success('已复制到剪贴板');
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      message.success('已复制到剪贴板');
    }
  };

  const buildMarkdownFromTestCases = (payload: any): string => {
    const cases = payload?.test_cases || [];
    const lines: string[] = ['# 测试用例集'];
    cases.forEach((c: any, i: number) => {
      lines.push(`\n## 用例 ${i + 1} - ${c.title || ''}`);
      lines.push(`\n**类型：** ${c.test_type || ''}`);
      if (c.priority) lines.push(`**优先级：** ${c.priority}`);
      if (c.description) lines.push(`**描述：** ${c.description}`);
      if (Array.isArray(c.tags) && c.tags.length) {
        lines.push(`**标签：** ${c.tags.join(', ')}`);
      }
      
      if (Array.isArray(c.preconditions) && c.preconditions.length) {
        lines.push(`\n### 前置条件`);
        c.preconditions.forEach((p: any) => lines.push(`- ${p}`));
      }
      
      if (Array.isArray(c.test_steps) && c.test_steps.length) {
        lines.push(`\n### 测试步骤`);
        c.test_steps.forEach((s: any) => {
          lines.push(`\n**步骤 ${s.step_number}：** ${s.action || ''}`);
          if (s.expected_result) {
            lines.push(`- **预期结果：** ${s.expected_result}`);
          }
          if (s.test_data && Object.keys(s.test_data).length > 0) {
            lines.push(`- **测试数据：**`);
            lines.push(`  \`\`\`json`);
            lines.push(`  ${JSON.stringify(s.test_data, null, 2)}`);
            lines.push(`  \`\`\``);
          }
        });
      }
      
      if (c.expected_result) {
        lines.push(`\n### 总体预期结果`);
        lines.push(c.expected_result);
      }
      
      if (c.test_data && Object.keys(c.test_data).length > 0) {
        lines.push(`\n### 测试数据`);
        lines.push(`\`\`\`json`);
        lines.push(JSON.stringify(c.test_data, null, 2));
        lines.push(`\`\`\``);
      }
      
      lines.push(`\n---`);
    });
    return lines.join('\n');
  };

  const buildHtmlFromTestCases = (payload: any): string => {
    const esc = (s: any) => (s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'));
    const formatJson = (obj: any) => {
      if (!obj || typeof obj !== 'object') return esc(String(obj));
      try {
        return esc(JSON.stringify(obj, null, 2));
      } catch {
        return esc(String(obj));
      }
    };
    
    const cases = payload?.test_cases || [];
    const parts: string[] = ['<h1>测试用例集</h1>'];
    cases.forEach((c: any, i: number) => {
      parts.push(`<div style="margin-bottom: 40px; border-bottom: 1px solid #ddd; padding-bottom: 30px;">`);
      parts.push(`<h2>用例 ${i + 1} - ${esc(c.title || '')}</h2>`);
      parts.push(`<div style="margin-bottom: 10px;"><b>类型：</b>${esc(c.test_type || '')}</div>`);
      if (c.priority) parts.push(`<div style="margin-bottom: 10px;"><b>优先级：</b>${esc(c.priority)}</div>`);
      if (c.description) parts.push(`<div style="margin-bottom: 10px;"><b>描述：</b>${esc(c.description)}</div>`);
      if (Array.isArray(c.tags) && c.tags.length) {
        parts.push(`<div style="margin-bottom: 10px;"><b>标签：</b>${esc(c.tags.join(', '))}</div>`);
      }
      
      if (Array.isArray(c.preconditions) && c.preconditions.length) {
        parts.push('<h3 style="margin-top: 20px; margin-bottom: 10px;">前置条件</h3><ul style="padding-left: 20px;">');
        c.preconditions.forEach((p: any) => parts.push(`<li style="margin-bottom: 5px;">${esc(p)}</li>`));
        parts.push('</ul>');
      }
      
      if (Array.isArray(c.test_steps) && c.test_steps.length) {
        parts.push('<h3 style="margin-top: 20px; margin-bottom: 10px;">测试步骤</h3>');
        c.test_steps.forEach((s: any) => {
          parts.push(`<div style="margin-bottom: 15px; padding: 10px; background-color: #f5f5f5; border-left: 3px solid #1890ff;">`);
          parts.push(`<div style="font-weight: bold; margin-bottom: 5px;">步骤 ${s.step_number}：${esc(s.action || '')}</div>`);
          if (s.expected_result) {
            parts.push(`<div style="margin-left: 20px; margin-top: 5px; margin-bottom: 5px;"><b>预期结果：</b>${esc(s.expected_result)}</div>`);
          }
          if (s.test_data && Object.keys(s.test_data).length > 0) {
            parts.push(`<div style="margin-left: 20px; margin-top: 5px;"><b>测试数据：</b></div>`);
            parts.push(`<pre style="margin-left: 20px; padding: 8px; background-color: #fff; border: 1px solid #ddd; border-radius: 4px; overflow-x: auto; font-size: 12px;">${formatJson(s.test_data)}</pre>`);
          }
          parts.push('</div>');
        });
      }
      
      if (c.expected_result) {
        parts.push(`<h3 style="margin-top: 20px; margin-bottom: 10px;">总体预期结果</h3>`);
        parts.push(`<div style="padding: 10px; background-color: #f0f9ff; border-left: 3px solid #1890ff;">${esc(c.expected_result)}</div>`);
      }
      
      if (c.test_data && Object.keys(c.test_data).length > 0) {
        parts.push(`<h3 style="margin-top: 20px; margin-bottom: 10px;">测试数据</h3>`);
        parts.push(`<pre style="padding: 10px; background-color: #fff; border: 1px solid #ddd; border-radius: 4px; overflow-x: auto; font-size: 12px;">${formatJson(c.test_data)}</pre>`);
      }
      
      parts.push('</div>');
    });
    return parts.join('');
  };

  // 使用 markmap 技术生成思维导图（Markdown 格式）
  const buildMarkmapMarkdownForTestCases = (payload: any): string => {
    const cases = payload?.test_cases || [];
    const lines: string[] = [];
    
    lines.push('# 测试用例集\n');
    
    cases.forEach((c: any, idx: number) => {
      lines.push(`## 用例 ${idx + 1}: ${c.title || '用例'}\n`);
      
      if (c.test_type) lines.push(`- **类型**: ${c.test_type}`);
      if (c.priority) lines.push(`- **优先级**: ${c.priority}`);
      if (c.description) lines.push(`- **描述**: ${c.description}`);
      if (Array.isArray(c.tags) && c.tags.length) {
        lines.push(`- **标签**: ${c.tags.join(', ')}`);
      }
      
      if (Array.isArray(c.preconditions) && c.preconditions.length) {
        lines.push(`\n### 前置条件\n`);
        c.preconditions.forEach((p: any) => lines.push(`- ${p}`));
        lines.push('');
      }
      
      if (Array.isArray(c.test_steps) && c.test_steps.length) {
        lines.push(`\n### 测试步骤\n`);
        c.test_steps.forEach((s: any) => {
          lines.push(`#### 步骤 ${s.step_number}: ${s.action || ''}\n`);
          if (s.expected_result) {
            lines.push(`- **预期结果**: ${s.expected_result}`);
          }
          if (s.test_data && Object.keys(s.test_data).length > 0) {
            lines.push(`- **测试数据**: \`\`\`json\n${JSON.stringify(s.test_data, null, 2)}\n\`\`\``);
          }
          lines.push('');
        });
      }
      
      if (c.expected_result) {
        lines.push(`\n### 总体预期结果\n`);
        lines.push(`${c.expected_result}\n`);
      }
      
      if (c.test_data && Object.keys(c.test_data).length > 0) {
        lines.push(`\n### 测试数据\n`);
        lines.push(`\`\`\`json\n${JSON.stringify(c.test_data, null, 2)}\n\`\`\`\n`);
      }
      
      lines.push('---\n');
    });
    
    return lines.join('\n');
  };

  // 生成包含 markmap 渲染的 HTML 文件
  const buildMarkmapHtmlForTestCases = (payload: any): string => {
    const markdown = buildMarkmapMarkdownForTestCases(payload);
    // 使用 JSON.stringify 安全地嵌入 markdown 内容，避免转义问题
    const markdownJson = JSON.stringify(markdown);
    
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>测试用例思维导图</title>
  <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.18.12/dist/index.min.js" 
          onerror="console.error('markmap-lib 加载失败'); window._markmapLibError = true;"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12/dist/index.min.js"
          onerror="console.error('markmap-view 加载失败'); window._markmapViewError = true;"></script>
  <style>
    body {
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
      background: #f5f5f5;
    }
    #markmap {
      width: 100%;
      height: 100vh;
      background: white;
    }
    .toolbar {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 1000;
      background: white;
      padding: 10px;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .toolbar button {
      margin: 0 5px;
      padding: 5px 10px;
      cursor: pointer;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      background: white;
    }
    .toolbar button:hover {
      background: #f0f0f0;
    }
  </style>
</head>
<body>
  <div class="toolbar">
    <button onclick="fit()">适应视图</button>
    <button onclick="exportSVG()">导出 SVG</button>
    <button onclick="exportHTML()">导出 HTML</button>
  </div>
  <svg id="markmap"></svg>
  
  <script>
    // 初始化思维导图的函数
    function initMarkmap() {
      if (!window.markmap || !window.markmapLib) {
        console.error('Markmap 库未加载');
        document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图加载失败</h2><p>请检查网络连接，确保可以访问 CDN</p></div>';
        return;
      }
      
      const { Markmap } = window.markmap;
      const { Transformer } = window.markmapLib;
      
      const transformer = new Transformer();
      const mm = Markmap.create('#markmap', {
        color: (node) => {
          // 根据节点层级设置不同颜色
          const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];
          return colors[node.depth % colors.length] || '#666';
        },
        duration: 300,
        maxWidth: 300,
        initialExpandLevel: 2,
      });
      
      try {
        // 从 JSON 中解析 markdown 内容（安全方式）
        // markdownJson 已经是 JSON.stringify 的结果，直接使用
        const markdownContent = JSON.parse(${markdownJson});
        const { root } = transformer.transform(markdownContent);
        mm.setData(root);
        mm.fit();
      } catch (e) {
        console.error('解析或渲染失败:', e);
        document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图渲染失败</h2><p>' + e.message + '</p></div>';
      }
      
      window.fit = function() {
        mm.fit();
      };
      
      window.exportSVG = function() {
        const svg = document.getElementById('markmap');
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        const svgUrl = URL.createObjectURL(svgBlob);
        const downloadLink = document.createElement('a');
        downloadLink.href = svgUrl;
        downloadLink.download = '测试用例思维导图.svg';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        URL.revokeObjectURL(svgUrl);
      };
      
      window.exportHTML = function() {
        const html = document.documentElement.outerHTML;
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.download = '测试用例思维导图.html';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        URL.revokeObjectURL(url);
      };
    }
    
    // 等待脚本加载完成后初始化
    function initWhenReady() {
      // 检查是否有脚本加载错误
      if (window._markmapLibError || window._markmapViewError) {
        const errorMsg = window._markmapLibError ? 'markmap-lib' : 'markmap-view';
        document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图库加载失败</h2><p>' + errorMsg + ' 加载失败，请检查网络连接或尝试使用预览功能</p></div>';
        return;
      }
      
      if (window.markmap && window.markmapLib && window.markmap.Markmap && window.markmapLib.Transformer) {
        try {
          initMarkmap();
        } catch (e) {
          console.error('初始化失败:', e);
          const errorMsg = e instanceof Error ? e.message : String(e);
          document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图初始化失败</h2><p>' + errorMsg + '</p><p>请检查浏览器控制台获取详细错误信息</p></div>';
        }
      } else {
        // 等待最多 10 秒
        let tries = 0;
        const checkInterval = setInterval(() => {
          tries++;
          
          // 检查是否有加载错误
          if (window._markmapLibError || window._markmapViewError) {
            clearInterval(checkInterval);
            const errorMsg = window._markmapLibError ? 'markmap-lib' : 'markmap-view';
            document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图库加载失败</h2><p>' + errorMsg + ' 加载失败，请检查网络连接</p></div>';
            return;
          }
          
          if (window.markmap && window.markmapLib && window.markmap.Markmap && window.markmapLib.Transformer) {
            clearInterval(checkInterval);
            try {
              initMarkmap();
            } catch (e) {
              console.error('初始化失败:', e);
              const errorMsg = e instanceof Error ? e.message : String(e);
              document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图初始化失败</h2><p>' + errorMsg + '</p></div>';
            }
          } else if (tries > 100) {
            clearInterval(checkInterval);
            document.body.innerHTML = '<div style="padding: 20px; text-align: center;"><h2>思维导图加载超时</h2><p>库加载超时（10秒），请检查网络连接，确保可以访问 CDN</p><p>如果问题持续，请尝试使用预览功能</p></div>';
          }
        }, 100);
      }
    }
    
    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initWhenReady);
    } else {
      setTimeout(initWhenReady, 200);
    }
  </script>
</body>
</html>`;
  };

  // 保留旧的 Freemind XML 生成函数（向后兼容）
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const buildFreemindXmlForTestCases = (payload: any): string => {
    const esc = (s: any) => (s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'));
    const cases = payload?.test_cases || [];
    const lines: string[] = [];
    lines.push('<?xml version="1.0" encoding="UTF-8"?>');
    lines.push('<map version="0.9.0">');
    lines.push('<node TEXT="测试用例集">');
    cases.forEach((c: any, idx: number) => {
      lines.push(`<node TEXT="用例${idx + 1}: ${esc(c.title || '用例')}">`);
      if (c.test_type) lines.push(`<node TEXT="类型: ${esc(c.test_type)}"/>`);
      if (c.priority) lines.push(`<node TEXT="优先级: ${esc(c.priority)}"/>`);
      if (c.description) lines.push(`<node TEXT="描述: ${esc(c.description)}"/>`);
      if (Array.isArray(c.tags) && c.tags.length) {
        lines.push(`<node TEXT="标签: ${esc(c.tags.join(', '))}"/>`);
      }
      if (Array.isArray(c.preconditions) && c.preconditions.length) {
        lines.push('<node TEXT="前置条件">');
        c.preconditions.forEach((p: any) => lines.push(`<node TEXT="${esc(p)}"/>`));
        lines.push('</node>');
      }
      if (Array.isArray(c.test_steps) && c.test_steps.length) {
        lines.push('<node TEXT="测试步骤">');
        c.test_steps.forEach((s: any) => {
          lines.push(`<node TEXT="步骤${s.step_number}: ${esc(s.action || '')}">`);
          if (s.expected_result) {
            lines.push(`<node TEXT="预期结果: ${esc(s.expected_result)}"/>`);
          }
          if (s.test_data && Object.keys(s.test_data).length > 0) {
            lines.push(`<node TEXT="测试数据: ${esc(JSON.stringify(s.test_data))}"/>`);
          }
          lines.push('</node>');
        });
        lines.push('</node>');
      }
      if (c.expected_result) {
        lines.push(`<node TEXT="总体预期结果: ${esc(c.expected_result)}"/>`);
      }
      if (c.test_data && Object.keys(c.test_data).length > 0) {
        lines.push(`<node TEXT="测试数据: ${esc(JSON.stringify(c.test_data))}"/>`);
      }
      lines.push('</node>');
    });
    lines.push('</node></map>');
    return lines.join('');
  };

  const handleDownloadTestCases = (type: 'json' | 'markdown' | 'pdf' | 'excel' | 'word' | 'mindmap') => {
    const data = getTestCasesData();
    if (!data) {
      message.warning('请先生成测试用例');
      return;
    }
    switch (type) {
      case 'json': {
        const str = JSON.stringify(data, null, 2);
        const blob = new Blob([str], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `测试用例_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        message.success('文件下载开始');
        break;
      }
      case 'markdown': {
        const md = buildMarkdownFromTestCases(data);
        const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `测试用例_${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        message.success('Markdown 下载开始');
        break;
      }
      case 'pdf': {
        const container = document.createElement('div');
        container.style.width = '800px';
        container.style.padding = '24px';
        container.style.background = '#fff';
        container.style.fontFamily = '"Microsoft YaHei", Arial, sans-serif';
        container.style.lineHeight = '1.6';
        container.innerHTML = buildHtmlFromTestCases(data);
        document.body.appendChild(container);
        html2canvas(container, { 
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff'
        }).then((canvas) => {
          const imgData = canvas.toDataURL('image/png', 1.0);
          const pdf = new jsPDF({ orientation: 'p', unit: 'pt', format: 'a4' });
          const pageWidth = pdf.internal.pageSize.getWidth();
          const pageHeight = pdf.internal.pageSize.getHeight();
          const margin = 40; // 页面边距
          const imgWidth = pageWidth - (margin * 2);
          const imgHeight = (canvas.height * imgWidth) / canvas.width;

          // 修复分页逻辑，避免空白页和重复内容
          let heightLeft = imgHeight;
          let position = -margin;
          
          // 添加第一页
          pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
          heightLeft -= (pageHeight - margin * 2);

          // 如果内容超过一页，继续添加页面
          while (heightLeft > 10) { // 10pt的容差，避免因小数导致的空白页
            pdf.addPage();
            position = -margin - (imgHeight - heightLeft); // 计算正确的Y位置偏移
            pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
            heightLeft -= (pageHeight - margin * 2);
          }
          
          pdf.save(`测试用例_${new Date().toISOString().split('T')[0]}.pdf`);
          document.body.removeChild(container);
          message.success('PDF 下载开始');
        }).catch((e) => {
          console.error(e);
          message.error('PDF 导出失败');
        });
        break;
      }
      case 'excel': {
        const cases = data.test_cases || [];
        const wb = XLSX.utils.book_new();
        
        // 为每个测试用例创建一个详细的数据行
        const rows: any[] = [];
        cases.forEach((c: any, idx: number) => {
          // 基本信息行
          rows.push({
            '用例编号': idx + 1,
            '标题': c.title || '',
            '类型': c.test_type || '',
            '优先级': c.priority || '',
            '描述': c.description || '',
            '标签': Array.isArray(c.tags) ? c.tags.join(', ') : '',
            '前置条件': Array.isArray(c.preconditions) ? c.preconditions.join('; ') : '',
            '总体预期结果': c.expected_result || '',
            '测试数据': c.test_data ? JSON.stringify(c.test_data, null, 2) : '',
            '步骤详情': '', // 将在下一行展开
          });
          
          // 步骤详情行
          if (Array.isArray(c.test_steps) && c.test_steps.length > 0) {
            c.test_steps.forEach((step: any, stepIdx: number) => {
              rows.push({
                '用例编号': idx + 1,
                '标题': '',
                '类型': '',
                '优先级': '',
                '描述': '',
                '标签': '',
                '前置条件': '',
                '总体预期结果': '',
                '测试数据': step.test_data ? JSON.stringify(step.test_data, null, 2) : '',
                '步骤详情': `步骤${step.step_number}: ${step.action || ''} | 预期结果: ${step.expected_result || ''}`,
              });
            });
          }
        });
        
        const sheet = XLSX.utils.json_to_sheet(rows);
        XLSX.utils.book_append_sheet(wb, sheet, '测试用例');
        const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
        const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `测试用例_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        message.success('Excel 下载开始');
        break;
      }
      case 'word': {
        (async () => {
          try {
            const cases = data.test_cases || [];
            const htmlParts: string[] = [];
            
            htmlParts.push('<!DOCTYPE html>');
            htmlParts.push('<html>');
            htmlParts.push('<head>');
            htmlParts.push('<meta charset="UTF-8">');
            htmlParts.push('<meta name="ProgId" content="Word.Document">');
            htmlParts.push('<style>');
            htmlParts.push('body { font-family: "Microsoft YaHei", Arial, sans-serif; padding: 20px; line-height: 1.6; }');
            htmlParts.push('h1 { border-bottom: 2px solid #333; padding-bottom: 10px; }');
            htmlParts.push('h2 { color: #666; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }');
            htmlParts.push('h3 { color: #888; margin-top: 20px; margin-bottom: 10px; }');
            htmlParts.push('ol, ul { margin-left: 20px; }');
            htmlParts.push('li { margin-bottom: 10px; line-height: 1.6; }');
            htmlParts.push('pre { background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd; border-radius: 4px; overflow-x: auto; font-size: 12px; }');
            htmlParts.push('.step-box { margin-bottom: 15px; padding: 10px; background-color: #f5f5f5; border-left: 3px solid #1890ff; }');
            htmlParts.push('</style>');
            htmlParts.push('</head>');
            htmlParts.push('<body>');
            htmlParts.push('<h1>测试用例集</h1>');
            
            cases.forEach((c: any, i: number) => {
              htmlParts.push(`<div style="margin-bottom: 40px; border-bottom: 1px solid #ddd; padding-bottom: 30px;">`);
              htmlParts.push(`<h2>用例 ${i + 1} - ${c.title || ''}</h2>`);
              htmlParts.push(`<p><strong>类型：</strong>${c.test_type || ''}</p>`);
              if (c.priority) htmlParts.push(`<p><strong>优先级：</strong>${c.priority}</p>`);
              if (c.description) htmlParts.push(`<p><strong>描述：</strong>${c.description}</p>`);
              if (Array.isArray(c.tags) && c.tags.length) {
                htmlParts.push(`<p><strong>标签：</strong>${c.tags.join(', ')}</p>`);
              }
              
              if (Array.isArray(c.preconditions) && c.preconditions.length) {
                htmlParts.push('<h3>前置条件</h3><ul>');
                c.preconditions.forEach((p: any) => htmlParts.push(`<li>${p}</li>`));
                htmlParts.push('</ul>');
              }
              
              if (Array.isArray(c.test_steps) && c.test_steps.length) {
                htmlParts.push('<h3>测试步骤</h3>');
                c.test_steps.forEach((s: any) => {
                  htmlParts.push(`<div class="step-box">`);
                  htmlParts.push(`<p><strong>步骤 ${s.step_number}：</strong>${s.action || ''}</p>`);
                  if (s.expected_result) {
                    htmlParts.push(`<p style="margin-left: 20px;"><strong>预期结果：</strong>${s.expected_result}</p>`);
                  }
                  if (s.test_data && Object.keys(s.test_data).length > 0) {
                    htmlParts.push(`<p style="margin-left: 20px;"><strong>测试数据：</strong></p>`);
                    htmlParts.push(`<pre style="margin-left: 20px;">${JSON.stringify(s.test_data, null, 2)}</pre>`);
                  }
                  htmlParts.push('</div>');
                });
              }
              
              if (c.expected_result) {
                htmlParts.push(`<h3>总体预期结果</h3>`);
                htmlParts.push(`<p>${c.expected_result}</p>`);
              }
              
              if (c.test_data && Object.keys(c.test_data).length > 0) {
                htmlParts.push(`<h3>测试数据</h3>`);
                htmlParts.push(`<pre>${JSON.stringify(c.test_data, null, 2)}</pre>`);
              }
              
              htmlParts.push('</div>');
            });
            
            htmlParts.push('</body>');
            htmlParts.push('</html>');
            
            const htmlContent = htmlParts.join('\n');
            const blob = new Blob(['\ufeff', htmlContent], { type: 'application/msword' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `测试用例_${new Date().toISOString().split('T')[0]}.doc`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            message.success('Word 文档下载开始');
          } catch (e) {
            console.error(e);
            message.error('Word 导出失败');
          }
        })();
        break;
      }
      case 'mindmap': {
        // 生成图片格式的思维导图
        const filename = `测试用例思维导图_${new Date().toISOString().split('T')[0]}.png`;
        downloadMindmapAsImage(data, 'testcase', filename);
        break;
      }
      default:
        return;
    }
  };

  // 处理API文档上传
  const handleAPIDocumentUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    const fileObj = file as File;
    
    // 验证文件类型
    const fileExt = fileObj.name.split('.').pop()?.toLowerCase();
    const allowedExts = ['json', 'yaml', 'yml'];
    
    if (!fileExt || !allowedExts.includes(fileExt)) {
      message.error('不支持的文件格式。仅支持: OpenAPI/Swagger (.json, .yaml, .yml), Postman Collection (.json)');
      onError?.(new Error('不支持的文件格式'));
      return;
    }
    
    // 验证文件大小（最大10MB）
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (fileObj.size > maxSize) {
      message.error('文件大小不能超过10MB');
      onError?.(new Error('文件大小超过限制'));
      return;
    }
    
    try {
      message.loading({ content: '正在解析API文档...', key: 'parse-api-doc', duration: 0 });
      
      const result = await parseAPIDocument(fileObj);
      
      if (result.success && result.parsed_doc) {
        // 保存解析后的文档
        setParsedAPIDoc(result.parsed_doc);
        
        // 自动填充表单
        apiTestForm.setFieldsValue({
          api_documentation: result.summary,
          base_url: result.base_url || apiTestFormData.base_url || ''
        });
        
        // 更新表单数据状态
        setApiTestFormData({
          ...apiTestFormData,
          api_documentation: result.summary,
          base_url: result.base_url || apiTestFormData.base_url || ''
        });
        
        message.success({
          content: `API文档解析成功！发现 ${result.endpoints_count} 个接口。文件名: ${result.filename}`,
          key: 'parse-api-doc',
          duration: 4
        });
        
        onSuccess?.(result);
      } else {
        throw new Error('API文档解析失败：未提取到接口信息');
      }
    } catch (error: any) {
      const errorMsg = error.message || 'API文档解析失败';
      message.error({
        content: errorMsg,
        key: 'parse-api-doc',
        duration: 4
      });
      onError?.(error);
    }
  };

  const handleAPITestGeneration = async (values: any) => {
    setLoading(true);
    setProgressVisible(true);
    setProgress(0);
    try {
      // 如果已解析API文档，传递parsed_doc
      const requestData: any = {
        api_documentation: values.api_documentation,
        base_url: values.base_url,
        test_scenarios: values.test_scenarios || []
      };
      
      if (parsedAPIDoc) {
        requestData.parsed_doc = parsedAPIDoc;
      }
      
      const response = await generateAPITests(requestData);
      setResults({ type: 'api_test_generation', data: response });
      message.success('API测试生成完成！');
    } catch (error) {
      message.error('API测试生成失败，请重试');
    } finally {
      setLoading(false);
      setProgressVisible(false);
    }
  };

  // 处理页面分析
  const handlePageAnalysis = async (pageUrl: string) => {
    if (!pageUrl || !pageUrl.trim()) {
      message.warning('请输入页面URL');
      return;
    }
    
    // 验证URL格式
    try {
      new URL(pageUrl);
    } catch {
      message.error('URL格式不正确，请输入完整的URL（如：https://example.com）');
      return;
    }
    
    setLoading(true);
    try {
      message.loading({ content: '正在分析页面结构...', key: 'analyze-page', duration: 0 });
      
      const result = await analyzePage(pageUrl, 2000);
      
      if (result.success && result.page_info) {
        // 保存页面分析结果
        setAnalyzedPageInfo(result.page_info);
        
        // 自动填充表单
        uiTestForm.setFieldsValue({
          page_url: pageUrl
        });
        
        // 更新表单数据状态
        setUITestFormData({
          ...uiTestFormData,
          page_url: pageUrl
        });
        
        const elementCount = result.page_info.element_count || {};
        message.success({
          content: `页面分析成功！发现 ${elementCount.buttons || 0} 个按钮，${elementCount.inputs || 0} 个输入框，${elementCount.forms || 0} 个表单。`,
          key: 'analyze-page',
          duration: 5
        });
      } else {
        throw new Error('页面分析失败：未获取到页面信息');
      }
    } catch (error: any) {
      const errorMsg = error.message || '页面分析失败';
      message.error({
        content: errorMsg,
        key: 'analyze-page',
        duration: 4
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUITestGeneration = async (values: any) => {
    setLoading(true);
    setProgressVisible(true);
    setProgress(0);
    try {
      // 处理user_actions：如果是字符串，保持字符串；如果是数组，转换为数组
      let userActions: string | string[] = values.user_actions;
      if (typeof userActions === 'string' && userActions.trim()) {
        // 如果是字符串，保持原样（业务需求描述）
        userActions = userActions.trim();
      } else if (Array.isArray(userActions) && userActions.length > 0) {
        // 如果是数组，保持数组格式
        userActions = userActions;
      } else {
        // 如果为空，设置为空字符串（让AI自动推断）
        userActions = "";
      }
      
      // 如果已分析页面，传递page_info
      const requestData: any = {
        page_url: values.page_url,
        user_actions: userActions,
        test_scenarios: values.test_scenarios || []
      };
      
      if (analyzedPageInfo) {
        requestData.page_info = analyzedPageInfo;
      }
      
      const response = await generateUITests(requestData);
      setResults({ type: 'ui_test_generation', data: response });
      message.success('UI测试生成完成！');
    } catch (error) {
      message.error('UI测试生成失败，请重试');
    } finally {
      setLoading(false);
      setProgressVisible(false);
    }
  };

  // 从测试用例生成自动化测试脚本
  const handleGenerateScriptFromTestCase = async () => {
    const testCaseData = testCasesJson || results?.data;
    if (!testCaseData || !testCaseData.test_cases || testCaseData.test_cases.length === 0) {
      message.warning('请先生成测试用例');
      return;
    }

    const firstTestCase = testCaseData.test_cases[0];
    const testType = firstTestCase.test_type;

    if (testType === 'api') {
      // 从测试用例中提取API信息
      const apiDoc = extractAPIDocFromTestCase(testCaseData.test_cases);
      const baseUrl = extractBaseURLFromTestCase(testCaseData.test_cases);
      
      if (!apiDoc) {
        message.warning('无法从测试用例中提取API文档信息，请使用API测试生成功能手动输入');
        return;
      }

      setLoading(true);
      try {
        const response = await generateAPITests({
          api_documentation: apiDoc,
          base_url: baseUrl || 'http://localhost:8000',
          test_scenarios: ['normal', 'error', 'boundary']
        });
        // 切换到API测试生成Tab并显示结果
        setResults({ type: 'api_test_generation', data: response });
        message.success('API测试脚本生成完成！请在"API测试生成"Tab查看结果');
      } catch (error: any) {
        console.error('API测试脚本生成失败:', error);
        const errorMsg = error?.response?.data?.detail || error?.message || 'API测试脚本生成失败，请重试';
        message.error(errorMsg);
      } finally {
        setLoading(false);
      }
    } else if (testType === 'ui') {
      // 从测试用例中提取UI信息
      const pageUrl = extractPageURLFromTestCase(testCaseData.test_cases);
      const userActions = extractUserActionsFromTestCase(testCaseData.test_cases);
      
      // 如果提取不到用户操作，从测试步骤中提取
      let finalUserActions: string[] = [...userActions];
      if (finalUserActions.length === 0) {
        testCaseData.test_cases.forEach((tc: any) => {
          if (tc.test_steps) {
            tc.test_steps.forEach((step: any) => {
              if (step.action) {
                finalUserActions.push(step.action);
              }
            });
          }
        });
        // 去重
        finalUserActions = Array.from(new Set(finalUserActions));
      }

      if (finalUserActions.length === 0) {
        finalUserActions = ['执行测试操作'];
      }

      setLoading(true);
      try {
        const response = await generateUITests({
          page_url: pageUrl || 'http://localhost:3000',
          user_actions: finalUserActions.slice(0, 10), // 限制数量避免过长
          test_scenarios: ['normal', 'error']
        });
        // 切换到UI测试生成Tab并显示结果
        setResults({ type: 'ui_test_generation', data: response });
        message.success('UI测试脚本生成完成！请在"UI测试生成"Tab查看结果');
      } catch (error: any) {
        console.error('UI测试脚本生成失败:', error);
        const errorMsg = error?.response?.data?.detail || error?.message || 'UI测试脚本生成失败，请重试';
        message.error(errorMsg);
      } finally {
        setLoading(false);
      }
    } else {
      message.info('功能测试用例暂不支持自动生成脚本，请手动编写测试代码');
    }
  };

  // 从测试用例中提取API文档信息
  const extractAPIDocFromTestCase = (testCases: any[]): string => {
    const apiInfo: string[] = [];
    testCases.forEach((tc: any) => {
      if (tc.test_data?.request_method && tc.test_data?.request_url) {
        apiInfo.push(`${tc.test_data.request_method} ${tc.test_data.request_url}`);
        if (tc.test_data.request_headers) {
          apiInfo.push(`Headers: ${JSON.stringify(tc.test_data.request_headers)}`);
        }
        if (tc.test_data.request_body) {
          apiInfo.push(`Body: ${JSON.stringify(tc.test_data.request_body)}`);
        }
        if (tc.expected_result) {
          apiInfo.push(`Expected: ${tc.expected_result}`);
        }
        apiInfo.push('---');
      }
    });
    return apiInfo.join('\n') || testCases.map((tc: any) => tc.title + ': ' + tc.description).join('\n');
  };

  // 从测试用例中提取基础URL
  const extractBaseURLFromTestCase = (testCases: any[]): string => {
    for (const tc of testCases) {
      if (tc.test_data?.request_url) {
        const url = tc.test_data.request_url;
        // 尝试从完整URL中提取基础URL
        try {
          const urlObj = new URL(url);
          return `${urlObj.protocol}//${urlObj.host}`;
        } catch {
          // 如果不是完整URL，返回默认值
          return 'http://localhost:8000';
        }
      }
    }
    return 'http://localhost:8000';
  };

  // 从测试用例中提取页面URL
  const extractPageURLFromTestCase = (testCases: any[]): string => {
    for (const tc of testCases) {
      if (tc.test_data?.page_url) {
        return tc.test_data.page_url;
      }
    }
    // 从test_steps中查找URL相关信息
    for (const tc of testCases) {
      if (tc.test_steps) {
        for (const step of tc.test_steps) {
          if (step.test_data?.expected_url) {
            return step.test_data.expected_url;
          }
          // 尝试从action中提取URL信息
          if (step.action && step.action.includes('http')) {
            const urlMatch = step.action.match(/https?:\/\/[^\s]+/);
            if (urlMatch) {
              return urlMatch[0];
            }
          }
        }
      }
    }
    // 如果实在找不到，返回一个默认值，让用户手动输入
    return 'http://localhost:3000'; // 默认本地开发地址
  };

  // 从测试用例中提取用户操作
  const extractUserActionsFromTestCase = (testCases: any[]): string[] => {
    const actions: string[] = [];
    testCases.forEach((tc: any) => {
      if (tc.test_steps) {
        tc.test_steps.forEach((step: any) => {
          if (step.action && step.test_data?.action_type) {
            actions.push(step.action);
          }
        });
      }
    });
    // 去重
    const uniqueActions = Array.from(new Set(actions));
    return uniqueActions;
  };

  // 下载脚本文件
  const handleDownloadScript = (code: string, filename: string) => {
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success(`已下载: ${filename}`);
  };

  // 提取Python代码（处理python_code可能是对象或字符串的情况）
  // 统一的转义字符处理函数
  // 只处理JSON字符串中的转义字符，不做任何其他修改
  const unescapeCodeString = (str: string): string => {
    if (!str) return '';
    
    // 处理JSON字符串中的转义字符
    // 使用简单的顺序处理，确保不会误处理
    let result = str;
    
    // 按顺序处理：先处理双重转义，再处理单转义，最后处理反斜杠
    // 双重转义（可能在嵌套的JSON字符串中）
    result = result
      .replace(/\\\\n/g, '\n')
      .replace(/\\\\r/g, '\r')
      .replace(/\\\\t/g, '\t')
      .replace(/\\\\"/g, '"')
      .replace(/\\\\'/g, "'");
    
    // 单转义
    result = result
      .replace(/\\n/g, '\n')
      .replace(/\\r/g, '\r')
      .replace(/\\t/g, '\t')
      .replace(/\\"/g, '"')
      .replace(/\\'/g, "'")
      .replace(/\\b/g, '\b')
      .replace(/\\f/g, '\f');
    
    // 处理剩余的反斜杠（成对的反斜杠变成一个）
    // 只处理成对的反斜杠，避免处理单个反斜杠
    result = result.replace(/\\\\/g, '\\');
    
    return result;
  };

  const extractPythonCode = (pythonCode: any): string => {
    if (!pythonCode) return '';
    
    // 如果是字符串，先处理转义字符
    if (typeof pythonCode === 'string') {
      return unescapeCodeString(pythonCode);
    }
    
    // 如果是对象，尝试提取代码
    if (typeof pythonCode === 'object') {
      // 优先选择 selenium，然后是 playwright，再是其他
      if (pythonCode.selenium) {
        return typeof pythonCode.selenium === 'string' ? unescapeCodeString(pythonCode.selenium) : '';
      }
      if (pythonCode.playwright) {
        return typeof pythonCode.playwright === 'string' ? unescapeCodeString(pythonCode.playwright) : '';
      }
      // 如果有其他键，使用第一个非空字符串值
      for (const key in pythonCode) {
        if (typeof pythonCode[key] === 'string' && pythonCode[key].trim()) {
          return unescapeCodeString(pythonCode[key]);
        }
      }
    }
    
    return '';
  };

  // 提取测试脚本代码（支持工程化结构）
  const extractScriptCode = (data: any): string => {
    if (!data) return '';
    
    // 如果是工程化结构（新格式）
    if (data.status === 'success' && (data.project_structure || data.api_client_class || data.api_tests)) {
      const allCode: string[] = [];
      
      // 1. 项目结构说明
      if (data.project_structure) {
        allCode.push('# ============================================');
        allCode.push('# 项目结构说明');
        allCode.push('# ============================================');
        allCode.push(data.project_structure.description || '');
        allCode.push('');
        if (data.project_structure.directories) {
          allCode.push('## 目录结构');
          data.project_structure.directories.forEach((dir: string) => {
            allCode.push(`# ${dir}`);
          });
          allCode.push('');
        }
        if (data.project_structure.files) {
          allCode.push('## 文件列表');
          data.project_structure.files.forEach((file: string) => {
            allCode.push(`# ${file}`);
          });
          allCode.push('');
        }
      }
      
      // 2. API客户端类
      if (data.api_client_class && data.api_client_class.code) {
        allCode.push('# ============================================');
        allCode.push(`# ${data.api_client_class.class_name || 'APIClient'}`);
        allCode.push(`# ${data.api_client_class.description || ''}`);
        allCode.push('# ============================================');
        allCode.push(extractPythonCode(data.api_client_class.code));
        allCode.push('');
      }
      
      // 3. 配置文件
      if (data.config_file && data.config_file.code) {
        allCode.push('# ============================================');
        allCode.push(`# ${data.config_file.file_name || 'config/settings.py'}`);
        allCode.push(`# ${data.config_file.description || '配置文件'}`);
        allCode.push('# ============================================');
        allCode.push(extractPythonCode(data.config_file.code));
        allCode.push('');
      }
      
      // 4. conftest.py
      if (data.conftest && data.conftest.code) {
        allCode.push('# ============================================');
        allCode.push('# conftest.py');
        allCode.push(`# ${data.conftest.description || 'pytest配置文件'}`);
        allCode.push('# ============================================');
        allCode.push(extractPythonCode(data.conftest.code));
        allCode.push('');
      }
      
      // 5. API测试文件
      if (data.api_tests && Array.isArray(data.api_tests)) {
        data.api_tests.forEach((test: any) => {
          allCode.push('# ============================================');
          allCode.push(`# ${test.file_name || 'test_api.py'}`);
          allCode.push(`# ${test.class_name || 'TestAPI'}`);
          allCode.push(`# ${test.description || ''}`);
          allCode.push('# ============================================');
          
          // 优先使用full_class_code，如果没有则组合test_methods
          if (test.full_class_code) {
            allCode.push(extractPythonCode(test.full_class_code));
          } else if (test.test_methods && Array.isArray(test.test_methods)) {
            allCode.push(`class ${test.class_name || 'TestAPI'}:`);
            test.test_methods.forEach((method: any) => {
              allCode.push('');
              allCode.push(`    # ${method.description || ''}`);
              allCode.push(`    ${extractPythonCode(method.code)}`);
            });
          }
          allCode.push('');
        });
      }
      
      // 6. requirements.txt
      if (data.requirements && data.requirements.packages) {
        allCode.push('# ============================================');
        allCode.push('# requirements.txt');
        allCode.push(`# ${data.requirements.description || '依赖包列表'}`);
        allCode.push('# ============================================');
        data.requirements.packages.forEach((pkg: string) => {
          allCode.push(pkg);
        });
        allCode.push('');
      }
      
      // 7. README.md
      if (data.readme && data.readme.content) {
        allCode.push('# ============================================');
        allCode.push('# README.md');
        allCode.push(`# ${data.readme.description || '项目说明文档'}`);
        allCode.push('# ============================================');
        allCode.push(data.readme.content);
        allCode.push('');
      }
      
      return allCode.join('\n');
    }
    
    // 如果是数组，提取所有测试的代码（旧格式兼容）
    if (Array.isArray(data)) {
      const allCode: string[] = [];
      data.forEach((test: any, index: number) => {
        const code = extractPythonCode(test.python_code) || test.code || '';
        if (code) {
          allCode.push(`# ${test.name || `Test ${index + 1}`}`);
          allCode.push(code);
          allCode.push('');
        }
      });
      return allCode.join('\n');
    }
    
    // 如果是对象，检查是否有api_tests或ui_tests（旧格式兼容）
    if (data.api_tests && Array.isArray(data.api_tests)) {
      const allCode: string[] = [];
      if (data.test_suite?.setup_code) {
        allCode.push('# Setup Code');
        allCode.push(data.test_suite.setup_code);
        allCode.push('');
      }
      data.api_tests.forEach((test: any, index: number) => {
        // 先尝试从python_code提取
        let code = extractPythonCode(test.python_code) || test.code || '';
        
        // 如果code为空，但description或raw_response包含JSON，尝试从那里提取
        if (!code && (test.description || test.raw_response)) {
          const rawContent = test.description || test.raw_response || '';
          // 尝试从原始内容中提取python_code
          try {
            // 尝试直接解析JSON
            if (rawContent.trim().startsWith('{') || rawContent.includes('```json')) {
              let jsonContent = rawContent;
              // 如果是markdown代码块，先提取JSON
              const jsonMatch = rawContent.match(/```json\s*([\s\S]*?)```/);
              if (jsonMatch) {
                jsonContent = jsonMatch[1];
              }
              const parsed = JSON.parse(jsonContent);
              if (parsed.api_tests && parsed.api_tests[0]?.python_code) {
                code = extractPythonCode(parsed.api_tests[0].python_code);
              } else if (parsed.python_code) {
                code = extractPythonCode(parsed.python_code);
              }
            }
          } catch (e) {
            // 解析失败，忽略
          }
        }
        
        if (code) {
          allCode.push(`# ${test.name || `API Test ${index + 1}`}`);
          allCode.push(code);
          allCode.push('');
        }
      });
      if (data.test_suite?.teardown_code) {
        allCode.push('# Teardown Code');
        allCode.push(data.test_suite.teardown_code);
      }
      return allCode.join('\n');
    }
    
    if (data.ui_tests && Array.isArray(data.ui_tests)) {
      const allCode: string[] = [];
      if (data.test_suite?.setup_code) {
        allCode.push('# Setup Code');
        allCode.push(data.test_suite.setup_code);
        allCode.push('');
      }
      data.ui_tests.forEach((test: any, index: number) => {
        // 先尝试从python_code提取
        let code = extractPythonCode(test.python_code) || test.code || '';
        
        // 如果code为空，但description或raw_response包含JSON，尝试从那里提取
        if (!code && (test.description || test.raw_response)) {
          const rawContent = test.description || test.raw_response || '';
          // 尝试从原始内容中提取python_code
          try {
            // 方法1: 尝试解析完整的JSON
            const jsonMatch = rawContent.match(/```json\s*([\s\S]*?)```/);
            if (jsonMatch) {
              try {
                const parsed = JSON.parse(jsonMatch[1]);
                if (parsed.ui_tests && parsed.ui_tests[0]?.python_code) {
                  code = extractPythonCode(parsed.ui_tests[0].python_code);
                } else if (parsed.python_code) {
                  code = extractPythonCode(parsed.python_code);
                }
              } catch (parseError) {
                // JSON解析失败，可能是被截断了，尝试用正则表达式提取
                // 方法2: 从JSON字符串中直接提取python_code字段（即使JSON不完整）
                const pythonCodeMatch = jsonMatch[1].match(/"python_code"\s*:\s*\{[^}]*"(?:selenium|playwright)"\s*:\s*"((?:[^"\\]|\\.)*)"/);
                if (pythonCodeMatch) {
                  code = pythonCodeMatch[1]
                    .replace(/\\n/g, '\n')
                    .replace(/\\"/g, '"')
                    .replace(/\\t/g, '\t')
                    .replace(/\\\\/g, '\\');
                } else {
                  // 方法3: 尝试提取简单的python_code字符串
                  const simplePythonCodeMatch = jsonMatch[1].match(/"python_code"\s*:\s*"((?:[^"\\]|\\.)*)"/);
                  if (simplePythonCodeMatch) {
                    code = simplePythonCodeMatch[1]
                      .replace(/\\n/g, '\n')
                      .replace(/\\"/g, '"')
                      .replace(/\\t/g, '\t')
                      .replace(/\\\\/g, '\\');
                  }
                }
              }
            } else if (rawContent.trim().startsWith('{')) {
              // 如果没有markdown代码块，但内容是JSON格式，尝试直接解析
              try {
                const parsed = JSON.parse(rawContent);
                if (parsed.ui_tests && parsed.ui_tests[0]?.python_code) {
                  code = extractPythonCode(parsed.ui_tests[0].python_code);
                }
              } catch (e) {
                // 解析失败，尝试正则提取
                const pythonCodeMatch = rawContent.match(/"python_code"\s*:\s*\{[^}]*"(?:selenium|playwright)"\s*:\s*"((?:[^"\\]|\\.)*)"/);
                if (pythonCodeMatch) {
                  code = pythonCodeMatch[1]
                    .replace(/\\n/g, '\n')
                    .replace(/\\"/g, '"')
                    .replace(/\\t/g, '\t')
                    .replace(/\\\\/g, '\\');
                }
              }
            }
            
            // 方法4: 如果还没找到，尝试查找Python代码块
            if (!code) {
              const pythonBlockMatch = rawContent.match(/```(?:python)?\s*\n([\s\S]*?)\n```/);
              if (pythonBlockMatch) {
                code = pythonBlockMatch[1].trim();
              }
            }
          } catch (e) {
            // 所有方法都失败，忽略
            console.warn('提取代码失败:', e);
          }
        }
        
        if (code) {
          allCode.push(`# ${test.name || `UI Test ${index + 1}`}`);
          allCode.push(code);
          allCode.push('');
        }
      });
      if (data.test_suite?.teardown_code) {
        allCode.push('# Teardown Code');
        allCode.push(data.test_suite.teardown_code);
      }
      return allCode.join('\n');
    }
    
    // 如果没有找到代码，返回JSON格式化输出
    return JSON.stringify(data, null, 2);
  };

  const renderResults = () => {
    if (!results) return null;

    let title = "AI生成结果";
    let isScript = false;
    if (results.type === 'api_test_generation') {
      title = "生成的API测试脚本";
      isScript = true;
    } else if (results.type === 'ui_test_generation') {
      title = "生成的UI测试脚本";
      isScript = true;
    }

    const scriptCode = isScript ? extractScriptCode(results.data) : null;
    const hasCode = scriptCode && scriptCode.trim().length > 0 && !scriptCode.startsWith('{');

    return (
      <Card 
        title={title} 
        style={{ marginTop: 16 }}
        extra={
          isScript && hasCode && (
            <Space>
              <Button 
                icon={<FileTextOutlined />}
                onClick={() => {
                  if (scriptCode) {
                    navigator.clipboard.writeText(scriptCode).then(() => {
                      message.success('代码已复制到剪贴板');
                    }).catch(() => {
                      message.error('复制失败');
                    });
                  }
                }}
              >
                复制代码
              </Button>
              <Button 
                type="primary"
                icon={<CodeOutlined />}
                onClick={() => {
                  if (scriptCode) {
                    const filename = results.type === 'api_test_generation' 
                      ? `api_tests_${new Date().toISOString().split('T')[0]}.py`
                      : `ui_tests_${new Date().toISOString().split('T')[0]}.py`;
                    handleDownloadScript(scriptCode, filename);
                  }
                }}
              >
                下载脚本
              </Button>
            </Space>
          )
        }
      >
        {isScript && hasCode ? (
          <pre style={{ 
            background: colorFillSecondary, 
            padding: 16, 
            borderRadius: 6, 
            overflow: 'auto', 
            maxHeight: '600px',
            margin: 0,
            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
            fontSize: '13px',
            lineHeight: '1.5'
          }}>
            {scriptCode}
          </pre>
        ) : (
          <pre style={{ background: colorFillSecondary, padding: 16, borderRadius: 6, overflow: 'auto', maxHeight: '600px' }}>
          {JSON.stringify(results.data, null, 2)}
        </pre>
        )}
        {isScript && (
          <div style={{ marginTop: 12 }}>
            <Typography.Text type="secondary">
              💡 提示：这是基于您的测试用例自动生成的{results.type === 'api_test_generation' ? 'API' : 'UI'}自动化测试脚本。
              {hasCode ? '您可以复制代码或下载.py文件，然后在测试框架中使用。' : '请检查生成的JSON结构，可能包含更多测试信息。'}
            </Typography.Text>
          </div>
        )}
      </Card>
    );
  };

  const items = [
    {
      key: 'requirement-analysis',
      label: (
        <span>
          <FileTextOutlined />
          需求分析
        </span>
      ),
      children: (
        <Card>
          <Form 
            layout="vertical" 
            form={requirementForm}
            initialValues={requirementFormData}
            onValuesChange={(changedValues, allValues) => {
              setRequirementFormData(allValues);
            }}
            onFinish={handleRequirementAnalysis}
          >
            <Form.Item
              label={
                <span>
                  需求描述
                  <Tooltip title="支持导入 Word (.doc, .docx)、PDF (.pdf)、Excel (.xls, .xlsx)、XMind (.xmind) 格式文档">
                    <span style={{ marginLeft: 8, color: '#999', fontSize: '12px' }}>
                      (支持文档导入)
                    </span>
                  </Tooltip>
                </span>
              }
              name="requirement_text"
              rules={[{ required: true, message: '请输入需求描述或上传文档' }]}
              extra={
                <Upload
                  customRequest={handleDocumentUpload}
                  accept=".doc,.docx,.pdf,.xls,.xlsx,.xmind"
                  showUploadList={false}
                  maxCount={1}
                >
                  <Button icon={<UploadOutlined />} size="small">
                    上传文档（Word/PDF/Excel/XMind）
                  </Button>
                </Upload>
              }
            >
              <TextArea rows={6} placeholder="请输入软件需求描述，或点击下方按钮上传文档..." />
            </Form.Item>
            <Form.Item label="项目背景" name="project_context">
              <TextArea rows={3} placeholder="请输入项目背景信息（可选）..." />
            </Form.Item>
            <Form.Item label="测试重点" name="test_focus">
              <Select
                mode="tags"
                placeholder="选择测试重点领域"
                options={[
                  { label: '功能测试', value: 'functional' },
                  { label: '性能测试', value: 'performance' },
                  { label: '安全测试', value: 'security' },
                  { label: '兼容性测试', value: 'compatibility' },
                  { label: '用户体验测试', value: 'ux' },
                ]}
              />
            </Form.Item>
            <Form.Item>
              <Space size="middle">
                <Button type="primary" htmlType="submit" loading={loading} icon={<RobotOutlined />}>
                  开始分析
                </Button>
                <Tooltip title={analysisJson ? "下载JSON格式" : "请先进行需求分析"}>
                  <Button 
                    type={analysisJson ? "primary" : "default"}
                    icon={<CodeOutlined />}
                    onClick={() => handleDownload('json')}
                    disabled={loading || !analysisJson}
                  >
                    JSON {analysisJson?.filename ? '(已生成)' : ''}
                  </Button>
                </Tooltip>
                <Tooltip title={analysisJson ? "下载Markdown格式" : "请先进行需求分析"}>
                  <Button
                    icon={<FileTextOutlined />}
                    onClick={() => handleDownload('markdown')}
                    disabled={loading || !analysisJson}
                  >
                    Markdown
                  </Button>
                </Tooltip>
                <Tooltip title={analysisJson ? "下载PDF格式" : "请先进行需求分析"}>
                  <Button
                    icon={<FilePdfOutlined />}
                    onClick={() => handleDownload('pdf')}
                    disabled={loading || !analysisJson}
                  >
                    PDF
                  </Button>
                </Tooltip>
                <Tooltip title={analysisJson ? "下载Word格式" : "请先进行需求分析"}>
                  <Button
                    icon={<FileWordOutlined />}
                    onClick={() => handleDownload('word')}
                    disabled={loading || !analysisJson}
                  >
                    Word
                  </Button>
                </Tooltip>
                <Tooltip title={analysisJson ? "下载Excel格式" : "请先进行需求分析"}>
                  <Button
                    icon={<FileExcelOutlined />}
                    onClick={() => handleDownload('excel')}
                    disabled={loading || !analysisJson}
                  >
                    Excel
                  </Button>
                </Tooltip>
                <Tooltip title={analysisJson ? "预览思维导图" : "请先进行需求分析"}>
                  <Button
                    icon={<EyeOutlined />}
                    onClick={() => {
                      let data: any = analysisJson?.data;
                      if (!data && analysisJson?.filename) {
                        // 如果有filename，需要异步加载数据
                        fetch(`http://localhost:8000/static/analysis_results/${analysisJson.filename}`)
                          .then(res => res.json())
                          .then(json => {
                            handlePreviewMindmap(json, 'analysis');
                          })
                          .catch(() => {
                            if (analysisJson?.data) {
                              handlePreviewMindmap(analysisJson.data, 'analysis');
                            } else {
                              message.error('无法加载数据');
                            }
                          });
                      } else if (data) {
                        handlePreviewMindmap(data, 'analysis');
                      }
                    }}
                    disabled={loading || !analysisJson}
                  >
                    预览
                  </Button>
                </Tooltip>
                <Tooltip title={analysisJson ? "下载思维导图" : "请先进行需求分析"}>
                  <Button
                    icon={<ApartmentOutlined />}
                    onClick={() => handleDownload('mindmap')}
                    disabled={loading || !analysisJson}
                  >
                    下载
                  </Button>
                </Tooltip>
              </Space>
            </Form.Item>
          </Form>
          <div style={{ position: 'relative', marginBottom: 16 }}>
            {(analysisJson as any)?.ai_model && (
              <div style={{ 
                marginTop: 16,
                marginBottom: 8, 
                padding: '8px 12px', 
                background: colorInfoBg, 
                border: `1px solid ${colorInfoBorder}`,
                borderRadius: 4,
                fontSize: '12px'
              }}>
                <span style={{ fontWeight: 'bold', marginRight: 8 }}>🤖 AI工具:</span>
                <span>{(analysisJson as any).ai_model.provider === 'deepseek' ? 'Deepseek' : (analysisJson as any).ai_model.provider === 'ollama' ? 'Ollama' : (analysisJson as any).ai_model.provider}</span>
                {(analysisJson as any).ai_model.model_name && <span style={{ marginLeft: 8, color: '#666' }}>({(analysisJson as any).ai_model.model_name})</span>}
              </div>
            )}
            <div
              style={{
                marginTop: (analysisJson as any)?.ai_model ? 8 : 16,
                padding: 16,
                border: `1px solid ${colorBorder}`,
                borderRadius: 4,
                backgroundColor: colorFillSecondary,
                height: '600px',
                overflowY: 'scroll',
                overflowX: 'auto',
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                fontSize: '13px',
                lineHeight: '1.6',
                position: 'relative'
              }}
            >
              <pre style={{
                margin: 0,
                padding: 0,
                background: 'transparent',
                border: 'none',
                fontFamily: 'inherit',
                fontSize: 'inherit',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflow: 'visible',
                width: '100%',
                display: 'block'
              }}>
              {streamAnalysis || '等待 AI 分析结果...'}
              </pre>
            </div>

          </div>
        </Card>
      ),
    },
    {
      key: 'test-case-generation',
      label: (
        <span>
          <BugOutlined />
          测试用例生成
        </span>
      ),
      children: (
        <Card>
          <Form 
            layout="vertical" 
            form={testCaseForm}
            initialValues={testCaseFormData}
            onValuesChange={(changedValues, allValues) => {
              setTestCaseFormData(allValues);
            }}
            onFinish={handleTestCaseGeneration}
          >
            <Form.Item
              label={
                <span>
                  需求描述
                  <Tooltip title="支持导入 Word (.doc, .docx)、PDF (.pdf)、Excel (.xls, .xlsx)、XMind (.xmind) 格式文档">
                    <span style={{ marginLeft: 8, color: '#999', fontSize: '12px' }}>
                      (支持文档导入)
                    </span>
                  </Tooltip>
                </span>
              }
              name="requirement_text"
              rules={[{ required: true, message: '请输入需求描述或上传文档' }]}
              extra={
                <Upload
                  customRequest={handleDocumentUploadForTestCase}
                  accept=".doc,.docx,.pdf,.xls,.xlsx,.xmind"
                  showUploadList={false}
                  maxCount={1}
                >
                  <Button icon={<UploadOutlined />} size="small">
                    上传文档（Word/PDF/Excel/XMind）
                  </Button>
                </Upload>
              }
            >
              <TextArea rows={4} placeholder="请输入需求描述，或点击下方按钮上传文档..." />
            </Form.Item>
            <Form.Item
              label="测试类型"
              name="test_type"
              rules={[{ required: true, message: '请选择测试类型' }]}
            >
              <Select placeholder="选择测试类型">
                <Option value="functional">功能测试 - 生成测试用例文档</Option>
                <Option value="api">接口测试 - 生成测试用例文档和自动化脚本</Option>
                <Option value="ui">UI测试 - 生成测试用例文档和自动化脚本</Option>
              </Select>
            </Form.Item>
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.test_type !== currentValues.test_type}
            >
              {({ getFieldValue }) => {
                const testType = getFieldValue('test_type');
                const isFunctional = testType === 'functional';
                
                return (
                  <Form.Item 
                    label="同时生成自动化脚本" 
                    name="generate_script"
                    valuePropName="checked"
                    initialValue={true}
                    help={
                      <Typography.Text type="secondary" style={{ fontSize: '12px' }}>
                        {isFunctional 
                          ? '功能测试不需要生成自动化脚本' 
                          : '💡 开启后，接口测试和UI测试将同时生成Python自动化测试脚本，节省时间和Token（默认开启）'
                        }
                      </Typography.Text>
                    }
                  >
                    <Switch 
                      checkedChildren="开启" 
                      unCheckedChildren="关闭" 
                      disabled={isFunctional}
                      checked={!isFunctional && (getFieldValue('generate_script') ?? true)}
                      onChange={(checked) => {
                        if (!isFunctional) {
                          testCaseForm.setFieldsValue({ generate_script: checked });
                        }
                      }}
                    />
                  </Form.Item>
                );
              }}
            </Form.Item>
            <Form.Item label="测试范围" name="test_scope">
              <TextArea rows={3} placeholder="请输入测试范围（可选）..." />
            </Form.Item>
            <Form.Item>
              <Space size="middle">
              <Button type="primary" htmlType="submit" loading={loading} icon={<RobotOutlined />}>
                生成测试用例
              </Button>
                <Tooltip title={testCasesJson ? "复制JSON格式" : "请先生成测试用例"}>
                  <Button 
                    icon={<FileTextOutlined />}
                    onClick={() => handleCopyTestCases()}
                    disabled={!testCasesJson}
                  >
                    复制
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "下载JSON格式" : "请先生成测试用例"}>
                  <Button 
                    type={testCasesJson ? "primary" : "default"}
                    icon={<CodeOutlined />}
                    onClick={() => handleDownloadTestCases('json')}
                    disabled={!testCasesJson}
                  >
                    JSON
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "下载Markdown格式" : "请先生成测试用例"}>
                  <Button
                    icon={<FileTextOutlined />}
                    onClick={() => handleDownloadTestCases('markdown')}
                    disabled={!testCasesJson}
                  >
                    Markdown
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "下载PDF格式" : "请先生成测试用例"}>
                  <Button
                    icon={<FilePdfOutlined />}
                    onClick={() => handleDownloadTestCases('pdf')}
                    disabled={!testCasesJson}
                  >
                    PDF
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "下载Word格式" : "请先生成测试用例"}>
                  <Button
                    icon={<FileWordOutlined />}
                    onClick={() => handleDownloadTestCases('word')}
                    disabled={!testCasesJson}
                  >
                    Word
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "下载Excel格式" : "请先生成测试用例"}>
                  <Button
                    icon={<FileExcelOutlined />}
                    onClick={() => handleDownloadTestCases('excel')}
                    disabled={!testCasesJson}
                  >
                    Excel
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "预览思维导图" : "请先生成测试用例"}>
                  <Button
                    icon={<EyeOutlined />}
                    onClick={() => {
                      const data = getTestCasesData();
                      if (data) {
                        handlePreviewMindmap(data, 'testcase');
                      }
                    }}
                    disabled={!testCasesJson}
                  >
                    预览
                  </Button>
                </Tooltip>
                <Tooltip title={testCasesJson ? "下载思维导图" : "请先生成测试用例"}>
                  <Button
                    icon={<ApartmentOutlined />}
                    onClick={() => handleDownloadTestCases('mindmap')}
                    disabled={!testCasesJson}
                  >
                    下载
                  </Button>
                </Tooltip>
              </Space>
            </Form.Item>
          </Form>
          <div style={{ position: 'relative', marginBottom: 16 }}>
            <div
              style={{
                marginTop: 16,
                padding: 16,
                border: `1px solid ${colorBorder}`,
                borderRadius: 4,
                backgroundColor: colorFillSecondary,
                height: '600px',
                overflowY: 'scroll',
                overflowX: 'auto',
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                fontSize: '13px',
                lineHeight: '1.6',
                position: 'relative'
              }}
            >
              <pre style={{
                margin: 0,
                padding: 0,
                background: 'transparent',
                border: 'none',
                fontFamily: 'inherit',
                fontSize: 'inherit',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflow: 'visible',
                width: '100%',
                display: 'block'
              }}>
                {streamTestCases || '等待 AI 生成测试用例...'}
              </pre>
            </div>
            {testCasesJson && (() => {
              const testCaseData = testCasesJson || results?.data;
              const testCases = testCaseData?.test_cases || [];
              const testType = testCases[0]?.test_type;
              const aiModel = testCaseData?.ai_model;
              
              // 检查是否有代码（如果开启了生成脚本）
              // 不仅检查python_code字段，还尝试从raw_response和流式内容中提取
              const extractCodeFromTestCase = (tc: any): string | null => {
                // 方法1: 直接检查python_code字段
                if (tc.python_code) {
                  const code = extractPythonCode(tc.python_code);
                  if (code && code.trim()) return code;
                }
                
                // 方法2: 从raw_response中提取（如果JSON被截断）
                if (tc.raw_response) {
                  const code = extractCodeFromText(tc.raw_response);
                  if (code) return code;
                }
                
                return null;
              };
              
              // 从文本中提取Python代码（支持多种格式）
              const extractCodeFromText = (text: string): string | null => {
                try {
                  // 尝试从JSON中提取python_code
                  const jsonMatch = text.match(/```json\s*([\s\S]*?)```/);
                  if (jsonMatch) {
                    try {
                      const parsed = JSON.parse(jsonMatch[1]);
                      if (parsed.python_code) {
                        const code = extractPythonCode(parsed.python_code);
                        if (code && code.trim()) return code;
                      }
                      // 如果解析的JSON中有test_cases，也检查一下
                      if (parsed.test_cases && Array.isArray(parsed.test_cases)) {
                        for (const testCase of parsed.test_cases) {
                          if (testCase.python_code) {
                            const code = extractPythonCode(testCase.python_code);
                            if (code && code.trim()) return code;
                          }
                        }
                      }
                    } catch (e) {
                      // JSON解析失败，尝试正则提取python_code字段
                      // 使用更宽松的正则来匹配多行代码字符串
                      const pythonCodePatterns = [
                        // 匹配 "python_code": {"selenium": "..." 或 "playwright": "..."
                        // 使用非贪婪匹配，但是要确保能匹配到完整的字符串（包括转义字符和空格）
                        /"python_code"\s*:\s*\{[\s\S]*?"(?:selenium|playwright)"\s*:\s*"([\s\S]*?)"(?:\s*[,}])/,
                        // 匹配 "python_code": "..."
                        /"python_code"\s*:\s*"([\s\S]*?)"(?:\s*[,}])/,
                      ];
                      for (const pattern of pythonCodePatterns) {
                        const match = jsonMatch[1].match(pattern);
                        if (match && match[1]) {
                          const code = unescapeCodeString(match[1]);
                          if (code && code.trim()) return code;
                        }
                      }
                    }
                  }
                  
                  // 如果JSON匹配失败，尝试直接从文本中查找python_code（可能没有markdown代码块）
                  // 使用更强大的正则来处理多行和转义字符
                  
                  // 方法1: 查找完整的python_code对象（处理嵌套对象和转义）
                  const pythonCodeObjMatch = text.match(/"python_code"\s*:\s*\{[\s\S]*?"(?:selenium|playwright)"\s*:\s*"([\s\S]*?)"(?:\s*,\s*"|\s*\})/);
                  if (pythonCodeObjMatch && pythonCodeObjMatch[1]) {
                    const code = unescapeCodeString(pythonCodeObjMatch[1]);
                    if (code && code.trim().length > 20) return code;
                  }
                  
                  // 方法2: 查找简单的python_code字符串
                  const pythonCodeStrMatch = text.match(/"python_code"\s*:\s*"([\s\S]*?)"(?:\s*[,}])/);
                  if (pythonCodeStrMatch && pythonCodeStrMatch[1]) {
                    const code = unescapeCodeString(pythonCodeStrMatch[1]);
                    if (code && code.trim().length > 20) return code;
                  }
                  
                  // 方法3: 对于被截断的JSON，尝试查找最后一个完整的python_code（不要求闭合引号）
                  // 使用更宽松的匹配，找到 "python_code" 之后的所有内容，直到文件结束或遇到明显的结束标记
                  const truncatedPythonCodeMatch = text.match(/"python_code"\s*:\s*\{[\s\S]*?"(?:selenium|playwright)"\s*:\s*"([\s\S]{100,})/);
                  if (truncatedPythonCodeMatch && truncatedPythonCodeMatch[1]) {
                    let codeStr = truncatedPythonCodeMatch[1];
                    // 尝试找到代码的结束位置（查找最后的引号或合理的结束位置）
                    // 如果代码被截断，找到最后一个完整的转义序列之后的位置
                    let endIndex = codeStr.length;
                    // 查找最后一个完整的语句（以换行符、引号或常见Python关键字结尾）
                    const endPattern = /(?:driver\.quit\(\)|finally:|except\s|print\([^)]*\)|assert\s[^\n]*|return\s[^\n]*)(?:\s*["\n])?/;
                    const endMatch = codeStr.match(endPattern);
                    if (endMatch) {
                      endIndex = codeStr.indexOf(endMatch[0]) + endMatch[0].length;
                    }
                    codeStr = codeStr.substring(0, endIndex);
                    // 移除末尾可能的未闭合字符（引号、括号等）
                    codeStr = codeStr.replace(/["}\]]+\s*$/, '');
                    let code = unescapeCodeString(codeStr);
                    if (code && code.trim().length > 50) return code;
                  }
                  
                  // 方法4: 尝试直接从文本中提取，即使JSON格式不完整
                  // 查找 "python_code" 字段后面的所有内容，尝试智能提取
                  const smartExtractMatch = text.match(/"python_code"[\s\S]{0,200}?"(?:selenium|playwright)"\s*:\s*"([\s\S]{200,}?)(?:"\s*[,}]|$)/);
                  if (smartExtractMatch && smartExtractMatch[1]) {
                    let code = unescapeCodeString(smartExtractMatch[1]);
                    // 检查代码是否包含Python关键字（确保是有效的代码）
                    if (code.includes('import ') || code.includes('def ') || code.includes('from ')) {
                      // 移除末尾可能的未闭合字符
                      code = code.replace(/["}\]]+\s*$/, '').trim();
                      if (code.length > 50) return code;
                    }
                  }
                  
                  // 尝试查找Python代码块（改进以匹配多行）
                  const pythonBlockMatch = text.match(/```(?:python|py)?\s*\n?([\s\S]*?)\n?```/);
                  if (pythonBlockMatch && pythonBlockMatch[1]) {
                    const code = pythonBlockMatch[1].trim();
                    if (code && code.length > 20) return code;
                  }
                  
                  // 最后尝试：查找包含def或import的代码块（即使没有代码块标记）
                  const codeBlockMatch = text.match(/(?:def\s+\w+|import\s+\w+|from\s+\w+\s+import)[\s\S]{50,}/);
                  if (codeBlockMatch) {
                    const code = codeBlockMatch[0].trim();
                    // 尝试提取完整的函数或模块
                    const lines = code.split('\n');
                    if (lines.length >= 3) {
                      return code;
                    }
                  }
                } catch (e) {
                  console.warn('从文本提取代码失败:', e);
                }
                return null;
                             };
               
                              // 收集所有测试用例的代码
               const allCodeParts: Array<{title: string, code: string}> = [];
               testCases.forEach((tc: any) => {
                 const code = extractCodeFromTestCase(tc);
                 if (code) {
                   allCodeParts.push({
                     title: tc.title || 'Test Case',
                     code: code
                   });
                 }
               });
               
                             // 如果从测试用例中没有提取到代码，尝试从流式内容中提取
              // 优先从保存的原始流式内容中提取，其次从显示的流式内容中提取
              if (allCodeParts.length === 0) {
                let streamCode = null;
                
                // 方法1: 从testCaseData中保存的原始流式内容提取
                if (testCaseData._rawStreamContent) {
                  streamCode = extractCodeFromText(testCaseData._rawStreamContent);
                }
                
                // 方法2: 从当前显示的流式内容提取
                if (!streamCode && streamTestCases && streamTestCases.trim()) {
                  streamCode = extractCodeFromText(streamTestCases);
                }
                
                if (streamCode) {
                  allCodeParts.push({
                    title: '从流式输出中提取的代码',
                    code: streamCode
                  });
                }
              }
               
               const hasPythonCode = allCodeParts.length > 0;
              
              if ((testType === 'api' || testType === 'ui') && hasPythonCode) {
                // 直接显示代码
                const allCode = allCodeParts
                  .map((part) => `# ${part.title}\n${part.code}`)
                  .join('\n\n');
                
                return (
                  <div style={{ marginTop: 16 }}>
                    {aiModel && (
                      <div style={{ 
                        marginBottom: 8, 
                        padding: '8px 12px', 
                        background: colorInfoBg, 
                        border: `1px solid ${colorInfoBorder}`,
                        borderRadius: 4,
                        fontSize: '12px'
                      }}>
                        <span style={{ fontWeight: 'bold', marginRight: 8 }}>🤖 AI工具:</span>
                        <span>{aiModel.provider === 'deepseek' ? 'Deepseek' : aiModel.provider === 'ollama' ? 'Ollama' : aiModel.provider}</span>
                        {aiModel.model_name && <span style={{ marginLeft: 8, color: '#666' }}>({aiModel.model_name})</span>}
                      </div>
                    )}
                    <Card 
                      title="自动化测试脚本" 
                      style={{ marginTop: 8 }}
                      extra={
                        <Space>
                          <Button 
                            icon={<FileTextOutlined />}
                            onClick={() => {
                              navigator.clipboard.writeText(allCode).then(() => {
                                message.success('代码已复制到剪贴板');
                              }).catch(() => {
                                message.error('复制失败');
                              });
                            }}
                          >
                            复制代码
                          </Button>
                          <Button 
                            type="primary"
                            icon={<CodeOutlined />}
                            onClick={() => {
                              const filename = testType === 'api' 
                                ? `api_tests_${new Date().toISOString().split('T')[0]}.py`
                                : `ui_tests_${new Date().toISOString().split('T')[0]}.py`;
                              handleDownloadScript(allCode, filename);
                            }}
                          >
                            下载脚本
                          </Button>
                        </Space>
                      }
                    >
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: 16, 
                        borderRadius: 6, 
                        overflowX: 'auto',
                        overflowY: 'auto',
                        maxHeight: '600px',
                        margin: 0,
                        fontSize: '13px',
                        lineHeight: '1.5',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {allCode}
                      </pre>
                    </Card>
                  </div>
                );
              } else if (testType === 'api' || testType === 'ui') {
                // 检查是否开启了生成脚本开关
                const generateScriptEnabled = testCaseForm.getFieldValue('generate_script') ?? true;
                
                if (generateScriptEnabled) {
                  // 开启了开关但没有代码，可能是生成失败或JSON被截断
                  return (
                    <div style={{ marginTop: 12 }}>
                      <Typography.Text type="warning">
                        ⚠️ 已开启"同时生成自动化脚本"，但未检测到代码。可能是：
                        <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                          <li>JSON响应被截断，代码未完整生成</li>
                          <li>AI响应格式异常，代码解析失败</li>
                        </ul>
                      </Typography.Text>
                      <div style={{ marginTop: 8 }}>
                        <Tooltip title={`手动生成${testType === 'api' ? 'API' : 'UI'}自动化测试脚本`}>
                          <Button 
                            type="primary"
                            icon={<CodeOutlined />}
                            onClick={handleGenerateScriptFromTestCase}
                            loading={loading}
                          >
                            手动生成自动化测试脚本
                          </Button>
                        </Tooltip>
                      </div>
                    </div>
                  );
                } else {
                  // 未开启开关，显示生成按钮
                  return (
                    <div style={{ marginTop: 12 }}>
                      <Tooltip title={`基于测试用例自动生成${testType === 'api' ? 'API' : 'UI'}自动化测试脚本`}>
                        <Button 
                          type="primary"
                          icon={<CodeOutlined />}
                          onClick={handleGenerateScriptFromTestCase}
                          loading={loading}
                        >
                          生成自动化测试脚本
                        </Button>
                      </Tooltip>
                    </div>
                  );
                }
              }
              return null;
            })()}
          </div>
        </Card>
      ),
    },
    {
      key: 'api-test-generation',
      label: (
        <span>
          <ApiOutlined />
          API测试生成
        </span>
      ),
      children: (
        <Card>
          <Form 
            layout="vertical" 
            form={apiTestForm}
            initialValues={apiTestFormData}
            onValuesChange={(changedValues, allValues) => {
              setApiTestFormData(allValues);
            }}
            onFinish={handleAPITestGeneration}
          >
            <Form.Item
              label={
                <Space>
                  <span>API文档</span>
                  <Upload
                    customRequest={handleAPIDocumentUpload}
                    accept=".json,.yaml,.yml"
                    showUploadList={false}
                  >
                    <Button icon={<UploadOutlined />} size="small" type="link">
                      上传API文档
                    </Button>
                  </Upload>
                </Space>
              }
              extra="支持OpenAPI/Swagger JSON/YAML、Postman Collection格式。上传后将自动解析并填充"
              name="api_documentation"
              rules={[{ required: true, message: '请输入API文档或上传API文档文件' }]}
            >
              <TextArea 
                rows={6} 
                placeholder="请输入API文档内容，或点击上方按钮上传API文档文件（OpenAPI/Swagger、Postman Collection）..." 
              />
            </Form.Item>
            <Form.Item
              label="基础URL"
              name="base_url"
              rules={[{ required: true, message: '请输入基础URL' }]}
            >
              <Input placeholder="例如：https://api.example.com" />
            </Form.Item>
            <Form.Item label="测试场景" name="test_scenarios">
              <Select
                mode="tags"
                placeholder="选择测试场景"
                options={[
                  { label: '正常流程测试', value: 'normal' },
                  { label: '异常处理测试', value: 'error' },
                  { label: '边界值测试', value: 'boundary' },
                  { label: '性能测试', value: 'performance' },
                ]}
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} icon={<RobotOutlined />}>
                生成API测试
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'ui-test-generation',
      label: (
        <span>
          <BugOutlined />
          UI测试生成
        </span>
      ),
      children: (
        <Card>
          <Form 
            layout="vertical" 
            form={uiTestForm}
            initialValues={uiTestFormData}
            onValuesChange={(changedValues, allValues) => {
              setUITestFormData(allValues);
            }}
            onFinish={handleUITestGeneration}
          >
            <Form.Item
              label={
                <Space>
                  <span>页面URL</span>
                  <Button 
                    type="link" 
                    size="small" 
                    icon={<EyeOutlined />}
                    onClick={() => {
                      const pageUrl = uiTestForm.getFieldValue('page_url');
                      if (pageUrl) {
                        handlePageAnalysis(pageUrl);
                      } else {
                        message.warning('请先输入页面URL');
                      }
                    }}
                    loading={loading}
                  >
                    分析页面
                  </Button>
                </Space>
              }
              extra="输入URL后点击'分析页面'按钮，系统将自动访问页面并分析结构，然后生成测试脚本"
              name="page_url"
              rules={[{ required: true, message: '请输入页面URL' }]}
            >
              <Input 
                placeholder="例如：https://example.com/login" 
                onPressEnter={(e) => {
                  const url = (e.target as HTMLInputElement).value;
                  if (url) {
                    handlePageAnalysis(url);
                  }
                }}
              />
            </Form.Item>
            <Form.Item
              label="业务需求/测试场景"
              name="user_actions"
              extra="描述您要测试的业务场景或功能，例如：'测试用户注册流程'、'测试商品添加到购物车'、'测试订单提交'等。如果不填写，AI将根据页面结构自动推断。"
            >
              <TextArea 
                rows={4} 
                placeholder="例如：测试用户注册完整流程，包括填写用户名、邮箱、密码，同意协议，点击注册按钮，验证注册成功提示。或者：测试商品搜索功能，输入关键词，筛选条件，查看搜索结果等。"
              />
            </Form.Item>
            <Form.Item label="测试场景类型（可选）" name="test_scenarios">
              <Select
                mode="tags"
                placeholder="选择测试场景类型（可选）"
                options={[
                  { label: '正常流程', value: 'normal' },
                  { label: '异常处理', value: 'error' },
                  { label: '边界条件', value: 'boundary' },
                  { label: '数据验证', value: 'validation' },
                  { label: '性能测试', value: 'performance' },
                ]}
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} icon={<RobotOutlined />}>
                生成UI测试
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
  ];

  return (
    <div>
      {/* 修复JSX结构，确保所有标签正确闭合 */}
      <Title level={2}>
        <RobotOutlined /> AI智能测试引擎
      </Title>
      <Paragraph>
        基于AI技术，自动分析需求、生成测试用例、创建API测试和UI自动化测试脚本
      </Paragraph>
      <Divider />
      <div>
        {progressVisible && (
          <div style={{ marginBottom: 16 }}>
            <Progress 
              percent={Math.round(progress)} 
              status={progress >= 100 ? "success" : "active"} 
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
        )}
        <Tabs 
          items={items} 
          destroyInactiveTabPane={false}
          onChange={(key) => {
            // 切换 Tab 时恢复对应的表单值
            if (key === 'requirement-analysis' && Object.keys(requirementFormData).length > 0) {
              requirementForm.setFieldsValue(requirementFormData);
            } else if (key === 'test-case-generation' && Object.keys(testCaseFormData).length > 0) {
              testCaseForm.setFieldsValue(testCaseFormData);
            } else if (key === 'api-test-generation' && Object.keys(apiTestFormData).length > 0) {
              apiTestForm.setFieldsValue(apiTestFormData);
            } else if (key === 'ui-test-generation' && Object.keys(uiTestFormData).length > 0) {
              uiTestForm.setFieldsValue(uiTestFormData);
            }
          }}
        />
        {/* 避免和测试用例Tab内的结果重复渲染 */}
        {results?.type !== 'test_case_generation' && renderResults()}
      </div>

      {/* 思维导图预览 Modal */}
      <Modal
        title={previewType === 'analysis' ? '需求分析思维导图' : '测试用例思维导图'}
        open={previewModalVisible}
        onCancel={() => {
          setPreviewModalVisible(false);
          if (markmapRef.current) {
            markmapRef.current.destroy();
            markmapRef.current = null;
          }
        }}
        footer={null}
        width="90%"
        style={{ top: 20 }}
        destroyOnClose={false}
      >
        <div style={{ width: '100%', height: '70vh', position: 'relative' }}>
          <svg
            ref={svgRef}
            style={{
              width: '100%',
              height: '100%',
            }}
          />
        </div>
      </Modal>
    </div>
  );
};

export default AIEngine;