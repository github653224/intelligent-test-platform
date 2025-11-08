import React, { useEffect, useLayoutEffect, useState, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography,
  App, Popconfirm, Descriptions, Drawer, Statistic, Row, Col,
  Spin, Tabs, Divider, Alert, Switch
} from 'antd';
import dayjs from 'dayjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import html2canvas from 'html2canvas';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined,
  PlayCircleOutlined, EyeOutlined,
  BarChartOutlined, ThunderboltOutlined, DownloadOutlined,
  CopyOutlined, EditOutlined, SaveOutlined, CloseOutlined
} from '@ant-design/icons';
import {
  listPerformanceTests, createPerformanceTest, deletePerformanceTest,
  executePerformanceTest, analyzePerformanceTest, getPerformanceTest,
  listProjects, generateK6Script, PerformanceTest, updatePerformanceTest
} from '../services/aiService';

const { Title } = Typography;
const { TextArea } = Input;

interface Project {
  id: number;
  name: string;
}

const PerformanceTests: React.FC = () => {
  const { message } = App.useApp();
  const location = useLocation(); // 获取当前路由
  const [items, setItems] = useState<PerformanceTest[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const isMountedRef = useRef(true);
  const isCurrentRouteRef = useRef(false); // 跟踪是否是当前路由
  const [modalOpen, setModalOpen] = useState(false);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedTest, setSelectedTest] = useState<PerformanceTest | null>(null);
  const [testDetail, setTestDetail] = useState<PerformanceTest | null>(null);
  const [form] = Form.useForm();
  const [selectedProjectId, setSelectedProjectId] = useState<number | undefined>(undefined);
  const [generatingScript, setGeneratingScript] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const reportContentRef = useRef<HTMLDivElement>(null);
  const [isEditingScript, setIsEditingScript] = useState(false);
  const [editedScript, setEditedScript] = useState<string>('');
  const [savingScript, setSavingScript] = useState(false);
  const [autoExecute, setAutoExecute] = useState(false); // 是否创建后自动执行
  const fetchingRef = useRef(false); // 防止重复调用
  // 轻量级轮询：只轮询运行中的测试状态
  const pollingIntervalsRef = useRef<Map<number, NodeJS.Timeout>>(new Map()); // 每个测试ID对应一个轮询定时器
  const abortControllerRef = useRef<AbortController | null>(null); // 用于取消正在进行的请求
  const startAnalysisPollingRef = useRef<((testId: number) => void) | null>(null); // 存储分析轮询函数引用

  const fetchProjects = useCallback(async () => {
    try {
      const data = await listProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (e: any) {
      console.error('加载项目列表失败', e);
      setProjects([]);
    }
  }, []);

  // 启动单个测试的状态轮询
  const startPolling = useCallback((testId: number) => {
    // 如果组件已卸载或不是当前路由，不启动轮询
    if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
      console.warn(`[PerformanceTests] 不在性能测试页面或组件已卸载，不启动测试 ${testId} 的轮询`, {
        pathname: location.pathname,
        isMounted: isMountedRef.current,
        isCurrentRoute: isCurrentRouteRef.current
      });
      return;
    }

    // 如果已经有轮询，先清除
    if (pollingIntervalsRef.current.has(testId)) {
      clearInterval(pollingIntervalsRef.current.get(testId)!);
      pollingIntervalsRef.current.delete(testId);
    }

    const interval = setInterval(async () => {
      // 每次轮询前都检查路由是否仍然是性能测试页面
      if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
        console.log(`[PerformanceTests] 离开性能测试页面或组件已卸载，停止测试 ${testId} 的轮询`, {
          pathname: location.pathname,
          isMounted: isMountedRef.current,
          isCurrentRoute: isCurrentRouteRef.current
        });
        clearInterval(interval);
        pollingIntervalsRef.current.delete(testId);
        return;
      }

      try {
        // 添加超时处理，避免轮询被阻塞
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('轮询超时')), 6000); // 6秒超时
        });
        
        const detail = await Promise.race([
          getPerformanceTest(testId),
          timeoutPromise
        ]) as any;
        
        // 再次检查路由和组件状态（异步操作后）
        if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
          console.log(`[PerformanceTests] 离开性能测试页面或组件已卸载，不更新测试 ${testId} 的状态`);
          clearInterval(interval);
          pollingIntervalsRef.current.delete(testId);
          return;
        }
        
        // 只在当前页面是性能测试页面时才更新状态
        setItems(prev => {
          // 双重检查：在函数内部再次检查路由和挂载状态
          if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
            return prev; // 如果不在当前路由，不更新状态
          }
          return prev.map(item => {
            if (item.id === testId) {
              return { ...item, ...detail };
            }
            return item;
          });
        });

        // 如果测试已完成，清除轮询
        if (detail.status !== 'running' && detail.status !== 'pending') {
          clearInterval(interval);
          pollingIntervalsRef.current.delete(testId);
          console.log(`[PerformanceTests] 测试 ${testId} 执行完成，停止轮询`, { status: detail.status });
          
          // 如果测试成功完成，检查是否需要启动分析轮询
          if (detail.status === 'completed' && detail.results) {
            // 检查是否已有分析结果
            if (!detail.analysis || !detail.analysis.markdown) {
              // 如果还没有分析结果，启动分析轮询（后端可能正在自动分析）
              console.log(`[PerformanceTests] 测试 ${testId} 执行完成，启动分析轮询`);
              // 延迟一点启动，给后端一些时间生成分析
              setTimeout(() => {
                if (isMountedRef.current && isCurrentRouteRef.current && location.pathname === '/performance-tests') {
                  // 使用 ref 来调用，避免循环依赖
                  if (startAnalysisPollingRef.current) {
                    startAnalysisPollingRef.current(testId);
                  }
                }
              }, 2000); // 延迟2秒，给后端时间生成分析
            } else {
              console.log(`[PerformanceTests] 测试 ${testId} 已有分析结果，无需启动分析轮询`);
            }
          }
        }
      } catch (e: any) {
        // 如果是超时或取消错误，不显示错误信息
        if (e.name === 'AbortError' || e.name === 'CanceledError' || e.message === '轮询超时') {
          console.log(`[PerformanceTests] 轮询测试 ${testId} 超时或被取消`);
        } else {
          console.error(`[PerformanceTests] 轮询测试 ${testId} 状态失败:`, e);
        }
        // 出错时不立即清除轮询，继续尝试（可能是临时网络问题）
        // 但如果连续失败多次，可以考虑清除
      }
    }, 2000); // 每2秒轮询一次

    pollingIntervalsRef.current.set(testId, interval);
    console.log(`[PerformanceTests] 启动测试 ${testId} 的轮询`);
  }, [location.pathname]);

  // 停止单个测试的状态轮询
  const stopPolling = useCallback((testId: number) => {
    const interval = pollingIntervalsRef.current.get(testId);
    if (interval) {
      clearInterval(interval);
      pollingIntervalsRef.current.delete(testId);
    }
  }, []);

  // 启动所有运行中测试的状态轮询
  const startPollingForRunningTests = useCallback((itemsList: PerformanceTest[]) => {
    itemsList.forEach(item => {
      if (item.status === 'running' || item.status === 'pending') {
        if (!pollingIntervalsRef.current.has(item.id)) {
          startPolling(item.id);
        }
      } else {
        // 如果状态不是 running 或 pending，确保停止轮询
        stopPolling(item.id);
      }
    });
  }, [startPolling, stopPolling]);

  const fetchItems = useCallback(async (showLoading: boolean = true) => {
    // 首先检查路由，必须在最前面检查
    if (location.pathname !== '/performance-tests') {
      console.log('[PerformanceTests][fetchItems] 不是性能测试页面，取消加载', { pathname: location.pathname });
      if (showLoading) {
        setLoading(false);
      }
      return;
    }
    
    console.log('[PerformanceTests][fetchItems] 开始加载数据', { showLoading, isMounted: isMountedRef.current, isCurrentRoute: isCurrentRouteRef.current, selectedProjectId, isFetching: fetchingRef.current, pathname: location.pathname });

    // 如果正在加载，防止重复调用
    if (fetchingRef.current) {
      console.warn('[PerformanceTests][fetchItems] 正在加载中，跳过重复调用');
      if (showLoading) {
        setLoading(false);
      }
      return;
    }

    // 设置加载标志
    fetchingRef.current = true;

    // 只在当前路由时设置 loading
    if (showLoading) {
      setLoading(true);
    }
    
    try {
      const params = selectedProjectId ? { project_id: selectedProjectId } : undefined;
      console.log('[PerformanceTests][fetchItems] 调用 API', { params });
      
      // 添加超时处理
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('请求超时')), 8000); // 8秒超时
      });
      
      const data = await Promise.race([
        listPerformanceTests(params),
        timeoutPromise
      ]) as any;
      
      console.log('[PerformanceTests][fetchItems] 数据加载成功', { dataLength: Array.isArray(data) ? data.length : 0, isMounted: isMountedRef.current });
      
      // 检查路由（异步操作后）
      if (location.pathname !== '/performance-tests') {
        console.warn('[fetchItems] 不在性能测试页面，不更新状态', {
          pathname: location.pathname
        });
        if (showLoading) {
          setLoading(false);
        }
        fetchingRef.current = false;
        return;
      }
      
      // 智能合并：如果新数据中某个字段为空，但旧数据中有值，保留旧数据
      setItems(prev => {
        // 检查路由
        if (location.pathname !== '/performance-tests') {
          console.warn('[PerformanceTests][fetchItems] 不在性能测试页面，跳过数据更新', {
            pathname: location.pathname
          });
          return prev; // 如果不在当前路由，不更新状态
        }
        
        const newItems = Array.isArray(data) ? data : [];
        console.log('[PerformanceTests][fetchItems] 更新数据', { prevLength: prev.length, newItemsLength: newItems.length });
        
        // 如果新数据为空，保留旧数据（防止数据丢失）
        if (newItems.length === 0 && prev.length > 0) {
          console.warn('[数据加载] 后端返回空数组，保留现有数据');
          return prev;
        }
        // 如果之前没有数据，使用新数据（即使是空数组也要更新，因为可能是真的没有数据）
        if (prev.length === 0) {
          console.log('[PerformanceTests][fetchItems] 首次加载，使用新数据', { newItemsLength: newItems.length });
          return newItems;
        }
        // 否则，合并更新：对于每个新项，如果旧数据中有对应的项，且新项的某些字段为空，保留旧数据
        const mergedItems = newItems.map(newItem => {
          const oldItem = prev.find(item => item.id === newItem.id);
          if (oldItem) {
            // 合并：先保留旧数据的所有字段，然后用新数据覆盖
            const merged = {
              ...oldItem,
              ...newItem,
              // 如果新项的某些字段为空，保留旧项的值
              results: newItem.results || oldItem.results,
              analysis: newItem.analysis || oldItem.analysis,
              analysis_generated_at: newItem.analysis_generated_at || oldItem.analysis_generated_at,
            };
            return merged;
          }
          return newItem;
        });
        
        // 如果合并后的数据为空，但之前有数据，保留旧数据（防止数据丢失）
        if (mergedItems.length === 0 && prev.length > 0) {
          console.warn('[数据合并] 合并后数据为空，保留现有数据');
          return prev;
        }
        
        console.log('[PerformanceTests][fetchItems] 合并完成', { mergedItemsLength: mergedItems.length });
        return mergedItems;
      });
      
      // 启动所有运行中测试的状态轮询（延迟启动，确保数据已更新）
      const newItems = Array.isArray(data) ? data : [];
      // 使用 setTimeout 确保在下一个事件循环中执行，此时数据已经更新
      setTimeout(() => {
        // 再次检查组件是否仍然挂载
        if (isMountedRef.current) {
          startPollingForRunningTests(newItems);
        }
      }, 500);
      
    } catch (e: any) {
      console.error('[fetchItems] 加载失败', e);
      
      // 检查路由
      if (location.pathname !== '/performance-tests') {
        console.log('[fetchItems] 不在性能测试页面，忽略错误');
        if (showLoading) {
          setLoading(false);
        }
        fetchingRef.current = false;
        return;
      }
      
      // 如果是AbortError或超时，说明请求被取消，不显示错误
      if (e.name !== 'AbortError' && e.name !== 'CanceledError' && e.message !== '请求超时') {
        if (isMountedRef.current && isCurrentRouteRef.current) {
          message.error('加载性能测试列表失败: ' + (e.response?.data?.detail || e.message || '未知错误'));
        }
      }
      
      // 保留现有数据，不清空
      setItems(prev => {
        if (prev.length > 0) {
          console.warn('[fetchItems] 加载失败，保留现有数据', { prevLength: prev.length });
          return prev;
        }
        // 如果没有现有数据，保持空数组
        return prev;
      });
      
      // 无论什么情况，都要清除loading（不依赖路由检查）
      if (showLoading) {
        console.log('[PerformanceTests][fetchItems] catch块中清除loading');
        setLoading(false);
      }
    } finally {
      fetchingRef.current = false;
      console.log('[PerformanceTests][fetchItems] 完成', { showLoading, pathname: location.pathname, isMounted: isMountedRef.current, isCurrentRoute: isCurrentRouteRef.current });
      // 确保loading被清除（双重保险）
      if (showLoading && location.pathname === '/performance-tests') {
        // 延迟清除，确保状态更新完成
        setTimeout(() => {
          if (location.pathname === '/performance-tests') {
            setLoading(false);
          }
        }, 100);
      }
    }
  }, [selectedProjectId, location.pathname, startPollingForRunningTests]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // 监听路由变化 - 使用 useLayoutEffect 确保在渲染前执行
  useLayoutEffect(() => {
    const isPerformanceTestsRoute = location.pathname === '/performance-tests';
    const wasCurrentRoute = isCurrentRouteRef.current;
    isCurrentRouteRef.current = isPerformanceTestsRoute;
    console.log('[PerformanceTests][useLayoutEffect] 路由变化', { pathname: location.pathname, isCurrentRoute: isPerformanceTestsRoute, wasCurrentRoute });
    
    // 如果不是当前路由，立即停止所有操作（必须在渲染前清除）
    if (!isPerformanceTestsRoute) {
      if (wasCurrentRoute) {
        console.log('[PerformanceTests] 离开当前路由，立即清除所有状态和轮询');
        isMountedRef.current = false;
        fetchingRef.current = false;
        
        // 清除所有轮询定时器（立即清除，防止继续执行）
        pollingIntervalsRef.current.forEach((interval, testId) => {
          console.log(`[PerformanceTests] 清除测试 ${testId} 的轮询`);
          clearInterval(interval);
        });
        pollingIntervalsRef.current.clear();
        
        // 取消所有正在进行的请求
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
        
        // 清除 loading（必须在渲染前清除）
        setLoading(false);
      }
      return;
    }
    
    // 是当前路由，确保标记已设置
    isMountedRef.current = true;
    
    // 参考 AI 引擎页面：不在路由变化时自动加载数据，只在用户点击刷新时加载
    // 这样可以避免性能测试执行时阻塞其他页面
  }, [location.pathname]);

  // 组件挂载和卸载时管理状态
  useEffect(() => {
    // 检查是否是当前路由
    if (location.pathname !== '/performance-tests') {
      console.log('[PerformanceTests] 不是当前路由，不初始化');
      // 确保离开路由时清除loading和重置状态
      setLoading(false);
      fetchingRef.current = false;
      isMountedRef.current = false;
      isCurrentRouteRef.current = false;
      return;
    }
    
    // 组件挂载时立即设置为 true（必须在设置loading之前）
    isMountedRef.current = true;
    isCurrentRouteRef.current = true;
    fetchingRef.current = false; // 重置加载标志
    console.log('[PerformanceTests][useEffect] 组件挂载', { isMounted: isMountedRef.current, pathname: location.pathname });
    
    // 首次进入页面时加载数据（只在没有数据时）
    if (items.length === 0 && !fetchingRef.current) {
      console.log('[PerformanceTests] 首次进入页面且没有数据，加载数据');
      fetchItems(true);
    }
    
    return () => {
      console.log('[PerformanceTests][useEffect] 组件卸载，开始清理', { 
        pollingCount: pollingIntervalsRef.current.size,
        isMounted: isMountedRef.current,
        pathname: location.pathname
      });
      
      // 首先标记组件已卸载（立即标记，防止新的异步操作）
      isMountedRef.current = false;
      isCurrentRouteRef.current = false;
      fetchingRef.current = false;
      
      // 取消所有正在进行的请求
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      
      // 清除所有轮询定时器
      pollingIntervalsRef.current.forEach((interval, testId) => {
        console.log(`[PerformanceTests] 清除测试 ${testId} 的轮询`);
        clearInterval(interval);
      });
      pollingIntervalsRef.current.clear();
      
      // 最后清除 loading（确保在所有异步操作之后）
      console.log('[PerformanceTests][useEffect] 组件卸载时强制清除全局 loading');
      setLoading(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  // 项目切换时重新加载数据
  useEffect(() => {
    // 如果组件未挂载，直接返回
    if (!isMountedRef.current) {
      console.warn('[PerformanceTests][useEffect] 组件未挂载，不处理项目切换');
      return;
    }
    
    console.log('[PerformanceTests][useEffect] 项目切换', { selectedProjectId, isMounted: isMountedRef.current, isFetching: fetchingRef.current });
    // 只在组件挂载且不在加载中时加载数据（首次加载已在挂载时处理）
    if (!fetchingRef.current) {
      fetchItems(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      
      // 生成 k6 脚本
      setGeneratingScript(true);
      message.loading({ content: 'AI 正在生成 k6 脚本...', key: 'generating' });
      
      const scriptResult = await generateK6Script({
        test_description: values.test_description,
        target_url: values.target_url,
        load_config: values.load_config ? {
          vus: values.load_config.vus || 10,
          duration: values.load_config.duration || '30s',
          stages: values.load_config.stages
        } : undefined
      });

      if (scriptResult.status !== 'success') {
        message.error({ content: `生成脚本失败: ${scriptResult.error}`, key: 'generating' });
        setGeneratingScript(false);
        return;
      }

      message.success({ content: '脚本生成成功，正在创建测试...', key: 'generating' });

      // 创建性能测试
      const newTest = await createPerformanceTest({
        project_id: values.project_id,
        name: values.name,
        description: values.description,
        test_description: values.test_description,
        target_url: values.target_url,
        load_config: values.load_config
      });

      message.success({ content: '性能测试创建成功', key: 'generating' });
      setModalOpen(false);
      form.resetFields();
      
      // 如果选择了自动执行，创建后立即执行
      if (autoExecute) {
        message.info({ content: '正在启动执行...', key: 'executing', duration: 2 });
        try {
          // 延迟一点执行，确保数据已刷新
          setTimeout(async () => {
            try {
              await executePerformanceTest(newTest.id);
              message.success({ content: '测试执行已启动', key: 'executing', duration: 3 });
              // 启动轮询
              if (isMountedRef.current && isCurrentRouteRef.current) {
                startPolling(newTest.id);
              }
            } catch (e: any) {
              message.error({ content: '启动执行失败: ' + (e.response?.data?.detail || e.message), key: 'executing' });
            }
          }, 500);
        } catch (e: any) {
          console.error('执行失败:', e);
        }
      }
      
      fetchItems(false); // 创建后刷新，不显示全局loading
    } catch (e: any) {
      message.error('创建失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setGeneratingScript(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deletePerformanceTest(id);
      message.success('删除成功');
      fetchItems(false); // 删除后刷新，不显示全局loading
    } catch (e: any) {
      message.error('删除失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const handleExecute = async (id: number) => {
    // 检查当前状态，防止重复点击（只检查 running 状态）
    const currentTest = items.find(item => item.id === id);
    if (currentTest && currentTest.status === 'running') {
      message.warning('测试正在执行中，请稍候...');
      return;
    }
    
    // 检查是否在当前路由
    if (location.pathname !== '/performance-tests') {
      console.warn('[PerformanceTests] 不在性能测试页面，不执行操作');
      return;
    }
    
    try {
      // 立即乐观更新状态为 running，使按钮立即置灰
      setItems(prev => {
        if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
          return prev;
        }
        return prev.map(item => {
          if (item.id === id) {
            return { ...item, status: 'running' };
          }
          return item;
        });
      });
      
      // 显示提示消息
      message.info({ content: '测试执行已启动，正在后台运行...', key: `executing-${id}`, duration: 3 });
      
      // 调用后端接口，后端会立即返回更新后的性能测试对象（状态已更新为 running）
      const updatedTest = await executePerformanceTest(id);
      
      // 再次检查路由（异步操作后）
      if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
        console.warn('[PerformanceTests] 执行完成后不在性能测试页面，不更新状态');
        return;
      }
      
      // 更新完整的状态（包括后端返回的其他字段）
      setItems(prev => {
        // 双重检查路由
        if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
          return prev;
        }
        return prev.map(item => {
          if (item.id === id) {
            return { ...item, ...updatedTest };
          }
          return item;
        });
      });
      
      // 启动轮询（只在当前路由时）
      if (updatedTest.status === 'running' || updatedTest.status === 'pending') {
        startPolling(id);
      }
      
    } catch (e: any) {
      // 如果执行失败，恢复状态
      setItems(prev => {
        if (location.pathname !== '/performance-tests' || !isMountedRef.current || !isCurrentRouteRef.current) {
          return prev;
        }
        return prev.map(item => {
          if (item.id === id) {
            // 恢复为之前的状态，或者设为 failed
            return { ...item, status: currentTest?.status || 'failed' };
          }
          return item;
        });
      });
      message.error({ content: '启动执行失败: ' + (e.response?.data?.detail || e.message), key: `executing-${id}` });
    }
  };

  // 检查分析是否正在进行中
  const isAnalyzing = useCallback((test: PerformanceTest): boolean => {
    if (test.analysis && !test.analysis.markdown && test.analysis_generated_at) {
      const generatedAt = new Date(test.analysis_generated_at).getTime();
      const now = Date.now();
      const fiveMinutesAgo = now - 5 * 60 * 1000;
      return generatedAt > fiveMinutesAgo;
    }
    return false;
  }, []);

  // 启动分析状态轮询
  const startAnalysisPolling = useCallback((testId: number) => {
    // 如果组件已卸载或不是当前路由，不启动轮询
    if (!isMountedRef.current || !isCurrentRouteRef.current) {
      console.warn(`[PerformanceTests] 组件已卸载或不是当前路由，不启动测试 ${testId} 的分析轮询`, {
        isMounted: isMountedRef.current,
        isCurrentRoute: isCurrentRouteRef.current
      });
      return;
    }

    // 如果已经有轮询，先清除
    if (pollingIntervalsRef.current.has(testId)) {
      clearInterval(pollingIntervalsRef.current.get(testId)!);
      pollingIntervalsRef.current.delete(testId);
    }

    const interval = setInterval(async () => {
      // 每次轮询前都检查组件是否已挂载
      if (!isMountedRef.current) {
        console.log(`[PerformanceTests] 组件已卸载，停止测试 ${testId} 的分析轮询`);
        clearInterval(interval);
        pollingIntervalsRef.current.delete(testId);
        return;
      }

      try {
        const detail = await getPerformanceTest(testId);
        
        // 再次检查组件是否已挂载（异步操作后）
        if (!isMountedRef.current) {
          console.log(`[PerformanceTests] 组件已卸载，不更新测试 ${testId} 的分析状态`);
          clearInterval(interval);
          pollingIntervalsRef.current.delete(testId);
          return;
        }
        
        // 更新列表中的该项（只在组件挂载时更新）
        setItems(prev => {
          if (!isMountedRef.current) {
            return prev; // 如果组件已卸载，不更新状态
          }
          return prev.map(item => {
            if (item.id === testId) {
              return { ...item, ...detail };
            }
            return item;
          });
        });

        // 如果分析已完成（有markdown），停止轮询
        if (detail.analysis && detail.analysis.markdown) {
          clearInterval(interval);
          pollingIntervalsRef.current.delete(testId);
          console.log(`[PerformanceTests] 测试 ${testId} 分析完成，停止轮询`);
          if (isMountedRef.current && isCurrentRouteRef.current) {
            message.success({ content: '分析完成', key: `analyzing-${testId}` });
          }
        } else if (!isAnalyzing(detail)) {
          // 如果分析已超时（超过5分钟），停止轮询
          clearInterval(interval);
          pollingIntervalsRef.current.delete(testId);
          console.log(`[PerformanceTests] 测试 ${testId} 分析超时，停止轮询`);
        }
      } catch (e) {
        console.error(`[PerformanceTests] 轮询测试 ${testId} 分析状态失败:`, e);
        // 如果出错，也检查组件是否已挂载
        if (!isMountedRef.current) {
          clearInterval(interval);
          pollingIntervalsRef.current.delete(testId);
        }
      }
    }, 2000); // 每2秒轮询一次

    pollingIntervalsRef.current.set(testId, interval);
    console.log(`[PerformanceTests] 启动测试 ${testId} 的分析轮询`);
  }, [isAnalyzing]);
  
  // 将 startAnalysisPolling 存储到 ref，供 startPolling 使用
  startAnalysisPollingRef.current = startAnalysisPolling;

  const handleAnalyze = async (id: number) => {
    // 检查当前状态，防止重复点击
    const currentTest = items.find(item => item.id === id);
    if (!currentTest) {
      message.error('测试不存在');
      return;
    }

    // 如果正在分析中，直接返回
    if (isAnalyzing(currentTest)) {
      message.warning('分析正在进行中，请稍候...');
      return;
    }
    
    try {
      // 显示加载消息（持续显示，直到分析完成）
      message.loading({ content: 'AI 正在分析性能测试结果，请稍候...', key: `analyzing-${id}`, duration: 0 });
      
      // 打开详情抽屉并切换到AI分析标签
      setSelectedTest(currentTest);
      setDetailDrawerOpen(true);
      setActiveTab('analysis');
      
      // 如果详情抽屉已经打开且已经有详情数据，不需要再次加载
      if (!testDetail || testDetail.id !== id) {
        try {
          const detail = await getPerformanceTest(id);
          // 检查组件是否仍然挂载
          if (isMountedRef.current) {
            setTestDetail(detail);
          }
        } catch (e) {
          if (isMountedRef.current) {
            console.error('加载详情失败:', e);
          }
        }
      }

      // 调用分析接口（后端会等待分析完成才返回，可能需要较长时间）
      const result = await analyzePerformanceTest(id);
      console.log('[性能测试] 分析接口返回结果:', {
        id: result.id,
        hasAnalysis: !!result.analysis,
        analysisKeys: result.analysis ? Object.keys(result.analysis) : [],
        hasMarkdown: !!(result.analysis && result.analysis.markdown),
        markdownLength: result.analysis?.markdown?.length || 0
      });
      
      // 更新列表和详情（检查组件是否仍然挂载且是当前路由）
      if (isMountedRef.current && isCurrentRouteRef.current) {
        setTestDetail(result);
        setItems(prev => prev.map(item => {
          if (item.id === id) {
            return { ...item, ...result };
          }
          return item;
        }));
        
        // 如果分析已完成（有markdown），显示成功消息
        if (result.analysis && result.analysis.markdown) {
          message.success({ content: '分析完成', key: `analyzing-${id}` });
        } else {
          // 如果还没有markdown，启动轮询
          message.info({ content: '分析已启动，正在后台生成报告...', key: `analyzing-${id}`, duration: 3 });
          startAnalysisPolling(id);
        }
      }
    } catch (e: any) {
      // 关闭加载消息
      message.destroy(`analyzing-${id}`);
      
      // 检查是否是超时错误
      if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
        // 超时错误：分析可能仍在进行，启动轮询等待结果
        message.warning({ 
          content: '分析请求超时，但分析可能仍在后台进行中，正在检查结果...', 
          key: `analyzing-${id}`,
          duration: 5
        });
        // 启动轮询，等待分析完成
        startAnalysisPolling(id);
      } else {
        // 其他错误：显示错误消息
        message.error({ 
          content: '启动分析失败: ' + (e.response?.data?.detail || e.message), 
          key: `analyzing-${id}`,
          duration: 5
        });
      }
    }
  };

  const handleViewDetail = async (test: PerformanceTest) => {
    setSelectedTest(test);
    setDetailDrawerOpen(true);
    setActiveTab('overview'); // 默认显示概览
    setIsEditingScript(false); // 重置编辑状态
    setEditedScript(''); // 清空编辑内容
    try {
      const detail = await getPerformanceTest(test.id);
      setTestDetail(detail);
      
      // 更新列表中的该项（确保数据同步）
      setItems(prev => prev.map(item => {
        if (item.id === test.id) {
          return { ...item, ...detail };
        }
        return item;
      }));
      
      // 如果测试正在执行中或分析中，启动轮询
      if (detail.status === 'running' || detail.status === 'pending') {
        startPolling(test.id);
      } else if (isAnalyzing(detail)) {
        startAnalysisPolling(test.id);
      }
    } catch (e: any) {
      message.error('加载详情失败: ' + (e.response?.data?.detail || e.message));
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
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '测试名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 150,
    },
    {
      title: '测试需求',
      dataIndex: 'ai_prompt',
      key: 'ai_prompt',
      ellipsis: {
        showTitle: true,
      },
      width: 250,
      render: (text: string | undefined) => {
        if (!text) return '-';
        return text.length > 50 ? `${text.substring(0, 50)}...` : text;
      },
    },
    {
      title: '项目',
      dataIndex: 'project_id',
      key: 'project_id',
      width: 120,
      render: (projectId: number) => {
        const project = projects.find(p => p.id === projectId);
        return project ? project.name : projectId;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '执行时长',
      dataIndex: 'duration',
      key: 'duration',
      width: 120,
      render: (duration: number | undefined) => {
        if (!duration) return '-';
        if (duration < 60) return `${duration.toFixed(1)}秒`;
        if (duration < 3600) return `${(duration / 60).toFixed(1)}分钟`;
        return `${(duration / 3600).toFixed(1)}小时`;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 320,
      fixed: 'right' as const,
      render: (_: any, record: PerformanceTest) => (
        <Space size="small" wrap>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {/* 执行按钮：基于 status 字段 */}
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id)}
            >
              执行
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              type="link"
              size="small"
              disabled
              icon={<PlayCircleOutlined />}
              loading={true}
            >
              执行中
            </Button>
          )}
          {record.status === 'failed' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id)}
            >
              重新执行
            </Button>
          )}
          {record.status === 'completed' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleExecute(record.id)}
              >
                重新执行
              </Button>
              <Button
                type="link"
                size="small"
                icon={<BarChartOutlined />}
                onClick={() => handleAnalyze(record.id)}
                disabled={(() => {
                  // 如果正在分析（有analysis但没有markdown，且在最近5分钟内），禁用按钮
                  if (record.analysis && !record.analysis.markdown && record.analysis_generated_at) {
                    const generatedAt = new Date(record.analysis_generated_at).getTime();
                    const now = Date.now();
                    const fiveMinutesAgo = now - 5 * 60 * 1000;
                    if (generatedAt > fiveMinutesAgo) {
                      return true;
                    }
                  }
                  return false;
                })()}
              >
                分析
              </Button>
            </>
          )}
          <Popconfirm
            title="确定删除这个性能测试吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Title level={4} style={{ margin: 0 }}>
            <ThunderboltOutlined /> 性能测试
          </Title>
          <Space>
            <Select
              placeholder="筛选项目"
              allowClear
              style={{ width: 200 }}
              value={selectedProjectId}
              onChange={(value) => setSelectedProjectId(value)}
            >
              {projects.map(project => (
                <Select.Option key={project.id} value={project.id}>
                  {project.name}
                </Select.Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => {
              // 强制清除loading状态，然后刷新
              setLoading(false);
              fetchItems(true);
            }} loading={loading && location.pathname === '/performance-tests'}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
              创建性能测试
            </Button>
          </Space>
        </Space>

        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 创建性能测试模态框 */}
      <Modal
        title="创建性能测试"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
          setAutoExecute(false); // 重置为默认值（关闭）
        }}
        width={800}
        confirmLoading={generatingScript}
        okText="创建"
        cancelText="取消"
        okButtonProps={{ disabled: generatingScript }}
        cancelButtonProps={{ disabled: generatingScript }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label={
              <Space>
                <span>创建后立即执行</span>
                <Switch 
                  checked={autoExecute} 
                  onChange={setAutoExecute}
                  checkedChildren="是"
                  unCheckedChildren="否"
                  disabled={generatingScript}
                />
              </Space>
            }
            extra="开启后，创建测试将自动开始执行"
          >
            {/* 这个表单项仅用于显示开关，不需要实际的值 */}
          </Form.Item>
          <Form.Item
            name="project_id"
            label="项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select placeholder="选择项目" disabled={generatingScript}>
              {projects.map(project => (
                <Select.Option key={project.id} value={project.id}>
                  {project.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="name"
            label="测试名称"
            rules={[{ required: true, message: '请输入测试名称' }]}
          >
            <Input placeholder="例如：API 接口压力测试" disabled={generatingScript} />
          </Form.Item>
          <Form.Item name="description" label="测试描述">
            <TextArea rows={2} placeholder="测试描述（可选）" disabled={generatingScript} />
          </Form.Item>
          <Form.Item
            name="test_description"
            label="测试需求（一句话描述）"
            rules={[{ required: true, message: '请描述性能测试需求' }]}
            extra="例如：对用户登录接口进行100并发用户持续30秒的压力测试"
          >
            <TextArea rows={3} placeholder="一句话描述性能测试需求，AI 将自动生成 k6 脚本" disabled={generatingScript} />
          </Form.Item>
          <Form.Item name="target_url" label="目标 URL（可选）">
            <Input placeholder="例如：https://api.example.com" disabled={generatingScript} />
          </Form.Item>
          <Form.Item label="负载配置（可选）" style={{ marginBottom: 0 }}>
            <Form.Item name={['load_config', 'vus']} style={{ display: 'inline-block', width: 'calc(50% - 8px)', marginRight: 16 }}>
              <InputNumber min={1} max={10000} placeholder="虚拟用户数" style={{ width: '100%' }} disabled={generatingScript} />
            </Form.Item>
            <Form.Item name={['load_config', 'duration']} style={{ display: 'inline-block', width: 'calc(50% - 8px)' }}>
              <Input placeholder="测试时长，如：30s, 5m" disabled={generatingScript} />
            </Form.Item>
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="性能测试详情"
        placement="right"
        width={900}
        open={detailDrawerOpen}
        onClose={() => {
          setDetailDrawerOpen(false);
          setSelectedTest(null);
          setTestDetail(null);
          setActiveTab('overview');
        }}
        closable={true}
      >
        {testDetail ? (
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <Tabs.TabPane tab="概览" key="overview">
              <Descriptions column={2} bordered>
                <Descriptions.Item label="测试名称">{testDetail.name}</Descriptions.Item>
                <Descriptions.Item label="状态">{getStatusTag(testDetail.status)}</Descriptions.Item>
                <Descriptions.Item label="项目ID">{testDetail.project_id}</Descriptions.Item>
                <Descriptions.Item label="执行时长">
                  {testDetail.duration ? `${testDetail.duration.toFixed(1)}秒` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="开始时间" span={2}>
                  {testDetail.start_time ? dayjs(testDetail.start_time).format('YYYY-MM-DD HH:mm:ss') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="结束时间" span={2}>
                  {testDetail.end_time ? dayjs(testDetail.end_time).format('YYYY-MM-DD HH:mm:ss') : '-'}
                </Descriptions.Item>
                {testDetail.description && (
                  <Descriptions.Item label="描述" span={2}>{testDetail.description}</Descriptions.Item>
                )}
              </Descriptions>

              {testDetail.results && testDetail.results.metrics && (
                <>
                  <Divider>性能指标</Divider>
                  <Row gutter={16}>
                    {Object.entries(testDetail.results.metrics)
                      .filter(([key]) => key !== 'root_group') // 排除root_group
                      .slice(0, 8)
                      .map(([key, value]: [string, any]) => {
                        // 调试：打印指标数据
                        if (key === 'http_req_failed' || key === 'vus') {
                          console.log(`[指标调试] ${key}:`, JSON.stringify(value, null, 2));
                        }
                        
                        // 根据指标类型显示不同的值
                        let displayValue: string | number = '-';
                        let suffix = '';
                        
                        if (typeof value === 'object' && value !== null) {
                          // 对于时长类指标（如 http_req_duration），显示平均值
                          // 注意：k6 的 http_req_duration 单位已经是毫秒（ms），不需要再转换
                          if (key.includes('duration') || key.includes('waiting') || key.includes('connecting')) {
                            if (value.avg !== undefined && value.avg !== null) {
                              // k6 的 JSON 输出中，http_req_duration 已经是毫秒，直接使用
                              displayValue = value.avg.toFixed(2);
                              suffix = 'ms';
                            } else if (value.p95 !== undefined && value.p95 !== null) {
                              displayValue = value.p95.toFixed(2);
                              suffix = 'ms (p95)';
                            } else if (value.min !== undefined && value.min !== null) {
                              displayValue = value.min.toFixed(2);
                              suffix = 'ms (min)';
                            } else if (value.max !== undefined && value.max !== null) {
                              displayValue = value.max.toFixed(2);
                              suffix = 'ms (max)';
                            }
                          }
                          // 对于失败率类指标（如 http_req_failed），显示比率
                          else if (key.includes('failed')) {
                            // http_req_failed 的 rate 字段表示失败率（0-1之间的小数）
                            if (value.rate !== undefined && value.rate !== null) {
                              displayValue = (value.rate * 100).toFixed(2);
                              suffix = '%';
                            } else if (value.values && typeof value.values === 'object') {
                              // 尝试从values中获取（values是一个对象，键是时间戳，值是0或1）
                              const valuesArray = Object.values(value.values) as (number | boolean)[];
                              if (valuesArray.length > 0) {
                                // 计算失败率：失败数 / 总数
                                // http_req_failed 的 values 中，1 或 true 表示失败，0 或 false 表示成功
                                const total = valuesArray.length;
                                const failed = valuesArray.filter(v => v === 1 || v === true || (typeof v === 'number' && v > 0)).length;
                                displayValue = ((failed / total) * 100).toFixed(2);
                                suffix = '%';
                              }
                            } else if (value.count !== undefined && value.count !== null) {
                              // 如果有 count 字段，尝试计算失败率
                              // 但需要知道总数，这里暂时显示失败数
                              displayValue = value.count;
                              suffix = '次';
                            }
                          }
                          // 对于计数类指标（如 http_reqs, iterations），显示总数
                          else if (key.includes('reqs') || key.includes('iterations')) {
                            if (value.count !== undefined && value.count !== null) {
                              displayValue = value.count;
                            }
                          }
                          // 对于VU类指标，显示当前值或最大值
                          else if (key.includes('vus')) {
                            if (key.includes('max')) {
                              // vus_max 显示最大值
                              if (value.max !== undefined && value.max !== null) {
                                displayValue = value.max;
                              } else if (value.values && typeof value.values === 'object') {
                                const valuesArray = Object.values(value.values) as number[];
                                if (valuesArray.length > 0) {
                                  displayValue = Math.max(...valuesArray);
                                }
                              }
                            } else {
                              // vus 显示当前值或最大值
                              // 优先使用 max 字段（如果有）
                              if (value.max !== undefined && value.max !== null) {
                                displayValue = value.max;
                              } else if (value.values && typeof value.values === 'object') {
                                const valuesArray = Object.values(value.values) as number[];
                                if (valuesArray.length > 0) {
                                  // 取最后一个值（当前值）或最大值
                                  displayValue = valuesArray[valuesArray.length - 1];
                                  // 如果最后一个值是0，尝试取最大值
                                  if (displayValue === 0) {
                                    displayValue = Math.max(...valuesArray);
                                  }
                                }
                              } else if (value.avg !== undefined && value.avg !== null) {
                                // 如果没有 values，使用平均值（四舍五入）
                                displayValue = Math.round(value.avg);
                              }
                            }
                          }
                          // 对于数据量类指标（如 data_received, data_sent），显示总和或平均值
                          else if (key.includes('data')) {
                            // data_received 和 data_sent 通常使用 count 或 sum 字段（单位：字节）
                            // k6 的 JSON 输出中，data_received 和 data_sent 的 count/sum 单位是字节（B）
                            let totalBytes = 0;
                            if (value.count !== undefined && value.count !== null && value.count > 0) {
                              // count 字段表示总字节数
                              totalBytes = value.count;
                            } else if (value.sum !== undefined && value.sum !== null && value.sum > 0) {
                              // sum 字段也表示总字节数
                              totalBytes = value.sum;
                            } else if (value.avg !== undefined && value.avg !== null && value.avg > 0) {
                              // 如果没有 count 或 sum，使用平均值（但平均值通常不准确，因为需要乘以请求数）
                              // 这里暂时使用平均值，但建议使用 count 或 sum
                              totalBytes = value.avg;
                            }
                            
                            if (totalBytes > 0) {
                              // 根据数据量大小选择合适的单位
                              if (totalBytes >= 1024 * 1024 * 1024) {
                                // >= 1GB，显示为 GB
                                displayValue = (totalBytes / (1024 * 1024 * 1024)).toFixed(2);
                                suffix = 'GB';
                              } else if (totalBytes >= 1024 * 1024) {
                                // >= 1MB，显示为 MB
                                displayValue = (totalBytes / (1024 * 1024)).toFixed(2);
                                suffix = 'MB';
                              } else {
                                // < 1MB，显示为 KB
                                displayValue = (totalBytes / 1024).toFixed(2);
                                suffix = 'KB';
                              }
                            }
                          }
                          // 默认显示平均值或计数
                          else {
                            if (value.avg !== undefined && value.avg !== null) {
                              displayValue = value.avg.toFixed(2);
                            } else if (value.count !== undefined && value.count !== null) {
                              displayValue = value.count;
                            }
                          }
                        } else if (typeof value === 'number') {
                          displayValue = value;
                        }
                        
                        // 格式化标题，添加中文名称
                        const metricNameMap: Record<string, string> = {
                          'http_req_duration': 'HTTP请求时长',
                          'http_req_failed': 'HTTP请求失败率',
                          'http_reqs': 'HTTP请求总数',
                          'iterations': '迭代次数',
                          'vus': '虚拟用户数',
                          'vus_max': '最大虚拟用户数',
                          'data_received': '接收数据量',
                          'data_sent': '发送数据量',
                          'http_req_waiting': 'HTTP请求等待时间',
                          'http_req_connecting': 'HTTP连接时间',
                          'iteration_duration': '迭代时长',
                        };
                        
                        const englishTitle = key
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, (l) => l.toUpperCase());
                        const chineseName = metricNameMap[key] || '';
                        const title = chineseName ? `${englishTitle} (${chineseName})` : englishTitle;
                        
                        return (
                          <Col span={8} key={key} style={{ marginBottom: 16 }}>
                            <Card size="small">
                              <Statistic
                                title={title}
                                value={displayValue}
                                suffix={suffix}
                                valueStyle={{ fontSize: 18 }}
                              />
                            </Card>
                          </Col>
                        );
                      })}
                  </Row>
                </>
              )}
            </Tabs.TabPane>

            <Tabs.TabPane tab="k6 脚本" key="script">
              {testDetail.k6_script ? (
                <div>
                  <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
                    <Title level={5} style={{ margin: 0 }}>K6 测试脚本</Title>
                    <Space>
                      {!isEditingScript ? (
                        <>
                          <Button
                            icon={<CopyOutlined />}
                            size="small"
                            onClick={() => {
                              navigator.clipboard.writeText(testDetail.k6_script || '');
                              message.success('脚本已复制到剪贴板');
                            }}
                          >
                            复制代码
                          </Button>
                          <Button
                            icon={<EditOutlined />}
                            size="small"
                            onClick={() => {
                              setEditedScript(testDetail.k6_script || '');
                              setIsEditingScript(true);
                            }}
                          >
                            编辑
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            icon={<SaveOutlined />}
                            size="small"
                            type="primary"
                            loading={savingScript}
                            onClick={async () => {
                              if (!testDetail.id) {
                                message.error('测试ID不存在');
                                return;
                              }
                              try {
                                setSavingScript(true);
                                await updatePerformanceTest(testDetail.id, {
                                  k6_script: editedScript
                                });
                                // 更新本地状态
                                setTestDetail({ ...testDetail, k6_script: editedScript });
                                setIsEditingScript(false);
                                message.success('脚本保存成功');
                                // 刷新列表
                                fetchItems(false);
                              } catch (e: any) {
                                message.error('保存失败: ' + (e.response?.data?.detail || e.message));
                              } finally {
                                setSavingScript(false);
                              }
                            }}
                          >
                            保存
                          </Button>
                          <Button
                            icon={<CloseOutlined />}
                            size="small"
                            onClick={() => {
                              setIsEditingScript(false);
                              setEditedScript('');
                            }}
                          >
                            取消
                          </Button>
                        </>
                      )}
                    </Space>
                  </Space>
                  {isEditingScript ? (
                    <TextArea
                      value={editedScript}
                      onChange={(e) => setEditedScript(e.target.value)}
                      rows={20}
                      style={{
                        fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                        fontSize: '13px',
                        lineHeight: '1.5'
                      }}
                      placeholder="请输入 K6 脚本内容"
                    />
                  ) : (
                    <div style={{ position: 'relative' }}>
                      <SyntaxHighlighter
                        language="javascript"
                        style={vscDarkPlus}
                        customStyle={{
                          borderRadius: '4px',
                          fontSize: '13px',
                          lineHeight: '1.5',
                          margin: 0
                        }}
                        showLineNumbers
                        wrapLines
                      >
                        {testDetail.k6_script}
                      </SyntaxHighlighter>
                    </div>
                  )}
                </div>
              ) : (
                <Alert message="脚本不存在" type="warning" />
              )}
            </Tabs.TabPane>

            <Tabs.TabPane tab="测试结果" key="results">
              {testDetail.results ? (
                <div>
                  {/* 显示错误信息（如果有） */}
                  {testDetail.results.execution_result?.error && (
                    <Alert
                      message="执行错误"
                      description={testDetail.results.execution_result.error}
                      type="error"
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  {testDetail.results.execution_result?.stderr && (
                    <Alert
                      message="错误输出 (stderr)"
                      description={
                        <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>
                          {testDetail.results.execution_result.stderr}
                        </pre>
                      }
                      type="error"
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  {testDetail.results.execution_result?.exit_code !== 0 && (
                    <Alert
                      message={`执行退出码: ${testDetail.results.execution_result.exit_code}`}
                      description={
                        testDetail.results.execution_result.exit_code === 99
                          ? "阈值检查失败（测试执行成功，但未达到性能阈值）"
                          : testDetail.results.execution_result.exit_code === 1
                          ? "脚本执行错误或测试失败"
                          : "未知错误"
                      }
                      type="warning"
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  {/* 显示标准输出（如果有） */}
                  {testDetail.results.execution_result?.stdout && (
                    <div style={{ marginBottom: 16 }}>
                      <Title level={5}>执行输出 (stdout)</Title>
                      <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto', maxHeight: 300, fontSize: 12 }}>
                        {testDetail.results.execution_result.stdout}
                      </pre>
                    </div>
                  )}
                  {/* 显示完整结果JSON */}
                  <Title level={5}>完整结果数据</Title>
                  <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto', maxHeight: 600 }}>
                    <code>{JSON.stringify(testDetail.results, null, 2)}</code>
                  </pre>
                </div>
              ) : (
                <Alert message="暂无测试结果" type="info" />
              )}
            </Tabs.TabPane>

            <Tabs.TabPane tab="AI 分析" key="analysis">
              {(() => {
                // 调试：打印分析数据结构
                if (testDetail.analysis) {
                  console.log('[性能测试-详情] 分析数据:', {
                    hasAnalysis: !!testDetail.analysis,
                    analysisKeys: Object.keys(testDetail.analysis),
                    hasMarkdown: !!(testDetail.analysis.markdown),
                    markdownType: typeof testDetail.analysis.markdown,
                    markdownLength: testDetail.analysis.markdown?.length || 0,
                    rawAnalysisType: typeof testDetail.analysis.raw_analysis,
                    fullAnalysis: testDetail.analysis
                  });
                }
                return null;
              })()}
              
              {/* 如果正在分析，显示分析中提示 */}
              {testDetail && isAnalyzing(testDetail) && (
                <Alert
                  message="AI 分析中，请稍后..."
                  description="正在生成性能分析报告，完成后将自动显示结果"
                  type="info"
                  icon={<Spin size="small" />}
                  style={{ marginBottom: 16 }}
                  showIcon
                />
              )}
              
              {/* 测试信息部分：展示用户输入和AI理解的测试配置 */}
              <div ref={reportContentRef}>
              <Card 
                title="📋 测试信息" 
                size="small" 
                style={{ marginBottom: 16 }}
                bordered
              >
                <Descriptions column={1} bordered size="small">
                  {/* 用户原始需求 */}
                  <Descriptions.Item label="用户输入的要求">
                    <div style={{ 
                      padding: '8px 12px', 
                      background: '#f5f5f5', 
                      borderRadius: '4px',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}>
                      {testDetail.ai_prompt || testDetail.description || '未提供'}
                    </div>
                  </Descriptions.Item>
                  
                  {/* AI理解的测试配置 */}
                  {(() => {
                    // 从 k6_script 中提取测试地址
                    const extractUrlFromScript = (script: string | null | undefined): string | null => {
                      if (!script) return null;
                      // 匹配 http:// 或 https:// 开头的 URL（更精确的匹配）
                      const urlPatterns = [
                        /https?:\/\/[^\s"'`\)]+/g,  // 标准 URL
                        /url:\s*['"](https?:\/\/[^'"]+)['"]/,  // url: "http://..."
                        /http\.get\(['"](https?:\/\/[^'"]+)['"]/,  // http.get("http://...")
                      ];
                      
                      for (const pattern of urlPatterns) {
                        const match = script.match(pattern);
                        if (match) {
                          // 提取第一个匹配的 URL
                          const url = match[1] || match[0];
                          // 清理可能的引号
                          return url.replace(/['"]/g, '');
                        }
                      }
                      return null;
                    };
                    
                    // 从 k6_script 中提取测试策略（stages、vus、duration等）
                    const extractStrategyFromScript = (script: string | null | undefined): any => {
                      if (!script) return null;
                      const strategy: any = {};
                      
                      // 提取 stages 配置
                      const stagesMatch = script.match(/stages:\s*\[([^\]]+)\]/s);
                      if (stagesMatch) {
                        try {
                          // 尝试解析 stages 数组
                          const stagesStr = stagesMatch[1];
                          const stages: any[] = [];
                          // 匹配每个 stage 对象
                          const stagePattern = /\{([^}]+)\}/g;
                          let stageMatch;
                          while ((stageMatch = stagePattern.exec(stagesStr)) !== null) {
                            const stageContent = stageMatch[1];
                            const durationMatch = stageContent.match(/duration:\s*['"]?([^'",}]+)['"]?/);
                            const targetMatch = stageContent.match(/target:\s*(\d+)/);
                            if (durationMatch || targetMatch) {
                              stages.push({
                                duration: durationMatch ? durationMatch[1].trim() : undefined,
                                target: targetMatch ? parseInt(targetMatch[1]) : undefined
                              });
                            }
                          }
                          if (stages.length > 0) {
                            strategy['阶段配置 (Stages)'] = stages.map((s, idx) => 
                              `阶段${idx + 1}: ${s.target ? `${s.target} VUs` : ''} ${s.duration ? `持续 ${s.duration}` : ''}`.trim()
                            ).join(' → ');
                          }
                        } catch (e) {
                          console.warn('解析 stages 失败:', e);
                        }
                      }
                      
                      // 提取 vus 配置
                      const vusMatch = script.match(/vus:\s*(\d+)/);
                      if (vusMatch) {
                        strategy['虚拟用户数 (VUs)'] = vusMatch[1];
                      }
                      
                      // 提取 duration 配置
                      const durationMatch = script.match(/duration:\s*['"]?([^'",}]+)['"]?/);
                      if (durationMatch && !strategy['阶段配置 (Stages)']) {
                        strategy['持续时间'] = durationMatch[1].trim();
                      }
                      
                      // 提取 iterations 配置
                      const iterationsMatch = script.match(/iterations:\s*(\d+)/);
                      if (iterationsMatch) {
                        strategy['迭代次数'] = iterationsMatch[1];
                      }
                      
                      return Object.keys(strategy).length > 0 ? strategy : null;
                    };
                    
                    // 从 execution_config 中提取测试策略
                    const getTestStrategyFromConfig = (config: any) => {
                      if (!config || typeof config !== 'object') return null;
                      const strategy: any = {};
                      if (config.vus !== undefined) strategy['虚拟用户数 (VUs)'] = config.vus;
                      if (config.duration !== undefined) strategy['持续时间'] = config.duration;
                      if (config.iterations !== undefined) strategy['迭代次数'] = config.iterations;
                      if (config.rampUp !== undefined) strategy['爬坡时间'] = config.rampUp;
                      if (config.rampDown !== undefined) strategy['下降时间'] = config.rampDown;
                      if (config.stages && Array.isArray(config.stages)) {
                        strategy['阶段配置'] = config.stages.map((stage: any, idx: number) => 
                          `阶段${idx + 1}: ${JSON.stringify(stage)}`
                        ).join('\n');
                      }
                      return Object.keys(strategy).length > 0 ? strategy : null;
                    };
                    
                    const testUrl = extractUrlFromScript(testDetail.k6_script);
                    // 优先从脚本中提取策略，如果没有则从 execution_config 中获取
                    const testStrategy = extractStrategyFromScript(testDetail.k6_script) || 
                                        getTestStrategyFromConfig(testDetail.execution_config);
                    
                    return (
                      <>
                        {/* 测试地址 */}
                        <Descriptions.Item label="测试地址">
                          {testUrl ? (
                            <a href={testUrl} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }}>
                              {testUrl}
                            </a>
                          ) : (
                            <span style={{ color: '#999' }}>未指定（从脚本中提取）</span>
                          )}
                        </Descriptions.Item>
                        
                        {/* 测试策略 */}
                        <Descriptions.Item label="测试策略">
                          {testStrategy ? (
                            <div style={{ 
                              padding: '8px 12px', 
                              background: '#e6f7ff', 
                              borderRadius: '4px'
                            }}>
                              {Object.entries(testStrategy).map(([key, value]) => (
                                <div key={key} style={{ marginBottom: '4px' }}>
                                  <strong>{key}:</strong> {String(value)}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span style={{ color: '#999' }}>
                              {testDetail.k6_script 
                                ? '策略信息在 K6 脚本中定义（查看"测试脚本"标签页）'
                                : '未配置'}
                            </span>
                          )}
                        </Descriptions.Item>
                      </>
                    );
                  })()}
                </Descriptions>
              </Card>
              
              {testDetail.analysis && Object.keys(testDetail.analysis).length > 0 ? (
                <div>
                  {/* 显示错误信息（如果有） */}
                  {testDetail.analysis.error && (
                    <Alert
                      message="分析警告"
                      description={testDetail.analysis.error}
                      type="warning"
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  
                  {/* 显示Markdown格式的分析报告 */}
                  {(() => {
                    // 检查是否有markdown，如果没有但有raw_analysis，尝试在前端格式化
                    let markdownContent = testDetail.analysis.markdown;
                    
                    if (!markdownContent && testDetail.analysis.raw_analysis) {
                      // 如果markdown不存在，但raw_analysis存在，尝试解析并格式化
                      console.log('[性能测试] Markdown不存在，尝试从raw_analysis生成');
                      const rawAnalysis = testDetail.analysis.raw_analysis;
                      
                      // 如果raw_analysis是字符串（Python字典格式），尝试解析
                      if (typeof rawAnalysis === 'string' && rawAnalysis.trim().startsWith('{')) {
                        try {
                          // 尝试解析Python字典字符串
                          const parsed = eval(`(${rawAnalysis})`); // 使用eval解析Python字典字符串
                          if (typeof parsed === 'object') {
                            // 这里可以调用一个格式化函数，但为了简单，我们显示提示
                            markdownContent = `## ⚠️ 分析数据格式异常\n\n分析数据已生成，但Markdown格式化失败。原始数据：\n\n\`\`\`json\n${JSON.stringify(parsed, null, 2)}\n\`\`\``;
                          }
                        } catch (e) {
                          console.error('[性能测试] 解析raw_analysis失败:', e);
                        }
                      }
                    }
                    
                    console.log('[性能测试] 渲染Markdown:', {
                      hasMarkdown: !!markdownContent,
                      markdownType: typeof markdownContent,
                      markdownLength: markdownContent?.length || 0,
                      markdownPreview: markdownContent?.substring(0, 200),
                      hasRawAnalysis: !!testDetail.analysis.raw_analysis,
                      rawAnalysisType: typeof testDetail.analysis.raw_analysis
                    });
                    
                    return markdownContent;
                  })() ? (
                    <div>
                      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
                        <Title level={5} style={{ margin: 0 }}>📊 AI 性能分析报告</Title>
                        <Space>
                          <Button
                            icon={<DownloadOutlined />}
                            size="small"
                            onClick={() => {
                              // 生成测试信息的 Markdown
                              const generateTestInfoMarkdown = () => {
                                let testInfoMd = '## 📋 测试信息\n\n';
                                
                                // 用户输入的要求
                                testInfoMd += '### 用户输入的要求\n\n';
                                testInfoMd += `${testDetail.ai_prompt || testDetail.description || '未提供'}\n\n`;
                                
                                // 从 k6_script 中提取测试地址
                                const extractUrlFromScript = (script: string | null | undefined): string | null => {
                                  if (!script) return null;
                                  const urlPatterns = [
                                    /https?:\/\/[^\s"'`\)]+/g,
                                    /url:\s*['"](https?:\/\/[^'"]+)['"]/,
                                    /http\.get\(['"](https?:\/\/[^'"]+)['"]/,
                                  ];
                                  for (const pattern of urlPatterns) {
                                    const match = script.match(pattern);
                                    if (match) {
                                      const url = match[1] || match[0];
                                      return url.replace(/['"]/g, '');
                                    }
                                  }
                                  return null;
                                };
                                
                                // 从 k6_script 中提取测试策略
                                const extractStrategyFromScript = (script: string | null | undefined): any => {
                                  if (!script) return null;
                                  const strategy: any = {};
                                  
                                  const stagesMatch = script.match(/stages:\s*\[([^\]]+)\]/s);
                                  if (stagesMatch) {
                                    try {
                                      const stagesStr = stagesMatch[1];
                                      const stages: any[] = [];
                                      const stagePattern = /\{([^}]+)\}/g;
                                      let stageMatch;
                                      while ((stageMatch = stagePattern.exec(stagesStr)) !== null) {
                                        const stageContent = stageMatch[1];
                                        const durationMatch = stageContent.match(/duration:\s*['"]?([^'",}]+)['"]?/);
                                        const targetMatch = stageContent.match(/target:\s*(\d+)/);
                                        if (durationMatch || targetMatch) {
                                          stages.push({
                                            duration: durationMatch ? durationMatch[1].trim() : undefined,
                                            target: targetMatch ? parseInt(targetMatch[1]) : undefined
                                          });
                                        }
                                      }
                                      if (stages.length > 0) {
                                        strategy['阶段配置 (Stages)'] = stages.map((s, idx) => 
                                          `阶段${idx + 1}: ${s.target ? `${s.target} VUs` : ''} ${s.duration ? `持续 ${s.duration}` : ''}`.trim()
                                        ).join(' → ');
                                      }
                                    } catch (e) {
                                      console.warn('解析 stages 失败:', e);
                                    }
                                  }
                                  
                                  const vusMatch = script.match(/vus:\s*(\d+)/);
                                  if (vusMatch) strategy['虚拟用户数 (VUs)'] = vusMatch[1];
                                  
                                  const durationMatch = script.match(/duration:\s*['"]?([^'",}]+)['"]?/);
                                  if (durationMatch && !strategy['阶段配置 (Stages)']) {
                                    strategy['持续时间'] = durationMatch[1].trim();
                                  }
                                  
                                  const iterationsMatch = script.match(/iterations:\s*(\d+)/);
                                  if (iterationsMatch) strategy['迭代次数'] = iterationsMatch[1];
                                  
                                  return Object.keys(strategy).length > 0 ? strategy : null;
                                };
                                
                                // 从 execution_config 中提取测试策略
                                const getTestStrategyFromConfig = (config: any) => {
                                  if (!config || typeof config !== 'object') return null;
                                  const strategy: any = {};
                                  if (config.vus !== undefined) strategy['虚拟用户数 (VUs)'] = config.vus;
                                  if (config.duration !== undefined) strategy['持续时间'] = config.duration;
                                  if (config.iterations !== undefined) strategy['迭代次数'] = config.iterations;
                                  if (config.rampUp !== undefined) strategy['爬坡时间'] = config.rampUp;
                                  if (config.rampDown !== undefined) strategy['下降时间'] = config.rampDown;
                                  if (config.stages && Array.isArray(config.stages)) {
                                    strategy['阶段配置'] = config.stages.map((stage: any, idx: number) => 
                                      `阶段${idx + 1}: ${JSON.stringify(stage)}`
                                    ).join('\n');
                                  }
                                  return Object.keys(strategy).length > 0 ? strategy : null;
                                };
                                
                                const testUrl = extractUrlFromScript(testDetail.k6_script);
                                const testStrategy = extractStrategyFromScript(testDetail.k6_script) || 
                                                    getTestStrategyFromConfig(testDetail.execution_config);
                                
                                // 测试地址
                                testInfoMd += '### 测试地址\n\n';
                                testInfoMd += testUrl ? `${testUrl}\n\n` : '未指定（从脚本中提取）\n\n';
                                
                                // 测试策略
                                testInfoMd += '### 测试策略\n\n';
                                if (testStrategy) {
                                  Object.entries(testStrategy).forEach(([key, value]) => {
                                    testInfoMd += `- **${key}**: ${String(value)}\n`;
                                  });
                                } else {
                                  testInfoMd += testDetail.k6_script 
                                    ? '策略信息在 K6 脚本中定义\n'
                                    : '未配置\n';
                                }
                                
                                testInfoMd += '\n---\n\n';
                                return testInfoMd;
                              };
                              
                              // 获取markdown内容，如果没有则尝试从raw_analysis生成
                              let markdownContent = testDetail.analysis.markdown;
                              
                              if (!markdownContent && testDetail.analysis.raw_analysis) {
                                const rawAnalysis = testDetail.analysis.raw_analysis;
                                if (typeof rawAnalysis === 'string' && rawAnalysis.trim().startsWith('{')) {
                                  try {
                                    const parsed = eval(`(${rawAnalysis})`);
                                    if (typeof parsed === 'object') {
                                      markdownContent = `## ⚠️ 分析数据格式异常\n\n分析数据已生成，但Markdown格式化失败。原始数据：\n\n\`\`\`json\n${JSON.stringify(parsed, null, 2)}\n\`\`\``;
                                    }
                                  } catch (e) {
                                    console.error('[性能测试] 解析raw_analysis失败:', e);
                                  }
                                }
                              }
                              
                              // 如果markdown包含原始字典字符串，尝试格式化
                              if (markdownContent && markdownContent.includes("'performance_rating'")) {
                                try {
                                  // 提取字典部分
                                  const dictMatch = markdownContent.match(/\{.*\}/s);
                                  if (dictMatch) {
                                    const dictStr = dictMatch[0];
                                    const parsed = eval(`(${dictStr})`);
                                    // 这里应该调用后端的格式化函数，但为了简单，我们显示JSON格式
                                    markdownContent = `## ⚠️ 分析数据格式异常\n\n分析数据已生成，但Markdown格式化失败。原始数据：\n\n\`\`\`json\n${JSON.stringify(parsed, null, 2)}\n\`\`\``;
                                  }
                                } catch (e) {
                                  console.error('[性能测试] 格式化markdown失败:', e);
                                }
                              }
                              
                              // 在报告开头添加测试信息
                              const testInfoMarkdown = generateTestInfoMarkdown();
                              const fullMarkdown = testInfoMarkdown + (markdownContent || '');
                              
                              const blob = new Blob([fullMarkdown], { type: 'text/markdown;charset=utf-8' });
                              const url = URL.createObjectURL(blob);
                              const link = document.createElement('a');
                              link.href = url;
                              link.download = `performance-analysis-${testDetail.id}-${dayjs().format('YYYYMMDD-HHmmss')}.md`;
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                              URL.revokeObjectURL(url);
                              message.success('Markdown报告已下载');
                            }}
                          >
                            下载报告
                          </Button>
                          <Button
                            icon={<DownloadOutlined />}
                            size="small"
                            onClick={async () => {
                              if (reportContentRef.current) {
                                try {
                                  message.loading({ content: '正在生成图片...', key: 'saveImage', duration: 0 });
                                  const canvas = await html2canvas(reportContentRef.current, {
                                    scale: 2,
                                    useCORS: true,
                                    backgroundColor: '#ffffff',
                                    logging: false,
                                  });
                                  const url = canvas.toDataURL('image/png');
                                  const link = document.createElement('a');
                                  link.href = url;
                                  link.download = `性能分析报告_${testDetail.name || testDetail.id}_${dayjs().format('YYYYMMDD-HHmmss')}.png`;
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
                            }}
                          >
                            保存为图片
                          </Button>
                        </Space>
                      </Space>
                      <Card 
                        size="small" 
                        style={{ 
                          background: '#f8f9fa',
                          borderRadius: 4
                        }}
                      >
                        <div 
                          style={{ 
                            lineHeight: '1.8',
                            padding: '16px',
                          }}
                        >
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              h1: ({node, ...props}) => <h1 style={{ marginTop: '20px', marginBottom: '12px', fontSize: '20px', fontWeight: 'bold', color: '#1890ff', borderBottom: '2px solid #1890ff', paddingBottom: '8px' }} {...props} />,
                              h2: ({node, ...props}) => <h2 style={{ marginTop: '18px', marginBottom: '10px', fontSize: '18px', fontWeight: 'bold', color: '#1890ff' }} {...props} />,
                              h3: ({node, ...props}) => <h3 style={{ marginTop: '16px', marginBottom: '8px', fontSize: '16px', fontWeight: 'bold', color: '#52c41a' }} {...props} />,
                              h4: ({node, ...props}) => <h4 style={{ marginTop: '14px', marginBottom: '6px', fontSize: '14px', fontWeight: 'bold', color: '#722ed1' }} {...props} />,
                              ul: ({node, ...props}) => <ul style={{ marginLeft: '20px', marginBottom: '12px', marginTop: '6px' }} {...props} />,
                              ol: ({node, ...props}) => <ol style={{ marginLeft: '20px', marginBottom: '12px', marginTop: '6px' }} {...props} />,
                              li: ({node, ...props}) => <li style={{ marginBottom: '6px', fontSize: '14px', lineHeight: '1.6' }} {...props} />,
                              p: ({node, ...props}) => <p style={{ marginBottom: '10px', fontSize: '14px', lineHeight: '1.6' }} {...props} />,
                              strong: ({node, ...props}) => <strong style={{ fontWeight: 'bold', color: '#1890ff' }} {...props} />,
                              code: ({node, inline, ...props}: any) => 
                                inline ? (
                                  <code style={{ background: '#f0f0f0', padding: '2px 6px', borderRadius: '3px', fontSize: '13px', fontFamily: 'Monaco, Consolas, monospace' }} {...props} />
                                ) : (
                                  <code style={{ display: 'block', background: '#f5f5f5', padding: '12px', borderRadius: '4px', overflow: 'auto', fontSize: '13px', fontFamily: 'Monaco, Consolas, monospace' }} {...props} />
                                ),
                              blockquote: ({node, ...props}) => <blockquote style={{ borderLeft: '4px solid #1890ff', paddingLeft: '16px', margin: '12px 0', color: '#666', fontStyle: 'italic' }} {...props} />,
                              table: ({node, ...props}) => <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '16px', marginTop: '12px' }} {...props} />,
                              thead: ({node, ...props}) => <thead style={{ backgroundColor: '#f5f5f5' }} {...props} />,
                              tbody: ({node, ...props}) => <tbody {...props} />,
                              tr: ({node, ...props}) => <tr style={{ borderBottom: '1px solid #e8e8e8' }} {...props} />,
                              th: ({node, ...props}) => <th style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold', backgroundColor: '#fafafa', border: '1px solid #e8e8e8' }} {...props} />,
                              td: ({node, ...props}) => <td style={{ padding: '12px', border: '1px solid #e8e8e8' }} {...props} />,
                            }}
                          >
                            {(() => {
                              // 获取markdown内容，如果没有则尝试从raw_analysis生成
                              let markdownContent = testDetail.analysis.markdown;
                              
                              console.log('[性能测试-渲染] Markdown内容检查:', {
                                hasMarkdown: !!markdownContent,
                                markdownType: typeof markdownContent,
                                markdownLength: markdownContent?.length || 0,
                                markdownPreview: markdownContent?.substring(0, 200) || 'N/A',
                                hasRawAnalysis: !!testDetail.analysis.raw_analysis,
                                rawAnalysisType: typeof testDetail.analysis.raw_analysis,
                                analysisKeys: Object.keys(testDetail.analysis || {})
                              });
                              
                              // 如果markdown为空或只有空白字符，尝试从raw_analysis生成
                              if (!markdownContent || (typeof markdownContent === 'string' && markdownContent.trim().length === 0)) {
                                console.log('[性能测试-渲染] Markdown为空，尝试从raw_analysis生成');
                                if (testDetail.analysis.raw_analysis) {
                                  const rawAnalysis = testDetail.analysis.raw_analysis;
                                  if (typeof rawAnalysis === 'string' && rawAnalysis.trim().startsWith('{')) {
                                    try {
                                      // 尝试解析Python字典字符串
                                      const parsed = eval(`(${rawAnalysis})`);
                                      if (typeof parsed === 'object') {
                                        markdownContent = `## ⚠️ 分析数据格式异常\n\n分析数据已生成，但Markdown格式化失败。原始数据：\n\n\`\`\`json\n${JSON.stringify(parsed, null, 2)}\n\`\`\``;
                                        console.log('[性能测试-渲染] 从raw_analysis生成了Markdown，长度:', markdownContent.length);
                                      }
                                    } catch (e) {
                                      console.error('[性能测试] 解析raw_analysis失败:', e);
                                    }
                                  } else if (typeof rawAnalysis === 'string') {
                                    // 如果raw_analysis是普通字符串，直接使用
                                    markdownContent = rawAnalysis;
                                    console.log('[性能测试-渲染] 使用raw_analysis作为Markdown，长度:', markdownContent.length);
                                  }
                                }
                              }
                              
                              // 如果还是没有内容，显示提示信息
                              if (!markdownContent || (typeof markdownContent === 'string' && markdownContent.trim().length === 0)) {
                                console.warn('[性能测试-渲染] Markdown内容为空，显示提示信息');
                                return '## ⚠️ 分析结果为空\n\n分析已完成，但未生成有效内容。请检查后端日志或重新生成分析报告。';
                              }
                              
                              return markdownContent;
                            })()}
                          </ReactMarkdown>
                        </div>
                      </Card>
                    </div>
                  ) : (
                    /* 如果没有Markdown，显示原始分析数据 */
                    <div>
                      {/* 显示关键指标（如果有） */}
                      {testDetail.analysis.key_metrics && (
                        <div style={{ marginBottom: 16 }}>
                          <Title level={5}>关键指标</Title>
                          <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto', maxHeight: 200, fontSize: 12 }}>
                            <code>{JSON.stringify(testDetail.analysis.key_metrics, null, 2)}</code>
                          </pre>
                        </div>
                      )}
                      
                      {/* 显示原始分析数据 */}
                      {testDetail.analysis.raw_analysis && (
                        <div style={{ marginBottom: 16 }}>
                          <Title level={5}>AI 分析结果</Title>
                          <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto', maxHeight: 400, fontSize: 12, whiteSpace: 'pre-wrap' }}>
                            {typeof testDetail.analysis.raw_analysis === 'string' 
                              ? testDetail.analysis.raw_analysis 
                              : JSON.stringify(testDetail.analysis.raw_analysis, null, 2)}
                          </pre>
                        </div>
                      )}
                      
                      {/* 显示完整分析数据 */}
                      <Title level={5}>完整分析数据</Title>
                      <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto', maxHeight: 600, fontSize: 12 }}>
                        <code>{JSON.stringify(testDetail.analysis, null, 2)}</code>
                      </pre>
                    </div>
                  )}
                  
                  {/* 如果分析结果为空，显示重新分析按钮 */}
                  {(!testDetail.analysis.raw_analysis && !testDetail.analysis.error && !testDetail.analysis.markdown) && (
                    <Button
                      type="primary"
                      icon={<BarChartOutlined />}
                      onClick={() => handleAnalyze(testDetail.id)}
                      disabled={isAnalyzing(testDetail)}
                      style={{ marginTop: 16 }}
                    >
                      重新生成 AI 分析报告
                    </Button>
                  )}
                </div>
              ) : testDetail.status === 'completed' || testDetail.status === 'failed' ? (
                <div>
                  <Alert 
                    message="暂无分析结果" 
                    description="点击下方按钮生成AI分析报告" 
                    type="info" 
                    style={{ marginBottom: 16 }} 
                  />
                  <Button
                    type="primary"
                    icon={<BarChartOutlined />}
                    onClick={() => handleAnalyze(testDetail.id)}
                    disabled={isAnalyzing(testDetail)}
                  >
                    生成 AI 分析报告
                  </Button>
                </div>
              ) : (
                <Alert message="请先完成测试执行" type="warning" />
              )}
              </div>
            </Tabs.TabPane>
          </Tabs>
        ) : (
          <Spin />
        )}
      </Drawer>
    </div>
  );
};

export default PerformanceTests;

