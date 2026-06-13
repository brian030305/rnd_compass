import os
import time
import requests
import oracledb
import pandas as pd
from datetime import datetime
from functools import wraps
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# .env 파일의 환경변수를 로드합니다.
load_dotenv()

# LOB 데이터(긴 텍스트) 끊김 방지 설정
oracledb.defaults.fetch_lobs = False

# --- [간이 TTL 캐시 데코레이터 구현] ---
# 기존 @st.cache_data(ttl=...) 기능을 외부 라이브러리 없이 FastAPI에서 에뮬레이트합니다.
def ttl_cache(ttl_seconds: int):
    cache = {}
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            
            if cache_key in cache:
                result, expire_time = cache[cache_key]
                if now < expire_time:
                    return result  # 캐시 만료 전이면 기존 데이터 반환
                    
            result = func(*args, **kwargs)
            cache[cache_key] = (result, now + ttl_seconds)
            return result
        return wrapper
    return decorator

# --- [데이터베이스 엔진 설정] ---
def get_oracle_engine():
    return oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN")
    )

def get_sqlalchemy_engine():
    def creator():
        return get_oracle_engine()
    return create_engine("oracle+oracledb://", creator=creator)


# --- [공공 데이터 API 수집 함수들] ---

def fetch_safety_cert_data():
    url = "https://api.odcloud.kr/api/15040703/v1/uddi:9bbbc4ab-d825-401f-b7c2-ff065808acec"
    headers = {'Authorization': f'Infuser {os.getenv("SAFETY_API_KEY")}'}
    params = {'page': '1', 'perPage': '100'} 
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()['data'])
            return df.rename(columns={'제품명': '사업/공고/제품명', '제조사명': '관련기관/제조사'})
    except Exception as e:
        print(f"fetch_safety_cert_data 에러: {e}")
    return pd.DataFrame()

def fetch_mss_data():
    url = "https://api.odcloud.kr/api/3034791/v1/uddi:80a74cfd-55d2-4dd3-81c7-d01567d0b3c4"
    headers = {'Authorization': f'Infuser {os.getenv("MSS_API_KEY")}'}
    params = {'page': '1', 'perPage': '100', 'returnType': 'JSON'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()['data'])
            return df.rename(columns={'사업명': '사업/공고/제품명', '소관기관': '관련기관/제조사'})
    except Exception as e:
        print(f"fetch_mss_data 에러: {e}")
    return pd.DataFrame()

def fetch_ktl_data():
    url = "https://api.odcloud.kr/api/15124638/v1/uddi:1c027a3c-13c4-49cc-a138-d84d3bd24624"
    headers = {'Authorization': f'Infuser {os.getenv("KTL_API_KEY")}'}
    params = {'page': '1', 'perPage': '100', 'returnType': 'JSON'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()['data'])
            return df.rename(columns={'업체기본주소': '사업/공고/제품명', '접수수량': '관련기관/제조사'})
    except Exception as e:
        print(f"fetch_ktl_data 에러: {e}")
    return pd.DataFrame()

def fetch_kiat_data():
    url = "https://api.odcloud.kr/api/15069713/v1/uddi:6a6f31dc-cd7c-4d15-83ad-a5d0f400cc1c"
    headers = {'Authorization': f'Infuser {os.getenv("KIAT_API_KEY")}'}
    params = {'page': '1', 'perPage': '100', 'returnType': 'JSON'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()['data'])
            return df.rename(columns={'지원시책명': '사업/공고/제품명', '지원기관명': '관련기관/제조사'})
    except Exception as e:
        print(f"fetch_kiat_data 에러: {e}")
    return pd.DataFrame()

def fetch_keit_min_data():
    url = "https://api.odcloud.kr/api/15147658/v1/uddi:552afd36-0661-41de-9eb4-c1cd7485c8f4"
    headers = {'Authorization': f'Infuser {os.getenv("KEIT_MIN_API_KEY")}'}
    params = {'page': '1', 'perPage': '100', 'returnType': 'JSON'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()['data'])
            return df.rename(columns={'부처': '관련기관/제조사', '2024년_사업수': '사업/공고/제품명'}) 
    except Exception as e:
        print(f"fetch_keit_min_data 에러: {e}")
    return pd.DataFrame()

def fetch_keit_rd_data():
    url = "https://api.odcloud.kr/api/15011218/v1/uddi:36cb9d74-b258-47ab-9c4d-bcea5e89e7dc"
    headers = {'Authorization': f'Infuser {os.getenv("KEIT_RD_API_KEY")}'}
    params = {'page': '1', 'perPage': '100', 'returnType': 'JSON'}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()['data'])
            return df.rename(columns={'사업명': '사업/공고/제품명'})
    except Exception as e:
        print(f"fetch_keit_rd_data 에러: {e}")
    return pd.DataFrame()

@ttl_cache(ttl_seconds=3600)
def fetch_local_keit_announcement():
    try:
        engine = get_oracle_engine()
        df = pd.read_sql("SELECT * FROM csv_data_tb", engine)
        return df
    except Exception as e:
        print(f"fetch_local_keit_announcement 에러: {e}")
        return pd.DataFrame()

@ttl_cache(ttl_seconds=86400) 
def fetch_national_business_api():
    api_key = os.getenv("NATIONAL_BUSINESS_SURVEY_API_KEY", "")
    if not api_key: return pd.DataFrame()
        
    url = "https://api.odcloud.kr/api/15087673/v1/uddi:32e6d6f0-6d01-4f62-b76e-b0ae5b840573" 
    headers = {'Authorization': f'Infuser {api_key}'}
    params = {'page': '1', 'perPage': '1000'}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data: return pd.DataFrame(data['data'])
    except Exception as e:
        print(f"fetch_national_business_api 에러: {e}")
    return pd.DataFrame()

@ttl_cache(ttl_seconds=86400)
def fetch_mss_tech_cert_api():
    api_key = os.getenv("MSS_TECH_CERT_API_KEY", "")
    if not api_key: return pd.DataFrame()
        
    url = "https://api.odcloud.kr/api/3033913/v1/uddi:27bb6889-e56d-4cdc-a222-9f02900c81e7" 
    headers = {'Authorization': f'Infuser {api_key}'}
    params = {'page': '1', 'perPage': '500'}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data: return pd.DataFrame(data['data'])
    except Exception as e:
        print(f"fetch_mss_tech_cert_api 에러: {e}")
    return pd.DataFrame()

def fetch_bizinfo_api():
    try:
        engine = get_oracle_engine()
        df = pd.read_sql("SELECT * FROM bizinfo_tb FETCH FIRST 500 ROWS ONLY", engine)
        
        if df.empty: return pd.DataFrame()
            
        known_keys = ['pblancId', 'pblancNm', 'reqstEndDe', 'reqstBgnde', 'insttNm', 'bizId', 'entrprsStle', 'jrsdcAsct', 'exntcInsttNm', 'pblancUrl','AI_REGION', 'AI_KEYWORD']
        mapping = {key.upper(): key for key in known_keys}
        df = df.rename(columns=lambda x: mapping.get(x.upper(), x))
        
        if 'reqstEndDe' in df.columns:
            df['마감일_계산용'] = pd.to_datetime(df['reqstEndDe'], errors='coerce')
            today = pd.Timestamp(datetime.now().date())
            valid_df = df[(df['마감일_계산용'] >= today) | (df['마감일_계산용'].isna())]
            return valid_df.drop(columns=['마감일_계산용']).head(200).reset_index(drop=True)
        return df.head(200)
            
    except Exception as e:
        print(f"오라클 DB(기업마당) 읽기 실패: {e}")
        return pd.DataFrame()

def admin_fetch_all_users():
    try:
        engine = get_oracle_engine()
        df = pd.read_sql("SELECT ID, COMPANY, LOCATION, INDUSTRY, TECH FROM users_tb", engine).fillna("")
        df.columns = df.columns.str.upper()
        return df
    except Exception as e:
        print(f"회원 목록을 불러오는 중 오류 발생: {e}")
        return pd.DataFrame()

def admin_delete_user(user_id):
    try:
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            query = text("DELETE FROM users_tb WHERE TO_CHAR(ID) = :user_id")
            conn.execute(query, {"user_id": str(user_id)})
            conn.commit()
        return True
    except Exception as e:
        print(f"계정 삭제 중 오류 발생: {e}")
        return False

def admin_change_user_password(user_id, hashed_pw):
    try:
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            query = text("UPDATE users_tb SET PW = :pw WHERE TO_CHAR(ID) = :user_id")
            conn.execute(query, {"pw": hashed_pw, "user_id": str(user_id)})
            conn.commit() 
        return True
    except Exception as e:
        print(f"관리자 비밀번호 변경 오류: {e}")
        return False

def fetch_kstartup_data():
    url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
    service_key = os.getenv("KSTARTUP_API_KEY")
    params = {'serviceKey': service_key, 'pageNo': 1, 'numOfRows': 100, 'returnType': 'JSON'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            items = []
            if "response" in result and "body" in result["response"] and "items" in result["response"]["body"]:
                items = result["response"]["body"]["items"]["item"]
            
            if items:
                df = pd.DataFrame(items).dropna(how='all')
                mapping = {
                    'pbancNm': '사업명', 'postsnNm': '사업명', 'title': '사업명',
                    'bizPrchDprtNm': '소관기관', 'pancInsttNm': '소관기관',
                    'pbancRcptBgngDt': '접수시작일', 'pbancRcptEndDt': '마감일',
                    'dtlPgUrl': '상세링크'
                }
                df = df.rename(columns=mapping)
                cols_to_keep = ['사업명', '소관기관', '접수시작일', '마감일', '상세링크']
                existing_cols = [c for c in cols_to_keep if c in df.columns]
                return df[existing_cols]
        return pd.DataFrame()
    except Exception as e:
        print(f"fetch_kstartup_data 에러: {e}")
        return pd.DataFrame()

def fetch_msit_rd_data():
    url = "http://apis.data.go.kr/1721000/msitannouncementinfo/businessAnnouncMentList"
    service_key = os.getenv("MSIT_API_KEY", "")
    params = {'serviceKey': service_key, 'pageNo': 1, 'numOfRows': 100, 'resultType': 'json'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            items = []
            if "response" in result and "body" in result["response"] and "items" in result["response"]["body"]:
                items_data = result["response"]["body"]["items"]
                if isinstance(items_data, dict) and "item" in items_data:
                    items = items_data["item"]
                elif isinstance(items_data, list):
                    items = items_data
            
            if items:
                df = pd.DataFrame(items)
                rename_dict = {}
                if 'title' in df.columns: rename_dict['title'] = '사업명'
                elif 'bizNm' in df.columns: rename_dict['bizNm'] = '사업명'
                elif 'anmtNm' in df.columns: rename_dict['anmtNm'] = '사업명'
                
                if rename_dict:
                    df = df.rename(columns=rename_dict)
                if '소관기관' not in df.columns:
                    df['소관기관'] = '과학기술정보통신부'
                return df
        return pd.DataFrame()
    except Exception as e:
        print(f"과기부 R&D 데이터 로드 실패: {e}")
        return pd.DataFrame()
