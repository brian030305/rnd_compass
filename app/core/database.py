import os
import oracledb
from sqlalchemy import create_engine
from dotenv import load_dotenv

# .env 파일의 환경변수를 불러옵니다.
load_dotenv()

# LOB 데이터 끊김 방지 설정
oracledb.defaults.fetch_lobs = False

# 1. 읽기 전용 엔진 (오라클 다이렉트)
def get_oracle_engine():
    return oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN")
    )

# 2. 쓰기/업데이트용 SQLAlchemy 엔진
def get_sqlalchemy_engine():
    def creator():
        return get_oracle_engine()
    return create_engine("oracle+oracledb://", creator=creator)

engine = get_sqlalchemy_engine()