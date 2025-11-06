import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Button, Card, Divider, Form, Input, Modal, Select, Space, Table, Tag, Typography, message, Popconfirm, Checkbox, Progress, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, RobotOutlined } from '@ant-design/icons';
import { listTestCases, createTestCase, updateTestCase, deleteTestCase, listProjects, listRequirements, generateTestCasesStream } from '../services/aiService';

const { Title } = Typography;
const { TextArea } = Input;

interface TestCase {
  id: number;
  project_id?: number;
  requirement_id?: number;
  title: string;
  description?: string;
  test_type: string;
  priority?: string;
  status?: string;
  test_data?: any;
  expected_result?: string;
  ai_generated?: boolean;
}

interface Project {
  id: number;
  name: string;
}

interface Requirement {
  id: number;
  title: string;
  project_id: number;
}

const TestCases: React.FC = () => {
  const [items, setItems] = useState<TestCase[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TestCase | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<number | undefined>(undefined);
  const [form] = Form.useForm();
  
  // AI生成相关状态
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [generatedTestCases, setGeneratedTestCases] = useState<any[]>([]);
  const [selectedTestCases, setSelectedTestCases] = useState<Set<number>>(new Set());
  const [aiForm] = Form.useForm();
  const [streamContent, setStreamContent] = useState('');

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

  const fetchRequirements = useCallback(async (projectId?: number) => {
    try {
      const data = await listRequirements(projectId ? { project_id: projectId } : undefined);
      setRequirements(Array.isArray(data) ? data : []);
    } catch (e: any) {
      // 静默处理，避免在没有需求时显示错误
      console.error('加载需求列表失败', e);
      setRequirements([]);
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = selectedProjectId ? { project_id: selectedProjectId } : undefined;
      const data = await listTestCases(params);
      setItems(Array.isArray(data) ? data : []);
    } catch (e: any) {
      // 如果是 404 或空数据，静默处理，显示空列表
      if (e?.response?.status === 404 || e?.response?.status === 200) {
        setItems([]);
      } else {
        // 只有真正的错误才显示提示
        console.error('加载测试用例失败:', e);
        // 不显示错误消息，避免在没有数据时显示错误提示
      }
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    fetchRequirements(selectedProjectId);
  }, [selectedProjectId, fetchRequirements]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 监听项目选择变化，更新需求列表和表单
  const handleProjectChange = (projectId: number | undefined) => {
    form.setFieldsValue({ requirement_id: undefined });
    fetchRequirements(projectId);
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      test_type: 'functional',
      priority: 'medium',
      status: 'draft',
      ai_generated: false,
      project_id: selectedProjectId,
    });
    setModalOpen(true);
  };

  const openEdit = useCallback((record: TestCase) => {
    setEditing(record);
    form.setFieldsValue({ ...record });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (record: TestCase) => {
    try {
      await deleteTestCase(record.id);
      message.success('删除成功');
      fetchData();
    } catch (e) {
      message.error('删除失败');
    }
  }, [fetchData]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        await updateTestCase(editing.id, values);
        message.success('更新成功');
      } else {
        if (!values.project_id) {
          message.error('请选择项目');
          return;
        }
        await createTestCase(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchData();
    } catch (e: any) {
      if (e?.response?.data?.detail) {
        message.error(e.response.data.detail);
      } else if (e?.errorFields) {
        // 表单校验错误
      } else {
        message.error('操作失败');
      }
    }
  };

  const handleAIGenerate = async () => {
    try {
      const values = await aiForm.validateFields(['requirement_text', 'test_type', 'project_id']);
      setAiGenerating(true);
      setStreamContent('');
      setGeneratedTestCases([]);
      setSelectedTestCases(new Set());

      let allContent = '';
      let jsonParsed = false;
      let isCollectingJson = false;
      let jsonContent = '';

      await generateTestCasesStream(
        {
          requirement_text: values.requirement_text,
          test_type: values.test_type,
          test_scope: {},
          generate_script: values.test_type !== 'functional',
        },
        (chunk: string) => {
          allContent += chunk;
          setStreamContent((prev) => prev + chunk);

          // 尝试提取JSON
          if (chunk.includes('#JSON_START#')) {
            isCollectingJson = true;
            jsonContent = '';
            const startIndex = chunk.indexOf('#JSON_START#');
            jsonContent = chunk.substring(startIndex + '#JSON_START#'.length);
          } else if (chunk.includes('#JSON_END#')) {
            const endIndex = chunk.indexOf('#JSON_END#');
            jsonContent += chunk.substring(0, endIndex);
            isCollectingJson = false;
            try {
              const parsed = JSON.parse(jsonContent);
              if (parsed.test_cases && Array.isArray(parsed.test_cases)) {
                setGeneratedTestCases(parsed.test_cases);
                jsonParsed = true;
              }
            } catch (e) {
              console.error('JSON解析失败:', e);
            }
          } else if (isCollectingJson) {
            jsonContent += chunk;
          }

          // 如果没有找到JSON标记，尝试从全部内容中提取JSON
          if (!jsonParsed && allContent.length > 100) {
            try {
              const jsonMatch = allContent.match(/\{[\s\S]*"test_cases"[\s\S]*\}/);
              if (jsonMatch) {
                const parsed = JSON.parse(jsonMatch[0]);
                if (parsed.test_cases && Array.isArray(parsed.test_cases) && parsed.test_cases.length > 0) {
                  setGeneratedTestCases(parsed.test_cases);
                  jsonParsed = true;
                }
              }
            } catch (e) {
              // 忽略解析错误，继续等待
            }
          }
        }
      );

      // 如果流式结束后还没有解析到JSON，尝试从全部内容提取
      if (!jsonParsed && allContent) {
        try {
          const jsonMatch = allContent.match(/\{[\s\S]*"test_cases"[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            if (parsed.test_cases && Array.isArray(parsed.test_cases)) {
              const testCases = parsed.test_cases;
              setGeneratedTestCases(testCases);
              // 立即设置选中状态
              const newIndices = testCases.map((_: any, idx: number) => idx);
              setSelectedTestCases(new Set(newIndices));
              jsonParsed = true;
              message.success(`成功生成 ${testCases.length} 个测试用例`);
            }
          }
        } catch (e) {
          message.warning('AI生成完成，但未能解析出测试用例，请查看生成内容');
        }
      }

      // 使用 setTimeout 确保状态更新后再检查
      setTimeout(() => {
        setGeneratedTestCases(current => {
          if (current.length === 0) {
            message.warning('未生成测试用例，请检查需求描述或重试');
          } else if (!jsonParsed) {
            // 只有在还没有解析成功时才显示成功消息
            message.success(`成功生成 ${current.length} 个测试用例`);
            const newIndices = current.map((_, idx) => idx);
            setSelectedTestCases(new Set(newIndices));
          }
          return current;
        });
      }, 200);
    } catch (e: any) {
      console.error('AI生成失败:', e);
      message.error('AI生成失败: ' + (e?.message || '未知错误'));
    } finally {
      setAiGenerating(false);
    }
  };

  const handleSaveGeneratedTestCases = async () => {
    if (selectedTestCases.size === 0) {
      message.warning('请至少选择一个测试用例');
      return;
    }

    try {
      const values = await aiForm.validateFields(['project_id', 'test_type']);
      
      // 确保使用最新的 generatedTestCases 状态
      const currentGeneratedCases = generatedTestCases;
      if (!currentGeneratedCases || currentGeneratedCases.length === 0) {
        message.error('没有可保存的测试用例，请重新生成');
        return;
      }
      
      // 将索引转换为测试用例对象，并过滤无效项
      const selectedCases = Array.from(selectedTestCases)
        .filter(idx => idx >= 0 && idx < currentGeneratedCases.length) // 确保索引有效
        .map(idx => currentGeneratedCases[idx])
        .filter(tc => tc != null && typeof tc === 'object'); // 过滤掉 undefined 和 null
      
      if (selectedCases.length === 0) {
        console.error('选中的测试用例无效:', {
          selectedTestCases: Array.from(selectedTestCases),
          generatedTestCasesLength: currentGeneratedCases.length,
          generatedTestCases: currentGeneratedCases
        });
        message.error('选中的测试用例无效，请重新选择或重新生成');
        return;
      }
      
      let successCount = 0;
      let failCount = 0;

      for (const testCase of selectedCases) {
        try {
          // 确保 testCase 存在且有必要的字段
          if (!testCase || typeof testCase !== 'object') {
            console.error('无效的测试用例对象:', testCase);
            failCount++;
            continue;
          }
          
          // 调试：打印原始数据
          console.log('保存测试用例原始数据:', {
            title: testCase.title,
            description: testCase.description,
            expected_result: testCase.expected_result,
            preconditions: testCase.preconditions,
            fullTestCase: testCase
          });
          
          // 正确处理 description 和 expected_result
          // description 应该使用 description 字段，如果没有则使用 preconditions（作为前置条件描述）
          const description = testCase.description || 
            (Array.isArray(testCase.preconditions) ? testCase.preconditions.join('; ') : testCase.preconditions) || 
            '';
          
          // expected_result 应该使用 expected_result 字段
          const expectedResult = testCase.expected_result || 
            (Array.isArray(testCase.expected_results) ? testCase.expected_results[0] : testCase.expected_results) || 
            '';
          
          // 调试：打印处理后的数据
          console.log('保存测试用例处理后的数据:', {
            description,
            expectedResult
          });
          
          await createTestCase({
            project_id: values.project_id,
            requirement_id: values.requirement_id,
            title: testCase.title || testCase.name || '未命名测试用例',
            description: description,
            test_type: values.test_type || testCase.test_type || 'functional',
            priority: testCase.priority || 'medium',
            status: 'draft',
            test_data: testCase.test_data || {},
            expected_result: expectedResult,
            ai_generated: true,
          });
          successCount++;
        } catch (e) {
          console.error('保存测试用例失败:', e, testCase);
          failCount++;
        }
      }

      if (successCount > 0) {
        message.success(`成功保存 ${successCount} 个测试用例${failCount > 0 ? `，${failCount} 个失败` : ''}`);
        setAiModalOpen(false);
        setGeneratedTestCases([]);
        setSelectedTestCases(new Set());
        setStreamContent('');
        aiForm.resetFields();
        fetchData();
      } else {
        message.error('保存失败，请重试');
      }
    } catch (e: any) {
      message.error('保存失败: ' + (e?.message || '未知错误'));
    }
  };

  const columns = useMemo(() => [
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
      title: '标题', 
      dataIndex: 'title', 
      width: 200,
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip placement="topLeft" title={text}>
          {text}
        </Tooltip>
      ),
    },
    { 
      title: '描述', 
      dataIndex: 'description', 
      width: 250,
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => {
        if (!text) return <span style={{ color: '#999' }}>-</span>;
        const truncated = text.length > 50 ? text.substring(0, 50) + '...' : text;
        return (
          <Tooltip placement="topLeft" title={text}>
            {truncated}
          </Tooltip>
        );
      },
    },
    { title: '类型', dataIndex: 'test_type', width: 100 },
    { title: '优先级', dataIndex: 'priority', width: 100, render: (v: string) => <Tag color={v === 'high' ? 'red' : v === 'low' ? 'green' : 'blue'}>{v || '-'}</Tag> },
    { title: '状态', dataIndex: 'status', width: 100 },
    { 
      title: '预期结果', 
      dataIndex: 'expected_result', 
      width: 250,
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => {
        if (!text) return <span style={{ color: '#999' }}>-</span>;
        const truncated = text.length > 50 ? text.substring(0, 50) + '...' : text;
        return (
          <Tooltip placement="topLeft" title={text}>
            {truncated}
          </Tooltip>
        );
      },
    },
    { title: 'AI', dataIndex: 'ai_generated', width: 80, render: (v: any) => (v === true || v === 'true') ? <Tag color="purple">AI</Tag> : '-' },
    {
      title: '操作',
      width: 160,
      fixed: 'right',
      render: (_: any, record: TestCase) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除该用例？" onConfirm={() => handleDelete(record)}>
            <Button icon={<DeleteOutlined />} size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ], [openEdit, handleDelete, projects]);

  return (
    <div>
      <Title level={2}>测试用例</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用例</Button>
          <Button type="primary" icon={<RobotOutlined />} onClick={() => setAiModalOpen(true)} style={{ background: '#722ed1', borderColor: '#722ed1' }}>AI生成用例</Button>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
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
          scroll={{ x: 1400 }}
        />
      </Card>

      <Modal
        title={editing ? '编辑测试用例' : '新建测试用例'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText={editing ? '保存' : '创建'}
      >
        <Form layout="vertical" form={form}>
          <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="例如：正常登录" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="补充该用例背景、前置条件等" />
          </Form.Item>
          <Form.Item label="测试类型" name="test_type" rules={[{ required: true, message: '请选择测试类型' }]}>
            <Select
              options={[
                { label: '功能测试', value: 'functional' },
                { label: 'API', value: 'api' },
                { label: 'UI', value: 'ui' },
              ]}
            />
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
                { label: '就绪', value: 'ready' },
                { label: '归档', value: 'archived' },
              ]}
            />
          </Form.Item>
          <Form.Item label="期望结果" name="expected_result">
            <TextArea rows={3} placeholder="例如：登录成功并跳转到首页" />
          </Form.Item>
          <Form.Item
            label="所属项目"
            name="project_id"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="选择项目"
              onChange={handleProjectChange}
              options={projects.map(p => ({ label: p.name, value: p.id }))}
            />
          </Form.Item>
          <Form.Item label="关联需求" name="requirement_id">
            <Select
              placeholder="选择需求（可选）"
              allowClear
              disabled={!form.getFieldValue('project_id')}
              options={requirements
                .filter(r => !form.getFieldValue('project_id') || r.project_id === form.getFieldValue('project_id'))
                .map(r => ({ label: r.title, value: r.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* AI生成测试用例Modal */}
      <Modal
        title="AI生成测试用例"
        open={aiModalOpen}
        onCancel={() => {
          setAiModalOpen(false);
          setGeneratedTestCases([]);
          setSelectedTestCases(new Set());
          setStreamContent('');
          aiForm.resetFields();
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setAiModalOpen(false);
            setGeneratedTestCases([]);
            setSelectedTestCases(new Set());
            setStreamContent('');
            aiForm.resetFields();
          }}>取消</Button>,
          generatedTestCases.length > 0 && (
            <Button
              key="save"
              type="primary"
              onClick={handleSaveGeneratedTestCases}
              disabled={selectedTestCases.size === 0}
            >
              保存选中 ({selectedTestCases.size})
            </Button>
          ),
          !aiGenerating && generatedTestCases.length === 0 && (
            <Button
              key="generate"
              type="primary"
              onClick={handleAIGenerate}
              loading={aiGenerating}
            >
              生成
            </Button>
          ),
        ]}
        width={800}
      >
        <Form layout="vertical" form={aiForm} initialValues={{ test_type: 'functional', generate_script: false }}>
          <Form.Item
            label="需求描述"
            name="requirement_text"
            rules={[{ required: true, message: '请输入需求描述' }]}
          >
            <TextArea
              rows={4}
              placeholder="请输入需求描述，AI将根据此需求生成测试用例..."
            />
          </Form.Item>
          <Form.Item
            label="测试类型"
            name="test_type"
            rules={[{ required: true, message: '请选择测试类型' }]}
          >
            <Select
              options={[
                { label: '功能测试', value: 'functional' },
                { label: 'API测试', value: 'api' },
                { label: 'UI测试', value: 'ui' },
              ]}
            />
          </Form.Item>
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
          <Form.Item label="关联需求" name="requirement_id">
            <Select
              placeholder="选择需求（可选）"
              allowClear
              options={requirements
                .filter(r => !aiForm.getFieldValue('project_id') || r.project_id === aiForm.getFieldValue('project_id'))
                .map(r => ({ label: r.title, value: r.id }))}
            />
          </Form.Item>
        </Form>

        {aiGenerating && (
          <div style={{ marginTop: 16 }}>
            <Progress percent={50} status="active" />
            <div style={{ marginTop: 8, padding: 12, background: '#f5f5f5', borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{streamContent}</pre>
            </div>
          </div>
        )}

        {generatedTestCases.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Typography.Title level={5}>生成的测试用例 ({generatedTestCases.length})</Typography.Title>
            <Table
              rowKey={(record: any) => `generated-${record._index ?? 0}`}
              dataSource={generatedTestCases.map((tc, idx) => ({ ...tc, _index: idx }))}
              pagination={false}
              rowSelection={{
                selectedRowKeys: Array.from(selectedTestCases).map(idx => `generated-${idx}`),
                onChange: (selectedRowKeys) => {
                  // 从 rowKey 中提取索引
                  const indices = (selectedRowKeys as string[])
                    .map(key => {
                      const match = key.toString().match(/generated-(\d+)/);
                      return match ? parseInt(match[1], 10) : null;
                    })
                    .filter(idx => idx !== null) as number[];
                  setSelectedTestCases(new Set(indices));
                },
              }}
              columns={[
                {
                  title: '选择',
                  width: 60,
                  render: (_: any, record: any) => (
                    <Checkbox
                      checked={selectedTestCases.has(record._index)}
                      onChange={(e) => {
                        const newSet = new Set(selectedTestCases);
                        if (e.target.checked) {
                          newSet.add(record._index);
                        } else {
                          newSet.delete(record._index);
                        }
                        setSelectedTestCases(newSet);
                      }}
                    />
                  ),
                },
                { 
                  title: '标题', 
                  dataIndex: 'title', 
                  width: 200,
                  ellipsis: {
                    showTitle: false,
                  },
                  render: (text: string) => (
                    <Tooltip placement="topLeft" title={text}>
                      {text || '-'}
                    </Tooltip>
                  ),
                },
                { title: '类型', dataIndex: 'test_type', width: 100 },
                { title: '优先级', dataIndex: 'priority', width: 100 },
                {
                  title: '描述',
                  dataIndex: 'description',
                  width: 200,
                  ellipsis: {
                    showTitle: false,
                  },
                  render: (text: string) => {
                    if (!text) return <span style={{ color: '#999' }}>-</span>;
                    const truncated = text.length > 50 ? text.substring(0, 50) + '...' : text;
                    return (
                      <Tooltip placement="topLeft" title={text}>
                        {truncated}
                      </Tooltip>
                    );
                  },
                },
                {
                  title: '预期结果',
                  dataIndex: 'expected_result',
                  width: 200,
                  ellipsis: {
                    showTitle: false,
                  },
                  render: (text: string) => {
                    if (!text) return <span style={{ color: '#999' }}>-</span>;
                    const truncated = text.length > 50 ? text.substring(0, 50) + '...' : text;
                    return (
                      <Tooltip placement="topLeft" title={text}>
                        {truncated}
                      </Tooltip>
                    );
                  },
                },
              ]}
              size="small"
            />
          </div>
        )}
      </Modal>

      <Divider />
      <p style={{ color: '#999' }}>提示：可以使用AI生成功能快速创建测试用例，也可以手动创建和编辑用例。</p>
    </div>
  );
};

export default TestCases;