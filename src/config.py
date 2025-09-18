"""
설정 로딩 모듈
환경변수 및 상수 관리
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# 환경변수 로드
load_dotenv()


# 이미지 처리 상수
MAX_SIDE = 2048  # 입력 이미지 최대 크기
OUT_1TO1 = 1024  # 1:1 비율 출력 크기
OUT_2X3 = (1024, 1536)  # 2:3 비율 출력 크기


@dataclass
class Config:
    """애플리케이션 설정"""
    OPENAI_API_KEY: str
    MODEL_TEXT: str = "gpt-4.1-mini"
    MODEL_IMAGE: str = "gpt-image-1"
    DEFAULT_OUT_ROOT: str = "out"
    
    def __post_init__(self):
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")


def get_config() -> Config:
    """설정 인스턴스 반환"""
    return Config(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        MODEL_TEXT=os.getenv("MODEL_TEXT", "gpt-4.1-mini"),
        MODEL_IMAGE=os.getenv("MODEL_IMAGE", "gpt-image-1"),
        DEFAULT_OUT_ROOT=os.getenv("DEFAULT_OUT_ROOT", "out"),
    )