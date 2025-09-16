#!/bin/bash

# 가상환경 활성화
source .venv/bin/activate

echo "🔧 jewelry-ai-gen 테스트 실행"
echo "================================"

# OpenAI API 키 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 API 키를 설정하세요."
    exit 1
fi

# API 키가 설정되었는지 확인
if grep -q "your-openai-api-key-here" .env; then
    echo "⚠️  OpenAI API 키를 설정해주세요:"
    echo "   vi .env  # OPENAI_API_KEY=sk-your-actual-key"
    echo ""
    echo "테스트는 API 키 없이도 기본 처리로 실행됩니다."
    echo ""
fi

echo "1️⃣ 상품 설명 생성 테스트"
python -m src.cli_desc --image samples/ring01.jpg --type ring --out out/test_desc
echo ""

echo "2️⃣ 누끼컷 생성 테스트"
python -m src.cli_thumb --image samples/ring01.jpg --type ring --out out/test_thumb
echo ""

echo "3️⃣ 연출컷 생성 테스트"
python -m src.cli_styled --image samples/ring01.jpg --type ring --out out/test_styled
echo ""

echo "4️⃣ 착용컷 생성 테스트"
python -m src.cli_wear --image samples/ring01.jpg --type ring --out out/test_wear
echo ""

echo "5️⃣ 클로즈업 착용컷 생성 테스트"
python -m src.cli_wear_closeup --image samples/ring01.jpg --type ring --out out/test_closeup
echo ""

echo "✅ 모든 테스트 완료!"
echo "📁 결과 확인: ls -la out/test_*"
echo ""
echo "🔍 생성된 파일들:"
find out/test_* -type f 2>/dev/null | head -20