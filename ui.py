#!/usr/bin/env python3
"""
주얼리 생성 시스템 GUI 실행
"""
import sys

try:
    from src.ui.main_window import main
except ImportError as e:
    print("Error: PySide6가 설치되지 않았습니다.")
    print("다음 명령으로 설치해주세요:")
    print("  pip install -r requirements.txt")
    print(f"\n상세 오류: {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()