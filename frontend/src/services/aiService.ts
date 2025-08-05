import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
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
}) => {
  const response = await apiClient.post('/ai/generate-test-cases', data);
  return response.data;
};

// 生成API测试
export const generateAPITests = async (data: {
  api_documentation: string;
  base_url: string;
  test_scenarios?: string[];
}) => {
  const response = await apiClient.post('/ai/generate-api-tests', data);
  return response.data;
};

// 生成UI测试
export const generateUITests = async (data: {
  page_url: string;
  user_actions: string[];
  test_scenarios?: string[];
}) => {
  const response = await apiClient.post('/ai/generate-ui-tests', data);
  return response.data;
};

// 检查AI引擎健康状态
export const checkAIEngineHealth = async () => {
  const response = await apiClient.get('/ai/health');
  return response.data;
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
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.slice(6).trim();
          if (content === '[DONE]') {
            return;
          }
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