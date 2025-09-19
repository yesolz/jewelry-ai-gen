#!/usr/bin/env python3
"""
주얼리 이미지 일괄 생성 스크립트
상품 설명, 제품 연출컷, 착용컷, 클로즈업 착용컷을 순차적으로 생성
"""
import argparse
import subprocess
import sys
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd: list, description: str) -> bool:
    """명령어 실행 및 결과 확인"""
    logger.info(f"\n{'='*60}")
    logger.info(f"실행: {description}")
    logger.info(f"명령어: {' '.join(cmd)}")
    logger.info(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ {description} 완료")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            logger.error(f"❌ {description} 실패")
            if result.stderr:
                logger.error(f"에러: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ {description} 실행 중 오류 발생: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="주얼리 이미지 일괄 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python generate_all.py --image samples/necklace.png --type necklace
  python generate_all.py --image samples/ring.jpg --type ring --out custom_output
        """
    )
    
    parser.add_argument(
        "--image", 
        required=True,
        help="입력 이미지 경로"
    )
    
    parser.add_argument(
        "--type",
        required=True,
        help="주얼리 타입 (ring, necklace, earring, bracelet, anklet, etc)"
    )
    
    parser.add_argument(
        "--out",
        help="출력 디렉토리 (기본값: 자동 생성)"
    )
    
    parser.add_argument(
        "--skip-desc",
        action="store_true",
        help="상품 설명 생성 건너뛰기"
    )
    
    args = parser.parse_args()
    
    # 입력 이미지 확인
    image_path = Path(args.image)
    if not image_path.exists():
        logger.error(f"이미지 파일을 찾을 수 없습니다: {args.image}")
        sys.exit(1)
    
    # 기본 출력 디렉토리 설정
    if args.out:
        base_out_dir = args.out
    else:
        # 이미지 파일명을 기반으로 출력 디렉토리 생성
        image_stem = image_path.stem
        base_out_dir = f"out/{image_stem}_{args.type}_all"
    
    logger.info(f"\n🎨 주얼리 이미지 일괄 생성 시작")
    logger.info(f"입력 이미지: {args.image}")
    logger.info(f"주얼리 타입: {args.type}")
    logger.info(f"출력 디렉토리: {base_out_dir}")
    
    # 실행할 작업 목록
    tasks = []
    
    # 1. 상품 설명 생성
    if not args.skip_desc:
        tasks.append({
            "name": "상품 설명 생성",
            "cmd": [
                sys.executable, "-m", "src.cli_desc",
                "--image", args.image,
                "--type", args.type,
                "--out", f"{base_out_dir}/desc"
            ]
        })
    
    # 2. 제품 연출컷 생성 (3:4)
    tasks.append({
        "name": "제품 연출컷 생성",
        "cmd": [
            sys.executable, "-m", "src.cli_styled",
            "--image", args.image,
            "--type", args.type,
            "--out", f"{base_out_dir}/styled"
        ]
    })
    
    # 주얼리 타입에 따라 작업 분기
    standard_types = ["ring", "necklace", "earring", "bracelet", "anklet"]
    
    if args.type.lower() in standard_types:
        # 3. 착용컷 생성 (3:4)
        tasks.append({
            "name": "착용컷 생성",
            "cmd": [
                sys.executable, "-m", "src.cli_wear",
                "--image", args.image,
                "--type", args.type,
                "--out", f"{base_out_dir}/wear"
            ]
        })
        
        # 4. 클로즈업 착용컷 생성 (3:4)
        tasks.append({
            "name": "클로즈업 착용컷 생성",
            "cmd": [
                sys.executable, "-m", "src.cli_wear_closeup",
                "--image", args.image,
                "--type", args.type,
                "--out", f"{base_out_dir}/closeup"
            ]
        })
    else:
        # 기타 주얼리의 경우 연출컷 3개 생성
        for i in range(1, 4):
            tasks.append({
                "name": f"제품 연출컷 {i} 생성",
                "cmd": [
                    sys.executable, "-m", "src.cli_styled",
                    "--image", args.image,
                    "--type", args.type,
                    "--out", f"{base_out_dir}/styled{i}"
                ]
            })
    
    # 작업 실행
    total_tasks = len(tasks)
    success_count = 0
    
    for i, task in enumerate(tasks, 1):
        logger.info(f"\n[{i}/{total_tasks}] {task['name']}")
        
        if run_command(task["cmd"], task["name"]):
            success_count += 1
        else:
            logger.warning(f"⚠️  {task['name']} 실패, 다음 작업 계속 진행...")
    
    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 작업 완료!")
    logger.info(f"성공: {success_count}/{total_tasks}")
    logger.info(f"출력 디렉토리: {base_out_dir}")
    logger.info(f"{'='*60}")
    
    # 실패한 작업이 있으면 exit code 1
    if success_count < total_tasks:
        sys.exit(1)


if __name__ == "__main__":
    main()