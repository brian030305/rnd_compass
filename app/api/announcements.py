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
        
        # 워커 봇이 적재한 오라클 DB의 공고 데이터를 불러옵니다.
        # AI가 1차적으로 통과(O)시키고 추천(Y)한 데이터만 1차 필터링하여 가져옵니다.
        query = """
            SELECT "pblancNm", "pblancUrl", "reqstBeginDe", "reqstEndDe", "pancInsttNm",
                   ai_region, ai_keyword, ai_summary, ai_reason, ai_target_hint
            FROM bizinfo_tb 
            WHERE ai_pass_yn = 'O' AND ai_recommend_yn = 'Y'
        """
        df = pd.read_sql(query, engine)
        
        if df.empty:
            return {"match_count": 0, "urgent_count": 0, "data": []}

        # 1. 지역(Location) 필터링
        if location != "전국":
            # 공고 지역이 '전국'이거나, 유저의 지역과 일치하는 것만 남김
            df = df[df['ai_region'].str.contains('전국') | df['ai_region'].str.contains(location, na=False)]

        # 2. 업종(Industry) 및 기술(Tech) 필터링
        if industry != "선택해주세요" and industry != "":
            # 공고 키워드에 유저의 업종이 포함되어 있거나, '업종무관(전분야)'인 것만 남김
            df = df[df['ai_keyword'].str.contains(industry, na=False) | df['ai_keyword'].str.contains('업종무관', na=False)]

        match_count = len(df)
        urgent_count = 0
        today = datetime.now().date()
        processed_data = []

        # 3. 마감일 계산 및 데이터 정제
        for _, row in df.iterrows():
            end_date_str = str(row.get('reqstEndDe', ''))
            days_left = None
            is_urgent = False
            
            # 날짜 형식 파싱 시도
            try:
                if len(end_date_str) >= 10:
                    end_date_obj = datetime.strptime(end_date_str[:10], "%Y-%m-%d").date()
                    days_left = (end_date_obj - today).days
                    if 0 <= days_left <= 7:
                        urgent_count += 1
                        is_urgent = True
            except:
                pass # 날짜 형식이 이상한 상시 공고 등은 패스

            processed_data.append({
                "title": str(row.get('pblancNm', '')),
                "url": str(row.get('pblancUrl', '')),
                "agency": str(row.get('pancInsttNm', '관할 기관')),
                "start_date": str(row.get('reqstBeginDe', '')),
                "end_date": end_date_str,
                "d_day": days_left if days_left is not None else "상시/미정",
                "is_urgent": is_urgent,
                "ai_summary": str(row.get('ai_summary', '')),
                "ai_reason": str(row.get('ai_reason', '')),
                "ai_target": str(row.get('ai_target_hint', ''))
            })

        # 마감일이 임박한 순(D-Day 기준)으로 정렬 (None 값은 뒤로)
        processed_data.sort(key=lambda x: (x['d_day'] is "상시/미정", x['d_day'] if isinstance(x['d_day'], int) else 9999))

        return {
            "status": "success",
            "match_count": match_count,
            "urgent_count": urgent_count,
            "data": processed_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공고 데이터 로드 실패: {str(e)}")