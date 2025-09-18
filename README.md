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

## 사용법

### 1. 상품 설명 생성

```bash
python -m src.cli_desc --image samples/ring01.jpg --type ring --out out/ring01_desc
```

### 2. 누끼컷 생성 (1:1)

```bash
python -m src.cli_thumb --image samples/ring01.jpg --type ring --out out/ring01_thumb
```

### 3. 제품 연출컷 생성 (2:3)

```bash
python -m src.cli_styled --image samples/ring01.jpg --type ring --out out/ring01_styled
```

### 4. 착용컷 생성 (2:3)

```bash
python -m src.cli_wear --image samples/ring01.jpg --type ring --out out/ring01_wear
```

### 5. 클로즈업 착용컷 생성 (2:3)

```bash
python -m src.cli_wear_closeup --image samples/ring01.jpg --type ring --out out/ring01_close
```

## 공통 옵션

- `--image <경로>`: 기준 이미지 파일 경로 (필수)
- `--type <종류>`: 주얼리 종류 (필수)
  - 지원: ring, necklace, earring, bracelet, pendant, 기타 텍스트
- `--out <경로>`: 출력 디렉토리 (선택)
  - 미지정 시: `out/작업종류_YYYYmmdd_HHMMSS`

## 출력 구조

```
out/
└── 작업명_20240101_123456/
    ├── meta.json          # 실행 메타데이터
    ├── run.log           # 실행 로그
    └── [작업별 결과물]
        ├── desc.md                    # 상품 설명
        ├── thumb_1to1.png            # 누끼컷
        ├── styled_2x3_01.png         # 연출컷
        ├── wear_2x3_01.png           # 착용컷
        └── wear_closeup_2x3_01.png   # 클로즈업
```

### 6. 일괄 생성 (전체 프로세스 한번에 실행)

#### Python 스크립트 사용

```bash
# 기본 사용법 (상품 설명, 제품 연출컷, 착용컷, 클로즈업 착용컷 모두 생성)
python generate_all.py --image samples/necklace.png --type necklace

# 출력 디렉토리 지정
python generate_all.py --image samples/ring.jpg --type ring --out out/my_ring

# 상품 설명 생성 건너뛰기
python generate_all.py --image samples/bracelet.jpg --type bracelet --skip-desc
```

#### Bash 스크립트 사용

```bash
# 기본 사용법
./generate_all.sh samples/necklace.png necklace

# 출력 디렉토리 지정
./generate_all.sh samples/ring.jpg ring out/my_ring
```

생성되는 디렉토리 구조:

```
out/necklace_necklace_all/
├── desc/           # 상품 설명
│   └── description.txt
├── styled/         # 제품 연출컷
│   └── styled_2x3_01.jpg
├── wear/           # 착용컷
│   └── wear_2x3_01.jpg
└── closeup/        # 클로즈업 착용컷
    └── wear_closeup_2x3_01.jpg
```

## 주의사항

- OpenAI API 키가 필요합니다
- 제품의 형태나 디자인을 변형하지 않도록 프롬프트가 설정되어 있습니다
- 생성된 이미지의 저작권 및 초상권 관련 책임은 사용자에게 있습니다
- 입력 이미지는 자동으로 최대 2048px로 리사이징됩니다

## 확장 예정 기능

- 웹 API 인터페이스 (FastAPI)
