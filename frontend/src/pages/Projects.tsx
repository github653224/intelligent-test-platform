import React, { useEffect, useLayoutEffect, useState, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Typography, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { listProjects, createProject, updateProject, deleteProject } from '../services/aiService';

const { Title } = Typography;
const { TextArea } = Input;

interface Project {
  id: number;
  name: string;
  description?: string;
  status?: string;
  config?: any;
  created_at?: string;
  updated_at?: string;
}

const Projects: React.FC = () => {
  const location = useLocation();
  const [items, setItems] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form] = Form.useForm();
  const isMountedRef = useRef(true);
  const isCurrentRouteRef = useRef(false);

  const fetchData = useCallback(async (showLoading: boolean = true) => {
    // 首先检查是否是当前路由 - 必须在最前面检查
    const isCurrentRoute = location.pathname === '/projects';
    if (!isCurrentRoute) {
      console.log('[Projects] 不是当前路由，不加载数据', { pathname: location.pathname });
      if (showLoading) {
        setLoading(false);
      }
      return;
    }
    
    console.log('[Projects] 开始加载数据', { isMounted: isMountedRef.current, isCurrentRoute: isCurrentRouteRef.current, pathname: location.pathname });
    if (showLoading) {
      setLoading(true);
    }
    try {
      const data = await listProjects();
      const newItems = Array.isArray(data) ? data : [];
      // 检查路由（异步操作后）
      if (location.pathname !== '/projects') {
        console.warn('[Projects] 不在项目管理页面，不更新状态');
        if (showLoading) {
          setLoading(false);
        }
        return;
      }
      // 如果新数据为空，但之前有数据，保留旧数据（防止数据丢失）
      setItems(prev => {
        if (location.pathname !== '/projects') {
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
        console.error('加载项目失败:', e);
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
  }, [location.pathname]);

  // 监听路由变化 - 使用 useLayoutEffect 确保在渲染前执行
  useLayoutEffect(() => {
    const isProjectsRoute = location.pathname === '/projects';
    const wasCurrentRoute = isCurrentRouteRef.current;
    isCurrentRouteRef.current = isProjectsRoute;

    console.log('[Projects] 路由变化', { pathname: location.pathname, isCurrentRoute: isProjectsRoute, wasCurrentRoute });

    if (!isProjectsRoute) {
      // 不是当前路由，立即停止所有操作（必须在渲染前清除）
      console.log('[Projects] 离开当前路由，立即清除状态');
      isMountedRef.current = false;
      setLoading(false); // 强制清除loading，无论之前是否在当前路由
      return;
    }

    // 是当前路由，确保标记已设置
    isMountedRef.current = true;

    // 首次进入页面时加载数据（只在之前不在当前路由时）
    if (!wasCurrentRoute) {
      console.log('[Projects] 首次进入项目管理页面，加载数据');
      // 延迟执行，确保状态已设置
      setTimeout(() => {
        if (location.pathname === '/projects' && isMountedRef.current && isCurrentRouteRef.current) {
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
    form.setFieldsValue({ status: 'active' });
    setModalOpen(true);
  };

  const openEdit = useCallback((record: Project) => {
    setEditing(record);
    form.setFieldsValue({ ...record });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (record: Project) => {
    try {
      await deleteProject(record.id);
      message.success('删除成功');
      if (location.pathname === '/projects') {
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
        await updateProject(editing.id, values);
        message.success('更新成功');
      } else {
        await createProject(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      if (location.pathname === '/projects') {
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
    { title: '项目名称', dataIndex: 'name', width: 200 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          active: { color: 'green', text: '活跃' },
          inactive: { color: 'default', text: '非活跃' },
          archived: { color: 'red', text: '已归档' },
        };
        const statusInfo = statusMap[status || 'active'] || statusMap.active;
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
      render: (_: any, record: Project) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该项目？"
            description="删除项目将同时删除关联的需求和测试用例"
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
      <Title level={2}>项目管理</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建项目
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => {
            // 强制清除loading状态，然后刷新
            setLoading(false);
            if (location.pathname === '/projects') {
              fetchData(true);
            }
          }} loading={loading && location.pathname === '/projects'}>
            刷新
          </Button>
        </Space>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={editing ? '编辑项目' : '新建项目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
        width={600}
      >
        <Form layout="vertical" form={form}>
          <Form.Item
            label="项目名称"
            name="name"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="例如：电商平台" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={4} placeholder="项目描述、背景等信息" />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={[
                { label: '活跃', value: 'active' },
                { label: '非活跃', value: 'inactive' },
                { label: '已归档', value: 'archived' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Projects;
