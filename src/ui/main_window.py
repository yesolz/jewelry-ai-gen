#!/usr/bin/env python3
"""
주얼리 생성 시스템 메인 UI
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QPixmap, QAction, QIcon, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton, QSplitter,
    QGroupBox, QGridLayout, QTextEdit, QFileDialog, QMessageBox,
    QHeaderView, QProgressBar, QToolBar, QComboBox, QSpinBox,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QScrollArea,
    QCheckBox, QTabWidget, QSizePolicy
)

# 프로젝트 루트 경로 설정
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pipeline import generate_all
from src.batch_processor import BatchProcessor, process_inbox_folders
from src.config_manager import config_manager
from src.ui.settings_dialog import SettingsDialog, FirstRunDialog


class ClickableImageLabel(QLabel):
    """클릭 가능한 이미지 라벨"""
    def __init__(self):
        super().__init__()
        self.image_path = None
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("border: 1px solid #ccc;")
        
    def set_image(self, image_path: str):
        """이미지 설정"""
        self.image_path = image_path
        if Path(image_path).exists():
            pixmap = QPixmap(image_path)
            self.setPixmap(pixmap.scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText("(생성되지 않음)")
            self.setPixmap(QPixmap())
    
    def mousePressEvent(self, event):
        """이미지 클릭 시 OS 기본 뷰어로 열기"""
        if event.button() == Qt.LeftButton and self.image_path and Path(self.image_path).exists():
            import subprocess
            import platform
            
            system = platform.system()
            try:
                if system == "Darwin":  # macOS
                    subprocess.run(["open", self.image_path])
                elif system == "Windows":
                    subprocess.run(["start", self.image_path], shell=True)
                else:  # Linux
                    subprocess.run(["xdg-open", self.image_path])
            except Exception as e:
                print(f"Failed to open image: {e}")




class GenerationThread(QThread):
    """백그라운드 생성 작업 스레드"""
    progress = Signal(str, int, int)  # message, current, total
    finished = Signal(dict)  # result
    error = Signal(str)  # error message
    
    def __init__(self, task_type: str, **kwargs):
        super().__init__()
        self.task_type = task_type
        self.kwargs = kwargs
    
    def run(self):
        try:
            if self.task_type == "generate_all":
                result = generate_all(**self.kwargs)
                self.finished.emit(result)
            elif self.task_type == "regenerate_cli":
                # CLI 모듈 직접 호출 (기존 방식)
                result = self._run_cli_regenerate()
                self.finished.emit(result)
            elif self.task_type == "regenerate_direct":
                # 직접 재생성 (병렬처리 최적화)
                result = self._run_direct_regenerate()
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
    
    def _run_cli_regenerate(self):
        """CLI 모듈을 직접 호출하여 재생성"""
        import subprocess
        
        job_id = self.kwargs["job_id"]
        artifact = self.kwargs["artifact"]
        
        # job 정보 읽기
        import json
        from pathlib import Path
        
        job_dir = Path("out") / job_id
        meta_path = job_dir / "meta.json"
        
        if not meta_path.exists():
            return {"success": False, "error": "Job meta.json not found"}
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        # work 이미지 준비
        work_dir = Path("work") / job_id
        work_image = work_dir / "input.png"
        
        if not work_image.exists():
            # 원본에서 다시 생성
            from src.pipeline import resize_image
            import shutil
            
            original_path = Path(meta.get("input_path", ""))
            if original_path.exists():
                work_dir.mkdir(parents=True, exist_ok=True)
                resized_path = resize_image(original_path)
                shutil.copy2(resized_path, work_image)
            else:
                return {"success": False, "error": "Original input image not found"}
        
        # CLI 명령 구성
        cmd = None
        if artifact == "desc":
            cmd = [sys.executable, "-m", "src.cli_desc", "--image", str(work_image), "--type", meta["type"], "--out", str(job_dir / "desc")]
        elif artifact == "styled":
            cmd = [sys.executable, "-m", "src.cli_styled", "--image", str(work_image), "--type", meta["type"], "--out", str(job_dir / "styled")]
        elif artifact in ["styled2", "styled3"]:
            cmd = [sys.executable, "-m", "src.cli_styled", "--image", str(work_image), "--type", meta["type"], "--out", str(job_dir / artifact)]
        elif artifact == "wear":
            cmd = [sys.executable, "-m", "src.cli_wear", "--image", str(work_image), "--type", meta["type"], "--out", str(job_dir / "wear")]
        elif artifact == "closeup":
            cmd = [sys.executable, "-m", "src.cli_wear_closeup", "--image", str(work_image), "--type", meta["type"], "--out", str(job_dir / "closeup")]
        
        if not cmd:
            return {"success": False, "error": f"Unknown artifact type: {artifact}"}
        
        # CLI 실행
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 성공 시 버전 정보 업데이트
                self._update_version_info(job_id, artifact)
                return {"success": True, "job_id": job_id, "artifact": artifact}
            else:
                return {"success": False, "error": result.stderr or "CLI execution failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_version_info(self, job_id: str, artifact: str):
        """버전 정보 업데이트"""
        import json
        import shutil
        from pathlib import Path
        from datetime import datetime
        
        job_dir = Path("out") / job_id
        meta_path = job_dir / "meta.json"
        
        # meta.json 읽기
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        # 다음 버전 번호
        artifact_info = meta["artifacts"].get(artifact, {"latest": 0, "versions": []})
        next_version = len(artifact_info["versions"]) + 1
        
        # 생성된 파일을 버전 파일로 이동
        artifact_dir = job_dir / artifact
        
        if artifact == "desc":
            src_file = artifact_dir / "desc.md"
            dst_file = artifact_dir / f"desc_v{next_version}.md"
        else:
            # 이미지 파일 찾기
            if artifact == "closeup":
                image_files = list(artifact_dir.glob("wear_closeup_*x*_*.png"))
            elif artifact.startswith("styled"):
                # styled, styled2, styled3 모두 동일한 패턴으로 찾기
                image_files = list(artifact_dir.glob("*_2x3_*.png")) + list(artifact_dir.glob("*_3x4_*.png"))
            else:
                image_files = list(artifact_dir.glob("*_2x3_*.png")) + list(artifact_dir.glob("*_3x4_*.png"))
            
            if image_files:
                src_file = image_files[0]
                dst_file = artifact_dir / f"{artifact}_v{next_version}.png"
            else:
                return
        
        # 파일 이동
        if src_file.exists():
            shutil.move(str(src_file), str(dst_file))
        
        # meta.json 업데이트
        version_info = {
            "v": next_version,
            "path": f"{artifact}/{dst_file.name}",
            "created_at": datetime.now().isoformat(),
            "regenerated": True
        }
        
        artifact_info["versions"].append(version_info)
        artifact_info["latest"] = next_version
        
        # 심볼릭 링크 생성/업데이트
        latest_link = artifact_dir / (f"{artifact}.md" if artifact == "desc" else f"{artifact}.png")
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(dst_file.relative_to(latest_link.parent))
        
        # meta.json 저장
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    
    def _run_direct_regenerate(self):
        """직접 재생성 (병렬처리 최적화) - 내부 모듈 직접 호출"""
        job_id = self.kwargs["job_id"]
        artifact = self.kwargs["artifact"]
        
        try:
            # job 정보 읽기
            job_dir = Path("out") / job_id
            meta_path = job_dir / "meta.json"
            
            if not meta_path.exists():
                return {"success": False, "error": "Job meta.json not found"}
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            # work 이미지 경로
            work_dir = Path("work") / job_id
            work_image = work_dir / "input.png"
            
            if not work_image.exists():
                # 원본에서 다시 생성
                from src.pipeline import resize_image
                import shutil
                
                original_path = Path(meta.get("input_path", ""))
                if original_path.exists():
                    work_dir.mkdir(parents=True, exist_ok=True)
                    resized_path = resize_image(original_path)
                    shutil.copy2(resized_path, work_image)
                else:
                    return {"success": False, "error": "Original input image not found"}
            
            # 직접 내부 모듈 호출 (subprocess 없이)
            jewelry_type = meta["type"]
            output_dir = job_dir / artifact
            
            if artifact == "desc":
                from src.processor import process_description
                result_dir = process_description(str(work_image), jewelry_type, str(output_dir))
                result = {"success": True, "output_dir": result_dir}
            elif artifact == "styled" or artifact.startswith("styled"):
                from src.processor import process_styled
                result_dir = process_styled(str(work_image), jewelry_type, str(output_dir))
                result = {"success": True, "output_dir": result_dir}
            elif artifact == "wear":
                from src.processor import process_wear
                result_dir = process_wear(str(work_image), jewelry_type, str(output_dir))
                result = {"success": True, "output_dir": result_dir}
            elif artifact == "closeup":
                from src.processor import process_wear_closeup
                result_dir = process_wear_closeup(str(work_image), jewelry_type, str(output_dir))
                result = {"success": True, "output_dir": result_dir}
            else:
                return {"success": False, "error": f"Unknown artifact type: {artifact}"}
            
            # 성공 시 버전 정보 업데이트
            if result.get("success", True) and result.get("output_dir"):
                self._update_version_info(job_id, artifact)
                return {"success": True, "job_id": job_id, "artifact": artifact}
            else:
                return {"success": False, "error": result.get("error", "Generation failed")}
                
        except ImportError as e:
            return {"success": False, "error": f"모듈 import 실패: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"재생성 실패: {str(e)}"}


class BatchGenerationThread(QThread):
    """배치 생성 작업 스레드 (폴더 기반 지원)"""
    progress = Signal(int, int, str, str)  # current, total, current_file, jewelry_type
    file_completed = Signal(str, dict, str)  # file_name, result, jewelry_type
    batch_finished = Signal(dict)  # final_stats
    error = Signal(str)  # error message
    
    def __init__(self, inbox_dir: Path = None, files: List[Path] = None, jewelry_type: str = None, max_workers: int = 2, auto_archive: bool = False):
        super().__init__()
        self.inbox_dir = inbox_dir
        self.files = files
        self.jewelry_type = jewelry_type
        self.max_workers = max_workers
        self.auto_archive = auto_archive
        self.processor = None
        self.folder_based = inbox_dir is not None
    
    def run(self):
        try:
            self.processor = BatchProcessor(max_workers=self.max_workers)
            
            # 자동 정리를 위한 파일 상태 추적
            file_results = {}
            
            if self.folder_based:
                # 폴더 기반 처리
                for file_path, result, jewelry_type in self.processor.process_inbox_batch(self.inbox_dir):
                    # 자동 정리를 위한 상태 저장
                    if self.auto_archive:
                        file_results[file_path] = (result, jewelry_type)
                    
                    # 개별 파일 완료 신호 (타입 정보 포함)
                    self.file_completed.emit(file_path.name, result, jewelry_type)
                    
                    # 진행률 업데이트
                    stats = self.processor.get_stats()
                    self.progress.emit(stats["processed"], stats["total"], file_path.name, jewelry_type)
            else:
                # 기존 방식: 단일 타입 처리
                for file_path, result in self.processor.process_batch(self.files, self.jewelry_type):
                    # 자동 정리를 위한 상태 저장
                    if self.auto_archive:
                        file_results[file_path] = (result, self.jewelry_type)
                    
                    # 개별 파일 완료 신호
                    self.file_completed.emit(file_path.name, result, self.jewelry_type)
                    
                    # 진행률 업데이트
                    stats = self.processor.get_stats()
                    self.progress.emit(stats["processed"], stats["total"], file_path.name, self.jewelry_type)
            
            # 자동 정리 수행
            if self.auto_archive and file_results:
                self._auto_archive_files(file_results)
            
            # 최종 결과
            final_stats = self.processor.get_stats()
            self.batch_finished.emit(final_stats)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _auto_archive_files(self, file_results):
        """완전히 성공한 파일만 자동 정리"""
        import shutil
        from datetime import datetime
        
        # 실행 ID 생성
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        
        for file_path, (result, jewelry_type) in file_results.items():
            if not file_path.exists():
                continue  # 이미 이동된 파일은 스킵
                
            # 상태 확인
            status = result.get("status", "failed")
            
            # 완전히 성공한 파일만 archive로 이동
            if status == "done":
                # 아카이브 디렉토리 생성
                archive_dir = Path("archive/success") / run_id / jewelry_type
                archive_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    # 파일 이동
                    dest_path = archive_dir / file_path.name
                    shutil.move(str(file_path), str(dest_path))
                    print(f"✅ Archived: {file_path.name} -> {archive_dir}")
                except Exception as e:
                    # 이동 실패 시 로그만 남기고 계속 진행
                    print(f"Failed to archive {file_path.name}: {e}")
            
            elif status == "partial":
                print(f"🔶 Keeping in inbox for regeneration: {file_path.name}")
                # partial은 inbox에 그대로 유지
                
            else:  # failed
                print(f"⚠️  Keeping in inbox for retry: {file_path.name}")
                # failed도 inbox에 그대로 유지


class JobDetailPanel(QWidget):
    """Job 상세 정보 패널"""
    regenerate_requested = Signal(str, str)  # job_id, artifact_type
    export_requested = Signal(str)  # job_id
    
    def __init__(self):
        super().__init__()
        self.current_job = None
        self.setup_ui()
    
    def setup_ui(self):
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 스크롤 내용 위젯
        content_widget = QWidget()
        layout = QVBoxLayout()
        
        # Job 정보
        info_group = QGroupBox("Job 정보")
        info_layout = QFormLayout()
        
        self.job_id_label = QLabel("-")
        self.status_label = QLabel("-")
        self.type_label = QLabel("-")
        self.created_label = QLabel("-")
        
        info_layout.addRow("Job ID:", self.job_id_label)
        info_layout.addRow("상태:", self.status_label)
        info_layout.addRow("종류:", self.type_label)
        info_layout.addRow("생성일:", self.created_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 산출물 미리보기
        artifacts_group = QGroupBox("산출물")
        artifacts_layout = QGridLayout()
        
        # 상품 설명
        desc_widget = QWidget()
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("상품 설명"))
        self.desc_preview = QTextEdit()
        self.desc_preview.setReadOnly(True)
        self.desc_preview.setMaximumHeight(150)
        desc_layout.addWidget(self.desc_preview)
        self.desc_regen_btn = QPushButton("재생성")
        self.desc_regen_btn.clicked.connect(lambda: self.regenerate_artifact("desc"))
        desc_layout.addWidget(self.desc_regen_btn)
        desc_widget.setLayout(desc_layout)
        artifacts_layout.addWidget(desc_widget, 0, 0, 1, 3)  # 3열에 걸쳐 표시
        
        # 이미지 산출물들
        self.image_previews = {}
        
        # 모든 산출물을 한 줄에 나란히 배치 (3개 위치)
        all_image_types = [
            ("styled", "연출컷 1", 1, 0), 
            ("wear", "착용컷", 1, 1), 
            ("closeup", "클로즈업", 1, 2),
            ("styled2", "연출컷 2", 1, 1),  # 기타 타입에서 착용컷 위치에 표시
            ("styled3", "연출컷 3", 1, 2)   # 기타 타입에서 클로즈업 위치에 표시
        ]
        
        for artifact_type, label_text, row, col in all_image_types:
            widget = QWidget()
            layout_v = QVBoxLayout()
            layout_v.addWidget(QLabel(label_text))
            
            # 클릭 가능한 이미지 라벨 사용
            image_label = ClickableImageLabel()
            image_label.setFixedSize(200, 300)
            image_label.setScaledContents(True)
            image_label.setAlignment(Qt.AlignCenter)
            layout_v.addWidget(image_label)
            
            regen_btn = QPushButton("재생성")
            regen_btn.clicked.connect(lambda checked, t=artifact_type: self.regenerate_artifact(t))
            layout_v.addWidget(regen_btn)
            
            widget.setLayout(layout_v)
            artifacts_layout.addWidget(widget, row, col)
            
            self.image_previews[artifact_type] = {
                "label": image_label,
                "button": regen_btn,
                "widget": widget  # 위젯 참조 추가 (숨기기/보이기용)
            }
        
        artifacts_group.setLayout(artifacts_layout)
        layout.addWidget(artifacts_group)
        
        # Export 버튼
        self.export_btn = QPushButton("Export 최종본")
        self.export_btn.clicked.connect(self.export_job)
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
        
        # 스크롤 내용 설정
        content_widget.setLayout(layout)
        scroll_area.setWidget(content_widget)
        
        # 메인 레이아웃에 스크롤 영역 추가
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
    
    def load_job(self, job_id: str):
        """Job 정보 로드 및 표시"""
        self.current_job = job_id
        job_dir = Path("out") / job_id
        
        if not job_dir.exists():
            return
        
        # meta.json 읽기
        meta_path = job_dir / "meta.json"
        if not meta_path.exists():
            return
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print(f"Empty meta.json file: {meta_path}")
                    return
                meta = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in meta.json: {meta_path}, error: {e}")
            return
        except Exception as e:
            print(f"Error reading meta.json: {meta_path}, error: {e}")
            return
        
        # 기본 정보 표시
        self.job_id_label.setText(job_id)
        self.status_label.setText(meta.get("status", "-"))
        self.type_label.setText(meta.get("type", "-"))
        self.created_label.setText(meta.get("created_at", "-")[:19])
        
        # 상품 설명 미리보기
        desc_file = job_dir / "desc" / "desc.md"
        if desc_file.exists():
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.desc_preview.setPlainText(content[:500])
        else:
            self.desc_preview.setPlainText("(생성되지 않음)")
        
        # 주얼리 타입 확인
        jewelry_type = meta.get("type", "").lower()
        is_standard_jewelry = jewelry_type in ["ring", "necklace", "earring", "bracelet", "anklet"]
        
        # 타입에 따라 라벨 동적 변경 및 표시 설정
        for artifact_type, widgets in self.image_previews.items():
            # 모든 위젯을 일단 표시
            widgets["widget"].setVisible(True)
            
            # 라벨 동적 변경
            label_widget = widgets["widget"].layout().itemAt(0).widget()  # QLabel
            
            if is_standard_jewelry:
                # 표준 주얼리: styled, wear, closeup 표시
                if artifact_type == "styled":
                    label_widget.setText("연출컷")
                elif artifact_type == "wear":
                    label_widget.setText("착용컷")
                elif artifact_type == "closeup":
                    label_widget.setText("클로즈업")
                elif artifact_type in ["styled2", "styled3"]:
                    # 추가 연출컷 숨기기
                    widgets["widget"].setVisible(False)
                    continue
            else:
                # 기타 주얼리: styled, styled2, styled3을 연출컷 1, 2, 3으로 표시
                if artifact_type == "styled":
                    label_widget.setText("연출컷 1")
                elif artifact_type == "styled2":
                    label_widget.setText("연출컷 2")
                elif artifact_type == "styled3":
                    label_widget.setText("연출컷 3")
                elif artifact_type in ["wear", "closeup"]:
                    # 착용컷, 클로즈업 숨기기
                    widgets["widget"].setVisible(False)
                    continue
            
            # 이미지 파일 확인 및 설정
            if artifact_type.startswith("styled") and artifact_type != "styled":
                # styled2, styled3의 경우 해당 폴더에서 이미지 찾기
                artifact_dir = job_dir / artifact_type
                if artifact_dir.exists():
                    # 생성된 이미지 파일 찾기
                    image_files = list(artifact_dir.glob("*_2x3_*.png")) + list(artifact_dir.glob("*_3x4_*.png"))
                    if image_files:
                        widgets["label"].set_image(str(image_files[0]))
                        widgets["button"].setEnabled(True)
                    else:
                        widgets["label"].set_image("")
                        widgets["button"].setEnabled(True)
                else:
                    widgets["label"].set_image("")
                    widgets["button"].setEnabled(True)
            else:
                # 기본 산출물들 (styled, wear, closeup)
                image_file = job_dir / artifact_type / f"{artifact_type}.png"
                if image_file.exists():
                    widgets["label"].set_image(str(image_file))
                    widgets["button"].setEnabled(True)
                else:
                    widgets["label"].set_image("")
                    widgets["button"].setEnabled(True)
    
    def regenerate_artifact(self, artifact_type: str):
        """산출물 재생성 요청"""
        if self.current_job:
            self.regenerate_requested.emit(self.current_job, artifact_type)
    
    def export_job(self):
        """Job export 요청"""
        if self.current_job:
            self.export_requested.emit(self.current_job)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    def __init__(self):
        super().__init__()
        self.current_thread = None
        self.batch_thread = None
        self.refresh_timer = None
        
        # 첫 실행 확인 및 설정
        self.check_first_run()
        
        self.setup_ui()
        self.refresh_dashboard_data()
        
        # 자동 새로고침 타이머 (5초)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard_data)
        self.refresh_timer.start(5000)
    
    def setup_ui(self):
        self.setWindowTitle("주얼리 AI 생성 시스템")
        self.resize(1400, 800)
        
        # 툴바
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 새로고침
        refresh_action = QAction("새로고침", self)
        refresh_action.triggered.connect(self.load_jobs)
        toolbar.addAction(refresh_action)
        
        # 설정
        settings_action = QAction("⚙️ 설정", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
        
        toolbar.addSeparator()
        
        
        # 일괄 생성 (강조된 버튼 스타일)
        batch_action = QAction("▶️ 일괄 생성 실행", self)
        batch_action.triggered.connect(self.batch_generate)
        batch_action.setToolTip("inbox 폴더의 이미지들을 일괄 처리합니다")
        toolbar.addAction(batch_action)
        
        # 툴바 스타일 개선
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f6f7fa, stop:1 #dadbde);
                border: 1px solid #c0c0c0;
                spacing: 6px;
                padding: 4px;
            }
            QToolBar QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #e8e8e8);
                border: 1px solid #a0a0a0;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                min-width: 80px;
                color: #333333;
            }
            QToolBar QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e8f4fd, stop:1 #bed8f0);
                border: 1px solid #4a90d9;
                color: #2d679f;
            }
            QToolBar QToolButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #bed8f0, stop:1 #98c4ec);
                border: 1px solid #2d679f;
                color: #1a4d73;
            }
            /* 종료 버튼 특별 스타일 */
            QToolBar QToolButton[text="프로그램 종료"] {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffebee, stop:1 #ffcdd2);
                border: 1px solid #e57373;
                color: #d32f2f;
            }
            QToolBar QToolButton[text="프로그램 종료"]:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffcdd2, stop:1 #ef9a9a);
                border: 1px solid #f44336;
                color: #b71c1c;
            }
            QToolBar QToolButton[text="프로그램 종료"]:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef9a9a, stop:1 #e57373);
                border: 1px solid #d32f2f;
                color: #b71c1c;
            }
        """)
        
        # 폴더 열기
        open_inbox_action = QAction("inbox 폴더 열기", self)
        open_inbox_action.triggered.connect(self.open_inbox_folder)
        toolbar.addAction(open_inbox_action)
        
        open_folder_action = QAction("출력 폴더 열기", self)
        open_folder_action.triggered.connect(self.open_output_folder)
        toolbar.addAction(open_folder_action)
        
        toolbar.addSeparator()
        
        # 우측 공간 확보
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # 종료 버튼 (우측 상단)
        exit_action = QAction("프로그램 종료", self)
        exit_action.triggered.connect(self.close)
        exit_action.setToolTip("프로그램을 안전하게 종료합니다")
        toolbar.addAction(exit_action)
        
        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 레이아웃
        layout = QHBoxLayout()
        
        # 스플리터
        splitter = QSplitter(Qt.Horizontal)
        
        # 좌측: 일반 모드와 대시보드 모드 전환 가능한 위젯
        self.left_widget = QWidget()
        self.setup_dashboard_mode()  # 기본은 대시보드 모드
        splitter.addWidget(self.left_widget)
        
        # 우측: 상세 패널
        self.detail_panel = JobDetailPanel()
        self.detail_panel.regenerate_requested.connect(self.regenerate_artifact)
        self.detail_panel.export_requested.connect(self.export_job)
        splitter.addWidget(self.detail_panel)
        
        splitter.setSizes([700, 700])
        layout.addWidget(splitter)
        
        main_widget.setLayout(layout)
        
        # 상태바에 진행률 바 추가
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(300)
        
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("준비됨")
    
    def check_first_run(self):
        """첫 실행 확인 및 설정 가이드"""
        if config_manager.is_first_run():
            dialog = FirstRunDialog(self)
            if dialog.exec() == QDialog.Accepted:
                # 설정이 완료되면 작업 폴더를 업데이트
                self.update_work_directory()
            else:
                # 나중에 설정하기를 선택한 경우
                config = config_manager.load_config()
                config["first_run"] = False
                config_manager.save_config(config)
        else:
            self.update_work_directory()
    
    def update_work_directory(self):
        """작업 디렉토리 업데이트"""
        work_folder = config_manager.get_work_folder()
        if work_folder:
            # 현재 작업 디렉토리를 설정된 폴더로 변경
            os.chdir(work_folder)
            print(f"✅ 작업 디렉토리: {work_folder}")
        else:
            print("⚠️  작업 폴더가 설정되지 않았습니다. 설정에서 작업 폴더를 선택해주세요.")
        
        # 모든 환경변수 적용
        config_manager.apply_environment_variables()
        
        # 설정 상태 확인
        if config_manager.has_valid_api_key():
            print("✅ API 키가 설정되었습니다.")
        else:
            print("⚠️  API 키가 설정되지 않았습니다. 설정에서 API 키를 입력해주세요.")
        
        model_settings = config_manager.get_model_settings()
        print(f"✅ 모델 설정: 텍스트={model_settings['model_text']}, 이미지={model_settings['model_image']}")
    
    def open_settings(self):
        """설정 다이얼로그 열기"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # 설정 변경 시 작업 디렉토리 업데이트
            self.update_work_directory()
            # 대시보드 새로고침
            self.refresh_dashboard_data()
            QMessageBox.information(self, "설정 완료", "설정이 저장되었습니다.")
    
    def setup_normal_mode(self):
        """일반 모드 UI 설정 (기존 Job 테이블)"""
        # 기존 위젯들 정리
        self._clear_left_widget()
        
        left_layout = QVBoxLayout()
        
        # 검색/필터
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("상태:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["전체", "processing", "reprocessing", "done", "partial", "failed", "오류"])
        self.status_filter.currentTextChanged.connect(self.filter_jobs)
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)
        
        # Job 테이블
        self.job_table = QTableWidget()
        self.job_table.setColumnCount(5)
        self.job_table.setHorizontalHeaderLabels(["Job ID", "종류", "상태", "생성일", "파일명"])
        self.job_table.horizontalHeader().setStretchLastSection(True)
        self.job_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.job_table.itemSelectionChanged.connect(self.on_job_selected)
        left_layout.addWidget(self.job_table)
        
        self.left_widget.setLayout(left_layout)
    
    def setup_dashboard_mode(self):
        """대시보드 모드 UI 설정 (inbox + 완료작업 분할)"""
        # 기존 위젯들 정리
        self._clear_left_widget()
        
        left_layout = QVBoxLayout()
        
        # 상단: inbox 대기 파일들
        inbox_group = QGroupBox("📥 대기 중인 파일 (Inbox)")
        inbox_layout = QVBoxLayout()
        
        # inbox 정보 표시
        inbox_info_layout = QHBoxLayout()
        self.inbox_count_label = QLabel("스캔 중...")
        inbox_info_layout.addWidget(self.inbox_count_label)
        inbox_info_layout.addStretch()
        
        # 새로고침 버튼
        refresh_inbox_btn = QPushButton("새로고침")
        refresh_inbox_btn.clicked.connect(self.refresh_dashboard_data)
        inbox_info_layout.addWidget(refresh_inbox_btn)
        inbox_layout.addLayout(inbox_info_layout)
        
        # inbox 파일 테이블
        self.inbox_table = QTableWidget()
        self.inbox_table.setColumnCount(3)
        self.inbox_table.setHorizontalHeaderLabels(["종류", "파일명", "경로"])
        self.inbox_table.horizontalHeader().setStretchLastSection(True)
        self.inbox_table.setMaximumHeight(200)  # 상단 영역 크기 제한
        inbox_layout.addWidget(self.inbox_table)
        
        inbox_group.setLayout(inbox_layout)
        left_layout.addWidget(inbox_group)
        
        # 하단: 완료된 작업들
        completed_group = QGroupBox("✅ 완료된 작업")
        completed_layout = QVBoxLayout()
        
        # 완료 작업 정보 표시
        completed_info_layout = QHBoxLayout()
        self.completed_count_label = QLabel("로딩 중...")
        completed_info_layout.addWidget(self.completed_count_label)
        completed_info_layout.addStretch()
        completed_layout.addLayout(completed_info_layout)
        
        # 상태 필터 (완료 작업용) - 별도 라인으로 분리
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("상태 필터:"))
        self.completed_status_filter = QComboBox()
        self.completed_status_filter.addItems(["전체", "processing", "reprocessing", "done", "partial", "failed", "오류"])
        self.completed_status_filter.currentTextChanged.connect(self.filter_completed_jobs)
        filter_layout.addWidget(self.completed_status_filter)
        filter_layout.addStretch()
        completed_layout.addLayout(filter_layout)
        
        # 완료 작업 테이블
        self.completed_table = QTableWidget()
        self.completed_table.setColumnCount(4)
        self.completed_table.setHorizontalHeaderLabels(["Job ID", "종류", "상태", "생성일"])
        self.completed_table.horizontalHeader().setStretchLastSection(True)
        self.completed_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.completed_table.itemSelectionChanged.connect(self.on_completed_job_selected)
        completed_layout.addWidget(self.completed_table)
        
        completed_group.setLayout(completed_layout)
        left_layout.addWidget(completed_group)
        
        self.left_widget.setLayout(left_layout)
    
    def _style_dialog_buttons(self, button_box):
        """다이얼로그 버튼에 스타일 적용"""
        # OK 버튼을 실행 버튼으로 변경
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText("🚀 일괄 생성 시작")
        ok_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CBF60, stop:1 #4CAF50);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #3d8b40);
            }
        """)
        
        # Cancel 버튼 스타일
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText("취소")
        cancel_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f44336, stop:1 #da190b);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f66356, stop:1 #f44336);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #da190b, stop:1 #c62828);
            }
        """)
    
    def _clear_left_widget(self):
        """왼쪽 위젯의 기존 내용을 안전하게 정리"""
        # 기존 위젯들 참조 제거
        if hasattr(self, 'job_table'):
            self.job_table = None
        if hasattr(self, 'status_filter'):
            self.status_filter = None
        if hasattr(self, 'inbox_table'):
            self.inbox_table = None
        if hasattr(self, 'completed_table'):
            self.completed_table = None
        if hasattr(self, 'completed_status_filter'):
            self.completed_status_filter = None
        
        # 기존 레이아웃 제거
        if self.left_widget.layout():
            layout = self.left_widget.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            QWidget().setLayout(layout)
    
    
    def refresh_dashboard_data(self):
        """대시보드 데이터 새로고침"""
        # inbox 파일 스캔
        pending_data = self.scan_inbox_files()
        self.update_inbox_table(pending_data)
        
        # 완료 작업 스캔
        completed_data = self.scan_completed_jobs()
        self.update_completed_jobs_table(completed_data)
    
    def scan_inbox_files(self):
        """inbox 폴더에서 대기 중인 파일들 스캔"""
        work_folder = config_manager.get_work_folder()
        if not work_folder:
            return {}
        
        inbox_dir = work_folder / "inbox"
        if not inbox_dir.exists():
            return {}
        
        from src.batch_processor import get_image_files
        
        pending_files = {}
        
        # 모든 하위 폴더 확인 (타입 제한 없음)
        for folder in inbox_dir.iterdir():
            if not folder.is_dir():
                continue
            
            folder_name = folder.name.lower()
            image_files = get_image_files(folder)
            if image_files:
                pending_files[folder_name] = image_files
        
        # 폴더 구조가 없으면 루트 레벨 파일 확인
        if not pending_files:
            root_files = get_image_files(inbox_dir)
            if root_files:
                pending_files["기타"] = root_files
        
        return pending_files
    
    def scan_completed_jobs(self):
        """완료된 작업들 스캔 (out/ 폴더의 모든 처리된 작업)"""
        work_folder = config_manager.get_work_folder()
        if not work_folder:
            return []
        
        out_dir = work_folder / "out"
        if not out_dir.exists():
            return []
        
        jobs = []
        for job_dir in out_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            meta_path = job_dir / "meta.json"
            if not meta_path.exists():
                continue
            
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        # 빈 파일인 경우
                        jobs.append({
                            "job_id": job_dir.name,
                            "type": "알 수 없음",
                            "status": "오류",
                            "created_at": "-",
                            "src_name": "빈 meta.json"
                        })
                        continue
                    meta = json.loads(content)
                
                # 모든 상태의 작업 포함 (done, partial, failed, processing)
                jobs.append({
                    "job_id": job_dir.name,
                    "type": meta.get("type", "-"),
                    "status": meta.get("status", "-"),
                    "created_at": meta.get("created_at", "-"),
                    "src_name": meta.get("src_name", "-")
                })
            except json.JSONDecodeError as e:
                # JSON 파싱 실패한 경우
                jobs.append({
                    "job_id": job_dir.name,
                    "type": "알 수 없음",
                    "status": "오류",
                    "created_at": "-",
                    "src_name": f"JSON 오류: {str(e)[:20]}..."
                })
            except Exception as e:
                # 기타 파싱 실패한 경우
                jobs.append({
                    "job_id": job_dir.name,
                    "type": "알 수 없음",
                    "status": "오류",
                    "created_at": "-",
                    "src_name": f"파일 오류: {str(e)[:20]}..."
                })
        
        # 생성일 기준 정렬 (최신순)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        return jobs
    
    def update_inbox_table(self, pending_data):
        """inbox 테이블 업데이트"""
        total_pending = sum(len(files) for files in pending_data.values())
        self.inbox_count_label.setText(f"대기 중인 파일: {total_pending}개")
        
        self.inbox_table.setRowCount(0)
        
        for jewelry_type, files in pending_data.items():
            for file_path in files:
                row = self.inbox_table.rowCount()
                self.inbox_table.insertRow(row)
                
                self.inbox_table.setItem(row, 0, QTableWidgetItem(jewelry_type))
                self.inbox_table.setItem(row, 1, QTableWidgetItem(file_path.name))
                self.inbox_table.setItem(row, 2, QTableWidgetItem(str(file_path)))
    
    def update_completed_jobs_table(self, completed_data):
        """완료 작업 테이블 업데이트"""
        self.completed_count_label.setText(f"완료된 작업: {len(completed_data)}개")
        
        self.completed_table.setRowCount(0)
        
        for job in completed_data:
            row = self.completed_table.rowCount()
            self.completed_table.insertRow(row)
            
            self.completed_table.setItem(row, 0, QTableWidgetItem(job["job_id"]))
            self.completed_table.setItem(row, 1, QTableWidgetItem(job["type"]))
            self.completed_table.setItem(row, 2, QTableWidgetItem(job["status"]))
            self.completed_table.setItem(row, 3, QTableWidgetItem(job["created_at"][:19]))
            
            # 상태에 따른 색상
            status_item = self.completed_table.item(row, 2)
            if job["status"] == "done":
                status_item.setBackground(Qt.green)
            elif job["status"] == "partial":
                status_item.setBackground(Qt.yellow)
            elif job["status"] == "failed":
                status_item.setBackground(Qt.red)
            elif job["status"] == "reprocessing":
                status_item.setBackground(Qt.cyan)  # 재처리 중은 하늘색
    
    def filter_completed_jobs(self, status: str):
        """완료 작업 상태별 필터링"""
        if not hasattr(self, 'completed_table'):
            return
        
        for row in range(self.completed_table.rowCount()):
            if status == "전체":
                self.completed_table.setRowHidden(row, False)
            else:
                job_status = self.completed_table.item(row, 2).text()
                self.completed_table.setRowHidden(row, job_status != status)
    
    def on_completed_job_selected(self):
        """완료 작업 선택 시 상세 정보 표시"""
        if not hasattr(self, 'completed_table'):
            return
        
        current_row = self.completed_table.currentRow()
        if current_row < 0:
            return
        
        job_id = self.completed_table.item(current_row, 0).text()
        self.detail_panel.load_job(job_id)
    
    def load_jobs(self):
        """Job 목록 로드 (일반 모드용)"""
        if not hasattr(self, 'job_table') or self.job_table is None:
            return
        
        out_dir = Path("out")
        if not out_dir.exists():
            return
        
        # 현재 선택된 job 저장
        current_selection = None
        try:
            if self.job_table.currentRow() >= 0:
                current_selection = self.job_table.item(self.job_table.currentRow(), 0).text()
        except (RuntimeError, AttributeError):
            # 위젯이 이미 삭제된 경우 무시
            pass
        
        try:
            self.job_table.setRowCount(0)
        except (RuntimeError, AttributeError):
            return
        jobs = []
        
        # 모든 job 디렉토리 확인
        for job_dir in out_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            meta_path = job_dir / "meta.json"
            if not meta_path.exists():
                continue
            
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        continue  # 빈 파일은 건너뛰기
                    meta = json.loads(content)
                
                jobs.append({
                    "job_id": job_dir.name,
                    "type": meta.get("type", "-"),
                    "status": meta.get("status", "-"),
                    "created_at": meta.get("created_at", "-"),
                    "src_name": meta.get("src_name", "-")
                })
            except (json.JSONDecodeError, Exception):
                continue  # 파싱 실패한 파일은 건너뛰기
        
        # 생성일 기준 정렬 (최신순)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 테이블에 추가
        try:
            for job in jobs:
                row = self.job_table.rowCount()
                self.job_table.insertRow(row)
                
                self.job_table.setItem(row, 0, QTableWidgetItem(job["job_id"]))
                self.job_table.setItem(row, 1, QTableWidgetItem(job["type"]))
                self.job_table.setItem(row, 2, QTableWidgetItem(job["status"]))
                self.job_table.setItem(row, 3, QTableWidgetItem(job["created_at"][:19]))
                self.job_table.setItem(row, 4, QTableWidgetItem(job["src_name"]))
                
                # 상태에 따른 색상
                status_item = self.job_table.item(row, 2)
                if job["status"] == "done":
                    status_item.setBackground(Qt.green)
                elif job["status"] == "partial":
                    status_item.setBackground(Qt.yellow)
                elif job["status"] == "failed":
                    status_item.setBackground(Qt.red)
                elif job["status"] == "reprocessing":
                    status_item.setBackground(Qt.cyan)  # 재처리 중은 하늘색
            
            # 이전 선택 복원
            if current_selection:
                for row in range(self.job_table.rowCount()):
                    if self.job_table.item(row, 0).text() == current_selection:
                        self.job_table.selectRow(row)
                        break
        except (RuntimeError, AttributeError):
            return
        
        self.statusBar().showMessage(f"{len(jobs)}개 작업 로드됨")
    
    def filter_jobs(self, status: str):
        """상태별 필터링 (일반 모드용)"""
        if not hasattr(self, 'job_table') or self.job_table is None:
            return
        
        try:
            for row in range(self.job_table.rowCount()):
                if status == "전체":
                    self.job_table.setRowHidden(row, False)
                else:
                    job_status = self.job_table.item(row, 2).text()
                    self.job_table.setRowHidden(row, job_status != status)
        except (RuntimeError, AttributeError):
            pass
    
    def on_job_selected(self):
        """Job 선택 시 상세 정보 표시 (일반 모드용)"""
        if not hasattr(self, 'job_table') or self.job_table is None:
            return
        
        try:
            current_row = self.job_table.currentRow()
            if current_row < 0:
                return
            
            job_id = self.job_table.item(current_row, 0).text()
            self.detail_panel.load_job(job_id)
        except (RuntimeError, AttributeError):
            pass
    
    def batch_generate(self):
        """일괄 생성 (폴더 구조 지원)"""
        # 작업 폴더 확인
        work_folder = config_manager.get_work_folder()
        if not work_folder:
            QMessageBox.warning(
                self, 
                "작업 폴더 미설정", 
                "먼저 설정에서 작업 폴더를 선택해주세요."
            )
            self.open_settings()
            return
        
        # inbox 폴더 기본 경로
        default_inbox = work_folder / "inbox"
        
        # inbox 폴더 선택
        inbox_dir = QFileDialog.getExistingDirectory(
            self, 
            "입력 폴더 선택", 
            str(default_inbox)
        )
        if not inbox_dir:
            return
        
        inbox_path = Path(inbox_dir)
        
        # 폴더 구조 확인
        files_by_type = process_inbox_folders(inbox_path)
        
        if files_by_type:
            # 폴더 구조 기반 처리
            total_files = sum(len(files) for files in files_by_type.values())
            
            # 확인 다이얼로그 (자동 정리 옵션 포함)
            dialog = QDialog(self)
            dialog.setWindowTitle("🚀 일괄 생성 - 폴더 기반 처리")
            dialog.setModal(True)
            dialog.resize(450, 350)
            
            layout = QVBoxLayout()
            
            # 안내 메시지
            label = QLabel("폴더 구조가 감지되었습니다.")
            label.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(label)
            
            # 타입별 요약
            type_summary = []
            for jewelry_type, files in files_by_type.items():
                type_summary.append(f"  • {jewelry_type}: {len(files)}개")
            
            summary_text = QLabel("\n".join(type_summary) + f"\n\n총 {total_files}개 파일을 처리합니다.")
            layout.addWidget(summary_text)
            
            # 동시 처리 설정
            layout.addWidget(QLabel(""))  # 간격
            workers_layout = QHBoxLayout()
            workers_layout.addWidget(QLabel("동시 처리 파일 수:"))
            workers_spin = QSpinBox()
            workers_spin.setRange(1, 8)
            workers_spin.setValue(2)
            workers_layout.addWidget(workers_spin)
            workers_layout.addWidget(QLabel("(2-3개 권장)"))
            workers_layout.addStretch()
            layout.addLayout(workers_layout)
            
            # 자동 정리 옵션
            layout.addWidget(QLabel(""))  # 간격
            auto_archive_check = QCheckBox("성공한 파일만 archive로 이동 (실패/부분 성공은 inbox에 유지)")
            auto_archive_check.setChecked(True)  # 기본적으로 체크
            layout.addWidget(auto_archive_check)
            
            # 버튼 (스타일 개선)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            self._style_dialog_buttons(button_box)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec() != QDialog.Accepted:
                return
            
            auto_archive = auto_archive_check.isChecked()
            max_workers = workers_spin.value()
            
            # 배치 처리 시작
            self.statusBar().showMessage(f"폴더 기반 배치 처리 시작... ({total_files}개 파일, {max_workers}개 동시 처리)")
            
            # 진행률 바 표시
            self.progress_bar.setMaximum(total_files)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            
            # 이전 배치 스레드 정리
            if self.batch_thread and self.batch_thread.isRunning():
                self.batch_thread.terminate()
                self.batch_thread.wait()
            
            # 배치 스레드 시작 (폴더 기반)
            self.batch_thread = BatchGenerationThread(
                inbox_dir=inbox_path,
                max_workers=max_workers,
                auto_archive=auto_archive
            )
            
        else:
            # 기존 방식: 단일 타입으로 처리
            from PySide6.QtWidgets import QInputDialog
            from src.batch_processor import get_image_files
            
            # 이미지 파일 찾기
            image_files = get_image_files(inbox_path)
            
            if not image_files:
                QMessageBox.information(self, "알림", "이미지 파일이 없습니다.")
                return
            
            # 단일 타입 처리 다이얼로그
            dialog = QDialog(self)
            dialog.setWindowTitle("🚀 일괄 생성 - 단일 타입 처리")
            dialog.setModal(True)
            dialog.resize(400, 300)
            
            layout = QVBoxLayout()
            
            # 안내 메시지
            label = QLabel("폴더 구조가 없어 단일 타입으로 처리합니다.")
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label)
            
            layout.addWidget(QLabel(f"{len(image_files)}개 이미지 파일이 발견되었습니다."))
            
            # 주얼리 타입 선택
            layout.addWidget(QLabel("주얼리 종류를 선택하세요:"))
            jewelry_combo = QComboBox()
            jewelry_types = ["ring", "necklace", "earring", "bracelet", "anklet", "other"]
            jewelry_combo.addItems(jewelry_types)
            layout.addWidget(jewelry_combo)
            
            # 동시 처리 설정
            layout.addWidget(QLabel(""))  # 간격
            single_workers_layout = QHBoxLayout()
            single_workers_layout.addWidget(QLabel("동시 처리 파일 수:"))
            single_workers_spin = QSpinBox()
            single_workers_spin.setRange(1, 8)
            single_workers_spin.setValue(2)
            single_workers_layout.addWidget(single_workers_spin)
            single_workers_layout.addWidget(QLabel("(2-3개 권장)"))
            single_workers_layout.addStretch()
            layout.addLayout(single_workers_layout)
            
            # 자동 정리 옵션
            layout.addWidget(QLabel(""))  # 간격
            auto_archive_check = QCheckBox("성공한 파일만 archive로 이동 (실패/부분 성공은 inbox에 유지)")
            auto_archive_check.setChecked(True)  # 기본적으로 체크
            layout.addWidget(auto_archive_check)
            
            # 버튼 (스타일 개선)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            self._style_dialog_buttons(button_box)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec() != QDialog.Accepted:
                return
            
            jewelry_type = jewelry_combo.currentText()
            auto_archive = auto_archive_check.isChecked()
            max_workers = single_workers_spin.value()
            
            # 배치 처리 시작
            self.statusBar().showMessage(f"단일 타입 배치 처리 시작... ({len(image_files)}개 파일, {max_workers}개 동시 처리)")
            
            # 진행률 바 표시
            self.progress_bar.setMaximum(len(image_files))
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            
            # 배치 스레드 시작 (기존 방식)
            self.batch_thread = BatchGenerationThread(
                files=image_files,
                jewelry_type=jewelry_type,
                max_workers=max_workers,
                auto_archive=auto_archive
            )
        
        # 이전 배치 스레드 정리
        if self.batch_thread and self.batch_thread.isRunning():
            self.batch_thread.terminate()
            self.batch_thread.wait()
        
        # 신호 연결 (타입 정보 포함)
        self.batch_thread.progress.connect(self.on_batch_progress)
        self.batch_thread.file_completed.connect(self.on_file_completed)
        self.batch_thread.batch_finished.connect(self.on_batch_finished)
        self.batch_thread.error.connect(self.on_generation_error)
        
        self.batch_thread.start()
    
    def regenerate_artifact(self, job_id: str, artifact_type: str):
        """산출물 재생성 - 병렬처리 지원"""
        reply = QMessageBox.question(self, "재생성 확인", 
                                   f"{artifact_type} 산출물을 재생성하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 재생성 시작 전 상태를 reprocessing으로 변경
            self._update_job_status(job_id, "reprocessing")
            self.statusBar().showMessage(f"{artifact_type} 재생성 중...")
            
            # 병렬 재생성 스레드 시작
            self.start_regeneration_thread(job_id, artifact_type)
    
    def start_regeneration_thread(self, job_id: str, artifact_type: str):
        """재생성 스레드 시작 (제한된 병렬처리 + 대기열)"""
        # 재생성 관리 초기화
        if not hasattr(self, 'regeneration_threads'):
            self.regeneration_threads = []
        if not hasattr(self, 'regeneration_queue'):
            self.regeneration_queue = []
        
        # 완료된 스레드 정리
        self.regeneration_threads = [t for t in self.regeneration_threads if t.isRunning()]
        
        # 설정에서 최대 동시 실행 개수 가져오기
        config = config_manager.load_config()
        max_regeneration_workers = min(config.get("max_workers", 2), 4)  # 최대 4개로 제한
        
        # 현재 실행 중인 재생성 개수 확인
        running_count = len(self.regeneration_threads)
        
        if running_count < max_regeneration_workers:
            # 즉시 실행
            self._start_regeneration_now(job_id, artifact_type)
            print(f"🔄 재생성 시작: {job_id}/{artifact_type} (실행중: {running_count + 1}/{max_regeneration_workers})")
        else:
            # 대기열에 추가
            self.regeneration_queue.append((job_id, artifact_type))
            self.statusBar().showMessage(f"재생성 대기 중... (대기열: {len(self.regeneration_queue)}개)")
            print(f"⏳ 재생성 대기열 추가: {job_id}/{artifact_type} (대기: {len(self.regeneration_queue)}개)")
    
    def _start_regeneration_now(self, job_id: str, artifact_type: str):
        """재생성 즉시 시작"""
        regen_thread = GenerationThread(
            "regenerate_direct",
            job_id=job_id,
            artifact=artifact_type
        )
        
        # 재생성 완료 시 콜백 (대기열 처리 포함)
        regen_thread.finished.connect(lambda result: self._on_regeneration_completed(result, job_id, regen_thread))
        regen_thread.error.connect(lambda error: self._on_regeneration_error(error, job_id, regen_thread))
        
        self.regeneration_threads.append(regen_thread)
        regen_thread.start()
    
    def _on_regeneration_completed(self, result, job_id: str, thread):
        """재생성 완료 처리 + 대기열 실행"""
        # 기존 완료 처리
        self.on_regeneration_finished(result, job_id)
        
        # 스레드 제거
        if thread in self.regeneration_threads:
            self.regeneration_threads.remove(thread)
        
        # 대기열에서 다음 작업 실행
        self._process_regeneration_queue()
    
    def _on_regeneration_error(self, error: str, job_id: str, thread):
        """재생성 오류 처리 + 대기열 실행"""
        # 기존 오류 처리
        self.on_regeneration_error(error, job_id)
        
        # 스레드 제거
        if thread in self.regeneration_threads:
            self.regeneration_threads.remove(thread)
        
        # 대기열에서 다음 작업 실행
        self._process_regeneration_queue()
    
    def _process_regeneration_queue(self):
        """대기열에서 다음 재생성 작업 실행"""
        if hasattr(self, 'regeneration_queue') and self.regeneration_queue:
            job_id, artifact_type = self.regeneration_queue.pop(0)
            self._start_regeneration_now(job_id, artifact_type)
            
            remaining = len(self.regeneration_queue)
            if remaining > 0:
                self.statusBar().showMessage(f"대기열에서 재생성 시작... (남은 대기: {remaining}개)")
            else:
                self.statusBar().showMessage("재생성 진행 중...")
            
            print(f"📤 대기열에서 실행: {job_id}/{artifact_type} (남은 대기: {remaining}개)")
    
    def _update_job_status(self, job_id: str, status: str):
        """Job 상태 업데이트"""
        try:
            job_dir = Path("out") / job_id
            meta_path = job_dir / "meta.json"
            
            if meta_path.exists():
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            print(f"Empty meta.json file for status update: {meta_path}")
                            return
                        meta = json.loads(content)
                    
                    meta["status"] = status
                    meta["updated_at"] = datetime.now().isoformat()
                    
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Failed to update job status for {job_id}: {e}")
                    return
                
                # 대시보드 새로고침
                self.refresh_dashboard_data()
        except Exception as e:
            print(f"Failed to update job status: {e}")
    
    def export_job(self, job_id: str):
        """Job export"""
        # 대상 폴더 선택
        export_dir = QFileDialog.getExistingDirectory(self, "Export 대상 폴더", "export")
        if not export_dir:
            return
        
        try:
            # CLI export 함수 사용
            import subprocess
            result = subprocess.run([
                sys.executable, "gen.py", "export",
                "--job", job_id,
                "--to", export_dir
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(self, "성공", f"Export 완료: {export_dir}")
            else:
                QMessageBox.warning(self, "실패", f"Export 실패: {result.stderr}")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))
    
    def open_inbox_folder(self):
        """inbox 폴더 열기"""
        import subprocess
        import platform
        
        work_folder = config_manager.get_work_folder()
        if not work_folder:
            QMessageBox.warning(
                self, 
                "작업 폴더 미설정", 
                "먼저 설정에서 작업 폴더를 선택해주세요."
            )
            self.open_settings()
            return
        
        inbox_dir = work_folder / "inbox"
        if not inbox_dir.exists():
            QMessageBox.warning(
                self, 
                "폴더 없음", 
                "inbox 폴더가 존재하지 않습니다."
            )
            return
        
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", str(inbox_dir)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", str(inbox_dir)])
            else:  # Linux
                subprocess.Popen(["xdg-open", str(inbox_dir)])
        except Exception as e:
            QMessageBox.warning(self, "오류", f"폴더 열기 실패: {str(e)}")
    
    def open_output_folder(self):
        """출력 폴더 열기"""
        import subprocess
        import platform
        
        out_dir = Path("out").absolute()
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", str(out_dir)])
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", str(out_dir)])
        else:  # Linux
            subprocess.Popen(["xdg-open", str(out_dir)])
    
    def on_generation_finished(self, result: dict):
        """생성 완료"""
        if result.get("success") or result.get("status"):
            self.statusBar().showMessage("생성 완료!")
            self.load_jobs()
        else:
            QMessageBox.warning(self, "경고", "일부 생성 실패")
    
    def on_regeneration_finished(self, result: dict, job_id: str):
        """재생성 완료"""
        if result.get("success"):
            # 재생성 성공 시 상태를 done으로 복원
            self._update_job_status(job_id, "done")
            self.statusBar().showMessage("재생성 완료!")
            self.load_jobs()
            # 현재 선택된 job 다시 로드
            self.detail_panel.load_job(job_id)
        else:
            # 재생성 실패 시 상태를 failed로 변경
            self._update_job_status(job_id, "failed")
            QMessageBox.warning(self, "실패", f"재생성 실패: {result.get('error')}")
    
    def on_regeneration_error(self, error: str, job_id: str):
        """재생성 오류"""
        # 오류 발생 시 상태를 failed로 변경
        self._update_job_status(job_id, "failed")
        QMessageBox.critical(self, "오류", f"재생성 중 오류 발생: {error}")
        self.statusBar().showMessage("재생성 오류 발생")
    
    def on_batch_progress(self, current: int, total: int, current_file: str, jewelry_type: str = ""):
        """배치 진행률 업데이트 (타입 정보 포함)"""
        self.progress_bar.setValue(current)
        if jewelry_type:
            self.statusBar().showMessage(f"처리 중... ({current}/{total}) - {current_file} ({jewelry_type})")
        else:
            self.statusBar().showMessage(f"처리 중... ({current}/{total}) - {current_file}")
    
    def on_file_completed(self, file_name: str, result: dict, jewelry_type: str = ""):
        """개별 파일 처리 완료 (타입 정보 포함)"""
        if result.get("success", False) or result.get("status") == "done":
            if jewelry_type:
                logger.info(f"✅ Completed: {file_name} ({jewelry_type})")
            else:
                logger.info(f"✅ Completed: {file_name}")
        else:
            if jewelry_type:
                logger.warning(f"⚠️  Failed: {file_name} ({jewelry_type}) - {result.get('error', 'Unknown error')}")
            else:
                logger.warning(f"⚠️  Failed: {file_name} - {result.get('error', 'Unknown error')}")
        
        # Job 목록 새로고침 (새로운 Job이 추가되었을 수 있음)
        self.load_jobs()
    
    def on_batch_finished(self, stats: dict):
        """배치 처리 완료"""
        self.progress_bar.setVisible(False)
        
        total = stats.get("total", 0)
        success = stats.get("success", 0)
        failed = stats.get("failed", 0)
        duration = stats.get("end_time", datetime.now()) - stats.get("start_time", datetime.now())
        
        # 결과 메시지
        message = f"배치 처리 완료! 성공: {success}/{total}, 실패: {failed}, 소요시간: {str(duration).split('.')[0]}"
        self.statusBar().showMessage(message)
        
        # 결과 다이얼로그
        result_text = f"""배치 처리 결과:

총 파일: {total}개
성공: {success}개  
실패: {failed}개
성공률: {(success/total*100):.1f}%
소요시간: {str(duration).split('.')[0]}

{'✅ 모든 파일이 성공적으로 처리되었습니다!' if failed == 0 else '⚠️  일부 파일 처리에 실패했습니다.'}"""
        
        if failed == 0:
            QMessageBox.information(self, "배치 처리 완료", result_text)
        else:
            QMessageBox.warning(self, "배치 처리 완료", result_text)
        
        # Job 목록 최종 새로고침
        self.load_jobs()
    
    def on_generation_error(self, error: str):
        """생성 오류"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "오류", f"생성 중 오류 발생: {error}")
        self.statusBar().showMessage("오류 발생")
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 스레드 정리"""
        # 실행 중인 스레드들 정리
        if hasattr(self, 'current_thread') and self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()
            self.current_thread.wait(3000)  # 3초 대기
        
        if hasattr(self, 'batch_thread') and self.batch_thread and self.batch_thread.isRunning():
            self.batch_thread.terminate()
            self.batch_thread.wait(3000)  # 3초 대기
        
        # 재생성 스레드들 정리
        if hasattr(self, 'regeneration_threads'):
            for thread in self.regeneration_threads:
                if thread.isRunning():
                    thread.terminate()
                    thread.wait(1000)  # 1초 대기
        
        # 재생성 대기열 정리
        if hasattr(self, 'regeneration_queue'):
            self.regeneration_queue.clear()
        
        # 타이머 정리
        if hasattr(self, 'refresh_timer') and self.refresh_timer:
            self.refresh_timer.stop()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 모던한 스타일 적용
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()