"""
공통 오케스트레이션 모듈
입력 검증, 출력 폴더 생성, 각 작업별 처리 함수
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .config import get_config
from .io_utils import create_output_dir, validate_image_path
from .text_gen import generate_description
from .image_gen import (
    generate_thumbnail,
    generate_styled_shot,
    generate_wear_shot,
    generate_wear_closeup
)


logger = logging.getLogger(__name__)


def create_metadata(
    image_path: str,
    jewelry_type: str,
    output_dir: Path,
    task: str
) -> Dict[str, Any]:
    """실행 메타데이터 생성"""
    config = get_config()
    return {
        "task": task,
        "input_image": str(image_path),
        "jewelry_type": jewelry_type,
        "output_directory": str(output_dir),
        "model_text": config.MODEL_TEXT,
        "model_image": config.MODEL_IMAGE,
        "timestamp": datetime.now().isoformat(),
    }


def save_metadata(metadata: Dict[str, Any], output_dir: Path) -> None:
    """메타데이터 저장"""
    meta_path = output_dir / "meta.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"메타데이터 저장: {meta_path}")


def process_description(
    image_path: str,
    jewelry_type: str,
    output_dir: str = None
) -> Path:
    """상품 설명 생성 처리"""
    # 입력 검증
    img_path = validate_image_path(image_path)
    
    # 출력 디렉토리 생성
    out_dir = create_output_dir(output_dir, "desc")
    
    # 메타데이터 생성
    metadata = create_metadata(image_path, jewelry_type, out_dir, "description")
    
    try:
        # 설명 생성
        logger.info(f"상품 설명 생성 시작: {img_path}")
        description = generate_description(img_path, jewelry_type)
        
        # 결과 저장
        desc_path = out_dir / "desc.md"
        with open(desc_path, 'w', encoding='utf-8') as f:
            f.write(description)
        
        logger.info(f"상품 설명 저장: {desc_path}")
        
        # 메타데이터 저장
        save_metadata(metadata, out_dir)
        
        return out_dir
        
    except Exception as e:
        logger.error(f"상품 설명 생성 실패: {e}")
        raise


def process_thumbnail(
    image_path: str,
    jewelry_type: str,
    output_dir: str = None
) -> Path:
    """누끼컷 생성 처리"""
    # 입력 검증
    img_path = validate_image_path(image_path)
    
    # 출력 디렉토리 생성
    out_dir = create_output_dir(output_dir, "thumb")
    
    # 메타데이터 생성
    metadata = create_metadata(image_path, jewelry_type, out_dir, "thumbnail")
    
    try:
        # 누끼컷 생성
        logger.info(f"누끼컷 생성 시작: {img_path}")
        thumb_path = generate_thumbnail(img_path, jewelry_type, out_dir)
        
        logger.info(f"누끼컷 저장: {thumb_path}")
        
        # 메타데이터 저장
        save_metadata(metadata, out_dir)
        
        return out_dir
        
    except Exception as e:
        logger.error(f"누끼컷 생성 실패: {e}")
        raise


def process_styled(
    image_path: str,
    jewelry_type: str,
    output_dir: str = None
) -> Path:
    """제품 연출컷 생성 처리"""
    # 입력 검증
    img_path = validate_image_path(image_path)
    
    # 출력 디렉토리 생성
    out_dir = create_output_dir(output_dir, "styled")
    
    # 메타데이터 생성
    metadata = create_metadata(image_path, jewelry_type, out_dir, "styled_shot")
    
    try:
        # 연출컷 생성
        logger.info(f"제품 연출컷 생성 시작: {img_path}")
        styled_paths = generate_styled_shot(img_path, jewelry_type, out_dir)
        
        logger.info(f"연출컷 저장: {len(styled_paths)}개")
        
        # 메타데이터 저장
        save_metadata(metadata, out_dir)
        
        return out_dir
        
    except Exception as e:
        logger.error(f"제품 연출컷 생성 실패: {e}")
        raise


def process_wear(
    image_path: str,
    jewelry_type: str,
    output_dir: str = None
) -> Path:
    """착용컷 생성 처리"""
    # 입력 검증
    img_path = validate_image_path(image_path)
    
    # 출력 디렉토리 생성
    out_dir = create_output_dir(output_dir, "wear")
    
    # 메타데이터 생성
    metadata = create_metadata(image_path, jewelry_type, out_dir, "wear_shot")
    
    try:
        # 착용컷 생성
        logger.info(f"착용컷 생성 시작: {img_path}")
        wear_paths = generate_wear_shot(img_path, jewelry_type, out_dir)
        
        logger.info(f"착용컷 저장: {len(wear_paths)}개")
        
        # 메타데이터 저장
        save_metadata(metadata, out_dir)
        
        return out_dir
        
    except Exception as e:
        logger.error(f"착용컷 생성 실패: {e}")
        raise


def process_wear_closeup(
    image_path: str,
    jewelry_type: str,
    output_dir: str = None
) -> Path:
    """클로즈업 착용컷 생성 처리"""
    # 입력 검증
    img_path = validate_image_path(image_path)
    
    # 출력 디렉토리 생성
    out_dir = create_output_dir(output_dir, "wear_closeup")
    
    # 메타데이터 생성
    metadata = create_metadata(image_path, jewelry_type, out_dir, "wear_closeup")
    
    try:
        # 클로즈업 착용컷 생성
        logger.info(f"클로즈업 착용컷 생성 시작: {img_path}")
        closeup_paths = generate_wear_closeup(img_path, jewelry_type, out_dir)
        
        logger.info(f"클로즈업 착용컷 저장: {len(closeup_paths)}개")
        
        # 메타데이터 저장
        save_metadata(metadata, out_dir)
        
        return out_dir
        
    except Exception as e:
        logger.error(f"클로즈업 착용컷 생성 실패: {e}")
        raise