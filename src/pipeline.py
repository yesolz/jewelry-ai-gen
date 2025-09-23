#!/usr/bin/env python3
"""
핵심 파이프라인 함수들
- generate_all: 4개 산출물 일괄 생성
- regenerate: 개별 산출물 재생성
"""
import hashlib
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any
from PIL import Image

logger = logging.getLogger(__name__)

ArtifactType = Literal["desc", "styled", "wear", "closeup"]

STANDARD_JEWELRY_TYPES = ["ring", "necklace", "earring", "bracelet", "anklet"]


def generate_job_id(file_path: Path, item_type: str) -> str:
    """파일 바이트와 item_type으로 job_id 생성 (SHA1 기반)"""
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    # 파일 바이트 + item_type을 조합하여 해시 생성
    content = file_bytes + item_type.encode('utf-8')
    sha1_hash = hashlib.sha1(content).hexdigest()
    
    # 앞 12자리만 사용
    return f"J{sha1_hash[:11]}"


def resize_image(image_path: Path, max_size: int = 2048) -> Path:
    """이미지 리사이즈 (최대 크기 제한)"""
    img = Image.open(image_path)
    
    # 이미지가 이미 작으면 그대로 반환
    if img.width <= max_size and img.height <= max_size:
        return image_path
    
    # 리사이즈 필요
    ratio = min(max_size / img.width, max_size / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # work 디렉토리에 임시 저장
    work_dir = Path("work")
    work_dir.mkdir(exist_ok=True)
    
    resized_path = work_dir / f"resized_{image_path.name}"
    resized.save(resized_path, quality=95)
    
    return resized_path


def run_generation_command(cmd: List[str], artifact_type: str) -> Dict[str, Any]:
    """생성 명령 실행 및 결과 반환"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "artifact": artifact_type,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            return {
                "success": False,
                "artifact": artifact_type,
                "error": result.stderr or "Unknown error",
                "stdout": result.stdout
            }
    except Exception as e:
        return {
            "success": False,
            "artifact": artifact_type,
            "error": str(e)
        }


def update_meta_json(meta_path: Path, artifact_type: str, version: int, 
                    prompt_data: Dict, success: bool, error: Optional[str] = None):
    """meta.json 업데이트"""
    # 기존 meta.json 읽기
    if meta_path.exists():
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    else:
        # 새로 생성
        meta = {
            "artifacts": {
                "desc": {"latest": 0, "versions": []},
                "styled": {"latest": 0, "versions": []},
                "wear": {"latest": 0, "versions": []},
                "closeup": {"latest": 0, "versions": []},
            },
            "errors": []
        }
    
    # 성공한 경우에만 버전 정보 추가
    if success:
        artifact_data = meta["artifacts"][artifact_type]
        
        # 파일 경로 결정
        if artifact_type == "desc":
            file_path = f"{artifact_type}/desc_v{version}.md"
        else:
            file_path = f"{artifact_type}/{artifact_type}_v{version}.png"
        
        # 버전 정보 추가
        version_info = {
            "v": version,
            "path": file_path,
            "prompt": prompt_data,
            "created_at": datetime.now().isoformat()
        }
        
        artifact_data["versions"].append(version_info)
        artifact_data["latest"] = version
        
        # 심볼릭 링크 생성/업데이트 (최신 버전 가리키기)
        job_dir = meta_path.parent
        latest_link = job_dir / artifact_type / (f"{artifact_type}.md" if artifact_type == "desc" else f"{artifact_type}.png")
        versioned_file = job_dir / file_path
        
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        # 상대 경로로 심볼릭 링크 생성
        latest_link.symlink_to(versioned_file.relative_to(latest_link.parent))
    else:
        # 실패 정보 추가
        meta["errors"].append({
            "artifact": artifact_type,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    # meta.json 저장
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def generate_all(input_path: str, item_type: str, out_dir: Optional[str] = None) -> Dict:
    """
    주얼리 이미지에서 4개 산출물 일괄 생성
    
    Args:
        input_path: 입력 이미지 경로
        item_type: 주얼리 타입 (ring, necklace, etc.)
        out_dir: 출력 디렉토리 (None일 경우 자동 생성)
    
    Returns:
        Dict: 생성 결과 정보
    """
    input_path = Path(input_path)
    
    # job_id 생성
    job_id = generate_job_id(input_path, item_type)
    
    # 출력 디렉토리 설정
    if out_dir is None:
        out_dir = f"out/{job_id}"
    out_path = Path(out_dir)
    
    # work 디렉토리 준비
    work_dir = Path("work") / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # 이미지 리사이즈 및 work 디렉토리로 복사
    resized_path = resize_image(input_path)
    work_image = work_dir / "input.png"
    shutil.copy2(resized_path, work_image)
    
    # meta.json 초기화
    meta_path = out_path / "meta.json"
    out_path.mkdir(parents=True, exist_ok=True)
    
    initial_meta = {
        "job_id": job_id,
        "src_name": input_path.name,
        "type": item_type,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "input_path": str(input_path),
        "artifacts": {
            "desc": {"latest": 0, "versions": []},
            "styled": {"latest": 0, "versions": []},
            "wear": {"latest": 0, "versions": []},
            "closeup": {"latest": 0, "versions": []},
            "styled2": {"latest": 0, "versions": []},
            "styled3": {"latest": 0, "versions": []},
        },
        "errors": []
    }
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(initial_meta, f, indent=2, ensure_ascii=False)
    
    # 생성 작업 목록 구성
    tasks = []
    results = {
        "job_id": job_id,
        "out_dir": str(out_path),
        "artifacts": {},
        "errors": []
    }
    
    # 1. 상품 설명 생성
    tasks.append({
        "type": "desc",
        "cmd": [
            sys.executable, "-m", "src.cli_desc",
            "--image", str(work_image),
            "--type", item_type,
            "--out", str(out_path / "desc")
        ]
    })
    
    # 2. 제품 연출컷
    tasks.append({
        "type": "styled",
        "cmd": [
            sys.executable, "-m", "src.cli_styled",
            "--image", str(work_image),
            "--type", item_type,
            "--out", str(out_path / "styled")
        ]
    })
    
    # 3. 표준 주얼리 타입인 경우 착용컷과 클로즈업
    if item_type.lower() in STANDARD_JEWELRY_TYPES:
        tasks.append({
            "type": "wear",
            "cmd": [
                sys.executable, "-m", "src.cli_wear",
                "--image", str(work_image),
                "--type", item_type,
                "--out", str(out_path / "wear")
            ]
        })
        
        tasks.append({
            "type": "closeup",
            "cmd": [
                sys.executable, "-m", "src.cli_wear_closeup",
                "--image", str(work_image),
                "--type", item_type,
                "--out", str(out_path / "closeup")
            ]
        })
    else:
        # 기타 주얼리는 연출컷 3개 추가 생성
        for i in range(2, 4):
            styled_dir = out_path / f"styled{i}"
            tasks.append({
                "type": f"styled{i}",
                "cmd": [
                    sys.executable, "-m", "src.cli_styled",
                    "--image", str(work_image),
                    "--type", item_type,
                    "--out", str(styled_dir)
                ]
            })
    
    # 작업 실행
    success_count = 0
    for task in tasks:
        artifact_type = task["type"]
        result = run_generation_command(task["cmd"], artifact_type)
        
        if result["success"]:
            success_count += 1
            results["artifacts"][artifact_type] = {
                "status": "success",
                "version": 1
            }
            
            # meta.json 업데이트
            # styled2, styled3도 이제 정상적으로 처리
            
            # 생성된 파일을 버전 파일로 이동
            artifact_dir = out_path / artifact_type
            if artifact_type == "desc":
                # desc.md가 있으면 desc_v1.md로 이동
                src_file = artifact_dir / "desc.md"
                if src_file.exists():
                    dst_file = artifact_dir / "desc_v1.md"
                    shutil.move(str(src_file), str(dst_file))
            else:
                # 이미지 파일 찾기 (2:3 또는 3:4 비율)
                if artifact_type == "closeup":
                    # closeup은 wear_closeup_2x3_01.png 형태로 생성됨
                    image_files = list(artifact_dir.glob("wear_closeup_*x*_*.png"))
                elif artifact_type.startswith("styled"):
                    # styled, styled2, styled3 모두 동일한 패턴
                    image_files = list(artifact_dir.glob("*_2x3_*.png")) + list(artifact_dir.glob("*_3x4_*.png"))
                else:
                    # 일반적인 패턴
                    image_files = list(artifact_dir.glob("*_2x3_*.png")) + list(artifact_dir.glob("*_3x4_*.png"))
                
                if image_files:
                    src_file = image_files[0]
                    dst_file = artifact_dir / f"{artifact_type}_v1.png"
                    shutil.move(str(src_file), str(dst_file))
            
            update_meta_json(meta_path, artifact_type, 1, 
                           {}, True)
        else:
            results["errors"].append({
                "artifact": artifact_type,
                "error": result.get("error", "Unknown error")
            })
            
            # meta.json에 에러 기록
            if artifact_type in ["desc", "styled", "wear", "closeup", "styled2", "styled3"]:
                update_meta_json(meta_path, artifact_type, 1, 
                               {}, False, 
                               result.get("error"))
    
    # 최종 상태 업데이트
    with open(meta_path, 'r', encoding='utf-8') as f:
        final_meta = json.load(f)
    
    final_meta["status"] = "done" if success_count == len(tasks) else "partial"
    final_meta["completed_at"] = datetime.now().isoformat()
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(final_meta, f, indent=2, ensure_ascii=False)
    
    results["status"] = final_meta["status"]
    results["total_tasks"] = len(tasks)
    results["success_count"] = success_count
    
    # work 디렉토리 정리 (옵션)
    # shutil.rmtree(work_dir)
    
    return results




if __name__ == "__main__":
    # 테스트 코드
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline test")
    parser.add_argument("--test-generate", action="store_true")
    parser.add_argument("--test-regenerate", action="store_true")
    parser.add_argument("--image", help="Test image path")
    parser.add_argument("--type", help="Jewelry type")
    parser.add_argument("--job-id", help="Job ID for regeneration")
    parser.add_argument("--artifact", help="Artifact to regenerate")
    
    args = parser.parse_args()
    
    if args.test_generate and args.image and args.type:
        result = generate_all(args.image, args.type)
        print(json.dumps(result, indent=2))
    
    elif args.test_regenerate and args.job_id and args.artifact:
        result = regenerate(args.job_id, args.artifact)
        print(json.dumps(result, indent=2))