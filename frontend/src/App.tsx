import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Requirements from './pages/Requirements';
import TestCases from './pages/TestCases';
import TestRuns from './pages/TestRuns';
import AIEngine from './pages/AIEngine';
import './App.css';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/requirements" element={<Requirements />} />
            <Route path="/test-cases" element={<TestCases />} />
            <Route path="/test-runs" element={<TestRuns />} />
            <Route path="/ai-engine" element={<AIEngine />} />
          </Routes>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App;