from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import announcements
from app.api import agent
from app.api import auth 

app = FastAPI(
    title="창업나침반 AI 에이전트 API",
    version="1.0.0"
)

# 🟢 5173 포트(Vite)와 3000 포트(React 기본)를 하나의 리스트로 통합
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 🟢 미들웨어 등록은 반드시 한 번만 실행!
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # OPTIONS, POST, GET 등 모든 방식 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

@app.get("/")
def read_root():
    return {"status": "healthy", "message": "창업나침반 백엔드 서버 구동 중"}

app.include_router(
    announcements.router, 
    prefix="/api/announcements", 
    tags=["공고 매칭 데이터"]
)

app.include_router(
    agent.router, 
    prefix="/api/agent", 
    tags=["AI 에이전트"]
)

app.include_router(
    auth.router, 
    prefix="/api/auth", 
    tags=["Authentication"]
)