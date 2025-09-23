# 주얼리 AI 생성 시스템 - macOS 앱 빌드 가이드

py2app을 사용하여 macOS .app 번들을 만드는 방법입니다.

## 🚀 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 앱 빌드 (자동화)
./build_macos_app.sh

# 또는 수동으로
python setup.py py2app
```

## 📋 결과물

- **파일**: `dist/JewelryAI.app`
- **크기**: 약 200-300MB
- **실행**: 더블클릭으로 바로 실행
- **설치**: Applications 폴더로 드래그앤드롭

## 🖥️ 설치 방법

### 자동 설치 (빌드 스크립트 사용)
```bash
./build_macos_app.sh
# 스크립트가 자동으로 Applications 폴더 설치까지 진행
```

### 수동 설치
1. `dist/JewelryAI.app`을 Applications 폴더로 복사
2. Launchpad에서 "JewelryAI" 검색
3. 또는 Dock에 드래그앤드롭

## 📤 다른 사람에게 전달

### 방법 1: .app 파일 직접 전달
```bash
# 압축해서 전달
zip -r JewelryAI.zip dist/JewelryAI.app
```

### 방법 2: DMG 이미지 생성
```bash
# DMG 파일 생성 (더 전문적)
hdiutil create -volname "JewelryAI" -srcfolder dist/JewelryAI.app -ov -format UDZO JewelryAI.dmg
```

## ✅ 포함된 것들

**py2app으로 번들된 .app 파일에는 모든 것이 포함됩니다:**
- Python 인터프리터
- 모든 pip 패키지 (PySide6, OpenAI, PIL 등)
- 프로젝트 소스 코드
- 설정 파일들

**받는 사람이 할 일:**
- Python 설치 불필요 ✅
- pip install 불필요 ✅  
- 더블클릭만 하면 바로 실행 ✅

## 🔧 문제 해결

### 1. 빌드 실패
```bash
# 기존 빌드 정리 후 재시도
rm -rf build dist
python setup.py py2app
```

### 2. 앱이 안 열림
- **macOS Gatekeeper**: 시스템 환경설정 → 보안 및 개인정보보호 → "확인되지 않은 개발자" 허용
- **터미널에서 실행하여 에러 확인**:
  ```bash
  /path/to/JewelryAI.app/Contents/MacOS/JewelryAI
  ```

### 3. 의존성 문제
```bash
# 가상환경에서 빌드 권장
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py py2app
```

## 📁 파일 구조

```
jewelry-ai-gen/
├── setup.py              # py2app 설정 파일
├── build_macos_app.sh     # 자동 빌드 스크립트
├── ui.py                  # 메인 GUI 애플리케이션
├── icon.icns              # 앱 아이콘 (선택사항)
├── requirements.txt       # 의존성 목록
├── dist/                  # 빌드 결과물
│   └── JewelryAI.app     # 실행 가능한 앱 번들
└── build/                # 빌드 임시 파일들
```

## 💡 팁

- **아이콘 추가**: `icon.icns` 파일을 추가하면 앱에 아이콘이 적용됩니다
- **가상환경 사용**: 깔끔한 빌드를 위해 가상환경에서 빌드하는 것을 권장합니다
- **첫 실행**: 앱 첫 실행 시 작업 폴더 설정 가이드가 나타납니다
- **설정 저장**: 한번 설정하면 앱 재시작 후에도 설정이 유지됩니다