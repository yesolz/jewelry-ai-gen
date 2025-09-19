#!/bin/bash
# 주얼리 이미지 일괄 생성 스크립트

# 사용법 출력
usage() {
    echo "사용법: $0 <이미지경로> <주얼리타입> [출력디렉토리]"
    echo ""
    echo "주얼리 타입:"
    echo "  - ring: 반지"
    echo "  - necklace: 목걸이"
    echo "  - earring: 귀걸이"
    echo "  - bracelet: 팔찌"
    echo "  - anklet: 발찌"
    echo "  - etc: 기타 (brooch, tiara 등)"
    echo ""
    echo "예제:"
    echo "  $0 samples/necklace.png necklace"
    echo "  $0 samples/ring.jpg ring out/custom_output"
    exit 1
}

# 인자 확인
if [ $# -lt 2 ]; then
    usage
fi

IMAGE_PATH="$1"
JEWELRY_TYPE="$2"
OUTPUT_DIR="${3:-out/$(basename "$IMAGE_PATH" | cut -d. -f1)_${JEWELRY_TYPE}_all}"

# 이미지 파일 확인
if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ 오류: 이미지 파일을 찾을 수 없습니다: $IMAGE_PATH"
    exit 1
fi

# 주얼리 타입은 이제 자유롭게 입력 가능

echo "🎨 주얼리 이미지 일괄 생성 시작"
echo "================================"
echo "입력 이미지: $IMAGE_PATH"
echo "주얼리 타입: $JEWELRY_TYPE"
echo "출력 디렉토리: $OUTPUT_DIR"
echo "================================"
echo ""

# 표준 주얼리 타입 확인
STANDARD_TYPES=("ring" "necklace" "earring" "bracelet" "anklet")
IS_STANDARD=0

# 주얼리 타입을 소문자로 변환하여 비교
JEWELRY_TYPE_LOWER=$(echo "$JEWELRY_TYPE" | tr '[:upper:]' '[:lower:]')

for type in "${STANDARD_TYPES[@]}"; do
    if [ "$JEWELRY_TYPE_LOWER" = "$type" ]; then
        IS_STANDARD=1
        break
    fi
done

# 작업 카운터 (표준 타입은 4개, 기타는 5개)
if [ $IS_STANDARD -eq 1 ]; then
    TOTAL=4
else
    TOTAL=5  # 설명 + 연출컷1개 + 추가 연출컷3개
fi
CURRENT=0
SUCCESS=0

# 함수: 명령 실행 및 결과 표시
run_task() {
    local TASK_NAME="$1"
    local CMD="$2"
    
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/$TOTAL] $TASK_NAME"
    echo "명령어: $CMD"
    echo "--------------------------------"
    
    if eval "$CMD"; then
        echo "✅ $TASK_NAME 완료"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "❌ $TASK_NAME 실패"
    fi
    echo ""
}

# 1. 상품 설명 생성
run_task "상품 설명 생성" \
    "python -m src.cli_desc --image '$IMAGE_PATH' --type '$JEWELRY_TYPE' --out '$OUTPUT_DIR/desc'"

# 2. 제품 연출컷 생성 (3:4)
run_task "제품 연출컷 생성" \
    "python -m src.cli_styled --image '$IMAGE_PATH' --type '$JEWELRY_TYPE' --out '$OUTPUT_DIR/styled'"

if [ $IS_STANDARD -eq 1 ]; then
    # 표준 주얼리 타입인 경우: 착용컷 생성
    # 3. 착용컷 생성 (3:4)
    run_task "착용컷 생성" \
        "python -m src.cli_wear --image '$IMAGE_PATH' --type '$JEWELRY_TYPE' --out '$OUTPUT_DIR/wear'"

    # 4. 클로즈업 착용컷 생성 (3:4)
    run_task "클로즈업 착용컷 생성" \
        "python -m src.cli_wear_closeup --image '$IMAGE_PATH' --type '$JEWELRY_TYPE' --out '$OUTPUT_DIR/closeup'"
else
    # 기타 주얼리 타입인 경우: 추가 연출컷 3개 생성
    for i in 1 2 3; do
        run_task "제품 연출컷 $i 생성" \
            "python -m src.cli_styled --image '$IMAGE_PATH' --type '$JEWELRY_TYPE' --out '$OUTPUT_DIR/styled$i'"
    done
fi

# 결과 요약
echo "================================"
echo "🎯 작업 완료!"
echo "성공: $SUCCESS/$TOTAL"
echo "출력 디렉토리: $OUTPUT_DIR"
echo "================================"

# 디렉토리 내용 표시
if [ -d "$OUTPUT_DIR" ]; then
    echo ""
    echo "📁 생성된 파일들:"
    find "$OUTPUT_DIR" -type f -name "*.jpg" -o -name "*.txt" | sort
fi

# 실패한 작업이 있으면 exit code 1
if [ $SUCCESS -lt $TOTAL ]; then
    exit 1
fi