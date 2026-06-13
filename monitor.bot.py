import os
import datetime
import shutil
import requests
from dotenv import load_dotenv

# 1. 환경변수 및 절대 경로 세팅
ENV_PATH = "/home/ubuntu/compass_2/.env"
LOG_FILE_PATH = "/home/ubuntu/compass_2/cron_bot.log"

load_dotenv(ENV_PATH)
discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

def send_alert_webhook(urgent_reasons, disk_percent, new_count, error_count, error_rate, is_weekday):
    if not discord_webhook_url:
        return
        
    msg = (
        f"🚨 **[긴급 시스템 경고] 상위 봇 판단 결과: 비상 상황 감지**\n\n"
        f"**[조치 필요 사유]**\n"
        + "\n".join([f"- {r}" for r in urgent_reasons]) + "\n\n"
        f"📌 **현재 시스템 상태 데이터**\n"
        f"- 디스크 점유율: {disk_percent:.1f}%\n"
        f"- 금일 수집 대상: {new_count}건\n"
        f"- 발생한 에러: {error_count}건 (에러율 {error_rate:.1f}%)\n"
        f"- 요일 판정: {'평일(수집 활성기)' if is_weekday else '주말/공휴일(수집 휴지기)'}"
    )
    
    try:
        requests.post(discord_webhook_url, json={"content": msg}, timeout=10)
    except Exception as e:
        print(f"웹훅 전송 실패: {e}")

def check_disk_usage():
    total, used, free = shutil.disk_usage("/")
    return (used / total) * 100

def analyze_logs():
    if not os.path.exists(LOG_FILE_PATH):
        return 0, 0, 0

    new_count = 0
    error_count = 0
    total_count = 0

    with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
        # 마지막으로 봇이 가동된 시점([시스템 시작]) 이후의 로그만 추출하여 오늘자 결과만 분석
        last_run_idx = 0
        for i, line in enumerate(lines):
            if "[시스템 시작]" in line:
                last_run_idx = i
        
        recent_lines = lines[last_run_idx:]
        
        for line in recent_lines:
            if "신규 공고:" in line and "건 발견" in line:
                try:
                    new_count = int(line.split("신규 공고:")[1].split("건")[0].strip())
                except:
                    pass
            if "[AI 분석 중]" in line:
                total_count += 1
            if "🚨" in line or "❌" in line or "⚠️ 개별 공고 Gemini 분석 실패" in line:
                error_count += 1

    return new_count, error_count, total_count

def main():
    print("🔎 상위 봇: 하위 시스템 점검 및 의사결정 프로세스 가동 중...")
    
    # 지표 1: 디스크 사용량 점검
    disk_usage_percent = check_disk_usage()
    
    # 지표 2 & 3: 최신 로그 기반 수집 건수 및 통신 에러율 도출
    new_count, error_count, total_count = analyze_logs()
    
    error_rate = 0.0
    if total_count > 0:
        error_rate = (error_count / total_count) * 100
        
    # 지표 4: 요일 확인 (0: 월요일 ~ 4: 금요일)
    today = datetime.datetime.today()
    is_weekday = today.weekday() < 5
    
    # 상위 봇 의사결정 (Rule Set)
    urgent_reasons = []

    if disk_usage_percent >= 85.0:
        urgent_reasons.append(f"서버 디스크 사용량 임계치 도달 ({disk_usage_percent:.1f}%)")
        
    if error_rate >= 10.0:
        urgent_reasons.append(f"AI 통신 에러율 기준 초과 ({error_rate:.1f}% - 총 {total_count}건 중 {error_count}건 실패)")
        
    if is_weekday and new_count == 0:
        urgent_reasons.append("평일임에도 신규 수집 공고가 0건입니다. (API 구조 변경 또는 벤더사 점검 의심)")

    # 판단 결과에 따른 분기 처리
    if urgent_reasons:
        print("⚠️ 비상 상황 감지됨. 관리자 직보 라인으로 알림을 송출합니다.")
        send_alert_webhook(urgent_reasons, disk_usage_percent, new_count, error_count, error_rate, is_weekday)
    else:
        print("✅ 모든 지표 정상 범위 내 확인. 관리자 알림을 생략하고 자체 종결합니다 (무소식이 희소식).")

if __name__ == "__main__":
    main()