import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Select,
  Space,
  message,
  Spin,
  Typography,
  Divider,
  Progress,
  Tooltip,
} from 'antd';
import {
  DownloadOutlined,
  CodeOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  ApartmentOutlined,
  RobotOutlined,
  FileTextOutlined,
  BugOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { analyzeRequirementStream, generateTestCases, generateAPITests, generateUITests } from '../services/aiService';

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
  // 添加loading状态声明
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<any>(null);
  const [streamAnalysis, setStreamAnalysis] = useState('');
  const [progress, setProgress] = useState(0);
  const [progressVisible, setProgressVisible] = useState(false);
  const [analysisJson, setAnalysisJson] = useState<AnalysisJsonData | null>(null);

  // 下载分析结果为JSON文件
  const handleDownload = (type: 'json' | 'pdf' | 'excel' | 'mindmap') => {
    if (!analysisJson) {
      message.warning('请先进行需求分析');
      return;
    }

    switch (type) {
      case 'json':
        if (analysisJson.status === 'success' && analysisJson.filename) {
          // 从静态文件目录下载保存的文件
          const downloadUrl = `http://localhost:8000/static/analysis_results/${analysisJson.filename}`;
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = analysisJson.filename || `需求分析结果_${new Date().toISOString().split('T')[0]}.json`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          message.success('文件下载开始');
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
      case 'pdf':
        // TODO: 实现PDF导出
        message.info('PDF导出功能开发中...');
        break;
      case 'excel':
        // TODO: 实现Excel导出
        message.info('Excel导出功能开发中...');
        break;
      case 'mindmap':
        // TODO: 实现思维导图导出
        message.info('思维导图导出功能开发中...');
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
    } else if (!loading && progress > 0) {
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

  const handleRequirementAnalysis = async (values: any) => {
    console.log('Starting requirement analysis...');  // 添加调试日志
    setLoading(true);
    setStreamAnalysis('');
    setProgressVisible(true);
    setProgress(0);
    setAnalysisJson(null);  // 重置JSON状态
    let accumulatedChunks = '';
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

  const handleTestCaseGeneration = async (values: any) => {
    setLoading(true);
    setProgressVisible(true);
    setProgress(0);
    try {
      const response = await generateTestCases(values);
      setResults({ type: 'test_case_generation', data: response });
      message.success('测试用例生成完成！');
    } catch (error) {
      message.error('测试用例生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleAPITestGeneration = async (values: any) => {
    setLoading(true);
    setProgressVisible(true);
    setProgress(0);
    try {
      const response = await generateAPITests(values);
      setResults({ type: 'api_test_generation', data: response });
      message.success('API测试生成完成！');
    } catch (error) {
      message.error('API测试生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleUITestGeneration = async (values: any) => {
    setLoading(true);
    setProgressVisible(true);
    setProgress(0);
    try {
      const response = await generateUITests(values);
      setResults({ type: 'ui_test_generation', data: response });
      message.success('UI测试生成完成！');
    } catch (error) {
      message.error('UI测试生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const renderResults = () => {
    if (!results) return null;

    return (
      <Card title="AI生成结果" style={{ marginTop: 16 }}>
        <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 6, overflow: 'auto' }}>
          {JSON.stringify(results.data, null, 2)}
        </pre>
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
          <Form layout="vertical" onFinish={handleRequirementAnalysis}>
            <Form.Item
              label="需求描述"
              name="requirement_text"
              rules={[{ required: true, message: '请输入需求描述' }]}
            >
              <TextArea rows={6} placeholder="请输入软件需求描述..." />
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
                <Tooltip title={analysisJson ? "下载PDF格式" : "请先进行需求分析"}>
                  <Button
                    icon={<FilePdfOutlined />}
                    onClick={() => handleDownload('pdf')}
                    disabled={loading || !analysisJson}
                  >
                    PDF
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
                <Tooltip title={analysisJson ? "下载思维导图" : "请先进行需求分析"}>
                  <Button
                    icon={<ApartmentOutlined />}
                    onClick={() => handleDownload('mindmap')}
                    disabled={loading || !analysisJson}
                  >
                    思维导图
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
                border: '1px solid #d9d9d9',
                borderRadius: 4,
                backgroundColor: '#f5f5f5',
                minHeight: 300,
                maxHeight: 600,
                overflowY: 'auto',
                fontFamily: 'Monaco, Consolas, monospace',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontSize: '14px',
                lineHeight: '1.6',
                position: 'relative'
              }}
            >
              {streamAnalysis || '等待 AI 分析结果...'}
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
          <Form layout="vertical" onFinish={handleTestCaseGeneration}>
            <Form.Item
              label="需求描述"
              name="requirement_text"
              rules={[{ required: true, message: '请输入需求描述' }]}
            >
              <TextArea rows={4} placeholder="请输入需求描述..." />
            </Form.Item>
            <Form.Item
              label="测试类型"
              name="test_type"
              rules={[{ required: true, message: '请选择测试类型' }]}
            >
              <Select placeholder="选择测试类型">
                <Option value="functional">功能测试</Option>
                <Option value="api">接口测试</Option>
                <Option value="ui">UI测试</Option>
              </Select>
            </Form.Item>
            <Form.Item label="测试范围" name="test_scope">
              <TextArea rows={3} placeholder="请输入测试范围（可选）..." />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} icon={<RobotOutlined />}>
                生成测试用例
              </Button>
            </Form.Item>
          </Form>
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
          <Form layout="vertical" onFinish={handleAPITestGeneration}>
            <Form.Item
              label="API文档"
              name="api_documentation"
              rules={[{ required: true, message: '请输入API文档' }]}
            >
              <TextArea rows={6} placeholder="请输入API文档内容..." />
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
          <Form layout="vertical" onFinish={handleUITestGeneration}>
            <Form.Item
              label="页面URL"
              name="page_url"
              rules={[{ required: true, message: '请输入页面URL' }]}
            >
              <Input placeholder="例如：https://example.com/login" />
            </Form.Item>
            <Form.Item
              label="用户操作"
              name="user_actions"
              rules={[{ required: true, message: '请输入用户操作' }]}
            >
              <Select
                mode="tags"
                placeholder="输入用户操作步骤"
                options={[
                  { label: '点击登录按钮', value: 'click_login' },
                  { label: '输入用户名', value: 'input_username' },
                  { label: '输入密码', value: 'input_password' },
                  { label: '提交表单', value: 'submit_form' },
                ]}
              />
            </Form.Item>
            <Form.Item label="测试场景" name="test_scenarios">
              <Select
                mode="tags"
                placeholder="选择测试场景"
                options={[
                  { label: '正常登录', value: 'normal_login' },
                  { label: '错误密码', value: 'wrong_password' },
                  { label: '空用户名', value: 'empty_username' },
                  { label: '记住密码', value: 'remember_password' },
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
        <Tabs items={items} />
        {renderResults()}
      </div>
    </div>
  );
};

export default AIEngine;