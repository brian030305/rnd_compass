from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.matcher import process_and_match_announcements
from app.services.ai_agent import call_school_llm

router = APIRouter()

class MatchRequest(BaseModel):
    user_message: str
    region: str       # 예: "부산"
    keyword: str      # 예: "IT"

@router.post("/chat")
def chat_and_match(request: MatchRequest):
    try:
        # 1. 파이썬이 데이터를 엄격하게 통제하여 일관된 매칭 결과를 뽑아냅니다.
        match_result = process_and_match_announcements(
            user_region=request.region,
            user_keyword=request.keyword
        )
        
        # 2. LLM에게는 파이썬이 통제한 결과물'만' 주입하여 정성적인 가이드라인 문장만 쓰게 만듭니다.
        # 이렇게 하면 LLM이 없는 공고를 지어내거나 수치를 맘대로 바꾸는 현상을 100% 방어합니다.
        system_instruction = f"""
        당신은 창업나침반의 비서입니다. 사용자의 질문인 '{request.user_message}'에 답변하세요.
        반드시 파이썬 시스템이 검증하여 찾아낸 다음 공고 데이터만 바탕으로 친절하게 안내문을 작성해야 합니다.
        [검증된 공고 데이터]: {match_result['items'][:2]}
        """
        
        ai_reply = call_school_llm(
            prompt="위 데이터에 기반하여 유저에게 추천 메시지를 작성해줘.",
            model_type="claude",
            system_prompt=system_instruction
        )
        
        return {
            "agent_reply": ai_reply,
            "matched_count": match_result["matched_count"],
            "raw_data": match_result["items"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
