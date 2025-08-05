import React, { useState } from 'react';
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
} from 'antd';
import { RobotOutlined, FileTextOutlined, BugOutlined, ApiOutlined } from '@ant-design/icons';
import { analyzeRequirementStream, generateTestCases, generateAPITests, generateUITests } from '../services/aiService';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const AIEngine: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [streamAnalysis, setStreamAnalysis] = useState('');

  const handleRequirementAnalysis = async (values: any) => {
    setLoading(true);
    setStreamAnalysis('');
    try {
      await analyzeRequirementStream(
        values,
        (chunk) => {
          setStreamAnalysis(prev => prev + chunk);
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
              <Button type="primary" htmlType="submit" loading={loading} icon={<RobotOutlined />}>
                开始分析
              </Button>
            </Form.Item>
          </Form>
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
            }}
          >
            {streamAnalysis || '等待 AI 分析结果...'}
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
      <Title level={2}>
        <RobotOutlined /> AI智能测试引擎
      </Title>
      <Paragraph>
        基于AI技术，自动分析需求、生成测试用例、创建API测试和UI自动化测试脚本
      </Paragraph>
      <Divider />
      <Spin spinning={loading}>
        <Tabs items={items} />
        {renderResults()}
      </Spin>
    </div>
  );
};

export default AIEngine;