#!/usr/bin/env python3
"""
주얼리 제품 연출컷(3:4) 생성 CLI
"""
import argparse
import sys
from pathlib import Path

from .processor import process_styled
from .logging_conf import setup_logging


def main():
    parser = argparse.ArgumentParser(description="주얼리 제품 연출컷 생성")
    parser.add_argument("--image", required=True, help="기준 이미지 경로")
    parser.add_argument("--type", required=True, help="주얼리 종류 (ring|necklace|earring|bracelet|anklet|etc)")
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
        # 연출컷 생성 처리
        output_dir = process_styled(
            image_path=args.image,
            jewelry_type=args.type,
            output_dir=args.out
        )
        print(f"✅ 연출컷 생성 완료: {output_dir}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 에러 발생: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()