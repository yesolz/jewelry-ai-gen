# jewelry-ai-gen

AI 기반 주얼리 상품 이미지 및 설명 자동 생성 도구

## 설치

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 입력
```

## 빠른 시작

### 1. 폴더 구조 준비 (한번만)

```bash
# 주얼리 타입별 폴더 생성
mkdir -p inbox/{ring,necklace,earring,bracelet,anklet,other}
```

### 2. 이미지 파일 배치

```bash
# 주얼리 타입별로 분류해서 넣기
cp my_ring_photos/* inbox/ring/
cp my_necklace_photos/* inbox/necklace/
```

### 3. 배치 처리 실행

```bash
# 폴더 구조 자동 감지하여 일괄 처리
python -m src.cli_gen run --input inbox --workers 2 --archive

# 또는 GUI로 실행
python -m src.ui.main_window
```

## 주요 기능

### 🖼️ PySide6 GUI 인터페이스

직관적인 그래픽 인터페이스로 모든 기능을 쉽게 사용할 수 있습니다.

```bash
python -m src.ui.main_window
```

**GUI 기능:**

- 📋 **작업 목록**: 모든 작업 상태 실시간 확인
- 🚀 **배치 처리**: 여러 이미지 동시 처리 (병렬 2개)
- 📊 **진행률 표시**: 실시간 진행 상황 모니터링
- 🔍 **미리보기**: 생성된 결과물 즉시 확인 (클릭으로 확대)
- 🔄 **재생성**: 개별 산출물 선택적 재생성
- 📦 **Export**: 최종 결과물 내보내기
- 🗂️ **자동 정리**: 성공한 파일만 archive로 이동

### 📁 폴더 구조 기반 일괄 처리

주얼리 타입별로 폴더를 구성하면 자동으로 감지하여 처리합니다.

#### 폴더 구조 예시

```
inbox/
├── ring/
│   ├── wedding01.jpg
│   └── diamond02.png
├── necklace/
│   ├── gold_chain.jpg
│   └── pearl.png
└── earring/
    └── stud.jpg
```

#### 실행 전 미리보기

```bash
python -m src.cli_gen dry-run --input inbox
```

출력 예시:

```
📁 Folder structure detected - will process by jewelry type:
======================================================================

💍 RING (2 files):
--------------------------------------------------
   1. wedding01.jpg                    (2.45 MB)
   2. diamond02.png                    (1.23 MB)

💍 NECKLACE (2 files):
--------------------------------------------------
   1. gold_chain.jpg                   (3.12 MB)
   2. pearl.png                        (0.98 MB)

======================================================================
📊 SUMMARY:
   Processing mode: Folder-based
   Jewelry types: 2
     - ring: 2 files
     - necklace: 2 files
   Total files: 4
```

#### 배치 처리 실행

```bash
# 기본 실행 (2개 동시 처리)
python -m src.cli_gen run --input inbox --workers 2

# 자동 정리 포함 (성공한 파일만 archive로 이동)
python -m src.cli_gen run --input inbox --workers 2 --archive

# 더 많은 워커로 빠른 처리
python -m src.cli_gen run --input inbox --workers 4 --archive
```

### 🔄 자동 정리 시스템

`--archive` 옵션을 사용하면 처리 결과에 따라 파일을 자동으로 정리합니다.

**동작 방식:**

- ✅ **완전 성공** (done): `archive/success/` 폴더로 이동
- 🔶 **부분 성공** (partial): inbox에 유지 (재생성 대기)
- ❌ **실패** (failed): inbox에 유지 (재처리 필요)

**결과 예시:**

```
# 처리 전
inbox/
├── ring/
│   ├── wedding01.jpg
│   ├── diamond02.png
│   └── broken03.jpg

# 처리 후
inbox/
└── ring/
    ├── diamond02.png    # 🔶 partial - 재생성 필요
    └── broken03.jpg     # ❌ failed - 재시도 필요

archive/success/
└── run_20241101_143022/
    └── ring/
        └── wedding01.jpg  # ✅ 완료된 파일만 이동
```

### 🎨 생성되는 산출물

각 주얼리 이미지에서 4가지 산출물이 생성됩니다:

1. **상품 설명** (desc.md): 한국어 상품명과 설명
2. **제품 연출컷** (styled.png): 2:3 비율 스튜디오 촬영
3. **착용컷** (wear.png): 2:3 비율 착용 이미지
4. **클로즈업** (closeup.png): 2:3 비율 착용 디테일

**기타 주얼리의 경우:**

- 착용컷 대신 추가 연출컷 3장 생성

### 🔁 개별 산출물 재생성

특정 산출물만 다시 생성할 수 있습니다.

```bash
# CLI로 재생성
python -m src.cli_gen regen --job J80fe2801762 --artifact desc    # 상품 설명
python -m src.cli_gen regen --job J80fe2801762 --artifact styled  # 연출컷
python -m src.cli_gen regen --job J80fe2801762 --artifact wear    # 착용컷
python -m src.cli_gen regen --job J80fe2801762 --artifact closeup # 클로즈업

# 또는 GUI에서 재생성 버튼 클릭
```

### 📤 최종 결과물 Export

완성된 작업의 최신 버전을 별도 폴더로 내보낼 수 있습니다.

```bash
# CLI로 export
python -m src.cli_gen export --job J80fe2801762 --to export/final_ring

# 또는 GUI에서 Export 버튼 클릭
```

## 고급 기능

### ⚡ 병렬 처리 성능

ThreadPoolExecutor를 사용한 동시 처리로 대량 작업 시간을 크게 단축합니다.

**성능 비교:**

- 순차 처리: 10개 파일 약 50-60분
- 병렬 처리 (2개): 10개 파일 약 25-30분 (50% 단축)
- 병렬 처리 (4개): 10개 파일 약 15-20분 (70% 단축)

**특징:**

- 파일당 10분 타임아웃
- 실패 시에도 계속 진행
- 실시간 진행률 표시

### 🔢 버전 관리 시스템

모든 산출물은 버전별로 관리되며, 재생성 시 새 버전이 생성됩니다.

```
out/J80fe2801762/
├── meta.json          # 작업 메타데이터
├── desc/
│   ├── desc.md        # 최신 버전 (심볼릭 링크)
│   ├── desc_v1.md     # 버전 1
│   └── desc_v2.md     # 버전 2 (재생성)
└── styled/
    ├── styled.png     # 최신 버전 (심볼릭 링크)
    └── styled_v1.png
```

### 🏷️ Job ID 시스템

파일 내용과 주얼리 타입을 기반으로 고유한 Job ID를 생성합니다.

- SHA1 해시 기반 (처음 11자리)
- 동일 파일 + 동일 타입 = 동일 Job ID

## 개별 CLI 도구

각 산출물을 개별적으로 생성할 수도 있습니다.

### 상품 설명 생성

```bash
python -m src.cli_desc --image samples/ring01.jpg --type ring --out out/ring01_desc
```

### 제품 연출컷 생성 (2:3)

```bash
python -m src.cli_styled --image samples/ring01.jpg --type ring --out out/ring01_styled
```

### 착용컷 생성 (2:3)

```bash
python -m src.cli_wear --image samples/ring01.jpg --type ring --out out/ring01_wear
```

### 클로즈업 착용컷 생성 (2:3)

```bash
python -m src.cli_wear_closeup --image samples/ring01.jpg --type ring --out out/ring01_close
```

## 공통 옵션

- `--image <경로>`: 입력 이미지 파일 경로
- `--type <종류>`: 주얼리 종류
  - 표준: ring, necklace, earring, bracelet, anklet
  - 기타: other
- `--out <경로>`: 출력 디렉토리
- `--workers <수>`: 병렬 처리 워커 수 (기본: 2)
- `--archive`: 성공한 파일 자동 정리

## 시스템 요구사항

- Python 3.8 이상
- OpenAI API 키 (GPT-4V, DALL-E 3)
- 4GB 이상 RAM 권장
- 안정적인 인터넷 연결

## 주의사항

- OpenAI API 키가 필요합니다
- 제품의 형태나 디자인을 변형하지 않도록 프롬프트가 설정되어 있습니다
- 생성된 이미지의 저작권 및 초상권 관련 책임은 사용자에게 있습니다
- 입력 이미지는 자동으로 최대 2048px로 리사이징됩니다

## 문제 해결

### 이미지가 생성되지 않을 때

- OpenAI API 키 확인
- 네트워크 연결 확인
- 입력 이미지 형식 확인 (jpg, png, webp 지원)

### 부분 성공(partial) 상태일 때

- GUI에서 개별 산출물 재생성 버튼 사용
- 또는 CLI로 특정 산출물만 재생성

### 메모리 부족 시

- `--workers` 수를 줄여서 실행 (예: `--workers 1`)
- 이미지 크기 확인 (자동 리사이징됨)

## 라이선스

이 프로젝트는 상업적 사용을 포함하여 자유롭게 사용할 수 있습니다.
생성된 콘텐츠에 대한 책임은 사용자에게 있습니다.
