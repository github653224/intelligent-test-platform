import React, { useEffect, useLayoutEffect, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, Row, Col, Statistic, Progress, Typography, Space, Spin, Table, Tag, Button, Modal, message, theme } from 'antd';
import html2canvas from 'html2canvas';
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
  ThunderboltOutlined,
} from '@ant-design/icons';
import { getDashboardStatistics, getRecentTestRuns, checkAIEngineHealth, analyzeTestSummary, analyzeTestSummaryStream } from '../services/aiService';
import MatrixRain from '../components/MatrixRain';
import TerminalDisplay from '../components/TerminalDisplay';
import { extractJsonFromStream, formatAnalysisAsMarkdown } from '../utils/markdownFormatter';
import ReactMarkdown from 'react-markdown';
import { useTheme } from '../contexts/ThemeContext';

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
  performance_tests?: {
    total: number;
    status: {
      pending: number;
      running: number;
      completed: number;
      failed: number;
    };
    with_analysis: number;
    recent_count: number;
  };
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme: themeMode } = useTheme();
  // 获取主题token
  const {
    token: { colorFillSecondary, colorBgContainer },
  } = theme.useToken();
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [aiEngineStatus, setAiEngineStatus] = useState<'healthy' | 'unhealthy' | 'unknown'>('unknown');
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [analysisModalOpen, setAnalysisModalOpen] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [streamText, setStreamText] = useState('');
  const [streamComplete, setStreamComplete] = useState(false);
  const [keyMetrics, setKeyMetrics] = useState<any>(null);
  const [finalAnalysisResult, setFinalAnalysisResult] = useState<string>('');
  const reportContentRef = useRef<HTMLDivElement>(null);
  const isMountedRef = useRef(true);
  const isCurrentRouteRef = useRef(false);

  const fetchDashboardData = async (showLoading: boolean = true) => {
    // 首先检查是否是当前路由 - 必须在最前面检查
    const isCurrentRoute = location.pathname === '/';
    if (!isCurrentRoute) {
      console.log('[Dashboard] 不是当前路由，不加载数据', { pathname: location.pathname });
      if (showLoading) {
        setLoading(false);
      }
      return;
    }
    
    console.log('[Dashboard] 开始加载数据', { isMounted: isMountedRef.current, isCurrentRoute: isCurrentRouteRef.current, pathname: location.pathname });
    if (showLoading) {
      setLoading(true);
    }
    try {
      const [statsData, recentRunsData, aiHealth] = await Promise.all([
        getDashboardStatistics(),
        getRecentTestRuns(10),
        checkAIEngineHealth().catch(() => ({ status: 'unknown' }))
      ]);
      
      // 检查路由（异步操作后）
      if (location.pathname !== '/') {
        console.warn('[Dashboard] 不在仪表板页面，不更新状态');
        if (showLoading) {
          setLoading(false);
        }
        return;
      }
      
      setStats(statsData);
      setRecentRuns(recentRunsData);
      setAiEngineStatus(aiHealth.status || 'unknown');
    } catch (e: any) {
      // 如果是AbortError，说明请求被取消，不显示错误
      if (e.name === 'AbortError' || e.name === 'CanceledError') {
        // 请求被取消，直接清除loading
        if (showLoading) {
          setLoading(false);
        }
        return;
      }
      console.error('加载仪表板数据失败:', e);
      // 无论什么情况，都要清除loading（不依赖路由检查）
      if (showLoading) {
        setLoading(false);
      }
    } finally {
      // 确保loading被清除（双重保险）
      if (showLoading) {
        setLoading(false);
      }
    }
  };


  // 监听路由变化 - 使用 useLayoutEffect 确保在渲染前执行
  useLayoutEffect(() => {
    const isDashboardRoute = location.pathname === '/';
    const wasCurrentRoute = isCurrentRouteRef.current;
    isCurrentRouteRef.current = isDashboardRoute;

    console.log('[Dashboard] 路由变化', { pathname: location.pathname, isCurrentRoute: isDashboardRoute, wasCurrentRoute });

    if (!isDashboardRoute) {
      // 不是当前路由，立即停止所有操作（必须在渲染前清除）
      console.log('[Dashboard] 离开当前路由，立即清除状态');
      isMountedRef.current = false;
      setLoading(false); // 强制清除loading，无论之前是否在当前路由
      return;
    }

    // 是当前路由，确保标记已设置
    isMountedRef.current = true;

    // 首次进入页面时加载数据（只在之前不在当前路由时）
    if (!wasCurrentRoute) {
      console.log('[Dashboard] 首次进入仪表板页面，加载数据');
      // 延迟执行，确保状态已设置
      setTimeout(() => {
        if (location.pathname === '/' && isMountedRef.current && isCurrentRouteRef.current) {
          fetchDashboardData(true);
        }
      }, 0);
    }
  }, [location.pathname, fetchDashboardData]);

  const handleAnalyze = async () => {
    console.log('开始AI分析');
    setAnalyzing(true);
    setAnalysisModalOpen(true);
    setStreamText('');
    setStreamComplete(false);
    setKeyMetrics(null);
    setAnalysisResult(null);
    setFinalAnalysisResult('');
    
    try {
      let accumulatedText = '';
      await analyzeTestSummaryStream(30, undefined, (data) => {
        console.log('收到流式数据:', data.type, data.content ? data.content.substring(0, 50) : '');
        if (data.type === 'summary') {
          setKeyMetrics(data.data);
        } else if (data.type === 'chunk' && data.content) {
          accumulatedText += data.content;
          setStreamText(accumulatedText);
          
          // 如果检测到 JSON_END 标记，立即尝试提取和格式化
          if (accumulatedText.includes('#JSON_END#')) {
            console.log('检测到 #JSON_END# 标记，开始提取JSON');
            const jsonData = extractJsonFromStream(accumulatedText);
            console.log('提取的JSON数据:', jsonData);
            if (jsonData) {
              const markdown = formatAnalysisAsMarkdown(jsonData);
              console.log('生成的Markdown:', markdown.substring(0, 200));
              if (markdown) {
                // 更新最终结果，但继续显示流式文本直到完成
                setFinalAnalysisResult(markdown);
                console.log('已设置最终Markdown结果');
              }
            } else {
              console.warn('未能提取JSON数据');
            }
          }
        } else if (data.type === 'done') {
          // 流式输出完成，尝试提取JSON并格式化为Markdown
          console.log('流式输出完成，开始提取JSON，文本长度:', accumulatedText.length);
          console.log('文本内容预览:', accumulatedText.substring(0, 500));
          const jsonData = extractJsonFromStream(accumulatedText);
          console.log('提取的JSON数据:', jsonData);
          if (jsonData) {
            const markdown = formatAnalysisAsMarkdown(jsonData);
            console.log('生成的Markdown长度:', markdown.length);
            console.log('Markdown预览:', markdown.substring(0, 300));
            if (markdown) {
              setFinalAnalysisResult(markdown);
              console.log('已设置最终Markdown结果');
            } else {
              console.warn('Markdown为空，使用原始文本');
              setFinalAnalysisResult(accumulatedText);
            }
          } else {
            console.warn('未能提取JSON，使用原始文本');
            // 如果没有找到JSON，直接使用原始文本
            setFinalAnalysisResult(accumulatedText);
          }
          setStreamComplete(true);
          setAnalyzing(false);
        } else if (data.type === 'error') {
          message.error('分析失败: ' + (data.message || '未知错误'));
          setAnalyzing(false);
          setStreamComplete(true);
          if (accumulatedText) {
            const jsonData = extractJsonFromStream(accumulatedText);
            if (jsonData) {
              const markdown = formatAnalysisAsMarkdown(jsonData);
              setFinalAnalysisResult(markdown || accumulatedText);
            } else {
              setFinalAnalysisResult(accumulatedText);
            }
          }
        }
      });
    } catch (e: any) {
      message.error('分析失败: ' + (e.message || '未知错误'));
      setAnalyzing(false);
      setStreamComplete(true);
      if (streamText) {
        const jsonData = extractJsonFromStream(streamText);
        if (jsonData) {
          const markdown = formatAnalysisAsMarkdown(jsonData);
          setFinalAnalysisResult(markdown || streamText);
        } else {
          setFinalAnalysisResult(streamText);
        }
      }
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
            onClick={() => {
              // 强制清除loading状态，然后刷新
              setLoading(false);
              if (location.pathname === '/') {
                fetchDashboardData(true);
              }
            }} 
            style={{ fontSize: 18, cursor: 'pointer' }}
            spin={loading && location.pathname === '/'}
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
        {stats.performance_tests && (
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="性能测试"
                value={stats.performance_tests.total}
                prefix={<ThunderboltOutlined />}
                valueStyle={{ color: '#ff7a45' }}
              />
            </Card>
          </Col>
        )}
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
        {stats.performance_tests && (
          <Col xs={24} lg={12}>
            <Card title="性能测试统计">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="待执行"
                      value={stats.performance_tests.status.pending}
                      valueStyle={{ color: '#faad14' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="执行中"
                      value={stats.performance_tests.status.running}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="已完成"
                      value={stats.performance_tests.status.completed}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="已失败"
                      value={stats.performance_tests.status.failed}
                      valueStyle={{ color: '#ff4d4f' }}
                    />
                  </Col>
                </Row>
                <div style={{ marginTop: 16 }}>
                  <Statistic
                    title="已生成分析报告"
                    value={stats.performance_tests.with_analysis}
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </div>
                {stats.performance_tests.recent_count > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Statistic
                      title="最近7天新增"
                      value={stats.performance_tests.recent_count}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </div>
                )}
              </Space>
            </Card>
          </Col>
        )}
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
          setStreamText('');
          setStreamComplete(false);
          setKeyMetrics(null);
          setFinalAnalysisResult('');
        }}
        footer={[
          <Button key="download" onClick={async () => {
            if (finalAnalysisResult) {
              try {
                const blob = new Blob([finalAnalysisResult], { type: 'text/markdown;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `AI测试分析报告_${new Date().toISOString().slice(0, 10)}.md`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
                message.success('报告下载成功');
              } catch (e) {
                message.error('下载失败: ' + (e as Error).message);
              }
            } else {
              message.warning('暂无报告内容');
            }
          }}>
            下载报告
          </Button>,
          <Button key="saveImage" onClick={async () => {
            if (reportContentRef.current) {
              try {
                message.loading({ content: '正在生成图片...', key: 'saveImage', duration: 0 });
                const canvas = await html2canvas(reportContentRef.current, {
                  scale: 2,
                  useCORS: true,
                  backgroundColor: themeMode === 'dark' ? '#141414' : '#ffffff',
                  logging: false,
                });
                const url = canvas.toDataURL('image/png');
                const link = document.createElement('a');
                link.href = url;
                link.download = `AI测试分析报告_${new Date().toISOString().slice(0, 10)}.png`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                message.success({ content: '图片保存成功', key: 'saveImage' });
              } catch (e) {
                message.error({ content: '保存图片失败: ' + (e as Error).message, key: 'saveImage' });
              }
            } else {
              message.warning('无法获取报告内容');
            }
          }}>
            保存为图片
          </Button>,
          <Button key="close" onClick={() => {
            setAnalysisModalOpen(false);
            setAnalysisResult(null);
            setStreamText('');
            setStreamComplete(false);
            setKeyMetrics(null);
            setFinalAnalysisResult('');
          }}>
            关闭
          </Button>,
        ]}
        width={1000}
        styles={{
          body: {
            position: 'relative',
            minHeight: '500px',
            padding: 0,
            overflow: 'hidden',
          }
        }}
      >
        {/* 代码雨遮罩层 - 只在分析时显示 */}
        {analyzing && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 1000,
            background: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}>
            {/* 顶部提示文字 */}
            <div style={{
              position: 'relative',
              zIndex: 1002,
              textAlign: 'center',
              padding: '16px 20px',
              color: '#ffffff',
              fontFamily: 'monospace',
              borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
              flexShrink: 0,
            }}>
              <Spin size="large" style={{ color: '#ffffff' }} />
              <div style={{ 
                marginTop: 12, 
                fontSize: '18px',
                fontWeight: 'bold',
              }}>
                AI智能分析中，请稍后...
              </div>
              <div style={{ 
                marginTop: 8, 
                fontSize: '14px',
                opacity: 0.8,
              }}>
                正在分析测试数据并生成报告
              </div>
            </div>

            {/* 代码雨背景（半透明） */}
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              opacity: 0.2,
              zIndex: 1000,
              pointerEvents: 'none',
            }}>
              <MatrixRain enabled={true} />
            </div>
            
            {/* AI实时输出内容 */}
            <div style={{
              position: 'relative',
              zIndex: 1001,
              flexShrink: 0,
              padding: '16px 20px',
              overflow: 'hidden',
            }}>
              <TerminalDisplay
                text={streamText || '正在连接AI分析引擎...\n\n'}
                speed={10}
                isStreaming={true}
                maxLines={3}
              />
            </div>
          </div>
        )}

        {/* 正常结果显示区域 - 只在分析完成后显示 */}
        {!analyzing && (
          <div ref={reportContentRef} style={{ padding: '20px', position: 'relative', zIndex: 1 }}>
            {keyMetrics && (
              <Card size="small" style={{ marginBottom: 12 }}>
                <Title level={4} style={{ marginBottom: 12, fontSize: '16px' }}>📊 关键指标</Title>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="总体通过率"
                      value={keyMetrics.overall_pass_rate || 0}
                      suffix="%"
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={6}>
                  <Statistic
                      title="测试运行次数"
                      value={keyMetrics.total_test_runs || 0}
                  />
              </Col>
                  <Col span={6}>
                  <Statistic
                      title="测试用例总数"
                      value={keyMetrics.total_test_cases || 0}
                  />
              </Col>
                  <Col span={6}>
                  <Statistic
                      title="失败率"
                      value={keyMetrics.failure_rate || 0}
                      suffix="%"
                      valueStyle={{ color: '#ff4d4f' }}
                    />
              </Col>
            </Row>
          </Card>
            )}

            {/* 分析结果展示 */}
            {streamComplete && finalAnalysisResult && (
              <Card size="small" style={{ marginTop: 16 }}>
                <Title level={4} style={{ marginBottom: 12 }}>🔍 AI分析洞察</Title>
                <div style={{ 
                  lineHeight: '1.6',
                  padding: '12px',
                  background: colorFillSecondary,
                  borderRadius: '4px'
                }}>
                  <ReactMarkdown
                    components={{
                      h2: ({node, ...props}) => <h2 style={{ marginTop: '16px', marginBottom: '8px', fontSize: '16px', fontWeight: 'bold', color: '#1890ff' }} {...props} />,
                      h3: ({node, ...props}) => <h3 style={{ marginTop: '12px', marginBottom: '6px', fontSize: '14px', fontWeight: 'bold', color: '#52c41a' }} {...props} />,
                      ul: ({node, ...props}) => <ul style={{ marginLeft: '18px', marginBottom: '8px', marginTop: '4px' }} {...props} />,
                      ol: ({node, ...props}) => <ol style={{ marginLeft: '18px', marginBottom: '8px', marginTop: '4px' }} {...props} />,
                      li: ({node, ...props}) => <li style={{ marginBottom: '4px', fontSize: '13px' }} {...props} />,
                      p: ({node, ...props}) => <p style={{ marginBottom: '8px', fontSize: '13px' }} {...props} />,
                      strong: ({node, ...props}) => <strong style={{ fontWeight: 'bold', color: '#1890ff' }} {...props} />,
                    }}
                  >
                    {finalAnalysisResult}
                  </ReactMarkdown>
                </div>
              </Card>
            )}

            {/* 如果还没有结果，显示空状态 */}
            {!streamComplete && !finalAnalysisResult && (
              <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" />
                <div style={{ marginTop: 16 }}>正在初始化分析...</div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Dashboard; 