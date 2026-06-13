import os
import requests
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def call_school_llm(prompt: str, model_type: str = "gemini", system_prompt: str = None) -> str:
    """
    학교 통합 플랫폼을 통해 AI를 호출하는 핵심 라우터 함수입니다.
    """
    
    # 1. 안전 금고(GitHub Secrets 또는 .env)에서 API 키 꺼내기
    api_key = os.getenv("SCHOOL_API_KEY")
    if not api_key:
        raise ValueError("서버 에러: SCHOOL_API_KEY가 설정되지 않았습니다.")

    base_url = "https://factchat-cloud.mindlogic.ai/v1/api"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 2. 목적지(URL) 및 데이터 규격 분기
    if model_type == "claude":
        url = f"{base_url}/anthropic/messages"
        payload = {
            "model": "claude-opus-4-5-20251101",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000
        }
        if system_prompt:
            payload["system"] = system_prompt

    elif model_type == "gemini":
        url = f"{base_url}/google/models/generate-content"
        payload = {
            "model": "gemini-2.5-flash",
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
            
    else:
        raise ValueError("지원하지 않는 AI 모델 타입입니다.")

    # 3. 학교 서버로 통신 발사 및 응답 처리
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status() 
        result_data = response.json()

        if model_type == "claude":
            return result_data["content"][0]["text"]
        elif model_type == "gemini":
            return result_data["candidates"][0]["content"]["parts"][0]["text"]
            
    except Exception as e:
        error_msg = f"API 호출 오류: {str(e)}"
        if 'response' in locals() and hasattr(response, 'text'):
            error_msg += f"\n상세: {response.text}"
        raise RuntimeError(error_msg)
