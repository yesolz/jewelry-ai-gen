#!/usr/bin/env python3
"""
주얼리 상품 설명 생성 CLI
"""
import argparse
import sys
from pathlib import Path

from .processor import process_description
from .logging_conf import setup_logging


def main():
    parser = argparse.ArgumentParser(description="주얼리 상품 설명 생성")
    parser.add_argument("--image", required=True, help="기준 이미지 경로")
    parser.add_argument("--type", required=True, help="주얼리 종류 (ring|necklace|earring|bracelet|pendant|기타)")
    parser.add_argument("--out", help="출력 디렉토리")
    
    args = parser.parse_args()
    
    # 로깅 설정
    if args.out:
        out_path = Path(args.out)
        out_path.mkdir(parents=True, exist_ok=True)
        log_file = out_path / "run.log"
        setup_logging(log_file)
    else:
        setup_logging()
    
    try:
        # 상품 설명 생성 처리
        output_dir = process_description(
            image_path=args.image,
            jewelry_type=args.type,
            output_dir=args.out
        )
        print(f"✅ 상품 설명 생성 완료: {output_dir}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 에러 발생: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()