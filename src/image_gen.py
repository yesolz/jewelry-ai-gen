"""
이미지 생성/편집 래퍼 모듈
OpenAI API를 사용한 이미지 생성
"""
import logging
from pathlib import Path
from typing import List

import openai
from PIL import Image

from .config import get_config, OUT_1TO1, OUT_3X4
from .io_utils import resize_image, save_image
from .text_gen import load_prompt


logger = logging.getLogger(__name__)


def generate_thumbnail(
    image_path: Path,
    jewelry_type: str,
    output_dir: Path
) -> Path:
    """누끼컷(1:1) 생성"""
    config = get_config()
    client = openai.Client(api_key=config.OPENAI_API_KEY)
    
    # 프롬프트 로드
    prompt = load_prompt("thumb", jewelry_type)
    
    # 이미지 리사이징
    img = resize_image(image_path)
    
    logger.info(f"누끼컷 생성 API 호출: {config.MODEL_IMAGE}")
    
    try:
        # 이미지를 base64로 인코딩
        import base64
        import tempfile
        from io import BytesIO
        
        # 이미지를 base64로 변환
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
        
        # gpt-image-1으로 이미지 생성 요청 (images API 사용)
        response = client.images.generate(
            model=config.MODEL_IMAGE,
            prompt=f"{prompt}\n\n이 이미지를 참고하여 1:1 정사각형 비율의 깨끗한 누끼컷 이미지를 생성해주세요.",
            n=1,
            size="1024x1024",
            quality="high"
        )
        
        # gpt-image-1 응답 처리
        logger.info("gpt-image-1 응답 받음, 이미지 다운로드 시도")
        
        # 생성된 이미지 다운로드
        import requests
        from PIL import Image as PILImage
        from io import BytesIO
        
        image_url = response.data[0].url
        image_response = requests.get(image_url)
        generated_img = PILImage.open(BytesIO(image_response.content))
        generated_img = generated_img.resize((OUT_1TO1, OUT_1TO1), Image.Resampling.LANCZOS)
        
        output_path = output_dir / "thumb_1to1.png"
        save_image(generated_img, output_path)
        
        logger.info(f"gpt-image-1로 누끼컷 생성 완료: {output_path}")
        return output_path
        
        # 기본 크롭 처리
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        cropped = img.crop((left, top, left + size, top + size))
        cropped = cropped.resize((OUT_1TO1, OUT_1TO1), Image.Resampling.LANCZOS)
        
        output_path = output_dir / "thumb_1to1.png"
        save_image(cropped, output_path)
        
        logger.info(f"누끼컷 생성 완료: {output_path}")
        return output_path
        
    except Exception as e:
        logger.warning(f"API 호출 실패, 기본 처리로 대체: {e}")
        
        # 실패 시 기본 크롭 처리
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        cropped = img.crop((left, top, left + size, top + size))
        cropped = cropped.resize((OUT_1TO1, OUT_1TO1), Image.Resampling.LANCZOS)
        
        output_path = output_dir / "thumb_1to1.png"
        save_image(cropped, output_path)
        
        return output_path


def generate_styled_shot(
    image_path: Path,
    jewelry_type: str,
    output_dir: Path,
    count: int = 2
) -> List[Path]:
    """제품 연출컷(3:4) 생성"""
    config = get_config()
    client = openai.Client(api_key=config.OPENAI_API_KEY)
    
    # 프롬프트 로드
    prompt = load_prompt("styled", jewelry_type)
    
    # 이미지 리사이징
    img = resize_image(image_path)
    
    logger.info(f"제품 연출컷 생성 API 호출: {config.MODEL_IMAGE}")
    
    output_paths = []
    
    for i in range(count):
        try:
            # 이미지를 base64로 인코딩
            import base64
            from io import BytesIO
            
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # gpt-image-1으로 이미지 생성 요청
            variation_prompt = f"{prompt}\n\n이 {jewelry_type} 제품을 사용하여 3:4 비율의 세련된 연출컷을 생성해주세요. (스타일 {i+1})"
            
            response = client.images.generate(
                model=config.MODEL_IMAGE,
                prompt=variation_prompt,
                n=1,
                size="1024x1536",  # 2:3 비율 (GPT-4 지원)
                quality="high"
            )
            
            # 생성된 이미지 처리
            import requests
            from PIL import Image as PILImage
            from io import BytesIO
            
            # 응답 확인
            if hasattr(response, 'data') and response.data:
                if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                    # base64 데이터 처리
                    logger.info("base64 형식의 이미지 데이터 처리 중")
                    b64_data = response.data[0].b64_json
                    
                    # 'data:image/png;base64,' 프리픽스 제거
                    if b64_data.startswith('data:image/'):
                        b64_data = b64_data.split(',')[1]
                    
                    # base64 디코딩
                    image_data = base64.b64decode(b64_data)
                    generated_image = PILImage.open(BytesIO(image_data))
                elif hasattr(response.data[0], 'url') and response.data[0].url:
                    # URL에서 이미지 다운로드
                    logger.info("URL에서 이미지 다운로드 중")
                    image_url = response.data[0].url
                    image_response = requests.get(image_url)
                    generated_image = PILImage.open(BytesIO(image_response.content))
                else:
                    logger.error(f"response.data[0] 속성: {vars(response.data[0]) if hasattr(response.data[0], '__dict__') else response.data[0]}")
                    raise ValueError("API 응답에서 이미지 데이터를 찾을 수 없습니다")
            else:
                logger.error(f"응답 형식 오류: {response}")
                raise ValueError("API 응답에서 data 속성을 찾을 수 없습니다")
                
            generated_image = generated_image.resize(OUT_3X4, Image.Resampling.LANCZOS)
            
            logger.info(f"gpt-image-1로 연출컷 {i+1} 생성 성공")
            
            output_path = output_dir / f"styled_3x4_{i+1:02d}.png"
            save_image(generated_image, output_path)
            output_paths.append(output_path)
            
            logger.info(f"연출컷 {i+1} 생성 완료: {output_path}")
            
        except Exception as e:
            logger.warning(f"연출컷 {i+1} API 호출 실패: {e}")
            
            # 실패 시 기본 리사이징
            resized = img.resize(OUT_3X4, Image.Resampling.LANCZOS)
            output_path = output_dir / f"styled_3x4_{i+1:02d}.png"
            save_image(resized, output_path)
            output_paths.append(output_path)
    
    return output_paths


def generate_wear_shot(
    image_path: Path,
    jewelry_type: str,
    output_dir: Path,
    count: int = 2
) -> List[Path]:
    """착용컷(3:4) 생성"""
    config = get_config()
    client = openai.Client(api_key=config.OPENAI_API_KEY)
    
    # 프롬프트 로드
    prompt = load_prompt("wear", jewelry_type)
    
    # 이미지 리사이징
    img = resize_image(image_path)
    
    logger.info(f"착용컷 생성 API 호출: {config.MODEL_IMAGE}")
    
    output_paths = []
    
    for i in range(count):
        try:
            # 이미지를 base64로 인코딩
            import base64
            from io import BytesIO
            
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # gpt-image-1으로 이미지 생성 요청
            variation_prompt = f"{prompt}\n\n이 {jewelry_type} 제품의 착용 모습을 3:4 비율로 자연스럽게 생성해주세요. (스타일 {i+1})"
            
            response = client.images.generate(
                model=config.MODEL_IMAGE,
                prompt=variation_prompt,
                n=1,
                size="1024x1536",  # 2:3 비율 (GPT-4 지원)
                quality="high"
            )
            
            # 생성된 이미지 처리
            import requests
            from PIL import Image as PILImage
            from io import BytesIO
            
            # 응답 확인
            if hasattr(response, 'data') and response.data:
                if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                    # base64 데이터 처리
                    logger.info("base64 형식의 이미지 데이터 처리 중")
                    b64_data = response.data[0].b64_json
                    
                    # 'data:image/png;base64,' 프리픽스 제거
                    if b64_data.startswith('data:image/'):
                        b64_data = b64_data.split(',')[1]
                    
                    # base64 디코딩
                    image_data = base64.b64decode(b64_data)
                    generated_image = PILImage.open(BytesIO(image_data))
                elif hasattr(response.data[0], 'url') and response.data[0].url:
                    # URL에서 이미지 다운로드
                    logger.info("URL에서 이미지 다운로드 중")
                    image_url = response.data[0].url
                    image_response = requests.get(image_url)
                    generated_image = PILImage.open(BytesIO(image_response.content))
                else:
                    logger.error(f"response.data[0] 속성: {vars(response.data[0]) if hasattr(response.data[0], '__dict__') else response.data[0]}")
                    raise ValueError("API 응답에서 이미지 데이터를 찾을 수 없습니다")
            else:
                logger.error(f"응답 형식 오류: {response}")
                raise ValueError("API 응답에서 data 속성을 찾을 수 없습니다")
                
            generated_image = generated_image.resize(OUT_3X4, Image.Resampling.LANCZOS)
            
            logger.info(f"gpt-image-1로 착용컷 {i+1} 생성 성공")
            
            output_path = output_dir / f"wear_3x4_{i+1:02d}.png"
            save_image(generated_image, output_path)
            output_paths.append(output_path)
            
            logger.info(f"착용컷 {i+1} 생성 완료: {output_path}")
            
        except Exception as e:
            logger.warning(f"착용컷 {i+1} API 호출 실패: {e}")
            
            # 실패 시 기본 리사이징
            resized = img.resize(OUT_3X4, Image.Resampling.LANCZOS)
            output_path = output_dir / f"wear_3x4_{i+1:02d}.png"
            save_image(resized, output_path)
            output_paths.append(output_path)
    
    return output_paths


def generate_wear_closeup(
    image_path: Path,
    jewelry_type: str,
    output_dir: Path,
    count: int = 2
) -> List[Path]:
    """클로즈업 착용컷(3:4) 생성"""
    config = get_config()
    client = openai.Client(api_key=config.OPENAI_API_KEY)
    
    # 프롬프트 로드
    prompt = load_prompt("wear_closeup", jewelry_type)
    
    # 이미지 리사이징
    img = resize_image(image_path)
    
    logger.info(f"클로즈업 착용컷 생성 API 호출: {config.MODEL_IMAGE}")
    
    output_paths = []
    
    for i in range(count):
        try:
            # 이미지를 base64로 인코딩
            import base64
            from io import BytesIO
            
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # gpt-image-1으로 이미지 생성 요청
            variation_prompt = f"{prompt}\n\n이 {jewelry_type} 제품의 클로즈업 착용 모습을 3:4 비율로 디테일하게 생성해주세요. (스타일 {i+1})"
            
            response = client.images.generate(
                model=config.MODEL_IMAGE,
                prompt=variation_prompt,
                n=1,
                size="1024x1536",  # 2:3 비율 (GPT-4 지원)
                quality="high"
            )
            
            # 생성된 이미지 처리
            import requests
            from PIL import Image as PILImage
            from io import BytesIO
            
            # 응답 확인
            if hasattr(response, 'data') and response.data:
                if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                    # base64 데이터 처리
                    logger.info("base64 형식의 이미지 데이터 처리 중")
                    b64_data = response.data[0].b64_json
                    
                    # 'data:image/png;base64,' 프리픽스 제거
                    if b64_data.startswith('data:image/'):
                        b64_data = b64_data.split(',')[1]
                    
                    # base64 디코딩
                    image_data = base64.b64decode(b64_data)
                    generated_image = PILImage.open(BytesIO(image_data))
                elif hasattr(response.data[0], 'url') and response.data[0].url:
                    # URL에서 이미지 다운로드
                    logger.info("URL에서 이미지 다운로드 중")
                    image_url = response.data[0].url
                    image_response = requests.get(image_url)
                    generated_image = PILImage.open(BytesIO(image_response.content))
                else:
                    logger.error(f"response.data[0] 속성: {vars(response.data[0]) if hasattr(response.data[0], '__dict__') else response.data[0]}")
                    raise ValueError("API 응답에서 이미지 데이터를 찾을 수 없습니다")
            else:
                logger.error(f"응답 형식 오류: {response}")
                raise ValueError("API 응답에서 data 속성을 찾을 수 없습니다")
                
            generated_image = generated_image.resize(OUT_3X4, Image.Resampling.LANCZOS)
            
            logger.info(f"gpt-image-1로 클로즈업 착용컷 {i+1} 생성 성공")
            
            output_path = output_dir / f"wear_closeup_3x4_{i+1:02d}.png"
            save_image(generated_image, output_path)
            output_paths.append(output_path)
            
            logger.info(f"클로즈업 착용컷 {i+1} 생성 완료: {output_path}")
            
        except Exception as e:
            logger.warning(f"클로즈업 착용컷 {i+1} API 호출 실패: {e}")
            
            # 실패 시 기본 리사이징
            resized = img.resize(OUT_3X4, Image.Resampling.LANCZOS)
            output_path = output_dir / f"wear_closeup_3x4_{i+1:02d}.png"
            save_image(resized, output_path)
            output_paths.append(output_path)
    
    return output_paths