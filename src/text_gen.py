"""
텍스트 생성 래퍼 모듈
OpenAI API를 사용한 텍스트 생성
"""
import logging
from pathlib import Path

import openai

from .config import get_config


logger = logging.getLogger(__name__)


def load_prompt(prompt_name: str, jewelry_type: str) -> str:
    """프롬프트 파일 로드 및 변수 치환"""
    prompt_path = Path(__file__).parent / "prompts" / f"{prompt_name}.md"
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    # 주얼리 종류 치환
    prompt = prompt.replace("{JEWELRY_TYPE}", jewelry_type)
    
    return prompt


def generate_description(image_path: Path, jewelry_type: str) -> str:
    """상품 설명 생성"""
    config = get_config()
    client = openai.Client(api_key=config.OPENAI_API_KEY)
    
    # 프롬프트 로드
    prompt = load_prompt("desc", jewelry_type)
    
    logger.info(f"텍스트 생성 API 호출: {config.MODEL_TEXT}")
    
    try:
        # 이미지를 base64로 인코딩
        import base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # OpenAI API 호출
        response = client.chat.completions.create(
            model=config.MODEL_TEXT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        description = response.choices[0].message.content
        logger.info(f"텍스트 생성 완료: {len(description)} 글자")
        
        return description
        
    except Exception as e:
        logger.error(f"텍스트 생성 API 호출 실패: {e}")
        # 실패 시 기본 템플릿 반환
        return f"""# {jewelry_type.upper()} 상품명 (생성 실패)

## 상품 설명
API 호출에 실패했습니다. 설정을 확인해주세요.
오류: {str(e)}

## 특징
- 수동으로 작성해주세요
"""