import React from 'react';
import { Card, Row, Col, Statistic, Progress, Typography, Space } from 'antd';
import {
  ProjectOutlined,
  FileTextOutlined,
  BugOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const Dashboard: React.FC = () => {
  // 模拟数据
  const stats = {
    totalProjects: 12,
    totalRequirements: 45,
    totalTestCases: 156,
    totalTestRuns: 89,
    passedTests: 142,
    failedTests: 14,
    successRate: 91,
  };

  return (
    <div>
      <Title level={2}>仪表板</Title>
      <Paragraph>欢迎使用AI智能自动化测试平台</Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总项目数"
              value={stats.totalProjects}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="需求数量"
              value={stats.totalRequirements}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="测试用例"
              value={stats.totalTestCases}
              prefix={<BugOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="测试执行"
              value={stats.totalTestRuns}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="测试结果概览">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Statistic
                  title="通过测试"
                  value={stats.passedTests}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </div>
              <div>
                <Statistic
                  title="失败测试"
                  value={stats.failedTests}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </div>
              <div>
                <Paragraph>成功率</Paragraph>
                <Progress
                  percent={stats.successRate}
                  status="active"
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="AI引擎状态">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Statistic
                  title="AI引擎状态"
                  value="运行中"
                  valueStyle={{ color: '#52c41a' }}
                />
              </div>
              <div>
                <Statistic
                  title="今日AI调用"
                  value={23}
                  suffix="次"
                  valueStyle={{ color: '#1890ff' }}
                />
              </div>
              <div>
                <Statistic
                  title="生成测试用例"
                  value={156}
                  suffix="个"
                  valueStyle={{ color: '#faad14' }}
                />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="快速操作">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Card size="small" hoverable>
                  <Statistic
                    title="新建项目"
                    value="+"
                    valueStyle={{ color: '#1890ff', fontSize: 24 }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Card size="small" hoverable>
                  <Statistic
                    title="需求分析"
                    value="AI"
                    valueStyle={{ color: '#52c41a', fontSize: 24 }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Card size="small" hoverable>
                  <Statistic
                    title="生成测试"
                    value="AI"
                    valueStyle={{ color: '#faad14', fontSize: 24 }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Card size="small" hoverable>
                  <Statistic
                    title="执行测试"
                    value="▶"
                    valueStyle={{ color: '#722ed1', fontSize: 24 }}
                  />
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard; 