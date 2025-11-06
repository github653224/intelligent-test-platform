import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, Typography, Space, Spin, Table, Tag, Button, Modal, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  ProjectOutlined,
  FileTextOutlined,
  BugOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { getDashboardStatistics, getRecentTestRuns, checkAIEngineHealth, analyzeTestSummary } from '../services/aiService';

const { Title, Paragraph } = Typography;

interface DashboardStats {
  total_projects: number;
  total_requirements: number;
  total_test_cases: number;
  total_test_runs: number;
  total_passed_tests: number;
  total_failed_tests: number;
  total_skipped_tests: number;
  total_error_tests: number;
  success_rate: number;
  recent_runs_count: number;
  recent_passed: number;
  recent_failed: number;
  test_run_status: {
    running: number;
    pending: number;
    completed: number;
    failed: number;
  };
  test_case_types: {
    functional: number;
    api: number;
    ui: number;
  };
  scheduled_test_runs: number;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [aiEngineStatus, setAiEngineStatus] = useState<'healthy' | 'unhealthy' | 'unknown'>('unknown');
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [analysisModalOpen, setAnalysisModalOpen] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [statsData, recentRunsData, aiHealth] = await Promise.all([
        getDashboardStatistics(),
        getRecentTestRuns(10),
        checkAIEngineHealth().catch(() => ({ status: 'unknown' }))
      ]);
      
      setStats(statsData);
      setRecentRuns(recentRunsData);
      setAiEngineStatus(aiHealth.status || 'unknown');
    } catch (e: any) {
      console.error('加载仪表板数据失败:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysisModalOpen(true);
    try {
      const result = await analyzeTestSummary(30);
      setAnalysisResult(result);
    } catch (e: any) {
      message.error('分析失败: ' + (e.message || '未知错误'));
      setAnalysisResult(null);
    } finally {
      setAnalyzing(false);
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待执行' },
      running: { color: 'processing', text: '执行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      cancelled: { color: 'warning', text: '已取消' },
    };
    const statusInfo = statusMap[status] || { color: 'default', text: status };
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载中...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div>
        <Title level={2}>仪表板</Title>
        <Card>暂无数据</Card>
      </div>
    );
  }

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <div>
          <Title level={2}>仪表板</Title>
          <Paragraph>欢迎使用AI智能自动化测试平台</Paragraph>
        </div>
        <Space>
          <Button 
            type="primary" 
            icon={<BugOutlined />}
            onClick={handleAnalyze}
            loading={analyzing}
          >
            AI智能分析
          </Button>
          <ReloadOutlined 
            onClick={fetchDashboardData} 
            style={{ fontSize: 18, cursor: 'pointer' }}
            spin={loading}
          />
        </Space>
      </Space>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总项目数"
              value={stats.total_projects}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="需求数量"
              value={stats.total_requirements}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="测试用例"
              value={stats.total_test_cases}
              prefix={<BugOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="测试执行"
              value={stats.total_test_runs}
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
                  value={stats.total_passed_tests}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </div>
              <div>
                <Statistic
                  title="失败测试"
                  value={stats.total_failed_tests}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </div>
              <div>
                <Statistic
                  title="跳过测试"
                  value={stats.total_skipped_tests}
                  valueStyle={{ color: '#faad14' }}
                />
              </div>
              <div>
                <Paragraph>成功率</Paragraph>
                <Progress
                  percent={stats.success_rate}
                  status={stats.success_rate >= 80 ? "active" : "exception"}
                  strokeColor={{
                    '0%': stats.success_rate >= 80 ? '#108ee9' : '#ff4d4f',
                    '100%': stats.success_rate >= 80 ? '#87d068' : '#ff7875',
                  }}
                />
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="测试运行状态">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="执行中"
                    value={stats.test_run_status.running}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="待执行"
                    value={stats.test_run_status.pending}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="已完成"
                    value={stats.test_run_status.completed}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="已失败"
                    value={stats.test_run_status.failed}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
              </Row>
              {stats.scheduled_test_runs > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Statistic
                    title="定时执行"
                    value={stats.scheduled_test_runs}
                    prefix={<ClockCircleOutlined />}
                    valueStyle={{ color: '#722ed1' }}
                  />
                </div>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="测试用例类型分布">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Statistic
                  title="功能测试"
                  value={stats.test_case_types.functional}
                  valueStyle={{ color: '#1890ff' }}
                />
              </div>
              <div>
                <Statistic
                  title="API测试"
                  value={stats.test_case_types.api}
                  valueStyle={{ color: '#52c41a' }}
                />
              </div>
              <div>
                <Statistic
                  title="UI测试"
                  value={stats.test_case_types.ui}
                  valueStyle={{ color: '#faad14' }}
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
                  value={aiEngineStatus === 'healthy' ? '运行中' : aiEngineStatus === 'unhealthy' ? '异常' : '未知'}
                  valueStyle={{ 
                    color: aiEngineStatus === 'healthy' ? '#52c41a' : 
                           aiEngineStatus === 'unhealthy' ? '#ff4d4f' : '#999'
                  }}
                />
              </div>
              <div>
                <Statistic
                  title="最近7天执行"
                  value={stats.recent_runs_count}
                  suffix="次"
                  valueStyle={{ color: '#1890ff' }}
                />
              </div>
              <div>
                <Space>
                  <Statistic
                    title="最近通过"
                    value={stats.recent_passed}
                    valueStyle={{ color: '#52c41a' }}
                  />
                  <Statistic
                    title="最近失败"
                    value={stats.recent_failed}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Space>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card 
            title="最近测试运行"
            extra={
              <Button type="link" onClick={() => navigate('/test-runs')}>
                查看全部
              </Button>
            }
          >
            <Table
              dataSource={recentRuns}
              rowKey="id"
              pagination={false}
              size="small"
              onRow={(record) => ({
                onClick: () => navigate(`/test-runs`),
                style: { cursor: 'pointer' }
              })}
              columns={[
                {
                  title: 'ID',
                  dataIndex: 'id',
                  width: 80,
                },
                {
                  title: '名称',
                  dataIndex: 'name',
                  ellipsis: true,
                },
                {
                  title: '状态',
                  dataIndex: 'status',
                  width: 100,
                  render: (status: string) => getStatusTag(status),
                },
                {
                  title: '总用例',
                  dataIndex: 'total_cases',
                  width: 80,
                  align: 'center',
                },
                {
                  title: '通过',
                  dataIndex: 'passed_cases',
                  width: 80,
                  align: 'center',
                  render: (value: number) => (
                    <span style={{ color: '#52c41a' }}>{value}</span>
                  ),
                },
                {
                  title: '失败',
                  dataIndex: 'failed_cases',
                  width: 80,
                  align: 'center',
                  render: (value: number) => (
                    <span style={{ color: '#ff4d4f' }}>{value}</span>
                  ),
                },
                {
                  title: '创建时间',
                  dataIndex: 'created_at',
                  width: 180,
                  render: (text: string) => text ? new Date(text).toLocaleString('zh-CN') : '-',
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* AI分析Modal */}
      <Modal
        title="🤖 AI智能测试分析报告"
        open={analysisModalOpen}
        onCancel={() => {
          setAnalysisModalOpen(false);
          setAnalysisResult(null);
        }}
        footer={[
          <Button key="close" onClick={() => {
            setAnalysisModalOpen(false);
            setAnalysisResult(null);
          }}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {analyzing ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>AI正在分析测试数据，请稍候...</div>
          </div>
        ) : analysisResult ? (
          <div>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Title level={4}>📊 关键指标</Title>
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="总体通过率"
                    value={analysisResult.key_metrics?.overall_pass_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="测试运行次数"
                    value={analysisResult.key_metrics?.total_test_runs || 0}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="测试用例总数"
                    value={analysisResult.key_metrics?.total_test_cases || 0}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="失败率"
                    value={analysisResult.key_metrics?.failure_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
              </Row>
            </Card>

            <Card size="small">
              <Title level={4}>🔍 AI分析洞察</Title>
              <div style={{ 
                whiteSpace: 'pre-wrap', 
                lineHeight: '1.8',
                maxHeight: '400px',
                overflowY: 'auto',
                padding: '12px',
                background: '#f8f9fa',
                borderRadius: '4px'
              }}>
                {typeof analysisResult.analysis === 'string' 
                  ? analysisResult.analysis 
                  : typeof analysisResult.analysis === 'object' && analysisResult.analysis !== null
                    ? JSON.stringify(analysisResult.analysis, null, 2)
                    : '暂无分析结果'}
              </div>
            </Card>
          </div>
        ) : null}
      </Modal>
    </div>
  );
};

export default Dashboard; 