from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from datetime import datetime
from app.core.database import get_oracle_engine

router = APIRouter()

@router.get("/dashboard-matches")
def get_dashboard_matches(
    location: str = Query(default="전국", description="유저 소재지"),
    industry: str = Query(default="업종무관(전분야)", description="유저 업종"),
    tech: str = Query(default="", description="유저 핵심 기술")
):
    try:
        engine = get_oracle_engine()
        
        # 🚨 오라클 대소문자 충돌을 원천 차단하기 위해 쿼리문에서 개별 컬럼 명시를 없애고 전체(*)를 가져옵니다.
        query = "SELECT * FROM bizinfo_tb"
        df = pd.read_sql(query, engine)
        
        if df.empty:
            return {"match_count": 0, "urgent_count": 0, "data": []}

        # ⭐ 핵심 해결책: 판다스가 가진 모든 컬럼명을 강제로 소문자로 통일합니다. (KeyError 방지)
        df.columns = [col.lower() for col in df.columns]
        

        # 1. 지역(Location) 필터링
        if location != "전국":
            df = df[df['ai_region'].str.contains('전국', na=False) | df['ai_region'].str.contains(location, na=False)]

        # 2. 업종(Industry) 필터링 (숲을 보는 완벽한 필터링)
        if industry != "선택해주세요" and industry != "" and industry != "업종무관(전분야)":
            keywords = industry.split('/')
            search_pattern = '|'.join(keywords)
            df = df[
                df['ai_keyword'].str.contains(search_pattern, na=False, regex=True) | 
                df['ai_keyword'].str.contains('업종무관', na=False)
            ]

        match_count = len(df)
        urgent_count = 0
        today = datetime.now().date()
        processed_data = []

        # 3. 마감일 계산 및 데이터 정제
        for _, row in df.iterrows():
            # ⭐ 진짜 컬럼명 적용: 통합된 날짜 텍스트를 가져옵니다. (예: "2026.06.01 ~ 2026.06.15")
            reqst_period = str(row.get('reqstbeginendde', '')).strip()
            
            days_left = None
            is_urgent = False
            
            # 프론트엔드에 그대로 보여줄 기간 텍스트
            period_text = reqst_period if reqst_period else "상시 접수 (공고 원문 확인 요망)"
            
            # D-Day 계산을 위해 '~' 기호 뒤에 있는 마감일 부분만 추출합니다.
            end_date_str = ""
            if '~' in reqst_period:
                end_date_str = reqst_period.split('~')[-1].strip() # ~ 기준 뒤쪽 텍스트
            else:
                end_date_str = reqst_period
            
            # 🟢 지저분한 날짜 포맷 정규화 (YYYY-MM-DD 형태로 변환)
            clean_end = end_date_str[:10].replace('.', '-').replace('/', '-')
            if len(clean_end) == 8 and clean_end.isdigit(): # 20260615 형태
                clean_end = f"{clean_end[:4]}-{clean_end[4:6]}-{clean_end[6:]}"
            
            try:
                if len(clean_end) == 10:
                    end_date_obj = datetime.strptime(clean_end, "%Y-%m-%d").date()
                    days_left = (end_date_obj - today).days
                    if 0 <= days_left <= 7:
                        urgent_count += 1
                        is_urgent = True
            except:
                pass 

            # 🟢 관할 기관명 처리
            agency = str(row.get('pancinsttnm', '')).strip()
            if not agency or agency == "nan":
                agency = str(row.get('jrsdinsttnm', '')).strip()

            raw_summary = str(row.get('ai_summary', '')).strip()
            raw_reason = str(row.get('ai_reason', '')).strip()
            
            if raw_summary.lower() == 'nan': raw_summary = ""
            if raw_reason.lower() == 'nan': raw_reason = ""

            processed_data.append({
                "title": str(row.get('pblancnm', '')),
                "url": str(row.get('pblancurl', '')),
                "agency": agency if agency and agency != "nan" else "관할 기관 미표기",
                "period": period_text,  
                "d_day": days_left if days_left is not None else "상시/미정",
                "is_urgent": is_urgent,
                # ⭐ 세탁된 변수를 넣어주면 빈칸일 때 우측의 기본 문구가 출력됩니다.
                "ai_summary": raw_summary if raw_summary else "🤖 AI가 공고 요약을 준비 중입니다.",
                "ai_reason": raw_reason if raw_reason else "추후 분석 결과가 업데이트될 예정입니다."
            })

        # 마감일 임박 순 정렬 
        processed_data.sort(key=lambda x: (x['d_day'] == "상시/미정", x['d_day'] if isinstance(x['d_day'], int) else 9999))

        return {
            "status": "success",
            "match_count": match_count,
            "urgent_count": urgent_count,
            "data": processed_data
        }

    except Exception as e:
        # 🚨 만약 또 에러가 발생하더라도, 이번에는 터미널에 정확한 이유가 빨간색 로그로 찍히도록 안전장치를 추가했습니다.
        print(f"🔥 대시보드 에러 상세 로그: {str(e)}")
        raise HTTPException(status_code=500, detail=f"공고 데이터 로드 실패: {str(e)}")