import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

const TestRuns: React.FC = () => {
  return (
    <div>
      <Title level={2}>测试执行</Title>
      <Card>
        <p>测试执行功能开发中...</p>
      </Card>
    </div>
  );
};

export default TestRuns; 