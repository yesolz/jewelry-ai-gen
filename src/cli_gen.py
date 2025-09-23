#!/usr/bin/env python3
"""
주얼리 생성 통합 CLI
gen run, gen regen, gen export 등 명령 제공
"""
import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .pipeline import generate_all
from .batch_processor import BatchProcessor, process_inbox_folders, get_image_files

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_run(args):
    """스냅샷 일괄 생성 실행"""
    input_dir = Path(args.input)
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # 실행 시작 시간
    run_start = datetime.now()
    run_id = run_start.strftime("run_%Y%m%d_%H%M%S")
    
    # 로그 디렉토리 생성
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 파일 핸들러 추가
    log_file = logs_dir / f"{run_id}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    logger.info(f"Starting batch run: {run_id}")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Workers: {args.workers}")
    
    # 폴더 구조 기반 처리인지 확인
    files_by_type = process_inbox_folders(input_dir)
    
    if files_by_type:
        # 폴더 구조 기반 처리
        logger.info("Detected folder structure - using folder-based processing")
        for jewelry_type, files in files_by_type.items():
            logger.info(f"  {jewelry_type}: {len(files)} files")
        
        total_files = sum(len(files) for files in files_by_type.values())
        
        # 결과 추적
        results = {
            "run_id": run_id,
            "start_time": run_start.isoformat(),
            "input_dir": str(input_dir),
            "total_files": total_files,
            "processed": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "jobs": [],
            "processing_mode": "folder_based",
            "jewelry_types": list(files_by_type.keys())
        }
        
        # 배치 처리기 사용 (폴더 기반)
        processor = BatchProcessor(max_workers=args.workers, timeout_per_file=600)
        
        for file_path, job_result, jewelry_type in processor.process_inbox_batch(input_dir):
            results["processed"] += 1
            
            # 상태별 분류
            status = job_result.get("status", "failed")
            
            if status == "done":
                results["success"] += 1
                logger.info(f"✅ Success ({jewelry_type}): {job_result.get('job_id', 'unknown')}")
                
                # 완전히 성공한 파일만 archive로 이동
                if args.archive:
                    archive_dir = Path("archive/success") / run_id / jewelry_type
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(archive_dir / file_path.name))
                    logger.info(f"Archived to: {archive_dir / file_path.name}")
                    
            elif status == "partial":
                results["partial"] += 1
                logger.info(f"🔶 Partial ({jewelry_type}): {job_result.get('job_id', 'unknown')} - Keeping in inbox for regeneration")
                # partial은 inbox에 그대로 유지 (재생성 대기)
                
            else:
                results["failed"] += 1
                error_msg = job_result.get("error", "Unknown error")
                logger.warning(f"⚠️  Failed ({jewelry_type}): {file_path.name} - {error_msg} - Keeping in inbox")
                # failed도 inbox에 그대로 유지 (재처리 필요)
            
            # 결과 기록
            results["jobs"].append({
                "file": file_path.name,
                "jewelry_type": jewelry_type,
                "job_id": job_result.get("job_id"),
                "status": job_result.get("status", "failed"),
                "artifacts": job_result.get("artifacts", {}),
                "errors": job_result.get("errors", [])
            })
    
    else:
        # 기존 방식: 단일 타입으로 처리
        logger.info(f"No folder structure detected - using single type processing: {args.type}")
        
        # 이미지 파일 찾기
        image_files = get_image_files(input_dir)
        
        if not image_files:
            logger.warning(f"No image files found in {input_dir}")
            return 0
        
        logger.info(f"Found {len(image_files)} images to process")
        
        # 결과 추적
        results = {
            "run_id": run_id,
            "start_time": run_start.isoformat(),
            "input_dir": str(input_dir),
            "total_files": len(image_files),
            "processed": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "jobs": [],
            "processing_mode": "single_type",
            "default_type": args.type
        }
        
        # 배치 처리기 사용 (기존 방식)
        processor = BatchProcessor(max_workers=args.workers, timeout_per_file=600)
        
        for file_path, job_result in processor.process_batch(image_files, args.type):
            results["processed"] += 1
            
            # 상태별 분류
            status = job_result.get("status", "failed")
            
            if status == "done":
                results["success"] += 1
                logger.info(f"✅ Success: {job_result.get('job_id', 'unknown')}")
                
                # 완전히 성공한 파일만 archive로 이동
                if args.archive:
                    archive_dir = Path("archive/success") / run_id / args.type
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(archive_dir / file_path.name))
                    logger.info(f"Archived to: {archive_dir / file_path.name}")
                    
            elif status == "partial":
                results["partial"] += 1
                logger.info(f"🔶 Partial: {job_result.get('job_id', 'unknown')} - Keeping in inbox for regeneration")
                # partial은 inbox에 그대로 유지 (재생성 대기)
                
            else:
                results["failed"] += 1
                error_msg = job_result.get("error", "Unknown error")
                logger.warning(f"⚠️  Failed: {file_path.name} - {error_msg} - Keeping in inbox")
                # failed도 inbox에 그대로 유지 (재처리 필요)
            
            # 결과 기록
            results["jobs"].append({
                "file": file_path.name,
                "jewelry_type": args.type,
                "job_id": job_result.get("job_id"),
                "status": job_result.get("status", "failed"),
                "artifacts": job_result.get("artifacts", {}),
                "errors": job_result.get("errors", [])
            })
    
    # 실행 완료
    run_end = datetime.now()
    results["end_time"] = run_end.isoformat()
    results["duration"] = str(run_end - run_start)
    
    # 실행 요약 저장
    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)
    
    summary_file = runs_dir / f"{run_id}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 결과 출력
    logger.info("\n" + "="*60)
    logger.info("BATCH RUN COMPLETE")
    logger.info(f"Mode: {results['processing_mode']}")
    if results['processing_mode'] == 'folder_based':
        logger.info(f"Types: {', '.join(results['jewelry_types'])}")
    else:
        logger.info(f"Type: {results['default_type']}")
    logger.info(f"Total: {results['total_files']}")
    logger.info(f"Processed: {results['processed']}")
    logger.info(f"Success: {results['success']}")
    logger.info(f"Partial: {results['partial']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Duration: {results['duration']}")
    logger.info(f"Summary: {summary_file}")
    logger.info(f"Log: {log_file}")
    logger.info("="*60)
    
    return 0 if results["failed"] == 0 else 1


def cmd_dry_run(args):
    """실행 대상 목록만 확인"""
    input_dir = Path(args.input)
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # 폴더 구조 기반 처리인지 확인
    files_by_type = process_inbox_folders(input_dir)
    
    if files_by_type:
        # 폴더 구조 기반 처리
        print("📁 Folder structure detected - will process by jewelry type:")
        print("=" * 70)
        
        total_files = 0
        for jewelry_type, files in files_by_type.items():
            total_files += len(files)
            print(f"\n💍 {jewelry_type.upper()} ({len(files)} files):")
            print("-" * 50)
            
            for idx, image_file in enumerate(files, 1):
                size = image_file.stat().st_size / 1024 / 1024  # MB
                print(f"  {idx:2d}. {image_file.name:<35} ({size:.2f} MB)")
        
        print("=" * 70)
        print(f"📊 SUMMARY:")
        print(f"   Processing mode: Folder-based")
        print(f"   Jewelry types: {len(files_by_type)}")
        for jewelry_type, files in files_by_type.items():
            print(f"     - {jewelry_type}: {len(files)} files")
        print(f"   Total files: {total_files}")
        
    else:
        # 기존 방식: 단일 타입으로 처리
        image_files = get_image_files(input_dir)
        
        if not image_files:
            print(f"No image files found in {input_dir}")
            return 0
        
        print("📁 No folder structure detected - will process as single type:")
        print("=" * 70)
        print(f"🔧 Default type: {args.type}")
        print("-" * 50)
        
        for idx, image_file in enumerate(image_files, 1):
            size = image_file.stat().st_size / 1024 / 1024  # MB
            print(f"{idx:3d}. {image_file.name:<40} ({size:.2f} MB)")
        
        print("=" * 70)
        print(f"📊 SUMMARY:")
        print(f"   Processing mode: Single type")
        print(f"   Default type: {args.type}")
        print(f"   Total files: {len(image_files)}")
    
    return 0


def cmd_regen(args):
    """단건 재생성"""
    logger.info(f"Regenerating {args.artifact} for job {args.job}")
    
    # 기존 CLI 모듈 직접 호출
    import json
    import subprocess
    
    job_dir = Path("out") / args.job
    meta_path = job_dir / "meta.json"
    
    if not meta_path.exists():
        logger.error(f"Job {args.job} not found")
        return 1
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    # work 이미지 준비
    work_dir = Path("work") / args.job
    work_image = work_dir / "input.png"
    
    if not work_image.exists():
        logger.info("Preparing work image from original...")
        from .pipeline import resize_image
        import shutil
        
        original_path = Path(meta.get("input_path", ""))
        if original_path.exists():
            work_dir.mkdir(parents=True, exist_ok=True)
            resized_path = resize_image(original_path)
            shutil.copy2(resized_path, work_image)
        else:
            logger.error("Original input image not found")
            return 1
    
    # CLI 명령 구성
    cmd_map = {
        "desc": ["src.cli_desc"],
        "styled": ["src.cli_styled"],
        "wear": ["src.cli_wear"],
        "closeup": ["src.cli_wear_closeup"]
    }
    
    if args.artifact not in cmd_map:
        logger.error(f"Unknown artifact type: {args.artifact}")
        return 1
    
    cmd = [
        sys.executable, "-m", cmd_map[args.artifact][0],
        "--image", str(work_image),
        "--type", meta["type"],
        "--out", str(job_dir / args.artifact)
    ]
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ Regeneration successful!")
            logger.info(f"Job ID: {args.job}")
            logger.info(f"Artifact: {args.artifact}")
            return 0
        else:
            logger.error(f"❌ CLI execution failed")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return 1
    except Exception as e:
        logger.error(f"❌ Execution error: {str(e)}")
        return 1


def cmd_export(args):
    """최종본 export"""
    job_dir = Path("out") / args.job
    if not job_dir.exists():
        logger.error(f"Job not found: {args.job}")
        return 1
    
    # meta.json 읽기
    meta_path = job_dir / "meta.json"
    if not meta_path.exists():
        logger.error("meta.json not found")
        return 1
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    # export 디렉토리 생성
    export_dir = Path(args.to)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # 각 artifact의 최신 버전 복사
    exported = []
    
    for artifact_type in ["desc", "styled", "wear", "closeup"]:
        artifact_info = meta["artifacts"].get(artifact_type, {})
        if artifact_info.get("latest", 0) > 0:
            # 최신 파일 찾기
            latest_file = job_dir / artifact_type / (
                f"{artifact_type}.md" if artifact_type == "desc" else f"{artifact_type}.png"
            )
            
            if latest_file.exists() or latest_file.is_symlink():
                # 실제 파일 경로 가져오기 (심볼릭 링크 해결)
                real_file = latest_file.resolve()
                
                # export 경로
                if artifact_type == "desc":
                    export_file = export_dir / "description.md"
                else:
                    export_file = export_dir / f"{artifact_type}.png"
                
                # 복사
                shutil.copy2(real_file, export_file)
                exported.append({
                    "type": artifact_type,
                    "source": str(latest_file),
                    "destination": str(export_file)
                })
                
                logger.info(f"Exported {artifact_type} -> {export_file}")
    
    # manifest.json 생성
    manifest = {
        "job_id": meta["job_id"],
        "item_type": meta["type"],
        "exported_at": datetime.now().isoformat(),
        "source_job": str(job_dir),
        "artifacts": exported
    }
    
    manifest_path = export_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✅ Export complete!")
    logger.info(f"Destination: {export_dir}")
    logger.info(f"Artifacts: {len(exported)}")
    logger.info(f"Manifest: {manifest_path}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="gen",
        description="Jewelry image generation CLI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # gen run
    run_parser = subparsers.add_parser("run", help="Run batch generation")
    run_parser.add_argument("--input", "--in", default="inbox", help="Input directory")
    run_parser.add_argument("--workers", type=int, default=3, help="Number of workers")
    run_parser.add_argument("--type", default="ring", help="Default jewelry type")
    run_parser.add_argument("--archive", action="store_true", help="Archive processed files")
    
    # gen dry-run
    dry_parser = subparsers.add_parser("dry-run", help="Show files to process")
    dry_parser.add_argument("--input", "--in", default="inbox", help="Input directory")
    
    # gen regen
    regen_parser = subparsers.add_parser("regen", help="Regenerate single artifact")
    regen_parser.add_argument("--job", required=True, help="Job ID")
    regen_parser.add_argument("--artifact", required=True, 
                            choices=["desc", "styled", "wear", "closeup"],
                            help="Artifact type to regenerate")
    
    # gen export
    export_parser = subparsers.add_parser("export", help="Export final artifacts")
    export_parser.add_argument("--job", required=True, help="Job ID")
    export_parser.add_argument("--to", required=True, help="Export destination")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 명령 실행
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "dry-run":
        return cmd_dry_run(args)
    elif args.command == "regen":
        return cmd_regen(args)
    elif args.command == "export":
        return cmd_export(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())