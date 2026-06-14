import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css' /* ⭐ 이 줄이 반드시 있어야 전체 화면에 디자인이 입혀집니다! */

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)