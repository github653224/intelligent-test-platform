import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// 检查 App.tsx 文件名是否正确（必须为 App.tsx，注意大小写），且与 index.tsx 在同一目录。
// 如果你之前创建的是 app.tsx 或 APP.tsx，请重命名为 App.tsx。