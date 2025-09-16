"""
로깅 설정 모듈
"""
import logging
import sys
from pathlib import Path


def setup_logging(
    log_file: Path = None,
    level: int = logging.INFO,
    format: str = None
) -> None:
    """로깅 설정"""
    if format is None:
        format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format))
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format))
        root_logger.addHandler(file_handler)
    
    # 외부 라이브러리 로깅 레벨 조정
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)