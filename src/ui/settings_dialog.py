"""
설정 다이얼로그
작업 폴더 선택 및 기타 설정
"""
import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, 
    QCheckBox, QSpinBox, QGroupBox, QMessageBox,
    QDialogButtonBox, QTextEdit
)

from ..config_manager import config_manager


class SettingsDialog(QDialog):
    """설정 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 작업 폴더 설정
        work_folder_group = QGroupBox("작업 폴더 설정")
        work_folder_layout = QVBoxLayout()
        
        # 현재 작업 폴더
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("현재 작업 폴더:"))
        self.work_folder_line = QLineEdit()
        self.work_folder_line.setReadOnly(True)
        current_layout.addWidget(self.work_folder_line)
        
        # 폴더 선택 버튼
        self.browse_btn = QPushButton("폴더 선택...")
        self.browse_btn.clicked.connect(self.browse_work_folder)
        current_layout.addWidget(self.browse_btn)
        
        work_folder_layout.addLayout(current_layout)
        
        # 설명
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(100)
        info_text.setPlainText(
            "작업 폴더를 선택하면 다음 하위 폴더들이 자동으로 생성됩니다:\n"
            "• inbox/ - 입력 이미지 파일들 (ring/, necklace/, other/ 등)\n"
            "• out/ - 생성된 결과물들\n"
            "• export/ - 최종 출력물\n"
            "• logs/ - 로그 파일들"
        )
        work_folder_layout.addWidget(info_text)
        
        work_folder_group.setLayout(work_folder_layout)
        layout.addWidget(work_folder_group)
        
        # API 키 설정
        api_group = QGroupBox("API 키 설정")
        api_layout = QFormLayout()
        
        # OpenAI API 키
        api_key_layout = QHBoxLayout()
        self.api_key_line = QLineEdit()
        self.api_key_line.setEchoMode(QLineEdit.Password)
        self.api_key_line.setPlaceholderText("sk-...")
        api_key_layout.addWidget(self.api_key_line)
        
        # 표시/숨기기 버튼
        self.show_api_btn = QPushButton("표시")
        self.show_api_btn.setMaximumWidth(60)
        self.show_api_btn.clicked.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(self.show_api_btn)
        
        # 테스트 버튼
        self.test_api_btn = QPushButton("테스트")
        self.test_api_btn.setMaximumWidth(60)
        self.test_api_btn.clicked.connect(self.test_api_key)
        api_key_layout.addWidget(self.test_api_btn)
        
        api_layout.addRow("OpenAI API 키:", api_key_layout)
        
        # API 키 상태
        self.api_status_label = QLabel("API 키가 설정되지 않았습니다")
        self.api_status_label.setStyleSheet("color: orange;")
        api_layout.addRow("상태:", self.api_status_label)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 모델 설정
        model_group = QGroupBox("모델 설정")
        model_layout = QFormLayout()
        
        # 텍스트 생성 모델
        self.model_text_line = QLineEdit()
        self.model_text_line.setPlaceholderText("gpt-4o")
        model_layout.addRow("텍스트 모델:", self.model_text_line)
        
        # 이미지 생성 모델
        self.model_image_line = QLineEdit()
        self.model_image_line.setPlaceholderText("gpt-image-1")
        model_layout.addRow("이미지 모델:", self.model_image_line)
        
        # 출력 폴더
        self.default_out_line = QLineEdit()
        self.default_out_line.setPlaceholderText("out")
        model_layout.addRow("출력 폴더:", self.default_out_line)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 처리 설정
        processing_group = QGroupBox("처리 설정")
        processing_layout = QFormLayout()
        
        # 동시 처리 수
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 8)
        self.max_workers_spin.setValue(2)
        processing_layout.addRow("동시 처리 파일 수:", self.max_workers_spin)
        
        # 자동 정리
        self.auto_archive_check = QCheckBox("성공한 파일을 자동으로 archive로 이동")
        self.auto_archive_check.setChecked(True)
        processing_layout.addRow("자동 정리:", self.auto_archive_check)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        # 폴더 열기 버튼
        self.open_folder_btn = QPushButton("작업 폴더 열기")
        self.open_folder_btn.clicked.connect(self.open_work_folder)
        self.open_folder_btn.setEnabled(False)
        button_layout.addWidget(self.open_folder_btn)
        
        button_layout.addStretch()
        
        # 확인/취소 버튼
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_settings(self):
        """현재 설정 로드"""
        config = config_manager.load_config()
        
        # 작업 폴더
        work_folder = config.get("work_folder", "")
        self.work_folder_line.setText(work_folder)
        self.open_folder_btn.setEnabled(bool(work_folder and Path(work_folder).exists()))
        
        # API 키
        api_key = config_manager.get_openai_api_key()
        self.api_key_line.setText(api_key)
        self.update_api_status()
        
        # 모델 설정
        model_settings = config_manager.get_model_settings()
        self.model_text_line.setText(model_settings["model_text"])
        self.model_image_line.setText(model_settings["model_image"])
        self.default_out_line.setText(model_settings["default_out_root"])
        
        # 처리 설정
        self.max_workers_spin.setValue(config.get("max_workers", 2))
        self.auto_archive_check.setChecked(config.get("auto_archive", True))
    
    def browse_work_folder(self):
        """작업 폴더 선택"""
        current_folder = self.work_folder_line.text()
        if not current_folder:
            current_folder = str(Path.home() / "Documents")
        
        folder = QFileDialog.getExistingDirectory(
            self, 
            "작업 폴더 선택",
            current_folder
        )
        
        if folder:
            self.work_folder_line.setText(folder)
            self.open_folder_btn.setEnabled(True)
            
            # 필요한 하위 폴더들 생성
            try:
                created_folders = config_manager.create_work_folders(Path(folder))
                if created_folders:
                    QMessageBox.information(
                        self,
                        "폴더 생성 완료",
                        f"다음 폴더들이 생성되었습니다:\n" + "\n".join(f"• {folder}" for folder in created_folders)
                    )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "폴더 생성 실패", 
                    f"일부 폴더 생성에 실패했습니다:\n{str(e)}"
                )
    
    def open_work_folder(self):
        """작업 폴더 열기"""
        work_folder = self.work_folder_line.text()
        if work_folder and Path(work_folder).exists():
            import subprocess
            import platform
            
            try:
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["open", work_folder])
                elif system == "Windows":
                    subprocess.run(["explorer", work_folder])
                else:  # Linux
                    subprocess.run(["xdg-open", work_folder])
            except Exception as e:
                QMessageBox.warning(self, "오류", f"폴더 열기 실패: {str(e)}")
    
    def accept(self):
        """설정 저장"""
        work_folder = self.work_folder_line.text().strip()
        
        if not work_folder:
            QMessageBox.warning(self, "경고", "작업 폴더를 선택해주세요.")
            return
        
        if not Path(work_folder).exists():
            QMessageBox.warning(self, "경고", "선택한 폴더가 존재하지 않습니다.")
            return
        
        # API 키 저장
        api_key = self.api_key_line.text().strip()
        if api_key:
            config_manager.set_openai_api_key(api_key)
        
        # 모델 설정 저장
        config_manager.set_model_settings(
            self.model_text_line.text().strip() or "gpt-4o",
            self.model_image_line.text().strip() or "gpt-image-1",
            self.default_out_line.text().strip() or "out"
        )
        
        # 설정 저장
        config = config_manager.load_config()
        config["work_folder"] = work_folder
        config["max_workers"] = self.max_workers_spin.value()
        config["auto_archive"] = self.auto_archive_check.isChecked()
        config["first_run"] = False
        
        config_manager.save_config(config)
        
        super().accept()
    
    def toggle_api_key_visibility(self):
        """API 키 표시/숨기기"""
        if self.api_key_line.echoMode() == QLineEdit.Password:
            self.api_key_line.setEchoMode(QLineEdit.Normal)
            self.show_api_btn.setText("숨기기")
        else:
            self.api_key_line.setEchoMode(QLineEdit.Password)
            self.show_api_btn.setText("표시")
    
    def test_api_key(self):
        """API 키 테스트"""
        api_key = self.api_key_line.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "경고", "API 키를 입력해주세요.")
            return
        
        if not api_key.startswith("sk-"):
            QMessageBox.warning(self, "경고", "올바른 OpenAI API 키 형식이 아닙니다.\n(sk-로 시작해야 합니다)")
            return
        
        # 간단한 API 테스트
        try:
            import openai
            import os
            
            # 임시로 API 키 설정
            old_key = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = api_key
            
            # OpenAI 클라이언트 생성 및 간단한 요청
            client = openai.OpenAI(api_key=api_key)
            
            # 모델 목록 요청 (가장 간단한 테스트)
            models = client.models.list()
            
            # 원래 키 복원
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)
            
            QMessageBox.information(self, "테스트 성공", "✅ API 키가 정상적으로 작동합니다!")
            self.update_api_status()
            
        except Exception as e:
            # 원래 키 복원
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)
            
            QMessageBox.warning(
                self, 
                "테스트 실패", 
                f"❌ API 키 테스트에 실패했습니다:\n{str(e)}"
            )
    
    def update_api_status(self):
        """API 키 상태 업데이트"""
        api_key = self.api_key_line.text().strip()
        
        if not api_key:
            self.api_status_label.setText("API 키가 설정되지 않았습니다")
            self.api_status_label.setStyleSheet("color: orange;")
        elif not api_key.startswith("sk-"):
            self.api_status_label.setText("잘못된 API 키 형식")
            self.api_status_label.setStyleSheet("color: red;")
        else:
            self.api_status_label.setText("API 키가 설정되었습니다")
            self.api_status_label.setStyleSheet("color: green;")


class FirstRunDialog(QDialog):
    """첫 실행 시 설정 가이드"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JewelryAI 초기 설정")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 환영 메시지
        welcome_label = QLabel("🎉 JewelryAI에 오신 것을 환영합니다!")
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # 안내 텍스트
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "처음 사용하시는군요! 먼저 작업 폴더를 설정해주세요.\n\n"
            "작업 폴더에는 다음과 같은 하위 폴더들이 자동으로 생성됩니다:\n\n"
            "📁 inbox/\n"
            "   ├── ring/      (반지 이미지)\n"
            "   ├── necklace/  (목걸이 이미지)\n"
            "   ├── earring/   (귀걸이 이미지)\n"
            "   └── other/     (기타 주얼리)\n\n"
            "📁 out/           (생성된 결과물)\n"
            "📁 export/        (최종 출력물)\n"
            "📁 logs/          (로그 파일)\n\n"
            "권장 위치: Documents/JewelryAI/"
        )
        layout.addWidget(info_text)
        
        # 폴더 선택
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("작업 폴더:"))
        self.folder_line = QLineEdit()
        self.folder_line.setPlaceholderText("작업 폴더를 선택해주세요...")
        folder_layout.addWidget(self.folder_line)
        
        self.browse_btn = QPushButton("선택...")
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_btn)
        
        layout.addLayout(folder_layout)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.skip_btn = QPushButton("나중에 설정")
        self.skip_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.skip_btn)
        
        self.ok_btn = QPushButton("설정 완료")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def browse_folder(self):
        """폴더 선택"""
        default_path = str(Path.home() / "Documents" / "JewelryAI")
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "작업 폴더 선택", 
            str(Path.home() / "Documents")
        )
        
        if folder:
            self.folder_line.setText(folder)
            self.ok_btn.setEnabled(True)
    
    def accept(self):
        """설정 저장하고 완료"""
        folder = self.folder_line.text().strip()
        
        if not folder:
            QMessageBox.warning(self, "경고", "작업 폴더를 선택해주세요.")
            return
        
        # 폴더 생성
        try:
            folder_path = Path(folder)
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # 하위 폴더들 생성
            created_folders = config_manager.create_work_folders(folder_path)
            
            # 설정 저장
            config_manager.set_work_folder(folder)
            
            QMessageBox.information(
                self,
                "설정 완료",
                f"작업 폴더가 설정되었습니다!\n\n폴더: {folder}\n\n이제 inbox 폴더에 이미지를 넣고 일괄 생성을 실행해보세요."
            )
            
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "오류",
                f"폴더 생성 중 오류가 발생했습니다:\n{str(e)}"
            )