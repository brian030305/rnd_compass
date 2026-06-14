import os
import requests
from fastapi.responses import RedirectResponse
from fastapi import APIRouter, HTTPException
import hashlib
import jwt  
from datetime import datetime, timedelta
from sqlalchemy import text
from app.core.database import get_sqlalchemy_engine, get_oracle_engine
from app.schemas.user import UserSignup, UserLogin
import pandas as pd

router = APIRouter()

# JWT 토큰 암호화 설정
SECRET_KEY = "startup_compass_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  

def make_hashes(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/signup")
def signup(user: UserSignup):
    try:
        engine = get_oracle_engine()
        # 🟢 수정됨: TO_CHAR 제거 (완벽한 VARCHAR2 매칭)
        check_df = pd.read_sql(f"SELECT ID FROM users_tb WHERE ID = '{user.user_id}'", engine)
        if not check_df.empty:
            raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

        hashed_pw = make_hashes(user.password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role = "SUPER_ADMIN" if user.user_id == 'admin' else "COMPANY_MASTER"
        
        # 🟢 수정됨: 쿼리문에 JOB_ROLE 컬럼 추가
        insert_query = text("""
            INSERT INTO users_tb (ID, PW, COMPANY, LOCATION, INDUSTRY, TECH, JOB_ROLE, ROLE, CREATED_AT) 
            VALUES (:id, :pw, :company, :location, :industry, :tech, :job_role, :role, :created_at)
        """)
        
        sql_engine = get_sqlalchemy_engine()
        with sql_engine.connect() as conn:
            conn.execute(insert_query, {
                "id": user.user_id, "pw": hashed_pw, "company": user.company_name,
                "location": user.location, "industry": user.industry, "tech": user.tech_field,
                "job_role": user.job_role,
                "role": role, "created_at": created_at
            })
            conn.commit()
            
        return {"status": "success", "message": f"{user.user_id}님 환영합니다! ({role} 권한 부여됨)"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")

@router.post("/login")
def login(user: UserLogin):
    try:
        engine = get_oracle_engine()
        # 🟢 수정됨: TO_CHAR 제거
        df = pd.read_sql(f"SELECT PW, COMPANY, ROLE, LOCATION, INDUSTRY, TECH FROM users_tb WHERE ID = '{user.user_id}'", engine)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="존재하지 않는 아이디입니다.")
            
        stored_password = str(df.iloc[0]['PW'])
        
        if make_hashes(user.password) == stored_password:
            user_info = {
                "user_id": user.user_id,
                "company": str(df.iloc[0]['COMPANY']),
                "role": str(df.iloc[0]['ROLE']),
                "location": str(df.iloc[0]['LOCATION']),
                "industry": str(df.iloc[0]['INDUSTRY']),
                "tech": str(df.iloc[0]['TECH'])
            }
            access_token = create_access_token(data=user_info)

            return {
                "status": "success", 
                "message": "로그인 성공",
                "access_token": access_token,  
                "token_type": "bearer",
                "data": user_info
            }
        else:
            raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 실패: {str(e)}")
    
# --- 디스코드 OAuth2 연동 ---

CLIENT_ID = os.getenv("Discord_Client_ID")
CLIENT_SECRET = os.getenv("Discord_Client_Secret")
REDIRECT_URI = "http://127.0.0.1:8000/api/auth/discord/callback"

@router.get("/discord/login/{user_id}")
def discord_login(user_id: str):
    discord_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify&state={user_id}"
    return RedirectResponse(discord_url)

@router.get("/discord/callback")
def discord_callback(code: str, state: str):
    user_id = state
    
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    
    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail="디스코드 인증에 실패했습니다.")
        
    access_token = token_res.json().get("access_token")
    
    user_res = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    discord_id = user_res.json().get("id")
    
    engine = get_sqlalchemy_engine()
    # ... (생략) ...
    with engine.connect() as conn:
        query = text("UPDATE users_tb SET DISCORD_ID = :discord_id WHERE ID = :user_id")
        conn.execute(query, {"discord_id": discord_id, "user_id": user_id})
        conn.commit()
        
    # 🟢 텍스트 대신 프론트엔드의 로그인 페이지로 강제 이동(리다이렉트) 시킵니다.
    return RedirectResponse(url="http://localhost:5173/login")