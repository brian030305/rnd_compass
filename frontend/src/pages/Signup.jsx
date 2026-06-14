import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function Signup() {
  const [formData, setFormData] = useState({
    user_id: '',
    password: '',
    company_name: '',
    location: '전국',
    industry: '업종무관(전분야)',
    tech_field: '',
    job_role: '' 
  });
  
  // ⭐ 화면 통째 전환 대신, 모달창(팝업)을 띄우기 위한 상태로 변경했습니다.
  const [isDiscordModalOpen, setIsDiscordModalOpen] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // 전국 17개 시/도 리스트
  const locations = [
    '전국', '서울', '경기', '인천', '강원', '충북', '충남', '대전', '세종', 
    '전북', '전남', '광주', '경북', '경남', '대구', '부산', '울산', '제주'
  ];

  // 세분화된 업종 리스트
  const industries = [
    '업종무관(전분야)', '정보통신/IT', '제조/하드웨어', '바이오/의료', 
    '지식서비스/컨설팅', '도소매/유통', '환경/에너지', '문화/콘텐츠', '기타'
  ];

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await axios.post('http://127.0.0.1:8000/api/auth/signup', formData);
      // ⭐ 가입 성공 시 페이지 이동 대신 모달창을 엽니다.
      setIsDiscordModalOpen(true);
    } catch (err) {
      const errMsg = err.response?.data?.detail;
      setError(typeof errMsg === 'string' ? errMsg : '회원가입에 실패했습니다. (백엔드 항목 불일치 또는 중복 아이디)');
    }
  };

  const handleDiscordConnect = () => {
    const discordAuthUrl = `https://discord.com/api/oauth2/authorize?client_id=1514932083435376731ID&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fapi%2Fauth%2Fdiscord%2Fcallback&response_type=code&scope=identify&state=${formData.user_id}`;
    window.location.href = discordAuthUrl;
  };

  return (
    // ⭐ relative 속성을 추가하여 모달이 폼 위에 정확히 뜨도록 설정했습니다.
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8 relative">
      <div className="w-full max-w-md space-y-6 bg-white p-8 rounded-xl shadow-lg">
        <div>
          <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900">기업 회원가입</h2>
        </div>
        <form className="mt-6 space-y-4" onSubmit={handleSignup}>
          {error && (
            <div className="text-red-500 text-sm text-center bg-red-50 p-2 rounded border border-red-200">
              {error}
            </div>
          )}
          
          <div className="space-y-3">
            <input type="text" required className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm" placeholder="아이디" onChange={(e) => setFormData({ ...formData, user_id: e.target.value })} />
            <input type="password" required className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm" placeholder="비밀번호" onChange={(e) => setFormData({ ...formData, password: e.target.value })} />
            <input type="text" required className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm" placeholder="기업명" onChange={(e) => setFormData({ ...formData, company_name: e.target.value })} />
            
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">소재지 선택</label>
              <select className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm bg-white" onChange={(e) => setFormData({ ...formData, location: e.target.value })}>
                {locations.map(loc => <option key={loc} value={loc}>{loc}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">주요 업종 선택</label>
              <select className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm bg-white" onChange={(e) => setFormData({ ...formData, industry: e.target.value })}>
                {industries.map(ind => <option key={ind} value={ind}>{ind}</option>)}
              </select>
            </div>

            <input type="text" className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm" placeholder="핵심 기술 키워드 (예: AI, 블록체인)" onChange={(e) => setFormData({ ...formData, tech_field: e.target.value })} />
            
            <input type="text" className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm" placeholder="본인의 직무/직책 (예: 기획자, 엔지니어, 대표)" onChange={(e) => setFormData({ ...formData, job_role: e.target.value })} />
          </div>

          <div className="pt-2">
            <button type="submit" className="flex w-full justify-center rounded-md bg-blue-600 py-2.5 px-3 text-sm font-semibold text-white hover:bg-blue-500 transition-colors">
              가입하기
            </button>
          </div>
        </form>
      </div>

      {/* ⭐ 회원가입 성공 시 띄우는 팝업(모달) UI 입니다. */}
      {isDiscordModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-sm text-center">
            <div className="text-4xl mb-4">🎉</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">회원가입 완료!</h2>
            <p className="text-sm text-gray-600 mb-6">
              디스코드 봇을 연동하시면 조건에 맞는<br/>새로운 지원사업 공고 알림을 받을 수 있습니다.
            </p>
            <div className="flex flex-col gap-3">
              <button onClick={handleDiscordConnect} className="w-full py-2.5 bg-[#5865F2] text-white font-bold rounded-md hover:bg-[#4752C4] transition flex justify-center items-center gap-2">
                <svg className="w-5 h-5 fill-current" viewBox="0 0 127.14 96.36"><path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1,105.25,105.25,0,0,0,32.19-16.14c2.64-27.38-4.51-51.11-19.32-72.1M42.63,65.22c-5.36,0-9.8-4.9-9.8-10.92s4.35-10.94,9.8-10.94,9.86,4.92,9.8,10.94S48.06,65.22,42.63,65.22Zm41.88,0c-5.36,0-9.8-4.9-9.8-10.92s4.35-10.94,9.8-10.94,9.86,4.92,9.8,10.94S89.92,65.22,84.51,65.22Z"/></svg>
                지금 연동하기
              </button>
              <button onClick={() => navigate('/login')} className="w-full py-2.5 bg-gray-100 text-gray-700 font-medium rounded-md hover:bg-gray-200 transition">
                나중에 연동하고 로그인하러 가기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}