import os
import sys
import json
import base64
import zipfile
import requests
import pandas as pd
from sqlalchemy import create_engine, text
import oracledb
from bs4 import BeautifulSoup
import time
import re
from dotenv import load_dotenv
import platform

load_dotenv()

print("🧪 [테스트 시작] 기존 공고 재분석 + admin DM 전용 final_bot_test 가동...")

oracle_user = os.getenv("ORACLE_USER")
oracle_password = os.getenv("ORACLE_PASSWORD")
oracle_dsn = os.getenv("ORACLE_DSN")
wallet_password = os.getenv("WALLET_PASSWORD")
wallet_base64 = os.getenv("WALLET_BASE64")
school_api_key = os.getenv("SCHOOL_API_KEY")
discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
discord_bot_token = os.getenv("DISCORD_BOT_TOKEN")

IS_LOCAL = (platform.system() == "Windows")
TEST_LIMIT = 100
ADMIN_ONLY_ID = "admin"

if IS_LOCAL:
    required_envs = [oracle_user, oracle_password, oracle_dsn, school_api_key]
else:
    required_envs = [oracle_user, oracle_password, oracle_dsn, wallet_password, wallet_base64, school_api_key]

if not all(required_envs):
    print("❌ 에러: 환경변수 설정 중 누락된 항목이 존재합니다.")
    sys.exit(1)


def send_discord_webhook(message):
    if not discord_webhook_url:
        return
    try:
        requests.post(discord_webhook_url, json={"content": message}, timeout=10)
    except Exception:
        pass


def send_discord_dm(discord_id, message):
    if not discord_bot_token or not discord_id or str(discord_id) == 'None':
        return

    headers = {
        "Authorization": f"Bot {discord_bot_token}",
        "Content-Type": "application/json"
    }

    try:
        dm_channel_res = requests.post(
            "https://discord.com/api/v10/users/@me/channels",
            json={"recipient_id": str(discord_id)},
            headers=headers,
            timeout=10
        )
        if dm_channel_res.status_code == 200:
            channel_id = dm_channel_res.json().get("id")
            requests.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                json={"content": message},
                headers=headers,
                timeout=10
            )
    except Exception as e:
        print(f"⚠️ DM 발송 실패 (ID: {discord_id}): {e}")


if not IS_LOCAL:
    os.makedirs("./bot_wallet", exist_ok=True)
    try:
        with open("bot_wallet.zip", "wb") as f:
            f.write(base64.b64decode(wallet_base64))
        with zipfile.ZipFile("bot_wallet.zip", 'r') as zip_ref:
            zip_ref.extractall("./bot_wallet")
    except Exception as e:
        error_msg = f"❌ [지갑 복원 실패] 에러: {e}"
        send_discord_webhook(error_msg)
        sys.exit(1)


def get_oracle_connection():
    if IS_LOCAL:
        return oracledb.connect(
            user=oracle_user,
            password=oracle_password,
            dsn=oracle_dsn
        )
    else:
        return oracledb.connect(
            user=oracle_user,
            password=oracle_password,
            dsn=oracle_dsn,
            wallet_location="./bot_wallet",
            wallet_password=wallet_password
        )


def normalize_region(region_raw: str) -> str:
    if not region_raw:
        return "전국"
    region = str(region_raw).strip()
    if region in ["", "없음", "미상", "불명", "null", "None"]:
        return "전국"
    return region


def normalize_keywords(keywords_raw):
    standard_keywords = [
        "IT/소프트웨어",
        "제조/하드웨어",
        "바이오/의료/헬스케어",
        "디자인/콘텐츠",
        "도소매/유통/물류",
        "농축수산/식품/F&B",
        "친환경/에너지",
        "업종무관(전분야)"
    ]

    if isinstance(keywords_raw, list):
        raw_list = keywords_raw
    else:
        raw = str(keywords_raw or "")
        raw = raw.replace("키워드:", "").strip()
        raw_list = [x.strip() for x in raw.split(",") if x.strip()]

    normalized = []
    for item in raw_list:
        for std in standard_keywords:
            if item == std:
                normalized.append(std)

    normalized = list(dict.fromkeys(normalized))

    if not normalized:
        normalized = ["업종무관(전분야)"]

    return normalized


def normalize_user_industry(user_industry_raw: str) -> str:
    val = str(user_industry_raw or "").strip()

    mapping = {
        "IT": "IT/소프트웨어",
        "IT/소프트웨어": "IT/소프트웨어",
        "제조": "제조/하드웨어",
        "제조/하드웨어": "제조/하드웨어",
        "바이오": "바이오/의료/헬스케어",
        "바이오/의료/헬스케어": "바이오/의료/헬스케어",
        "디자인": "디자인/콘텐츠",
        "디자인/콘텐츠": "디자인/콘텐츠",
        "도소매": "도소매/유통/물류",
        "도소매/유통/물류": "도소매/유통/물류",
        "농축수산": "농축수산/식품/F&B",
        "농축수산/식품/F&B": "농축수산/식품/F&B",
        "친환경": "친환경/에너지",
        "친환경/에너지": "친환경/에너지",
        "업종무관": "업종무관(전분야)",
        "업종무관(전분야)": "업종무관(전분야)"
    }

    return mapping.get(val, val)


def is_fatal_ai_error(status_code: int, response_text: str) -> bool:
    text_lower = (response_text or "").lower()

    if status_code in [401, 403, 429]:
        return True

    fatal_keywords = [
        "quota",
        "credit",
        "insufficient",
        "exceeded",
        "unauthorized",
        "forbidden",
        "billing",
        "rate limit"
    ]
    return any(k in text_lower for k in fatal_keywords)


def call_gemini_analysis(core_text: str, api_key: str):
    gemini_url = "https://factchat-cloud.mindlogic.ai/v1/api/google/models/generate-content"

    prompt = f"""
당신은 정부지원사업 공고를 매우 보수적으로 판정하는 심사 보조 시스템입니다.

아래 공고 원문을 읽고 반드시 JSON 객체만 출력하세요.
설명 문장, 마크다운, 코드블록 없이 JSON만 반환하세요.

[중요 원칙]
- 애매하면 추천하지 마세요.
- 지원사업 성격이 불명확하면 X로 판단하세요.
- 단순 행사, 설명회, 교육, 모집공고, 홍보성 안내는 X
- 실제 자금, 사업화, R&D, 바우처, 실증, 창업지원 등 명확한 지원사업만 O
- 업종이나 대상 조건이 불명확하면 recommend_yn은 N
- "업종무관(전분야)"는 실제로 전 업종 대상 근거가 명확할 때만 허용

[판단 규칙]
1. pass_yn: 정상적인 지원사업이면 "O", 아니면 "X"
2. summary: 2~3문장, 180자 이내
3. region: 대표 지역 1개만. 전국이면 "전국"
4. keywords: 아래 표준 업종 리스트 중 해당 항목만 배열로 반환
5. reason: 왜 이렇게 판정했는지 1문장
6. evidence: 핵심 근거 표현 2~5개 배열
7. target_hint: 지원대상/자격조건 요약 1문장
8. recommend_yn:
   - 지원대상, 성격, 업종/지역 단서가 비교적 명확하면 "Y"
   - 애매하거나 과추천 위험이 있으면 "N"

표준 업종 리스트:
- IT/소프트웨어
- 제조/하드웨어
- 바이오/의료/헬스케어
- 디자인/콘텐츠
- 도소매/유통/물류
- 농축수산/식품/F&B
- 친환경/에너지
- 업종무관(전분야)

반환 예시:
{{
  "pass_yn": "O",
  "summary": "중소기업 대상 디지털 전환 및 사업화 지원 공고다. 지원 대상과 내용이 비교적 명확하다.",
  "region": "전국",
  "keywords": ["IT/소프트웨어"],
  "reason": "디지털 전환 및 소프트웨어 고도화 지원이 명시되어 있다.",
  "evidence": ["디지털 전환", "소프트웨어", "중소기업"],
  "target_hint": "중소기업 및 관련 창업기업 대상",
  "recommend_yn": "Y"
}}

공고 원문:
{core_text}
""".strip()

    payload = {
        "model": "gemini-2.5-flash",
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
        # 가능하면 temperature 제어 옵션이 지원될 때 추가 고려
        # "generationConfig": {"temperature": 0}
    }

    res = requests.post(
        gemini_url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=90
    )

    if res.status_code != 200:
        raise requests.HTTPError(f"Gemini API 오류 {res.status_code}: {res.text}", response=res)

    res_json = res.json()

    try:
        answer_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        raise ValueError(f"Gemini 응답 파싱 실패: {res_json}")

    answer_text = re.sub(r"^```json\s*", "", answer_text)
    answer_text = re.sub(r"^```", "", answer_text)
    answer_text = re.sub(r"\s*```$", "", answer_text).strip()

    try:
        parsed = json.loads(answer_text)
    except Exception:
        match = re.search(r"\{.*\}", answer_text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
        else:
            raise ValueError(f"JSON 파싱 실패. 원문 응답: {answer_text}")

    pass_yn = str(parsed.get("pass_yn", "X")).strip().upper()
    summary = str(parsed.get("summary", "")).strip()
    region = normalize_region(parsed.get("region", "전국"))
    keywords = normalize_keywords(parsed.get("keywords", []))
    reason = str(parsed.get("reason", "")).strip()
    target_hint = str(parsed.get("target_hint", "")).strip()
    recommend_yn = str(parsed.get("recommend_yn", "N")).strip().upper()

    evidence_raw = parsed.get("evidence", [])
    if isinstance(evidence_raw, list):
        evidence = [str(x).strip() for x in evidence_raw if str(x).strip()]
    else:
        evidence = [str(evidence_raw).strip()] if str(evidence_raw).strip() else []

    if pass_yn not in ["O", "X"]:
        pass_yn = "X"

    if recommend_yn not in ["Y", "N"]:
        recommend_yn = "N"

    if not summary:
        summary = "요약 없음"

    if not reason:
        reason = "판정 근거 없음"

    if not target_hint:
        target_hint = "지원대상 정보 불명확"

    return {
        "pass_yn": pass_yn,
        "summary": summary[:200],
        "region": region,
        "keywords": keywords,
        "reason": reason[:500],
        "evidence": evidence[:5],
        "target_hint": target_hint[:500],
        "recommend_yn": recommend_yn
    }


BLACKLIST_WORDS = r"농업|어업|수산|축산|귀농|귀촌|전통시장|소상공인|음식점|미용|학원|숙박|재해복구|초중고|예술인"

engine = create_engine('oracle+oracledb://', creator=get_oracle_connection)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
})

new_data_list = []
success_count = 0
filtered_count = 0
fatal_ai_stop = False

try:
    print(f"1️⃣ 기존 공고 {TEST_LIMIT}건 조회 중...")
    test_df = pd.read_sql(f"""
        SELECT "pblancId", "pblancNm", "pblancUrl"
        FROM bizinfo_tb
        WHERE "pblancUrl" IS NOT NULL
        FETCH FIRST {TEST_LIMIT} ROWS ONLY
    """, engine)


    print(f"✔️ 테스트 대상 공고: {len(test_df)}건")

    for _, db_row in test_df.iterrows():
        pid = str(db_row['pblancId'])
        title = str(db_row['pblancNm'])
        pblanc_url = str(db_row['pblancUrl'])

        if not pblanc_url.startswith("http"):
            continue

        print(f"🔍 [재분석 중] {title[:40]}")

        row = {
            'pblancId': pid,
            'pblancNm': title,
            'pblancUrl': pblanc_url,
            'ai_pass_yn': '미검증',
            'ai_summary': '대기중',
            'ai_region': '전국',
            'ai_keyword': '업종무관(전분야)',
            'ai_reason': '',
            'ai_evidence': '',
            'ai_target_hint': '',
            'ai_recommend_yn': 'N'
        }

        if re.search(BLACKLIST_WORDS, title):
            row['ai_pass_yn'] = "X"
            row['ai_summary'] = "제목 기반 1차 블랙리스트 필터 제외"
            row['ai_region'] = "무관"
            row['ai_keyword'] = "필터제외"
            row['ai_reason'] = "사전 제외 업종/키워드에 해당"
            row['ai_evidence'] = title[:100]
            row['ai_target_hint'] = "추천 제외"
            row['ai_recommend_yn'] = "N"
            filtered_count += 1
        else:
            try:
                page_res = session.get(pblanc_url, timeout=20)
                page_res.raise_for_status()

                soup = BeautifulSoup(page_res.text, 'html.parser')
                for script in soup(["script", "style"]):
                    script.extract()

                core_text = soup.get_text(separator=' ', strip=True)
                core_text = re.sub(r"\s+", " ", core_text).strip()[:4000]

                if not core_text:
                    row['ai_pass_yn'] = "에러"
                    row['ai_summary'] = "공고 본문 추출 실패"
                    row['ai_region'] = "전국"
                    row['ai_keyword'] = "본문없음"
                    row['ai_reason'] = "본문이 비어 있어 판정 불가"
                    row['ai_evidence'] = ""
                    row['ai_target_hint'] = "불명확"
                    row['ai_recommend_yn'] = "N"
                else:
                    try:
                        analysis = call_gemini_analysis(core_text, school_api_key)

                        row['ai_pass_yn'] = analysis['pass_yn']
                        row['ai_summary'] = analysis['summary']
                        row['ai_region'] = analysis['region']
                        row['ai_keyword'] = ", ".join(analysis['keywords'])
                        row['ai_reason'] = analysis['reason']
                        row['ai_evidence'] = ", ".join(analysis['evidence'])
                        row['ai_target_hint'] = analysis['target_hint']
                        row['ai_recommend_yn'] = analysis['recommend_yn']

                        if analysis['pass_yn'] == "O":
                            success_count += 1

                    except requests.HTTPError as http_err:
                        status_code = http_err.response.status_code if http_err.response is not None else 0
                        response_text = http_err.response.text if http_err.response is not None else str(http_err)

                        print(f"🚨 Gemini API HTTP 오류: {status_code} / {response_text[:300]}")

                        row['ai_pass_yn'] = "통신 에러"
                        row['ai_summary'] = f"Gemini HTTP 오류: {status_code}"
                        row['ai_region'] = "전국"
                        row['ai_keyword'] = "분석실패"
                        row['ai_reason'] = "AI API 통신 오류"
                        row['ai_evidence'] = ""
                        row['ai_target_hint'] = "불명확"
                        row['ai_recommend_yn'] = "N"

                        if is_fatal_ai_error(status_code, response_text):
                            fatal_ai_stop = True
                            send_discord_webhook(f"❌ [치명적 Gemini 오류] 상태코드 {status_code}: {response_text[:500]}")
                            new_data_list.append(row)
                            break

                    except Exception as e:
                        print(f"⚠️ 개별 공고 Gemini 분석 실패: {e}")
                        row['ai_pass_yn'] = "에러"
                        row['ai_summary'] = f"개별 분석 실패: {str(e)[:120]}"
                        row['ai_region'] = "전국"
                        row['ai_keyword'] = "분석실패"
                        row['ai_reason'] = "개별 공고 AI 분석 실패"
                        row['ai_evidence'] = ""
                        row['ai_target_hint'] = "불명확"
                        row['ai_recommend_yn'] = "N"

            except Exception as e:
                row['ai_pass_yn'] = "에러"
                row['ai_summary'] = str(e)[:120]
                row['ai_region'] = "전국"
                row['ai_keyword'] = "페이지처리실패"
                row['ai_reason'] = "공고 페이지 처리 실패"
                row['ai_evidence'] = ""
                row['ai_target_hint'] = "불명확"
                row['ai_recommend_yn'] = "N"

        new_data_list.append(row)

        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE bizinfo_tb
                    SET ai_pass_yn = :ai_pass_yn,
                        ai_summary = :ai_summary,
                        ai_region = :ai_region,
                        ai_keyword = :ai_keyword,
                        ai_reason = :ai_reason,
                        ai_evidence = :ai_evidence,
                        ai_target_hint = :ai_target_hint,
                        ai_recommend_yn = :ai_recommend_yn
                    WHERE "pblancId" = :pblancId

                """), row)
        except Exception as e:
            print(f"⚠️ DB UPDATE 실패 (pblancId={pid}): {e}")

        time.sleep(2)

        if fatal_ai_stop:
            break

    print(f"🎉 기존 공고 {len(new_data_list)}건 재분석/UPDATE 완료")
    send_discord_webhook(
        f"🧪 **테스트 재분석 완료**\n"
        f"- 대상: {len(new_data_list)}건\n"
        f"- 추천 판정(O): {success_count}건\n"
        f"- 블랙리스트 제외: {filtered_count}건\n"
        f"- DM 발송 대상: admin only"
    )

    print("2️⃣ admin 전용 DM 발송 시작...")
    users_df = pd.read_sql(
        f"SELECT ID, LOCATION, INDUSTRY, DISCORD_ID FROM USERS_TB WHERE ID = '{ADMIN_ONLY_ID}' AND DISCORD_ID IS NOT NULL",
        engine
    )

    for _, user in users_df.iterrows():
        user_id = str(user['ID']).strip()
        user_discord_id = str(user['DISCORD_ID']).strip()
        user_loc = str(user['LOCATION']).strip()
        user_ind = normalize_user_industry(user['INDUSTRY'])

        matched_msgs = []

        for row in new_data_list:
            if str(row.get('ai_pass_yn', '')) != "O":
                continue

            if str(row.get('ai_recommend_yn', 'N')) != "Y":
                continue

            grant_region = str(row.get('ai_region', '전국')).strip()
            grant_keyword_raw = str(row.get('ai_keyword', '업종무관(전분야)')).strip()
            grant_keywords = normalize_keywords(grant_keyword_raw)

            region_match = ("전국" in grant_region or user_loc in grant_region)
            industry_match = (
                user_ind in grant_keywords or
                ("업종무관(전분야)" in grant_keywords and str(row.get('ai_recommend_yn', 'N')) == "Y")
            )

            if region_match and industry_match:
                matched_msgs.append(
                    f"📌 **{row.get('pblancNm', '')}**\n"
                    f"- 📍 지역: {grant_region}\n"
                    f"- 🔑 키워드: {', '.join(grant_keywords)}\n"
                    f"- 💡 요약: {row.get('ai_summary', '')}\n"
                    f"- ✅ 추천이유: {row.get('ai_reason', '')}\n"
                    f"- 👤 지원대상: {row.get('ai_target_hint', '')}\n"
                    f"- 🔗 {row.get('pblancUrl', '')}\n"
                )

        if matched_msgs:
            final_msg = (
                f"**{user_id}** 님, 테스트 재분석 기준 추천 결과입니다.\n"
                f"(지역: {user_loc}, 분야: {user_ind})\n\n"
                + "\n".join(matched_msgs[:5])
            )
            send_discord_dm(user_discord_id, final_msg)
            print(f"   => [{user_id}]님께 테스트 추천 DM 전송 완료!")
        else:
            empty_msg = (
                f"**{user_id}** 님, 테스트 재분석 결과\n"
                f"조건(지역: {user_loc}, 분야: {user_ind})에 맞는 추천 공고가 없었습니다."
            )
            send_discord_dm(user_discord_id, empty_msg)
            print(f"   => [{user_id}]님께 테스트 '추천 없음' DM 전송 완료!")

except Exception as e:
    send_discord_webhook(f"❌ [final_bot_test 내부 에러]: {e}")
    print(f"❌ [final_bot_test 내부 에러]: {e}")
