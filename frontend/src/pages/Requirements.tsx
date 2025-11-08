import React, { useEffect, useLayoutEffect, useState, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Typography, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { listRequirements, createRequirement, updateRequirement, deleteRequirement, listProjects } from '../services/aiService';

const { Title } = Typography;
const { TextArea } = Input;

interface Requirement {
  id: number;
  project_id: number;
  title: string;
  description?: string;
  priority?: string;
  status?: string;
  ai_analysis?: any;
  created_at?: string;
  updated_at?: string;
}

interface Project {
  id: number;
  name: string;
}

const Requirements: React.FC = () => {
  const location = useLocation();
  const [items, setItems] = useState<Requirement[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Requirement | null>(null);
  const isMountedRef = useRef(true);
  const isCurrentRouteRef = useRef(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | undefined>(undefined);
  const [form] = Form.useForm();

  const fetchProjects = useCallback(async () => {
    try {
      const data = await listProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (e: any) {
      // 静默处理，避免在没有项目时显示错误
      console.error('加载项目列表失败', e);
      setProjects([]);
    }
  }, []);

  const fetchData = useCallback(async (showLoading: boolean = true) => {
    // 首先检查是否是当前路由 - 必须在最前面检查
    const isCurrentRoute = location.pathname === '/requirements';
    if (!isCurrentRoute) {
      console.log('[Requirements] 不是当前路由，不加载数据', { pathname: location.pathname });
      if (showLoading) {
        setLoading(false);
      }
      return;
    }
    
    console.log('[Requirements] 开始加载数据', { isMounted: isMountedRef.current, isCurrentRoute: isCurrentRouteRef.current, pathname: location.pathname });
    if (showLoading) {
      setLoading(true);
    }
    try {
      const params = selectedProjectId ? { project_id: selectedProjectId } : undefined;
      const data = await listRequirements(params);
      const newItems = Array.isArray(data) ? data : [];
      // 检查路由（异步操作后）
      if (location.pathname !== '/requirements') {
        console.warn('[Requirements] 不在需求管理页面，不更新状态');
        if (showLoading) {
          setLoading(false);
        }
        return;
      }
      // 如果新数据为空，但之前有数据，保留旧数据（防止数据丢失）
      setItems(prev => {
        if (location.pathname !== '/requirements') {
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
      // 如果是 404 或空数据，静默处理，显示空列表
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
        // 只有真正的错误才显示提示
        console.error('加载需求失败:', e);
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
    const isRequirementsRoute = location.pathname === '/requirements';
    const wasCurrentRoute = isCurrentRouteRef.current;
    isCurrentRouteRef.current = isRequirementsRoute;

    console.log('[Requirements] 路由变化', { pathname: location.pathname, isCurrentRoute: isRequirementsRoute, wasCurrentRoute });

    if (!isRequirementsRoute) {
      // 不是当前路由，立即停止所有操作（必须在渲染前清除）
      console.log('[Requirements] 离开当前路由，立即清除状态');
      isMountedRef.current = false;
      setLoading(false); // 强制清除loading，无论之前是否在当前路由
      return;
    }

    // 是当前路由，确保标记已设置
    isMountedRef.current = true;

    // 首次进入页面时加载数据（只在之前不在当前路由时）
    if (!wasCurrentRoute) {
      console.log('[Requirements] 首次进入需求管理页面，加载数据');
      // 延迟执行，确保状态已设置
      setTimeout(() => {
        if (location.pathname === '/requirements' && isMountedRef.current && isCurrentRouteRef.current) {
          fetchData(true);
        }
      }, 0);
    }
  }, [location.pathname, fetchData]);

  // 注意：不再使用 useEffect 自动加载数据，只在 useLayoutEffect 中处理
  // 这样可以避免重复调用和 loading 状态异常

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      priority: 'medium',
      status: 'draft',
      project_id: selectedProjectId,
    });
    setModalOpen(true);
  };

  const openEdit = useCallback((record: Requirement) => {
    setEditing(record);
    form.setFieldsValue({ ...record });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (record: Requirement) => {
    try {
      await deleteRequirement(record.id);
      message.success('删除成功');
      if (location.pathname === '/requirements') {
        fetchData(true);
      }
    } catch (e) {
      message.error('删除失败');
    }
  }, [fetchData, location.pathname]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        await updateRequirement(editing.id, values);
        message.success('更新成功');
      } else {
        await createRequirement(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      if (location.pathname === '/requirements') {
        fetchData(true);
      }
    } catch (e: any) {
      if (e?.response?.data?.detail) {
        message.error(e.response.data.detail);
      } else {
        message.error('操作失败');
      }
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    {
      title: '项目',
      dataIndex: 'project_id',
      width: 150,
      render: (projectId: number) => {
        const project = projects.find(p => p.id === projectId);
        return project ? project.name : `项目 ${projectId}`;
      },
    },
    { title: '标题', dataIndex: 'title', width: 200 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 100,
      render: (priority: string) => {
        const priorityMap: Record<string, { color: string; text: string }> = {
          high: { color: 'red', text: '高' },
          medium: { color: 'orange', text: '中' },
          low: { color: 'blue', text: '低' },
        };
        const priorityInfo = priorityMap[priority || 'medium'] || priorityMap.medium;
        return <Tag color={priorityInfo.color}>{priorityInfo.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          draft: { color: 'default', text: '草稿' },
          reviewing: { color: 'orange', text: '评审中' },
          approved: { color: 'green', text: '已批准' },
          implemented: { color: 'blue', text: '已实现' },
          archived: { color: 'red', text: '已归档' },
        };
        const statusInfo = statusMap[status || 'draft'] || statusMap.draft;
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (text: string) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      width: 160,
      fixed: 'right' as const,
      render: (_: any, record: Requirement) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该需求？"
            description="删除需求将同时删除关联的测试用例"
            onConfirm={() => handleDelete(record)}
            okText="确认"
            cancelText="取消"
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
      <Title level={2}>需求管理</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建需求
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => {
            // 强制清除loading状态，然后刷新
            setLoading(false);
            if (location.pathname === '/requirements') {
              fetchData(true);
            }
          }} loading={loading && location.pathname === '/requirements'}>
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
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1400 }}
        />
      </Card>

      <Modal
        title={editing ? '编辑需求' : '新建需求'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
        width={700}
      >
        <Form layout="vertical" form={form}>
          <Form.Item
            label="所属项目"
            name="project_id"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="选择项目"
              options={projects.map(p => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
          <Form.Item
            label="需求标题"
            name="title"
            rules={[{ required: true, message: '请输入需求标题' }]}
          >
            <Input placeholder="例如：用户登录功能" />
          </Form.Item>
          <Form.Item label="需求描述" name="description">
            <TextArea rows={4} placeholder="详细描述需求内容、背景等信息" />
          </Form.Item>
          <Form.Item label="优先级" name="priority">
            <Select
              options={[
                { label: '高', value: 'high' },
                { label: '中', value: 'medium' },
                { label: '低', value: 'low' },
              ]}
            />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={[
                { label: '草稿', value: 'draft' },
                { label: '评审中', value: 'reviewing' },
                { label: '已批准', value: 'approved' },
                { label: '已实现', value: 'implemented' },
                { label: '已归档', value: 'archived' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Requirements;
