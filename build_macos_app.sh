#!/bin/bash
echo "🎯 주얼리 AI 생성 시스템 - macOS .app 번들 생성"
echo "================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 오류 처리
set -e
trap 'echo -e "${RED}❌ 빌드 중 오류가 발생했습니다${NC}"; exit 1' ERR

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo -e "${BLUE}🔄 가상환경 활성화...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${BLUE}🔄 가상환경 활성화...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다.${NC}"
fi

# Python 버전 확인
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "${BLUE}🐍 Python 버전: $python_version${NC}"

# 의존성 설치
echo -e "${BLUE}🔄 의존성 설치 중...${NC}"
pip3 install -r requirements.txt

# 기존 빌드 정리
echo -e "${BLUE}🧹 기존 빌드 파일 정리...${NC}"
rm -rf build dist

# py2app 빌드 실행
echo -e "${BLUE}🚀 .app 번들 생성 시작...${NC}"
python3 setup.py py2app

# 결과 확인
if [ -d "dist/JewelryAI.app" ]; then
    echo -e "${GREEN}✅ .app 번들 생성 성공!${NC}"
    echo -e "${BLUE}📁 앱 번들: dist/JewelryAI.app${NC}"
    echo
    
    # 앱 크기 확인
    app_size=$(du -sh dist/JewelryAI.app | cut -f1)
    echo -e "${BLUE}📊 앱 크기: $app_size${NC}"
    echo
    
    # 설치 방법 안내
    echo -e "${YELLOW}📋 설치 방법:${NC}"
    echo "1. dist/JewelryAI.app을 Applications 폴더로 드래그앤드롭"
    echo "2. 또는 더블클릭으로 바로 실행"
    echo "3. Launchpad에서 'JewelryAI' 검색"
    echo
    
    # Applications 폴더로 자동 복사 옵션
    read -p "📂 Applications 폴더로 자동 설치할까요? (Y/n): " install_app
    if [[ $install_app != "n" && $install_app != "N" && $install_app != "no" ]]; then
        if [ -d "/Applications" ]; then
            echo -e "${BLUE}🔄 Applications 폴더로 설치 중...${NC}"
            
            # 기존 앱이 있다면 제거
            if [ -d "/Applications/JewelryAI.app" ]; then
                echo -e "${YELLOW}⚠️  기존 앱을 제거합니다...${NC}"
                rm -rf "/Applications/JewelryAI.app"
            fi
            
            cp -R "dist/JewelryAI.app" "/Applications/"
            echo -e "${GREEN}✅ 설치 완료! Launchpad에서 'JewelryAI'를 찾아보세요${NC}"
            
            # 바로 실행할지 묻기
            read -p "🚀 지금 앱을 실행할까요? (Y/n): " run_app
            if [[ $run_app != "n" && $run_app != "N" && $run_app != "no" ]]; then
                open "/Applications/JewelryAI.app"
                echo -e "${GREEN}✅ 앱을 실행했습니다!${NC}"
            fi
        else
            echo -e "${RED}❌ Applications 폴더를 찾을 수 없습니다${NC}"
        fi
    fi
    
    # Finder에서 폴더 열기
    read -p "📂 Finder에서 dist 폴더를 열까요? (Y/n): " open_finder
    if [[ $open_finder != "n" && $open_finder != "N" && $open_finder != "no" ]]; then
        open dist
    fi
    
else
    echo -e "${RED}❌ .app 번들을 찾을 수 없습니다${NC}"
    exit 1
fi

echo
echo -e "${GREEN}🎉 macOS 앱 번들 생성 완료!${NC}"
echo -e "${BLUE}💡 이제 다른 Mac에서도 Python 설치 없이 실행할 수 있습니다${NC}"