import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

// 나중에 만들 3개의 핵심 페이지 컴포넌트를 미리 임포트 (지금은 에러가 나도 정상입니다)
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen font-sans text-gray-900">
        <Routes>
          {/* 기본 주소(/)로 오면 Dashboard로 보냅니다 */}
          <Route path="/" element={<Navigate to="/dashboard" />} />
          
          {/* 우리가 앞으로 만들 3개의 핵심 페이지 주소입니다 */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App