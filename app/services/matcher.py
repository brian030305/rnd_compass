import os
import requests
import pandas as pd
from app.services.gov_api import fetch_bizinfo_api

def process_and_match_announcements(user_region: str, user_keyword: str) -> dict:
    """
    [백엔드 자동화 로직]
    DB 데이터를 파이썬이 필터링하고, 발견 시 디스코드로 자동 알림을 쏩니다.
    """
    raw_df = fetch_bizinfo_api() 
    
    if raw_df is None or raw_df.empty:
        return {"status": "success", "matched_count": 0, "items": []}

    # 1. 실제 컬럼명을 사용한 정량 필터링
    region_cond = raw_df['AI_REGION'].str.contains(user_region, case=False, na=False) | \
              raw_df['jrsdInsttNm'].str.contains(user_region, case=False, na=False)

    keyword_cond = raw_df['AI_KEYWORD'].str.contains(user_keyword, case=False, na=False) | \
               raw_df['HASHTAGS'].str.contains(user_keyword, case=False, na=False)
    
    controlled_df = raw_df[region_cond & keyword_cond]

    # 2. 결과 가공
    matched_items = []
    for _, row in controlled_df.iterrows():
        matched_items.append({
            "title": row.get('pblancNm', '제목 없음'),
            "institution": row.get('excInsttNm', '기관 미상'),
            "period": row.get('reqstBeginEndDe', '기한 미정'),
            "ai_summary": row.get('ai_summary', 'AI 분석 대기중')
        })

    matched_count = len(matched_items)

    # 3. 디스코드 알림 발송 (이 부분이 핵심!)
    if matched_count > 0:
        send_discord_alert(matched_items, matched_count)

    return {
        "status": "success",
        "matched_count": matched_count,
        "items": matched_items
    }

def send_discord_alert(items, count):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url: return

    msg = f"🚨 **[창업나침반] 맞춤 공고 {count}건 발견!**\n\n"
    for item in items[:10]:
        msg += f"📌 **{item['title']}**\n   🏢 {item['institution']}\n   🤖 {item['ai_summary'][:50]}...\n\n"
    
    requests.post(webhook_url, json={"content": msg, "username": "창업나침반 AI"})
