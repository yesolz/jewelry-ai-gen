"""
파일 입출력 유틸리티
이미지 리사이징, 확장자 처리, 디렉토리 관리
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from .config import MAX_SIDE, get_config


logger = logging.getLogger(__name__)


def validate_image_path(image_path: str) -> Path:
    """이미지 경로 검증"""
    path = Path(image_path)
    
    if not path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")
    
    if not path.is_file():
        raise ValueError(f"경로가 파일이 아닙니다: {image_path}")
    
    # 지원 확장자 확인
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {path.suffix}")
    
    return path


def resize_image(image_path: Path, max_side: int = MAX_SIDE) -> Image.Image:
    """이미지를 최대 크기로 리사이징"""
    with Image.open(image_path) as img:
        # EXIF 회전 정보 적용
        img = apply_exif_rotation(img)
        
        # 이미 작은 경우 그대로 반환
        if img.width <= max_side and img.height <= max_side:
            return img.copy()
        
        # 비율 유지하며 리사이징
        ratio = min(max_side / img.width, max_side / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        
        logger.info(f"이미지 리사이징: {img.size} -> {new_size}")
        return img.resize(new_size, Image.Resampling.LANCZOS)


def apply_exif_rotation(img: Image.Image) -> Image.Image:
    """EXIF 정보에 따라 이미지 회전"""
    try:
        # EXIF 데이터에서 회전 정보 추출
        exif = img._getexif()
        if exif is not None:
            for orientation in exif.keys():
                if orientation == 274:  # Orientation 태그
                    if exif[orientation] == 3:
                        img = img.rotate(180, expand=True)
                    elif exif[orientation] == 6:
                        img = img.rotate(270, expand=True)
                    elif exif[orientation] == 8:
                        img = img.rotate(90, expand=True)
                    break
    except Exception:
        # EXIF 처리 실패 시 무시
        pass
    
    return img


def create_output_dir(output_dir: Optional[str], task_type: str) -> Path:
    """출력 디렉토리 생성"""
    config = get_config()
    
    if output_dir:
        out_path = Path(output_dir)
    else:
        # 기본 디렉토리 구조: out/TASK_YYYYmmdd_HHMMSS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(config.DEFAULT_OUT_ROOT) / f"{task_type}_{timestamp}"
    
    # 디렉토리 생성
    out_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"출력 디렉토리 생성: {out_path}")
    
    return out_path


def save_image(img: Image.Image, output_path: Path, format: str = "PNG") -> None:
    """이미지 저장"""
    if format.upper() == "JPEG" and img.mode in ('RGBA', 'LA', 'P'):
        # JPEG는 알파 채널을 지원하지 않음
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = rgb_img
    
    img.save(output_path, format=format, quality=95 if format == "JPEG" else None)
    logger.info(f"이미지 저장: {output_path}")


def get_aspect_ratio_size(ratio: str, base_width: int = 1024) -> Tuple[int, int]:
    """비율에 따른 크기 계산"""
    ratios = {
        "1:1": (base_width, base_width),
        "3:4": (base_width, int(base_width * 4 / 3)),
        "4:3": (base_width, int(base_width * 3 / 4)),
        "16:9": (base_width, int(base_width * 9 / 16)),
        "9:16": (base_width, int(base_width * 16 / 9)),
    }
    
    return ratios.get(ratio, (base_width, base_width))