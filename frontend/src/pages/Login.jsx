import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const [formData, setFormData] = useState({ user_id: '', password: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      // 백엔드 로그인 API 호출
      const res = await axios.post('http://127.0.0.1:8000/api/auth/login', formData);
      
      // 발급받은 JWT 토큰을 브라우저에 저장
      localStorage.setItem('token', res.data.access_token);
      
      // 로그인 성공 시 대시보드로 이동
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다. 아이디와 비밀번호를 확인하세요.');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 bg-white p-8 rounded-xl shadow-lg">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            창업나침반 로그인
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleLogin}>
          {error && (
            <div className="text-red-500 text-sm text-center bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <label className="sr-only">아이디</label>
              <input
                type="text"
                required
                className="relative block w-full rounded-md border-0 py-2.5 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:z-10 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm"
                placeholder="아이디를 입력하세요"
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
              />
            </div>
            <div>
              <label className="sr-only">비밀번호</label>
              <input
                type="password"
                required
                className="relative block w-full rounded-md border-0 py-2.5 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:z-10 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm"
                placeholder="비밀번호를 입력하세요"
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              className="group relative flex w-full justify-center rounded-md bg-blue-600 py-2.5 px-3 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
            >
              로그인
            </button>
          </div>
        </form>
        
        <div className="text-center">
          <button
            onClick={() => navigate('/signup')}
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            아직 계정이 없으신가요? 회원가입하기
          </button>
        </div>
      </div>
    </div>
  );
}