import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

const TestCases: React.FC = () => {
  return (
    <div>
      <Title level={2}>测试用例</Title>
      <Card>
        <p>测试用例管理功能开发中...</p>
      </Card>
    </div>
  );
};

export default TestCases; 