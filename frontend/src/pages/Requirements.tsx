import React, { useState } from 'react';
import { Card, Input, Button, message } from 'antd';
import { analyzeRequirementStream } from '../services/aiService';

const Requirements: React.FC = () => {
  const [requirement, setRequirement] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    if (!requirement.trim()) {
      message.warning('请输入需求描述');
      return;
    }
    setLoading(true);
    setAnalysis('');
    try {
      await analyzeRequirementStream(
        { requirement_text: requirement },
        (chunk) => {
          setAnalysis(prev => prev + chunk);
        }
      );
    } catch (error) {
      message.error('分析失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="需求分析">
      <Input.TextArea
        rows={4}
        value={requirement}
        onChange={(e) => setRequirement(e.target.value)}
        placeholder="请输入需求描述"
      />
      <Button
        type="primary"
        onClick={handleAnalyze}
        loading={loading}
        style={{ marginTop: 16 }}
      >
        开始分析
      </Button>
      <div
        style={{
          marginTop: 16,
          whiteSpace: 'pre-wrap',
          minHeight: 200,
          padding: 16,
          border: '1px solid #d9d9d9',
          borderRadius: 4,
          background: '#fafafa'
        }}
      >
        {analysis || 'AI输出结果将在这里实时显示...'}
      </div>
    </Card>
  );
};

export default Requirements;