#!/usr/bin/env python3
"""
배치 처리 시스템
- ThreadPoolExecutor로 2개 동시 처리
- 파일당 10분 타임아웃
- 실패 시 계속 진행
- 폴더 구조 기반 자동 타입 감지
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Generator, Tuple, Dict, List
from datetime import datetime

from .pipeline import generate_all

logger = logging.getLogger(__name__)

# 지원하는 주얼리 타입
JEWELRY_TYPES = ["ring", "necklace", "earring", "bracelet", "anklet", "etc"]


def get_image_files(directory: Path) -> List[Path]:
    """디렉토리에서 이미지 파일 찾기"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(directory.glob(f"*{ext}"))
        image_files.extend(directory.glob(f"*{ext.upper()}"))
    
    return sorted(image_files)


def process_inbox_folders(inbox_dir: Path) -> Dict[str, List[Path]]:
    """
    inbox 하위 폴더별로 파일 분류
    
    Args:
        inbox_dir: inbox 디렉토리 경로
        
    Returns:
        Dict[jewelry_type, files]: 타입별 파일 목록
    """
    files_by_type = {}
    
    if not inbox_dir.exists() or not inbox_dir.is_dir():
        logger.warning(f"Inbox directory not found: {inbox_dir}")
        return files_by_type
    
    # 하위 폴더들을 확인 (모든 폴더 허용)
    for folder in inbox_dir.iterdir():
        if not folder.is_dir():
            continue
            
        folder_name = folder.name.lower()
        image_files = get_image_files(folder)
        if image_files:
            files_by_type[folder_name] = image_files
            logger.info(f"Found {len(image_files)} images in {folder_name}/ folder")
        else:
            logger.info(f"No images found in {folder_name}/ folder")
    
    total_files = sum(len(files) for files in files_by_type.values())
    logger.info(f"Total files to process: {total_files} across {len(files_by_type)} jewelry types")
    
    return files_by_type


class BatchProcessor:
    """배치 처리 관리자"""
    
    def __init__(self, max_workers: int = 2, timeout_per_file: int = 600):
        """
        Args:
            max_workers: 동시 처리할 최대 파일 수 (기본 2개)
            timeout_per_file: 파일당 타임아웃 초 (기본 10분)
        """
        self.max_workers = max_workers
        self.timeout_per_file = timeout_per_file
        self.stats = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None
        }
    
    def process_batch(self, files: List[Path], jewelry_type: str) -> Generator[Tuple[Path, Dict], None, None]:
        """
        파일 목록을 배치로 처리
        
        Args:
            files: 처리할 이미지 파일 목록
            jewelry_type: 주얼리 타입
            
        Yields:
            Tuple[Path, Dict]: (파일경로, 결과딕셔너리)
        """
        self.stats["total"] = len(files)
        self.stats["start_time"] = datetime.now()
        
        logger.info(f"Starting batch processing: {len(files)} files, {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업 제출
            future_to_file = {}
            for file_path in files:
                future = executor.submit(self._process_single_file, file_path, jewelry_type)
                future_to_file[future] = file_path
            
            # 완료되는 대로 결과 수집
            for future in as_completed(future_to_file, timeout=None):
                file_path = future_to_file[future]
                self.stats["processed"] += 1
                
                try:
                    result = future.result(timeout=self.timeout_per_file)
                    
                    if result.get("success", False) or result.get("status") == "done":
                        self.stats["success"] += 1
                        logger.info(f"✅ Success: {file_path.name} -> {result.get('job_id', 'unknown')}")
                    else:
                        self.stats["failed"] += 1
                        logger.warning(f"⚠️  Partial/Failed: {file_path.name}")
                    
                    yield file_path, result
                    
                except Exception as e:
                    self.stats["failed"] += 1
                    error_msg = str(e)
                    
                    if "timeout" in error_msg.lower():
                        logger.error(f"⏰ Timeout: {file_path.name} (>{self.timeout_per_file}s)")
                    else:
                        logger.error(f"❌ Error: {file_path.name} - {error_msg}")
                    
                    yield file_path, {
                        "success": False,
                        "error": error_msg,
                        "timeout": "timeout" in error_msg.lower()
                    }
        
        self.stats["end_time"] = datetime.now()
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        logger.info(f"Batch processing complete:")
        logger.info(f"  Total: {self.stats['total']}")
        logger.info(f"  Success: {self.stats['success']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info(f"  Duration: {duration}")
    
    def _process_single_file(self, file_path: Path, jewelry_type: str) -> Dict:
        """단일 파일 처리"""
        try:
            logger.info(f"Processing: {file_path.name}")
            result = generate_all(
                input_path=str(file_path),
                item_type=jewelry_type
            )
            return result
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict:
        """처리 통계 반환"""
        return self.stats.copy()
    
    def get_progress(self) -> float:
        """진행률 반환 (0.0 ~ 1.0)"""
        if self.stats["total"] == 0:
            return 0.0
        return self.stats["processed"] / self.stats["total"]
    
    def get_success_rate(self) -> float:
        """성공률 반환 (0.0 ~ 1.0)"""
        if self.stats["processed"] == 0:
            return 0.0
        return self.stats["success"] / self.stats["processed"]
    
    def process_inbox_batch(self, inbox_dir: Path) -> Generator[Tuple[Path, Dict, str], None, None]:
        """
        inbox 폴더 구조 기반 배치 처리
        
        Args:
            inbox_dir: inbox 디렉토리 경로
            
        Yields:
            Tuple[Path, Dict, str]: (파일경로, 결과딕셔너리, 주얼리타입)
        """
        # 폴더별로 파일 분류
        files_by_type = process_inbox_folders(inbox_dir)
        
        if not files_by_type:
            logger.warning("No jewelry folders found in inbox")
            return
        
        # 전체 파일 수 계산
        total_files = sum(len(files) for files in files_by_type.values())
        self.stats["total"] = total_files
        self.stats["start_time"] = datetime.now()
        
        logger.info(f"Starting folder-based batch processing: {total_files} files across {len(files_by_type)} types")
        
        # 타입별로 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업 제출 (타입 정보도 함께)
            future_to_file = {}
            for jewelry_type, files in files_by_type.items():
                logger.info(f"Submitting {len(files)} {jewelry_type} files for processing")
                for file_path in files:
                    future = executor.submit(self._process_single_file, file_path, jewelry_type)
                    future_to_file[future] = (file_path, jewelry_type)
            
            # 완료되는 대로 결과 수집
            for future in as_completed(future_to_file, timeout=None):
                file_path, jewelry_type = future_to_file[future]
                self.stats["processed"] += 1
                
                try:
                    result = future.result(timeout=self.timeout_per_file)
                    
                    if result.get("success", False) or result.get("status") == "done":
                        self.stats["success"] += 1
                        logger.info(f"✅ Success: {file_path.name} ({jewelry_type}) -> {result.get('job_id', 'unknown')}")
                    else:
                        self.stats["failed"] += 1
                        logger.warning(f"⚠️  Partial/Failed: {file_path.name} ({jewelry_type})")
                    
                    yield file_path, result, jewelry_type
                    
                except Exception as e:
                    self.stats["failed"] += 1
                    error_msg = str(e)
                    
                    if "timeout" in error_msg.lower():
                        logger.error(f"⏰ Timeout: {file_path.name} ({jewelry_type}) (>{self.timeout_per_file}s)")
                    else:
                        logger.error(f"❌ Error: {file_path.name} ({jewelry_type}) - {error_msg}")
                    
                    yield file_path, {
                        "success": False,
                        "error": error_msg,
                        "timeout": "timeout" in error_msg.lower()
                    }, jewelry_type
        
        self.stats["end_time"] = datetime.now()
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        logger.info(f"Folder-based batch processing complete:")
        logger.info(f"  Total: {self.stats['total']}")
        logger.info(f"  Success: {self.stats['success']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info(f"  Duration: {duration}")


class BatchProgressTracker:
    """배치 처리 진행률 추적기"""
    
    def __init__(self, batch_processor: BatchProcessor):
        self.processor = batch_processor
        self.callbacks = []
    
    def add_progress_callback(self, callback):
        """진행률 업데이트 콜백 추가"""
        self.callbacks.append(callback)
    
    def notify_progress(self, current: int, total: int, current_file: str = ""):
        """진행률 업데이트 알림"""
        progress = current / total if total > 0 else 0.0
        
        for callback in self.callbacks:
            try:
                callback(current, total, progress, current_file)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")


if __name__ == "__main__":
    # 테스트 코드
    import sys
    
    if len(sys.argv) > 1:
        test_files = [Path(f) for f in sys.argv[1:]]
        processor = BatchProcessor(max_workers=2)
        
        for file_path, result in processor.process_batch(test_files, "ring"):
            print(f"{file_path.name}: {result.get('status', 'failed')}")
        
        print(f"Final stats: {processor.get_stats()}")