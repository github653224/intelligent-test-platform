import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000, // 减少超时时间到10秒，避免长时间等待
  headers: {
    'Content-Type': 'application/json',
  },
});

// 需求分析
export const analyzeRequirement = async (data: {
  requirement_text: string;
  project_context?: string;
  test_focus?: string[];
}) => {
  const response = await apiClient.post('/ai/analyze-requirement', data);
  return response.data;
};

// 生成测试用例
export const generateTestCases = async (data: {
  requirement_text: string;
  test_type: string;
  test_scope?: any;
  generate_script?: boolean;
}) => {
  const response = await apiClient.post('/ai/generate-test-cases', data);
  return response.data;
};

// 流式生成测试用例
export const generateTestCasesStream = async (
  data: {
    requirement_text: string;
    test_type: string;
    test_scope?: any;
    generate_script?: boolean;
  },
  onChunk: (chunk: string) => void
) => {
  const response = await fetch(`${API_BASE_URL}/ai/generate-test-cases-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      const text = decoder.decode(value);
      const lines = text.split('\n');
      for (const rawLine of lines) {
        const line = rawLine;
        if (line.startsWith('data: ')) {
          const content = line.slice(6).trim();
          if (content === '[DONE]') return;
          if (content) onChunk(content);
        } else {
          const content = line.trim();
          if (content) onChunk(content);
        }
      }
    }
  } finally {
    reader?.releaseLock();
  }
};

// 生成API测试
export const generateAPITests = async (data: {
  api_documentation: string;
  base_url: string;
  test_scenarios?: string[];
  parsed_doc?: any;  // 解析后的API文档结构（可选）
}) => {
  const response = await apiClient.post('/ai/generate-api-tests', data, {
    timeout: 300000, // 5分钟超时（生成所有接口需要更长时间）
  });
  return response.data;
};

// 分析页面结构
export const analyzePage = async (url: string, waitTime: number = 2000): Promise<{
  success: boolean;
  page_info: any;
  summary: string;
}> => {
  const response = await apiClient.post('/ai/analyze-page', {
    url,
    wait_time: waitTime
  }, {
    timeout: 60000, // 60秒超时（页面分析可能需要时间）
  });
  return response.data;
};

// 生成UI测试
export const generateUITests = async (data: {
  page_url: string;
  user_actions: string | string[];  // 支持字符串（业务需求）或数组（操作步骤）
  test_scenarios?: string[];
  page_info?: any;  // 页面分析结果（可选）
}) => {
  const response = await apiClient.post('/ai/generate-ui-tests', data, {
    timeout: 300000, // 5分钟超时（页面分析和AI生成需要更长时间）
  });
  return response.data;
};

// 项目 CRUD
export const listProjects = async () => {
  const response = await apiClient.get('/projects/');
  return response.data;
};

export const getProject = async (id: number) => {
  const response = await apiClient.get(`/projects/${id}`);
  return response.data;
};

export const createProject = async (data: {
  name: string;
  description?: string;
  status?: string;
  config?: any;
}) => {
  const response = await apiClient.post('/projects/', data);
  return response.data;
};

export const updateProject = async (id: number, data: Partial<{
  name: string;
  description?: string;
  status?: string;
  config?: any;
}>) => {
  const response = await apiClient.put(`/projects/${id}`, data);
  return response.data;
};

export const deleteProject = async (id: number) => {
  const response = await apiClient.delete(`/projects/${id}`);
  return response.data;
};

// 需求 CRUD
export const listRequirements = async (params?: { project_id?: number }) => {
  const response = await apiClient.get('/requirements/', { params });
  return response.data;
};

export const getRequirement = async (id: number) => {
  const response = await apiClient.get(`/requirements/${id}`);
  return response.data;
};

export const createRequirement = async (data: {
  project_id: number;
  title: string;
  description?: string;
  priority?: string;
  status?: string;
  ai_analysis?: any;
}) => {
  const response = await apiClient.post('/requirements/', data);
  return response.data;
};

export const updateRequirement = async (id: number, data: Partial<{
  project_id: number;
  title: string;
  description?: string;
  priority?: string;
  status?: string;
  ai_analysis?: any;
}>) => {
  const response = await apiClient.put(`/requirements/${id}`, data);
  return response.data;
};

export const deleteRequirement = async (id: number) => {
  const response = await apiClient.delete(`/requirements/${id}`);
  return response.data;
};

// 测试用例 CRUD
export const listTestCases = async (params?: { project_id?: number }) => {
  const response = await apiClient.get('/test-cases/', { params });
  return response.data;
};

export const getTestCase = async (id: number) => {
  const response = await apiClient.get(`/test-cases/${id}`);
  return response.data;
};

export const createTestCase = async (data: {
  project_id: number;
  requirement_id?: number;
  title: string;
  description?: string;
  test_type: string;
  priority?: string;
  status?: string;
  test_data?: any;
  expected_result?: string;
  ai_generated?: boolean;
}) => {
  const response = await apiClient.post('/test-cases/', data);
  return response.data;
};

export const updateTestCase = async (id: number, data: Partial<{
  project_id: number;
  requirement_id?: number;
  title: string;
  description?: string;
  test_type: string;
  priority?: string;
  status?: string;
  test_data?: any;
  expected_result?: string;
  ai_generated?: boolean;
}>) => {
  const response = await apiClient.put(`/test-cases/${id}`, data);
  return response.data;
};

export const deleteTestCase = async (id: number) => {
  const response = await apiClient.delete(`/test-cases/${id}`);
  return response.data;
};

// 检查AI引擎健康状态
export const checkAIEngineHealth = async () => {
  const response = await apiClient.get('/ai/health');
  return response.data;
};

// 测试运行 CRUD
export const listTestRuns = async (params?: { project_id?: number; test_suite_id?: number; status?: string }) => {
  const response = await apiClient.get('/test-runs/', { params });
  return response.data;
};

export const getTestRun = async (id: number) => {
  const response = await apiClient.get(`/test-runs/${id}`);
  return response.data;
};

export const createTestRun = async (data: {
  project_id: number;
  test_suite_id?: number;
  name: string;
  test_case_ids?: number[];
  execution_config?: any;
}) => {
  const response = await apiClient.post('/test-runs/', data);
  return response.data;
};

export const updateTestRun = async (id: number, data: Partial<{
  name: string;
  status: string;
  end_time: string;
  results: any;
}>) => {
  const response = await apiClient.put(`/test-runs/${id}`, data);
  return response.data;
};

export const deleteTestRun = async (id: number) => {
  const response = await apiClient.delete(`/test-runs/${id}`);
  return response.data;
};

export const executeTestRun = async (id: number) => {
  const response = await apiClient.post(`/test-runs/${id}/execute`);
  return response.data;
};

export const cancelTestRun = async (id: number) => {
  const response = await apiClient.post(`/test-runs/${id}/cancel`);
  return response.data;
};

// 测试报告
export const getTestRunSummary = async (id: number) => {
  const response = await apiClient.get(`/test-runs/${id}/report/summary`);
  return response.data;
};

export const getTestRunDetailedReport = async (id: number) => {
  const response = await apiClient.get(`/test-runs/${id}/report/detailed`);
  return response.data;
};

export const getTestRunHtmlReport = async (id: number) => {
  const response = await fetch(`${API_BASE_URL}/test-runs/${id}/report/html`);
  return response.text();
};

export const getTestRunJsonReport = async (id: number) => {
  const response = await apiClient.get(`/test-runs/${id}/report/json`);
  return response.data;
};

export const downloadTestRunCsvReport = async (id: number) => {
  const response = await fetch(`${API_BASE_URL}/test-runs/${id}/report/csv`);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `test_run_${id}_report.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

// 手动验证测试结果
export const manuallyVerifyTestResult = async (data: {
  test_run_id: number;
  test_case_id: number;
  status: string;
  actual_result?: string;
  verification_notes?: string;
  failure_reason?: string;
  bug_id?: string;
  verified_by?: string;
  step_results?: Array<{
    step_number: number;
    status: string;
    result?: string;
    notes?: string;
  }>;
}) => {
  const response = await apiClient.post(`/test-runs/${data.test_run_id}/verify`, data);
  return response.data;
};

// 批量验证测试结果
export const batchVerifyTestResults = async (test_run_id: number, verifications: Array<{
  test_case_id: number;
  status: string;
  actual_result?: string;
  verification_notes?: string;
  failure_reason?: string;
  bug_id?: string;
  verified_by?: string;
  step_results?: Array<{
    step_number: number;
    status: string;
    result?: string;
    notes?: string;
  }>;
}>) => {
  const response = await apiClient.post(`/test-runs/${test_run_id}/verify/batch`, {
    test_run_id,
    verifications
  });
  return response.data;
};

// 定时执行相关API
export const setTestRunSchedule = async (test_run_id: number, schedule_config: any) => {
  const response = await apiClient.post(`/test-runs/${test_run_id}/schedule`, schedule_config);
  return response.data;
};

export const removeTestRunSchedule = async (test_run_id: number) => {
  const response = await apiClient.delete(`/test-runs/${test_run_id}/schedule`);
  return response.data;
};

export const getTestRunSchedule = async (test_run_id: number) => {
  const response = await apiClient.get(`/test-runs/${test_run_id}/schedule`);
  return response.data;
};

// 统计信息API
export const getDashboardStatistics = async () => {
  const response = await apiClient.get('/statistics/dashboard');
  return response.data;
};

export const getRecentTestRuns = async (limit: number = 10) => {
  const response = await apiClient.get('/statistics/test-runs/recent', {
    params: { limit }
  });
  return response.data;
};

// AI测试报告汇总分析
export const analyzeTestSummary = async (days: number = 30, projectId?: number) => {
  const params: any = { days };
  if (projectId) {
    params.project_id = projectId;
  }
  const response = await apiClient.get('/analysis/test-runs/analyze-summary', { params });
  return response.data;
};

// AI测试报告汇总分析（流式）
export const analyzeTestSummaryStream = async (
  days: number = 30,
  projectId: number | undefined,
  onChunk: (data: { type: string; content?: string; data?: any; message?: string }) => void
) => {
  const params = new URLSearchParams({ days: days.toString() });
  if (projectId) {
    params.append('project_id', projectId.toString());
  }

  const response = await fetch(`${API_BASE_URL}/analysis/test-runs/analyze-summary-stream?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n');

      for (const rawLine of lines) {
        const line = rawLine.trim();
        if (line.startsWith('data: ')) {
          const content = line.slice(6).trim();
          if (content === '[DONE]') {
            onChunk({ type: 'done' });
            return;
          }
          if (content) {
            try {
              const data = JSON.parse(content);
              onChunk(data);
            } catch (e) {
              // 如果不是JSON，直接作为文本内容
              onChunk({ type: 'chunk', content });
            }
          }
        } else if (line) {
          // 兼容没有data:前缀的情况
          try {
            const data = JSON.parse(line);
            onChunk(data);
          } catch (e) {
            onChunk({ type: 'chunk', content: line });
          }
        }
      }
    }
  } finally {
    reader?.releaseLock();
  }
};

// 解析文档（Word、PDF、Excel、XMind）
export const parseDocument = async (file: File): Promise<{
  success: boolean;
  filename: string;
  text: string;
  metadata: any;
  text_length: number;
}> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/ai/parse-document`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '文档解析失败');
  }
  
  return response.json();
};

// 解析API文档（OpenAPI/Swagger、Postman Collection）
export const parseAPIDocument = async (file: File): Promise<{
  success: boolean;
  filename: string;
  parsed_doc: any;
  summary: string;
  endpoints_count: number;
  base_url: string;
}> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/ai/parse-api-document`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API文档解析失败');
  }
  
  return response.json();
};

// 流式需求分析
export const analyzeRequirementStream = async (
  data: {
    requirement_text: string;
    project_context?: string;
    test_focus?: string[];
  },
  onChunk: (chunk: string) => void
) => {
  const response = await fetch(`${API_BASE_URL}/ai/analyze-requirement-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n');

      for (const rawLine of lines) {
        const line = rawLine; // keep original for minimal mutation
        if (line.startsWith('data: ')) {
          const content = line.slice(6).trim();
          if (content === '[DONE]') {
            return;
          }
          if (content) {
            onChunk(content);
          }
        } else {
          // 兼容后端转发导致的多行数据未带 data: 前缀的情况
          const content = line.trim();
          if (content) {
            onChunk(content);
          }
        }
      }
    }
  } finally {
    reader?.releaseLock();
  }
};

// ==================== 性能测试 API ====================

export interface PerformanceTest {
  id: number;
  project_id: number;
  name: string;
  description?: string;
  k6_script?: string;
  script_generated_by_ai?: string;
  ai_prompt?: string; // AI生成脚本时的提示词（用户原始需求）
  execution_config?: any;
  status: string; // pending, running, completed, failed, cancelled
  start_time?: string;
  end_time?: string;
  duration?: number;
  results?: any;
  analysis?: any;
  analysis_generated_at?: string;
  created_at: string;
  updated_at: string;
}

export interface K6ScriptGenerateRequest {
  test_description: string;
  target_url?: string;
  load_config?: {
    vus?: number;
    duration?: string;
    stages?: any[];
  };
}

// 生成 k6 脚本
export const generateK6Script = async (data: K6ScriptGenerateRequest) => {
  const response = await apiClient.post('/performance-tests/generate-script', data);
  return response.data;
};

// 创建性能测试
export const createPerformanceTest = async (data: {
  project_id: number;
  name: string;
  description?: string;
  test_description: string;
  target_url?: string;
  load_config?: any;
}) => {
  const response = await apiClient.post('/performance-tests', data);
  return response.data;
};

// 获取性能测试列表
export const listPerformanceTests = async (params?: { project_id?: number }) => {
  // 列表查询使用更短的超时时间，确保快速响应
  const response = await apiClient.get('/performance-tests', { 
    params,
    timeout: 5000  // 5秒超时
  });
  return response.data;
};

// 获取性能测试详情
export const getPerformanceTest = async (id: number) => {
  // 详情查询使用更短的超时时间，避免阻塞
  const response = await apiClient.get(`/performance-tests/${id}`, {
    timeout: 5000  // 5秒超时
  });
  return response.data;
};

// 执行性能测试
export const executePerformanceTest = async (id: number) => {
  // 执行API应该立即返回，使用短超时
  const response = await apiClient.post(`/performance-tests/${id}/execute`, {}, {
    timeout: 5000  // 5秒超时
  });
  return response.data;
};

// 分析性能测试结果
export const analyzePerformanceTest = async (id: number) => {
  const response = await apiClient.post(`/performance-tests/${id}/analyze`, {}, {
    timeout: 180000, // 3分钟超时，AI分析可能需要较长时间
  });
  return response.data;
};

// 更新性能测试
export const updatePerformanceTest = async (id: number, data: Partial<PerformanceTest>) => {
  const response = await apiClient.put(`/performance-tests/${id}`, data);
  return response.data;
};

// 删除性能测试
export const deletePerformanceTest = async (id: number) => {
  const response = await apiClient.delete(`/performance-tests/${id}`);
  return response.data;
};