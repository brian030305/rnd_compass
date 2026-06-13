import os
import sys
import base64
import zipfile
import oracledb
from app.services.ai_agent import call_school_llm

# 1. 환경 변수 세팅 (final_bot.py와 동일하게 맞춤)
DB_USER = os.getenv("ORACLE_USER")
DB_PASS = os.getenv("ORACLE_PASSWORD")
DB_DSN  = os.getenv("ORACLE_DSN")
WALLET_PASS = os.getenv("WALLET_PASSWORD")
WALLET_B64  = os.getenv("WALLET_BASE64")

if not all([DB_USER, DB_PASS, DB_DSN, WALLET_PASS, WALLET_B64]):
    print("❌ 치명적 에러: 환경 변수(Secrets)가 누락되었습니다.")
    sys.exit(1)

# 2. 보안 지갑(Wallet) 파일 복원 세팅
os.makedirs("./bot_wallet", exist_ok=True)
try:
    with open("bot_wallet.zip", "wb") as f:
        f.write(base64.b64decode(WALLET_B64))
    with zipfile.ZipFile("bot_wallet.zip", 'r') as zip_ref:
        zip_ref.extractall("./bot_wallet")
except Exception as e:
    print(f"❌ 지갑 파일 복원 실패: {e}")
    sys.exit(1)

def generate_tags(title, content):
    """AI를 이용해 지역과 키워드만 정밀하게 추출"""
    system_instruction = """
    당신은 지원사업 공고의 핵심 키워드를 추출하는 데이터 전처리 로직입니다.
    사용자가 공고 제목과 내용을 주면, 반드시 아래 2가지 항목만 추출하여 양식에 맞춰 대답하세요.
    
    [양식]
    지역: (서울, 부산, 전국 등. 해당 없으면 '전국')
    키워드: (IT, SW, 제조업, 청년 등 핵심 키워드 최대 3개, 쉼표로 구분)
    """
    prompt = f"다음 공고에서 지역과 키워드를 추출해.\n제목: {title}\n내용: {content[:300]}"
    
    try:
        reply = call_school_llm(prompt=prompt, model_type="claude", system_prompt=system_instruction)
        
        region, keyword = "전국", "일반"
        for line in reply.split('\n'):
            line = line.strip()
            if line.startswith("지역:"): region = line.replace("지역:", "").strip()
            elif line.startswith("키워드:"): keyword = line.replace("키워드:", "").strip()
            
        return region, keyword
    except Exception as e:
        print(f"AI 처리 에러: {e}")
        return "에러", "에러"

def run_migration():
    print("🚀 기존 공고 데이터 AI 태그 자동 채우기 시작...")
    
    try:
        # 3. oracledb를 이용한 안전한 지갑 접속
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASS,
            dsn=DB_DSN,
            wallet_location="./bot_wallet",
            wallet_password=WALLET_PASS
        )
        cursor = connection.cursor()
        
        # DB 업데이트
            cursor.execute("""
                UPDATE "bizinfo_tb" 
                SET AI_REGION = :1, AI_KEYWORD = :2 
                WHERE "pblancId" = :3
            """, (region, keyword, pblanc_id))
        
        rows = cursor.fetchall()
        print(f"📌 총 {len(rows)}개의 빈칸 공고에 태그를 채웁니다.")
        
        for row in rows:
            pblanc_id, title, content = row
            content_safe = content if content else "내용 없음"
            
            print(f"분석 중: {title[:20]}...")
            region, keyword = generate_tags(title, content_safe)
            
            # DB 업데이트
            cursor.execute("""
                UPDATE bizinfo_tb 
                SET AI_REGION = :1, AI_KEYWORD = :2 
                WHERE pblancId = :3
            """, (region, keyword, pblanc_id))
            
            connection.commit()
            print(f"  👉 완료 | 지역: {region} | 키워드: {keyword}")
            
        print("✅ 모든 마이그레이션이 성공적으로 끝났습니다!")
        
    except Exception as e:
        print(f"❌ DB 작업 중 에러 발생: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

if __name__ == "__main__":
    run_migration()
