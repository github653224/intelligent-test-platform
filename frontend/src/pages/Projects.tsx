import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

const Projects: React.FC = () => {
  return (
    <div>
      <Title level={2}>项目管理</Title>
      <Card>
        <p>项目管理功能开发中...</p>
      </Card>
    </div>
  );
};

export default Projects; 