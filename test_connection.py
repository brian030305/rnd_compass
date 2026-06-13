from app.core.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 'DB 연결 성공!' FROM DUAL"))
        print(result.scalar())
except Exception as e:
    print(f"연결 실패: {e}")