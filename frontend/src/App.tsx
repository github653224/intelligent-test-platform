import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Requirements from './pages/Requirements';
import TestCases from './pages/TestCases';
import TestRuns from './pages/TestRuns';
import PerformanceTests from './pages/PerformanceTests';
import AIEngine from './pages/AIEngine';
import './App.css';

const AppContent: React.FC = () => {
  const { theme: themeMode } = useTheme();
  
  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        algorithm: themeMode === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <AntdApp>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/requirements" element={<Requirements />} />
              <Route path="/test-cases" element={<TestCases />} />
              <Route path="/test-runs" element={<TestRuns />} />
              <Route path="/performance-tests" element={<PerformanceTests />} />
              <Route path="/ai-engine" element={<AIEngine />} />
            </Routes>
          </Layout>
        </Router>
      </AntdApp>
    </ConfigProvider>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;