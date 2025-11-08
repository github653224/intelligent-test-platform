import React, { useEffect, useLayoutEffect, useState, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Typography, 
  message, Popconfirm, Progress, Divider, Descriptions, Drawer, 
  Tooltip, Statistic, Row, Col, InputNumber, DatePicker, Spin
} from 'antd';
import dayjs from 'dayjs';
import { 
  PlusOutlined, DeleteOutlined, ReloadOutlined, 
  PlayCircleOutlined, StopOutlined, EyeOutlined,
  DownloadOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import { 
  listTestRuns, createTestRun, deleteTestRun, 
  executeTestRun, cancelTestRun, getTestRunDetailedReport,
  downloadTestRunCsvReport, manuallyVerifyTestResult,
  setTestRunSchedule, removeTestRunSchedule, getTestRunSchedule,
  listProjects, listTestCases
} from '../services/aiService';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const { Title } = Typography;
const { TextArea } = Input;

interface TestRun {
  id: number;
  project_id: number;
  test_suite_id?: number;
  name: string;
  status: string;
  start_time?: string;
  end_time?: string;
  results?: any;
  total_cases?: number;
  passed_cases?: number;
  failed_cases?: number;
  skipped_cases?: number;
  duration?: number;
  created_at?: string;
  updated_at?: string;
}

interface Project {
  id: number;
  name: string;
}

interface TestCase {
  id: number;
  title: string;
  test_type: string;
  project_id: number;
}

const TestRuns: React.FC = () => {
  const location = useLocation();
  const [items, setItems] = useState<TestRun[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const isMountedRef = useRef(true);
  const isCurrentRouteRef = useRef(false);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedTestRun, setSelectedTestRun] = useState<TestRun | null>(null);
  const [testRunDetail, setTestRunDetail] = useState<any>(null);
  const [form] = Form.useForm();
  const [selectedProjectId, setSelectedProjectId] = useState<number | undefined>(undefined);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // 手动验证相关状态
  const [verificationModalOpen, setVerificationModalOpen] = useState(false);
  const [verifyingTestCase, setVerifyingTestCase] = useState<any>(null);
  const [verificationForm] = Form.useForm();
  
  // Drawer宽度状态
  const [drawerWidth, setDrawerWidth] = useState(800);
  const [isResizing, setIsResizing] = useState(false);
  
  // 测试用例选择相关状态
  const [testCaseSearchText, setTestCaseSearchText] = useState('');
  const [testCaseTypeFilter, setTestCaseTypeFilter] = useState<string | undefined>(undefined);
  
  // 定时执行相关状态
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [schedulingTestRun, setSchedulingTestRun] = useState<TestRun | null>(null);
  const [scheduleForm] = Form.useForm();

  const fetchProjects = useCallback(async () => {
    try {
      const data = await listProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (e: any) {
      console.error('加载项目列表失败', e);
      setProjects([]);
    }
  }, []);

  const fetchTestCases = useCallback(async (projectId?: number) => {
    try {
      const data = await listTestCases(projectId ? { project_id: projectId } : undefined);
      setTestCases(Array.isArray(data) ? data : []);
    } catch (e: any) {
      console.error('加载测试用例列表失败', e);
      setTestCases([]);
    }
  }, []);

  const fetchData = useCallback(async (showLoading: boolean = true) => {
    // 首先检查是否是当前路由 - 必须在最前面检查
    const isCurrentRoute = location.pathname === '/test-runs';
    if (!isCurrentRoute) {
      console.log('[TestRuns] 不是当前路由，不加载数据', { pathname: location.pathname });
      if (showLoading) {
        setLoading(false);
      }
      return;
    }
    
    console.log('[TestRuns] 开始加载数据', { isMounted: isMountedRef.current, isCurrentRoute: isCurrentRouteRef.current, pathname: location.pathname });
    if (showLoading) {
      setLoading(true);
    }
    try {
      const params = selectedProjectId ? { project_id: selectedProjectId } : undefined;
      const data = await listTestRuns(params);
      const newItems = Array.isArray(data) ? data : [];
      // 检查路由（异步操作后）
      if (location.pathname !== '/test-runs') {
        console.warn('[TestRuns] 不在测试执行页面，不更新状态');
        if (showLoading) {
          setLoading(false);
        }
        return;
      }
      // 如果新数据为空，但之前有数据，保留旧数据（防止数据丢失）
      setItems(prev => {
        if (location.pathname !== '/test-runs') {
          return prev;
        }
        if (newItems.length === 0 && prev.length > 0) {
          console.warn('[数据加载] 后端返回空数组，保留现有数据');
          return prev;
        }
        return newItems;
      });
    } catch (e: any) {
      // 如果是AbortError，说明请求被取消，不显示错误
      if (e.name === 'AbortError' || e.name === 'CanceledError') {
        // 请求被取消，直接清除loading
        if (showLoading) {
          setLoading(false);
        }
        return;
      }
      if (e?.response?.status === 404 || e?.response?.status === 200) {
        // 404 或空数据时，如果之前有数据，保留旧数据
        if (isMountedRef.current && isCurrentRouteRef.current) {
          setItems(prev => {
            if (prev.length > 0) {
              console.warn('[数据加载] 请求返回空，保留现有数据');
              return prev;
            }
            return [];
          });
        }
      } else {
        console.error('加载测试运行失败:', e);
      }
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
  }, [selectedProjectId, location.pathname]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // 监听路由变化 - 使用 useLayoutEffect 确保在渲染前执行
  useLayoutEffect(() => {
    const isTestRunsRoute = location.pathname === '/test-runs';
    const wasCurrentRoute = isCurrentRouteRef.current;
    isCurrentRouteRef.current = isTestRunsRoute;

    console.log('[TestRuns] 路由变化', { pathname: location.pathname, isCurrentRoute: isTestRunsRoute, wasCurrentRoute });

    if (!isTestRunsRoute) {
      // 不是当前路由，立即停止所有操作（必须在渲染前清除）
      console.log('[TestRuns] 离开当前路由，立即清除状态');
      isMountedRef.current = false;
      setLoading(false); // 强制清除loading，无论之前是否在当前路由
      // 清除轮询
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      return;
    }

    // 是当前路由，确保标记已设置
    isMountedRef.current = true;

    // 首次进入页面时加载数据（只在之前不在当前路由时）
    if (!wasCurrentRoute) {
      console.log('[TestRuns] 首次进入测试执行页面，加载数据');
      // 延迟执行，确保状态已设置
      setTimeout(() => {
        if (location.pathname === '/test-runs' && isMountedRef.current && isCurrentRouteRef.current) {
          fetchData(true);
        }
      }, 0);
    }
  }, [location.pathname, fetchData]);

  // 注意：不再使用 useEffect 自动加载数据，只在 useLayoutEffect 中处理
  // 这样可以避免重复调用和 loading 状态异常

  // 单独处理轮询逻辑
  useEffect(() => {
    // 检查是否是当前路由
    if (location.pathname !== '/test-runs') {
      return;
    }
    
    if (!isMountedRef.current || !isCurrentRouteRef.current) {
      return;
    }

    const hasRunning = items.some(item => item.status === 'running');
    
    if (hasRunning && !pollingIntervalRef.current) {
      // 有正在运行的测试，启动轮询
      const interval = setInterval(() => {
        // 每次轮询前检查组件是否已挂载和是否是当前路由
        if (!isMountedRef.current || !isCurrentRouteRef.current) {
          clearInterval(interval);
          pollingIntervalRef.current = null;
          return;
        }
        // 不显示 loading，只更新数据
        fetchData(false);
      }, 3000); // 每3秒刷新一次
      pollingIntervalRef.current = interval;
    } else if (!hasRunning && pollingIntervalRef.current) {
      // 没有正在运行的测试，停止轮询
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [items, fetchData, location.pathname]);

  useEffect(() => {
    if (selectedProjectId) {
      fetchTestCases(selectedProjectId);
    }
  }, [selectedProjectId, fetchTestCases]);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      project_id: selectedProjectId,
    });
    setModalOpen(true);
  };

  const openDetail = async (record: TestRun) => {
    setSelectedTestRun(record);
    try {
      const detail = await getTestRunDetailedReport(record.id);
      setTestRunDetail(detail);
      setDetailDrawerOpen(true);
    } catch (e: any) {
      message.error('加载详情失败');
      console.error(e);
    }
  };

  const handleDelete = useCallback(async (record: TestRun) => {
    try {
      if (record.status === 'running') {
        await cancelTestRun(record.id);
      }
      await deleteTestRun(record.id);
      message.success('删除成功');
      fetchData();
    } catch (e) {
      message.error('删除失败');
    }
  }, [fetchData]);

  const handleExecute = async (record: TestRun) => {
    try {
      await executeTestRun(record.id);
      message.success('测试执行已启动');
      fetchData();
    } catch (e: any) {
      message.error('启动测试失败: ' + (e?.response?.data?.detail || '未知错误'));
    }
  };

  const handleCancel = async (record: TestRun) => {
    try {
      await cancelTestRun(record.id);
      message.success('测试已取消');
      fetchData();
    } catch (e: any) {
      message.error('取消测试失败: ' + (e?.response?.data?.detail || '未知错误'));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (!values.project_id) {
        message.error('请选择项目');
        return;
      }
      if (!values.test_case_ids || values.test_case_ids.length === 0) {
        message.error('请至少选择一个测试用例');
        return;
      }
      
      // 解析执行配置
      let executionConfig = {};
      if (values.execution_config) {
        try {
          executionConfig = typeof values.execution_config === 'string' 
            ? JSON.parse(values.execution_config) 
            : values.execution_config;
        } catch (e) {
          message.warning('执行配置格式错误，将使用默认配置');
          executionConfig = {};
        }
      }
      
      await createTestRun({
        project_id: values.project_id,
        test_suite_id: values.test_suite_id,
        name: values.name,
        test_case_ids: values.test_case_ids,
        execution_config: executionConfig,
      });
      message.success('测试运行已创建，请在列表中选择执行');
      setModalOpen(false);
      setTestCaseSearchText('');
      setTestCaseTypeFilter(undefined);
      form.resetFields();
      fetchData();
    } catch (e: any) {
      if (e?.response?.data?.detail) {
        message.error(e.response.data.detail);
      } else {
        message.error('操作失败');
      }
    }
  };

  const [reportPreviewOpen, setReportPreviewOpen] = useState(false);
  const [reportPreviewUrl, setReportPreviewUrl] = useState<string | null>(null);
  const [reportPreviewLoading, setReportPreviewLoading] = useState(false);
  const [reportPreviewError, setReportPreviewError] = useState<string | null>(null);
  const reportTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  // 监听iframe加载状态
  useEffect(() => {
    if (!reportPreviewUrl || !reportPreviewOpen) {
      return;
    }

    const checkIframeLoad = () => {
      if (iframeRef.current) {
        try {
          // 尝试访问iframe的内容，如果可访问说明已加载完成
          const iframeDoc = iframeRef.current.contentDocument || iframeRef.current.contentWindow?.document;
          if (iframeDoc && iframeDoc.readyState === 'complete') {
            console.log('Report iframe loaded (via useEffect check)');
            setReportPreviewLoading(false);
            setReportPreviewError(null);
            if (reportTimeoutRef.current) {
              clearTimeout(reportTimeoutRef.current);
              reportTimeoutRef.current = null;
            }
            return true;
          }
        } catch (e) {
          // 跨域情况下无法访问contentDocument，这是正常的
          // 在这种情况下，我们依赖于onLoad事件或定时器
        }
      }
      return false;
    };

    // 立即检查一次
    if (checkIframeLoad()) {
      return;
    }

    // 设置定期检查（每200ms检查一次，最多检查10次 = 2秒）
    let checkCount = 0;
    const checkInterval = setInterval(() => {
      checkCount++;
      if (checkIframeLoad()) {
        clearInterval(checkInterval);
      } else if (checkCount >= 10) {
        // 如果2秒后还没检测到加载完成，但iframe已存在，假设它已加载
        // 这可能是因为跨域限制导致无法访问contentDocument，但内容实际上已经加载
        if (iframeRef.current) {
          console.log('Iframe exists but cannot verify load state (likely cross-origin), assuming loaded after 2s');
          setReportPreviewLoading(false);
          setReportPreviewError(null);
          if (reportTimeoutRef.current) {
            clearTimeout(reportTimeoutRef.current);
            reportTimeoutRef.current = null;
          }
        }
        clearInterval(checkInterval);
      }
    }, 200);

    // 备用方案：如果1.5秒后iframe存在但检测失败，直接隐藏加载状态
    // 这样可以更快地显示内容，即使ECharts等资源还在加载
    const fallbackTimer = setTimeout(() => {
      if (iframeRef.current && reportPreviewLoading) {
        console.log('Fallback: hiding loading state after 1.5s (content may still be loading)');
        setReportPreviewLoading(false);
        setReportPreviewError(null);
        if (reportTimeoutRef.current) {
          clearTimeout(reportTimeoutRef.current);
          reportTimeoutRef.current = null;
        }
      }
      clearInterval(checkInterval);
    }, 1500);

    return () => {
      clearInterval(checkInterval);
      clearTimeout(fallbackTimer);
    };
  }, [reportPreviewUrl, reportPreviewOpen, reportPreviewLoading]);

  const handleViewReport = async (testRunId: number) => {
    try {
      setReportPreviewLoading(true);
      setReportPreviewError(null);
      // 清除之前的超时
      if (reportTimeoutRef.current) {
        clearTimeout(reportTimeoutRef.current);
      }
      
      // 找到对应的测试运行记录
      const testRun = items.find(tr => tr.id === testRunId);
      setSelectedTestRun(testRun || null);
      
      // 获取HTML报告URL
      const reportUrl = `${API_BASE_URL}/test-runs/${testRunId}/report/html`;
      
      // 设置超时（15秒），如果15秒后还没加载完成，显示错误
      // 注意：由于跨域限制，可能无法检测到iframe加载完成，但内容实际上已经加载
      // useEffect会在2秒后自动隐藏加载状态（如果iframe存在），所以这个超时主要用于兜底
      reportTimeoutRef.current = setTimeout(() => {
        setReportPreviewLoading(false);
        // 不显示错误，因为内容可能已经加载了，只是检测不到
        // 如果用户看不到内容，可以使用"在新窗口打开"按钮
      }, 15000);
      
      setReportPreviewUrl(reportUrl);
      setReportPreviewOpen(true);
    } catch (e: any) {
      console.error('Load report error:', e);
      message.error('加载报告失败: ' + (e.message || '未知错误'));
      setReportPreviewError(e.message || '加载失败');
      setReportPreviewLoading(false);
      if (reportTimeoutRef.current) {
        clearTimeout(reportTimeoutRef.current);
        reportTimeoutRef.current = null;
      }
    }
  };

  const handleDownloadReport = async (testRunId: number, format: 'csv' | 'json' = 'csv') => {
    try {
      if (format === 'csv') {
        await downloadTestRunCsvReport(testRunId);
        message.success('CSV报告下载成功');
      } else if (format === 'json') {
        const response = await fetch(`${API_BASE_URL}/test-runs/${testRunId}/report/json`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `test_run_${testRunId}_report.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        message.success('JSON报告下载成功');
      }
    } catch (e: any) {
      message.error('下载报告失败');
    }
  };

  const openScheduleModal = async (record: TestRun) => {
    setSchedulingTestRun(record);
    try {
      const scheduleInfo = await getTestRunSchedule(record.id);
      if (scheduleInfo.scheduled && scheduleInfo.schedule_config) {
        scheduleForm.setFieldsValue({
          type: scheduleInfo.schedule_config.type,
          cron_expression: scheduleInfo.schedule_config.cron_expression || '',
          interval: scheduleInfo.schedule_config.interval || {},
          run_time: scheduleInfo.schedule_config.run_time ? dayjs(scheduleInfo.schedule_config.run_time) : null,
        });
      } else {
        scheduleForm.resetFields();
        scheduleForm.setFieldsValue({ type: 'interval' });
      }
    } catch (e: any) {
      scheduleForm.resetFields();
      scheduleForm.setFieldsValue({ type: 'interval' });
    }
    setScheduleModalOpen(true);
  };

  const handleScheduleSubmit = async () => {
    if (!schedulingTestRun) return;
    
    try {
      const values = await scheduleForm.validateFields();
      const scheduleConfig: any = { type: values.type };
      
      if (values.type === 'cron') {
        if (!values.cron_expression) {
          message.error('请输入Cron表达式');
          return;
        }
        scheduleConfig.cron_expression = values.cron_expression;
      } else if (values.type === 'interval') {
        scheduleConfig.interval = {
          seconds: values.interval?.seconds || 0,
          minutes: values.interval?.minutes || 0,
          hours: values.interval?.hours || 0,
          days: values.interval?.days || 0,
        };
      } else if (values.type === 'once') {
        if (!values.run_time) {
          message.error('请选择执行时间');
          return;
        }
        // 将 dayjs 对象转换为 ISO 字符串
        scheduleConfig.run_time = dayjs(values.run_time).toISOString();
      }
      
      await setTestRunSchedule(schedulingTestRun.id, scheduleConfig);
      message.success('定时执行已设置');
      setScheduleModalOpen(false);
      fetchData();
    } catch (e: any) {
      if (e?.response?.data?.detail) {
        message.error(e.response.data.detail);
      } else {
        message.error('设置定时执行失败');
      }
    }
  };

  const handleRemoveSchedule = async (testRunId: number) => {
    try {
      await removeTestRunSchedule(testRunId);
      message.success('定时执行已移除');
      fetchData();
    } catch (e: any) {
      message.error('移除定时执行失败');
    }
  };

  const openVerificationModal = (testResult: any) => {
    setVerifyingTestCase(testResult);
    verificationForm.setFieldsValue({
      status: testResult.status === 'skipped' ? 'passed' : testResult.status,
      actual_result: testResult.actual_result || '',
      verification_notes: testResult.verification_notes || '',
      failure_reason: testResult.failure_reason || '',
      bug_id: testResult.bug_id || '',
      verified_by: '当前用户', // 这里可以从用户上下文获取
    });
    setVerificationModalOpen(true);
  };

  // 处理Drawer宽度调整
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX;
      // 限制宽度在400px到1200px之间
      if (newWidth >= 400 && newWidth <= 1200) {
        setDrawerWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  // 获取过滤后的测试用例
  const getFilteredTestCases = useCallback(() => {
    const projectId = selectedProjectId || form.getFieldValue('project_id');
    let filtered = testCases.filter(tc => {
      if (projectId && tc.project_id !== projectId) {
        return false;
      }
      
      // 类型过滤
      if (testCaseTypeFilter && tc.test_type !== testCaseTypeFilter) {
        return false;
      }
      
      // 搜索过滤
      if (testCaseSearchText) {
        const searchLower = testCaseSearchText.toLowerCase();
        return tc.title.toLowerCase().includes(searchLower) ||
               tc.test_type.toLowerCase().includes(searchLower);
      }
      
      return true;
    });
    
    return filtered;
  }, [testCases, testCaseTypeFilter, testCaseSearchText, selectedProjectId, form]);

  const handleVerificationSubmit = async () => {
    if (!selectedTestRun || !verifyingTestCase) return;
    
    try {
      const values = await verificationForm.validateFields();
      await manuallyVerifyTestResult({
        test_run_id: selectedTestRun.id,
        test_case_id: verifyingTestCase.test_case_id,
        status: values.status,
        actual_result: values.actual_result,
        verification_notes: values.verification_notes,
        failure_reason: values.failure_reason,
        bug_id: values.bug_id,
        verified_by: values.verified_by,
      });
      
      message.success('验证结果已保存');
      setVerificationModalOpen(false);
      setVerifyingTestCase(null);
      verificationForm.resetFields();
      
      // 立即刷新详情
      if (selectedTestRun) {
        try {
          // 使用新的查询确保获取最新数据
          const detail = await getTestRunDetailedReport(selectedTestRun.id);
          setTestRunDetail(detail);
        } catch (e) {
          console.error('刷新详情失败:', e);
          // 如果失败，延迟重试
          setTimeout(async () => {
            try {
              const detail = await getTestRunDetailedReport(selectedTestRun.id);
              setTestRunDetail(detail);
            } catch (retryError) {
              console.error('重试刷新详情失败:', retryError);
            }
          }, 500);
        }
      }
      
      // 刷新列表
      fetchData();
    } catch (e: any) {
      message.error('保存验证结果失败: ' + (e?.response?.data?.detail || '未知错误'));
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

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 80, fixed: 'left' },
    {
      title: '项目',
      dataIndex: 'project_id',
      width: 120,
      render: (projectId: number) => {
        const project = projects.find(p => p.id === projectId);
        return project ? project.name : `项目 ${projectId}`;
      },
    },
    { 
      title: '名称', 
      dataIndex: 'name', 
      width: 200,
      ellipsis: {
        showTitle: false,
      },
      render: (text: string, record: TestRun) => (
        <Space>
          <Tooltip placement="topLeft" title={text}>
            {text}
          </Tooltip>
          {record.results?.scheduled && (
            <Tooltip title="已设置定时执行">
              <Tag icon={<ClockCircleOutlined />} color="blue">定时</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '测试统计',
      width: 220,
      render: (_: any, record: TestRun) => {
        const total = record.total_cases || 0;
        const passed = record.passed_cases || 0;
        const failed = record.failed_cases || 0;
        const skipped = record.skipped_cases || 0;
        
        if (total === 0) {
          // 尝试从 results 中获取 test_case_ids 的数量
          const testCaseIds = record.results?.test_case_ids || [];
          const totalCases = testCaseIds.length || 0;
          if (totalCases > 0) {
            return <span style={{ color: '#666' }}>总计: {totalCases} 个用例</span>;
          }
          return '-';
        }
        
        return (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div style={{ fontSize: '12px' }}>
              <span style={{ fontWeight: 'bold', color: '#1890ff' }}>总计: {total}</span>
              {' | '}
              <span style={{ color: '#52c41a' }}>通过: {passed}</span>
              {' | '}
              <span style={{ color: '#ff4d4f' }}>失败: {failed}</span>
              {' | '}
              <span style={{ color: '#faad14' }}>跳过: {skipped}</span>
            </div>
            {record.status === 'running' && (
              <Progress percent={Math.round(((passed + failed + skipped) / total) * 100)} size="small" />
            )}
          </Space>
        );
      },
    },
    {
      title: '通过率',
      width: 100,
      render: (_: any, record: TestRun) => {
        const total = record.total_cases || 0;
        const passed = record.passed_cases || 0;
        if (total === 0) return '-';
        const passRate = Math.round((passed / total) * 100);
        return (
          <span style={{ color: passRate === 100 ? '#52c41a' : passRate >= 80 ? '#faad14' : '#ff4d4f' }}>
            {passRate}%
          </span>
        );
      },
    },
    {
      title: '执行时长',
      width: 100,
      render: (_: any, record: TestRun) => {
        if (!record.duration) return '-';
        return `${record.duration.toFixed(2)}s`;
      },
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      width: 180,
      render: (text: string) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      width: 180,
      render: (text: string) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      width: 380,
      fixed: 'right',
      render: (_: any, record: TestRun) => (
        <Space>
          <Button 
            icon={<EyeOutlined />} 
            size="small" 
            onClick={() => openDetail(record)}
          >
            详情
          </Button>
          {record.status === 'running' ? (
            <Button 
              icon={<StopOutlined />} 
              size="small" 
              danger
              onClick={() => handleCancel(record)}
            >
              取消
            </Button>
          ) : record.status === 'pending' || record.status === 'failed' ? (
            <Button 
              icon={<PlayCircleOutlined />} 
              size="small" 
              type="primary"
              onClick={() => handleExecute(record)}
            >
              执行
            </Button>
          ) : null}
          {record.status === 'completed' && (
            <>
              <Button 
                icon={<EyeOutlined />} 
                size="small"
                onClick={() => {
                  const reportUrl = `${API_BASE_URL}/test-runs/${record.id}/report/html`;
                  window.open(reportUrl, '_blank');
                }}
              >
                查看报告
              </Button>
            </>
          )}
          <Button
            icon={<ClockCircleOutlined />}
            size="small"
            onClick={() => openScheduleModal(record)}
          >
            {record.results?.scheduled ? '定时设置' : '定时执行'}
          </Button>
          {record.results?.scheduled && (
            <Popconfirm
              title="确认移除定时执行？"
              onConfirm={() => handleRemoveSchedule(record.id)}
            >
              <Button size="small" danger>
                取消定时
              </Button>
            </Popconfirm>
          )}
          <Popconfirm 
            title="确认删除该测试运行？" 
            onConfirm={() => handleDelete(record)}
          >
            <Button icon={<DeleteOutlined />} size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>测试执行</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建测试运行
          </Button>
            <Button icon={<ReloadOutlined />} onClick={() => {
              // 强制清除loading状态，然后刷新
              setLoading(false);
              if (location.pathname === '/test-runs') {
                fetchData(true);
              }
            }} loading={loading && location.pathname === '/test-runs'}>
            刷新
            </Button>
          <Select
            placeholder="筛选项目"
            allowClear
            style={{ width: 200 }}
            value={selectedProjectId}
            onChange={(value) => setSelectedProjectId(value)}
            options={projects.map(p => ({ label: p.name, value: p.id }))}
          />
        </Space>
        <Table
          rowKey="id"
          columns={columns as any}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
          scroll={{ x: 1600 }}
        />
      </Card>

      {/* 创建测试运行Modal */}
      <Modal
        title="新建测试运行"
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => {
          setModalOpen(false);
          setTestCaseSearchText('');
          setTestCaseTypeFilter(undefined);
          form.resetFields();
        }}
        okText="创建"
        width={900}
      >
        <Form layout="vertical" form={form}>
          <Form.Item
            label="测试运行名称"
            name="name"
            rules={[{ required: true, message: '请输入测试运行名称' }]}
          >
            <Input placeholder="例如：回归测试 - 2024-01-01" />
          </Form.Item>
          <Form.Item
            label="所属项目"
            name="project_id"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="选择项目"
              onChange={(value) => {
                setSelectedProjectId(value);
                fetchTestCases(value);
              }}
              options={projects.map(p => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
          <Form.Item
            label="选择测试用例"
            name="test_case_ids"
            rules={[{ required: true, message: '请至少选择一个测试用例' }]}
          >
            <div>
              <Space style={{ marginBottom: 8, width: '100%' }} direction="vertical" size="small">
                <Space>
                  <Select
                    placeholder="按类型筛选"
                    allowClear
                    style={{ width: 150 }}
                    value={testCaseTypeFilter}
                    onChange={(value) => setTestCaseTypeFilter(value)}
                    options={[
                      { label: '功能测试', value: 'functional' },
                      { label: 'API测试', value: 'api' },
                      { label: 'UI测试', value: 'ui' },
                    ]}
                  />
                  <Input
                    placeholder="搜索测试用例..."
                    allowClear
                    value={testCaseSearchText}
                    onChange={(e) => setTestCaseSearchText(e.target.value)}
                    style={{ width: 200 }}
                  />
                  <Button
                    size="small"
                    type="primary"
                    onClick={() => {
                      const filteredCases = getFilteredTestCases();
                      const allFilteredIds = filteredCases.map(tc => tc.id);
                      console.log('全选当前结果:', { filteredCases: filteredCases.length, allFilteredIds });
                      // 如果使用了搜索或类型筛选，只选择当前过滤后的用例
                      if (testCaseSearchText || testCaseTypeFilter) {
                        form.setFieldsValue({ test_case_ids: allFilteredIds });
                      } else {
                        // 如果没有筛选，合并到已选择的用例
                        const currentValues = form.getFieldValue('test_case_ids') || [];
                        const newValues = Array.from(new Set([...currentValues, ...allFilteredIds]));
                        form.setFieldsValue({ test_case_ids: newValues });
                      }
                    }}
                  >
                    全选当前结果
                  </Button>
                  <Button
                    size="small"
                    onClick={() => {
                      form.setFieldsValue({ test_case_ids: [] });
                    }}
                  >
                    清空选择
                  </Button>
                </Space>
                <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.test_case_ids !== currentValues.test_case_ids}>
                  {({ getFieldValue }) => {
                    const selectedCount = getFieldValue('test_case_ids')?.length || 0;
                    return selectedCount > 0 ? (
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        已选择 {selectedCount} 个测试用例
                      </div>
                    ) : null;
                  }}
                </Form.Item>
              </Space>
              <Form.Item noStyle shouldUpdate>
                {({ getFieldValue }) => (
                  <Select
                    mode="multiple"
                    placeholder="选择要执行的测试用例"
                    disabled={!form.getFieldValue('project_id')}
                    value={getFieldValue('test_case_ids')}
                    onChange={(values) => form.setFieldsValue({ test_case_ids: values })}
                    filterOption={false}
                    showSearch
                    searchValue={testCaseSearchText}
                    onSearch={setTestCaseSearchText}
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '8px 0' }} />
                    <div style={{ padding: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', color: '#666' }}>
                        共 {getFilteredTestCases().length} 个用例
                      </span>
                      <Space>
                        <Button
                          type="link"
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            const filteredCases = getFilteredTestCases();
                            const allFilteredIds = filteredCases.map(tc => tc.id);
                            console.log('下拉框内全选:', { filteredCases: filteredCases.length, allFilteredIds });
                            // 如果使用了搜索或类型筛选，只选择当前过滤后的用例
                            if (testCaseSearchText || testCaseTypeFilter) {
                              form.setFieldsValue({ test_case_ids: allFilteredIds });
                            } else {
                              // 如果没有筛选，合并到已选择的用例
                              const currentValues = form.getFieldValue('test_case_ids') || [];
                              const newValues = Array.from(new Set([...currentValues, ...allFilteredIds]));
                              form.setFieldsValue({ test_case_ids: newValues });
                            }
                          }}
                        >
                          全选当前结果
                        </Button>
                        <Button
                          type="link"
                          size="small"
                          onClick={() => {
                            const filteredCases = getFilteredTestCases();
                            const filteredIds = filteredCases.map(tc => tc.id);
                            const currentValues = form.getFieldValue('test_case_ids') || [];
                            const newValues = currentValues.filter((id: number) => !filteredIds.includes(id));
                            form.setFieldsValue({ test_case_ids: newValues });
                          }}
                        >
                          取消当前结果
                        </Button>
                      </Space>
                    </div>
                  </>
                )}
                options={getFilteredTestCases().map(tc => {
                  const testTypeMap: Record<string, { color: string; text: string }> = {
                    functional: { color: 'blue', text: '功能' },
                    api: { color: 'green', text: 'API' },
                    ui: { color: 'purple', text: 'UI' },
                  };
                  const typeInfo = testTypeMap[tc.test_type] || { color: 'default', text: tc.test_type };
                  
                  return {
                    label: (
                      <Space>
                        <Tag color={typeInfo.color} style={{ fontSize: '11px', margin: 0 }}>
                          {typeInfo.text}
                        </Tag>
                        <span>{tc.title}</span>
                      </Space>
                    ),
                    value: tc.id,
                  };
                })}
                  />
                )}
              </Form.Item>
            </div>
          </Form.Item>
          <Form.Item 
            label="执行配置（可选）" 
            name="execution_config"
            tooltip='JSON格式配置，例如：{"base_url": "http://localhost:8000", "timeout": 30, "browser": "chrome", "headless": true}'
          >
            <TextArea 
              rows={3} 
              placeholder='{"base_url": "http://localhost:8000", "timeout": 30}'
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 测试运行详情Drawer */}
      <Drawer
        title="测试运行详情"
        placement="right"
        width={drawerWidth}
        open={detailDrawerOpen}
        onClose={() => {
          setDetailDrawerOpen(false);
          setSelectedTestRun(null);
          setTestRunDetail(null);
        }}
        styles={{
          body: { padding: '24px', position: 'relative' },
        }}
      >
        {/* 可拖拽调整宽度的条 */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: '4px',
            cursor: 'col-resize',
            backgroundColor: isResizing ? '#1890ff' : 'transparent',
            zIndex: 1000,
            transition: isResizing ? 'none' : 'background-color 0.2s',
          }}
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsResizing(true);
          }}
          onMouseEnter={(e) => {
            if (!isResizing) {
              e.currentTarget.style.backgroundColor = '#1890ff';
            }
          }}
          onMouseLeave={(e) => {
            if (!isResizing) {
              e.currentTarget.style.backgroundColor = 'transparent';
            }
          }}
        />
        {testRunDetail && (
          <div style={{ paddingLeft: '8px' }}>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="ID">{testRunDetail.test_run_id}</Descriptions.Item>
              <Descriptions.Item label="名称">{testRunDetail.test_run_name}</Descriptions.Item>
              <Descriptions.Item label="状态">{getStatusTag(testRunDetail.status)}</Descriptions.Item>
              <Descriptions.Item label="通过率">{testRunDetail.pass_rate}%</Descriptions.Item>
              <Descriptions.Item label="开始时间">{testRunDetail.start_time || '-'}</Descriptions.Item>
              <Descriptions.Item label="结束时间">{testRunDetail.end_time || '-'}</Descriptions.Item>
              <Descriptions.Item label="执行时长">{testRunDetail.duration?.toFixed(2) || '0'} 秒</Descriptions.Item>
            </Descriptions>

            <Divider>统计信息</Divider>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="总用例数" value={testRunDetail.statistics?.total_cases || 0} />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="通过" 
                  value={testRunDetail.statistics?.passed_cases || 0} 
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="失败" 
                  value={testRunDetail.statistics?.failed_cases || 0} 
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="跳过" 
                  value={testRunDetail.statistics?.skipped_cases || 0} 
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            </Row>

            <Divider>测试结果</Divider>
            <Table
              rowKey={(record: any) => record.test_case_id}
              dataSource={testRunDetail.test_results || []}
              pagination={false}
              columns={[
                {
                  title: '测试用例',
                  dataIndex: 'test_case_title',
                  width: 200,
                  ellipsis: true,
                },
                {
                  title: '状态',
                  dataIndex: 'status',
                  width: 100,
                  render: (status: string, record: any) => {
                    const statusMap: Record<string, { color: string }> = {
                      passed: { color: 'success' },
                      failed: { color: 'error' },
                      skipped: { color: 'warning' },
                      error: { color: 'error' },
                      blocked: { color: 'default' },
                    };
                    const statusInfo = statusMap[status] || { color: 'default' };
                    return (
                      <Tooltip title={record.manually_verified ? '已手动验证' : ''}>
                        <Tag color={statusInfo.color}>{status.toUpperCase()}</Tag>
                      </Tooltip>
                    );
                  },
                },
                {
                  title: '执行时长',
                  dataIndex: 'duration',
                  width: 100,
                  render: (duration: number) => `${duration?.toFixed(2) || 0}s`,
                },
                {
                  title: '实际结果',
                  dataIndex: 'actual_result',
                  width: 200,
                  ellipsis: {
                    showTitle: false,
                  },
                  render: (text: string) => {
                    if (!text) return <span style={{ color: '#999' }}>-</span>;
                    return (
                      <Tooltip placement="topLeft" title={text}>
                        <span>{text.length > 50 ? text.substring(0, 50) + '...' : text}</span>
                      </Tooltip>
                    );
                  },
                },
                {
                  title: '验证信息',
                  width: 220,
                  render: (_: any, record: any) => {
                    if (record.manually_verified) {
                      return (
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <div>
                            <Tag color="blue" style={{ fontSize: '11px', marginRight: '4px' }}>已手动验证</Tag>
                            <span style={{ fontSize: '12px' }}>{record.verified_by || '-'}</span>
                          </div>
                          <div style={{ fontSize: '12px', color: '#999' }}>
                            {record.verified_at ? new Date(record.verified_at).toLocaleString('zh-CN') : '-'}
                          </div>
                          {record.verification_notes && (
                            <Tooltip title={record.verification_notes}>
                              <div style={{ fontSize: '12px', color: '#666', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                备注: {record.verification_notes}
                              </div>
                            </Tooltip>
                          )}
                        </Space>
                      );
                    }
                    return <span style={{ color: '#999' }}>-</span>;
                  },
                },
                {
                  title: '错误信息',
                  dataIndex: 'error_message',
                  ellipsis: true,
                  render: (text: string, record: any) => {
                    if (record.failure_reason) {
                      return (
                        <Tooltip title={record.failure_reason}>
                          <span>{record.failure_reason}</span>
                        </Tooltip>
                      );
                    }
                    return text || '-';
                  },
                },
                {
                  title: '操作',
                  width: 120,
                  fixed: 'right',
                  render: (_: any, record: any) => {
                    // 如果状态是running，不显示按钮
                    if (record.status === 'running') {
                      return null;
                    }
                    
                    // 如果已手动验证，显示"修改"按钮；否则显示"手动验证"按钮
                    const buttonText = record.manually_verified ? '修改' : '手动验证';
                    
                    return (
                      <Space>
                        <Button
                          size="small"
                          type={record.manually_verified ? 'default' : 'primary'}
                          onClick={() => openVerificationModal(record)}
                        >
                          {buttonText}
                        </Button>
                      </Space>
                    );
                  },
                },
              ]}
            />
          </div>
        )}
      </Drawer>

      {/* 手动验证Modal */}
      <Modal
        title={verifyingTestCase?.manually_verified ? "修改验证结果" : "手动验证测试结果"}
        open={verificationModalOpen}
        onOk={handleVerificationSubmit}
        onCancel={() => {
          setVerificationModalOpen(false);
          setVerifyingTestCase(null);
          verificationForm.resetFields();
        }}
        okText={verifyingTestCase?.manually_verified ? "更新验证结果" : "保存验证结果"}
        width={700}
      >
        {verifyingTestCase && (
          <Form layout="vertical" form={verificationForm}>
            <Form.Item label="测试用例">
              <Input value={verifyingTestCase.test_case_title} disabled />
            </Form.Item>
            <Form.Item
              label="验证状态"
              name="status"
              rules={[{ required: true, message: '请选择验证状态' }]}
            >
              <Select
                options={[
                  { label: '通过', value: 'passed' },
                  { label: '失败', value: 'failed' },
                  { label: '阻塞', value: 'blocked' },
                  { label: '跳过', value: 'skipped' },
                ]}
              />
            </Form.Item>
            <Form.Item
              label="实际结果"
              name="actual_result"
              tooltip="填写实际测试结果，用于与预期结果对比"
            >
              <TextArea rows={3} placeholder="例如：功能正常，用户成功登录并跳转到首页" />
            </Form.Item>
            <Form.Item
              label="验证备注"
              name="verification_notes"
              tooltip="填写验证过程中的备注信息"
            >
              <TextArea rows={3} placeholder="例如：在Chrome浏览器中测试通过，Firefox中未测试" />
            </Form.Item>
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.status !== currentValues.status}
            >
              {({ getFieldValue }) => {
                const status = getFieldValue('status');
                if (status === 'failed') {
                  return (
                    <>
                      <Form.Item
                        label="失败原因"
                        name="failure_reason"
                        rules={[{ required: true, message: '请填写失败原因' }]}
                      >
                        <TextArea rows={2} placeholder="例如：登录按钮点击无响应，页面未跳转" />
                      </Form.Item>
                      <Form.Item
                        label="关联缺陷ID"
                        name="bug_id"
                        tooltip="如有缺陷单，请填写缺陷ID"
                      >
                        <Input placeholder="例如：BUG-12345" />
                      </Form.Item>
                    </>
                  );
                }
                return null;
              }}
            </Form.Item>
            <Form.Item
              label="验证人"
              name="verified_by"
            >
              <Input placeholder="验证人姓名" />
            </Form.Item>
          </Form>
        )}
      </Modal>

      {/* 定时执行设置Modal */}
      <Modal
        title="设置定时执行"
        open={scheduleModalOpen}
        onOk={handleScheduleSubmit}
        onCancel={() => {
          setScheduleModalOpen(false);
          setSchedulingTestRun(null);
          scheduleForm.resetFields();
        }}
        okText="保存"
        width={600}
      >
        <Form layout="vertical" form={scheduleForm}>
          <Form.Item
            label="调度类型"
            name="type"
            rules={[{ required: true, message: '请选择调度类型' }]}
          >
            <Select
              options={[
                { label: '间隔执行（每隔一段时间执行）', value: 'interval' },
                { label: 'Cron表达式（定时执行）', value: 'cron' },
                { label: '一次性执行（指定时间执行一次）', value: 'once' },
              ]}
            />
          </Form.Item>
          
          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.type !== currentValues.type}>
            {({ getFieldValue }) => {
              const scheduleType = getFieldValue('type');
              
              if (scheduleType === 'interval') {
                return (
                  <>
                    <Form.Item label="间隔时间">
                      <Space>
                        <Form.Item name={['interval', 'days']} noStyle>
                          <InputNumber min={0} placeholder="天" addonAfter="天" />
                        </Form.Item>
                        <Form.Item name={['interval', 'hours']} noStyle>
                          <InputNumber min={0} max={23} placeholder="小时" addonAfter="小时" />
                        </Form.Item>
                        <Form.Item name={['interval', 'minutes']} noStyle>
                          <InputNumber min={0} max={59} placeholder="分钟" addonAfter="分钟" />
                        </Form.Item>
                        <Form.Item name={['interval', 'seconds']} noStyle>
                          <InputNumber min={0} max={59} placeholder="秒" addonAfter="秒" />
                        </Form.Item>
                      </Space>
                    </Form.Item>
                    <div style={{ fontSize: '12px', color: '#999', marginTop: '-16px', marginBottom: '16px' }}>
                      例如：每天执行可设置为 1 天，每小时执行可设置为 1 小时
                    </div>
                  </>
                );
              }
              
              if (scheduleType === 'cron') {
                return (
                  <>
                    <Form.Item
                      label="Cron表达式"
                      name="cron_expression"
                      rules={[{ required: true, message: '请输入Cron表达式' }]}
                      tooltip="标准Cron表达式，例如：0 0 * * * 表示每天0点执行"
                    >
                      <Input placeholder="例如: 0 0 * * * (每天0点执行)" />
                    </Form.Item>
                    <div style={{ fontSize: '12px', color: '#999', marginTop: '-16px', marginBottom: '16px' }}>
                      格式：秒 分 时 日 月 周，例如：0 0 9 * * 1-5 表示工作日上午9点执行
                    </div>
                  </>
                );
              }
              
              if (scheduleType === 'once') {
                return (
                  <Form.Item
                    label="执行时间"
                    name="run_time"
                    rules={[{ required: true, message: '请选择执行时间' }]}
                  >
                    <DatePicker
                      showTime
                      format="YYYY-MM-DD HH:mm:ss"
                      style={{ width: '100%' }}
                      placeholder="选择执行时间"
                    />
                  </Form.Item>
                );
              }
              
              return null;
            }}
          </Form.Item>
        </Form>
      </Modal>

      {/* 报告预览Modal */}
      <Modal
        title="测试报告预览"
        open={reportPreviewOpen}
        onCancel={() => {
          setReportPreviewOpen(false);
          setReportPreviewUrl(null);
          setReportPreviewLoading(false);
          setReportPreviewError(null);
          if (reportTimeoutRef.current) {
            clearTimeout(reportTimeoutRef.current);
            reportTimeoutRef.current = null;
          }
        }}
        footer={[
          <Button key="open-new" onClick={() => {
            if (reportPreviewUrl) {
              window.open(reportPreviewUrl, '_blank');
            }
          }}>
            在新窗口打开
          </Button>,
          <Button key="download-csv" onClick={() => {
            if (selectedTestRun) {
              handleDownloadReport(selectedTestRun.id, 'csv');
            }
          }}>
            下载CSV
          </Button>,
          <Button key="download-json" onClick={() => {
            if (selectedTestRun) {
              handleDownloadReport(selectedTestRun.id, 'json');
            }
          }}>
            下载JSON
          </Button>,
          <Button key="close" onClick={() => {
            setReportPreviewOpen(false);
            setReportPreviewUrl(null);
            setReportPreviewLoading(false);
            setReportPreviewError(null);
            if (reportTimeoutRef.current) {
              clearTimeout(reportTimeoutRef.current);
              reportTimeoutRef.current = null;
            }
          }}>
            关闭
          </Button>,
        ]}
        width="95%"
        style={{ top: 20 }}
        styles={{ body: { height: 'calc(100vh - 120px)', padding: 0 } }}
      >
        {reportPreviewLoading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>加载报告中...</div>
          </div>
        ) : reportPreviewError ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <div style={{ color: '#ff4d4f', marginBottom: 16 }}>加载失败: {reportPreviewError}</div>
            <Button onClick={() => {
              if (selectedTestRun) {
                handleViewReport(selectedTestRun.id);
              }
            }}>
              重试
            </Button>
          </div>
        ) : reportPreviewUrl ? (
          <iframe
            ref={iframeRef}
            key={reportPreviewUrl}
            src={reportPreviewUrl}
            style={{
              width: '100%',
              height: 'calc(100vh - 120px)',
              border: 'none',
              display: 'block',
              minHeight: '600px',
            }}
            title="测试报告预览"
            onLoad={(e) => {
              console.log('Report iframe onLoad event fired');
              // 立即隐藏加载状态，onLoad事件已经说明内容加载完成
              setReportPreviewLoading(false);
              setReportPreviewError(null);
              if (reportTimeoutRef.current) {
                clearTimeout(reportTimeoutRef.current);
                reportTimeoutRef.current = null;
              }
            }}
            onError={(e) => {
              console.error('Report iframe load error:', e);
              setReportPreviewLoading(false);
              setReportPreviewError('无法加载报告内容，请检查网络连接');
              if (reportTimeoutRef.current) {
                clearTimeout(reportTimeoutRef.current);
                reportTimeoutRef.current = null;
              }
            }}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <div>无法加载报告</div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TestRuns;
