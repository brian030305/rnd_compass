import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const [announcements, setAnnouncements] = useState([]);
  const [stats, setStats] = useState({ match_count: 0, urgent_count: 0 });
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // 회원정보 수정 모달 상태 관리
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editFormData, setEditFormData] = useState({});
  
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        window.atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join('')
      );
      const decodedUser = JSON.parse(jsonPayload);
      setUserInfo(decodedUser);
      setEditFormData(decodedUser); // 수정 폼 초기값 세팅

      fetchDashboardData(decodedUser);
    } catch (error) {
      navigate('/login');
    }
  }, [navigate]);

  const fetchDashboardData = async (user) => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/announcements/dashboard-matches', {
        params: { location: user.location, industry: user.industry, tech: user.tech || '' }
      });
      if (res.data.status === 'success') {
        setAnnouncements(res.data.data);
        setStats({ match_count: res.data.match_count, urgent_count: res.data.urgent_count });
      }
    } catch (error) {
      console.error('데이터 로딩 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  // 회원정보 수정 제출 함수
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    // TODO: 백엔드에 회원정보 수정 API(PUT 요청) 연결 필요
    alert('회원정보가 성공적으로 수정되었습니다! (백엔드 API 연결 후 최종 반영됩니다.)');
    setUserInfo(editFormData);
    setIsEditModalOpen(false);
    // 정보가 바뀌었으니 데이터 다시 불러오기
    setLoading(true);
    fetchDashboardData(editFormData);
  };

  if (loading) return <div className="flex h-screen items-center justify-center text-gray-600">데이터를 불러오는 중입니다...</div>;

  return (
    <div className="min-h-screen bg-gray-50 font-sans relative">
      
      {/* --- 상단 네비게이션 바 --- */}
      <nav className="bg-white shadow-sm px-6 py-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-700">창업나침반 AI</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-700 font-medium">
            {userInfo?.company} ({userInfo?.user_id})님 환영합니다
          </span>
          {/* ⭐ 회원정보 수정 버튼 추가 */}
          <button 
            onClick={() => setIsEditModalOpen(true)}
            className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition"
          >
            회원정보 수정
          </button>
          <button onClick={handleLogout} className="px-4 py-2 text-sm font-medium text-white bg-gray-800 rounded-md hover:bg-gray-700 transition">
            로그아웃
          </button>
        </div>
      </nav>

      {/* --- 회원정보 수정 모달창 --- */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-md">
            <h2 className="text-xl font-bold mb-6 text-gray-900">회원정보 수정</h2>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">소재지</label>
                <select 
                  className="w-full rounded-md border py-2 px-3 focus:ring-2 focus:ring-blue-600"
                  value={editFormData.location}
                  onChange={(e) => setEditFormData({...editFormData, location: e.target.value})}
                >
                  <option value="전국">전국</option>
                  <option value="서울">서울</option>
                  <option value="부산">부산</option>
                  <option value="대구">대구</option>
                  <option value="인천">인천</option>
                  <option value="광주">광주</option>
                  <option value="대전">대전</option>
                  <option value="울산">울산</option>
                  <option value="세종">세종</option>
                  <option value="경기">경기</option>
                  <option value="강원">강원</option>
                  <option value="충북">충북</option>
                  <option value="충남">충남</option>
                  <option value="전북">전북</option>
                  <option value="전남">전남</option>
                  <option value="경북">경북</option>
                  <option value="경남">경남</option>
                  <option value="제주">제주</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">업종</label>
                <select 
                  className="w-full rounded-md border py-2 px-3 focus:ring-2 focus:ring-blue-600"
                  value={editFormData.industry}
                  onChange={(e) => setEditFormData({...editFormData, industry: e.target.value})}
                >
                  <option value="업종무관(전분야)">업종무관(전분야)</option>
                  <option value="정보통신/IT">정보통신/IT</option>
                  <option value="제조/하드웨어">제조/하드웨어</option>
                  <option value="바이오/의료">바이오/의료</option>
                  <option value="도소매/유통">도소매/유통</option>
                  <option value="서비스/플랫폼">서비스/플랫폼</option>
                  <option value="교육/에듀테크">교육/에듀테크</option>
                  <option value="문화/콘텐츠">문화/콘텐츠</option>
                  <option value="환경/에너지">환경/에너지</option>
                  <option value="농식품/푸드테크">농식품/푸드테크</option>
                  <option value="금융/핀테크">금융/핀테크</option>
                  <option value="기타">기타</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">핵심 기술 키워드</label>
                <input 
                  type="text" 
                  className="w-full rounded-md border py-2 px-3 focus:ring-2 focus:ring-blue-600"
                  value={editFormData.tech || ''}
                  onChange={(e) => setEditFormData({...editFormData, tech: e.target.value})}
                  placeholder="예: AI, 빅데이터, 블록체인 등"
                />
              </div>
              {/* ⭐ 1. 비밀번호 변경 영역 추가 */}
              <div className="border-t border-gray-100 pt-4 mt-2">
                <label className="block text-xs font-semibold text-gray-600 mb-1">새 비밀번호 (변경 시에만 입력)</label>
                <input 
                  type="password" 
                  className="w-full rounded-md border py-2 px-3 focus:ring-2 focus:ring-blue-600 mb-2"
                  value={editFormData.newPassword || ''}
                  onChange={(e) => setEditFormData({...editFormData, newPassword: e.target.value})}
                  placeholder="변경할 비밀번호 입력"
                />
              </div>

              {/* ⭐ 2. 디스코드 연동 버튼 영역 추가 */}
              <div className="border-t border-gray-100 pt-4">
                <label className="block text-xs font-semibold text-gray-600 mb-2">알림 설정</label>
                <button 
                  type="button" 
                  onClick={() => {
                    const discordAuthUrl = `https://discord.com/api/oauth2/authorize?client_id=1514932083435376731&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fapi%2Fauth%2Fdiscord%2Fcallback&response_type=code&scope=identify&state=${userInfo?.user_id}`;
                    window.location.href = discordAuthUrl;
                  }}
                  className="w-full py-2 bg-[#5865F2] text-white font-medium rounded-md hover:bg-[#4752C4] flex items-center justify-center gap-2 transition"
                >
                  <svg className="w-5 h-5 fill-current" viewBox="0 0 127.14 96.36">
                    <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1,105.25,105.25,0,0,0,32.19-16.14c2.64-27.38-4.51-51.11-19.32-72.1M42.63,65.22c-5.36,0-9.8-4.9-9.8-10.92s4.35-10.94,9.8-10.94,9.86,4.92,9.8,10.94S48.06,65.22,42.63,65.22Zm41.88,0c-5.36,0-9.8-4.9-9.8-10.92s4.35-10.94,9.8-10.94,9.86,4.92,9.8,10.94S89.92,65.22,84.51,65.22Z"/>
                  </svg>
                  디스코드 봇 연동하기
                </button>
              </div>

              {/* --- 기존 취소 및 저장 버튼 코드 --- */}
              <div className="flex gap-3 pt-6">
                <button type="button" onClick={() => setIsEditModalOpen(false)} className="w-1/2 py-2 bg-gray-100 text-gray-700 rounded-md font-medium hover:bg-gray-200">
                  취소
                </button>
                <button type="submit" className="w-1/2 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700">
                  저장 및 다시 검색
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- 메인 콘텐츠 (기존과 동일) --- */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div><p className="text-sm text-gray-500 font-medium mb-1">AI 맞춤 추천 공고</p><p className="text-3xl font-bold text-gray-900">{stats.match_count}건</p></div>
            <div className="p-4 bg-blue-50 rounded-full text-blue-600">📊</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div><p className="text-sm text-gray-500 font-medium mb-1">마감 임박 (D-7 이내)</p><p className="text-3xl font-bold text-red-600">{stats.urgent_count}건</p></div>
            <div className="p-4 bg-red-50 rounded-full text-red-600">⏰</div>
          </div>
        </div>

        <h2 className="text-xl font-bold text-gray-800 mb-4">추천 지원사업 목록</h2>
        
        {announcements.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl shadow-sm border border-gray-100">
            <p className="text-gray-500">현재 조건에 맞는 추천 공고가 없습니다.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {announcements.map((item, index) => (
              <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col justify-between hover:shadow-md transition">
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-xs font-semibold px-2.5 py-1 bg-gray-100 text-gray-600 rounded-md">{item.agency}</span>
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-md ${item.is_urgent ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                      {item.d_day === '상시/미정' ? item.d_day : `D-${item.d_day}`}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2 line-clamp-2">{item.title}</h3>
                  <p className="text-sm font-medium text-gray-700 mb-3 bg-gray-50 inline-block px-2 py-1 rounded">
                    📅 접수 기간 : {item.period}
                  </p>
                  <div className="mt-4 bg-blue-50/50 p-4 rounded-lg border border-blue-100/50">
                    <p className="text-sm font-semibold text-blue-800 mb-1">🤖 AI 핵심 요약</p>
                    <p className="text-sm text-gray-700 mb-2">{item.ai_summary}</p>
                    <p className="text-xs text-gray-500"><span className="font-semibold text-gray-600">추천 사유:</span> {item.ai_reason}</p>
                  </div>
                </div>
                <div className="mt-6 pt-4 border-t border-gray-100">
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="block w-full text-center py-2 bg-white border-2 border-blue-600 text-blue-600 font-semibold rounded-md hover:bg-blue-50 transition">
                    공고 원문 보기
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}