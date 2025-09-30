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
    QDialogButtonBox, QTextEdit, QTabWidget,
    QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QWidget
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
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 기본 설정 탭
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
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
        general_layout.addWidget(work_folder_group)
        
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
        general_layout.addWidget(api_group)
        
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
        general_layout.addWidget(model_group)
        
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
        general_layout.addWidget(processing_group)
        
        general_tab.setLayout(general_layout)
        tab_widget.addTab(general_tab, "일반 설정")
        
        # 프롬프트 설정 탭
        prompt_tab = self.create_prompt_tab()
        tab_widget.addTab(prompt_tab, "프롬프트 설정")
        
        layout.addWidget(tab_widget)
        
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
    
    def create_prompt_tab(self):
        """프롬프트 설정 탭 생성"""
        prompt_widget = QWidget()
        layout = QVBoxLayout()
        
        # 프롬프트 타입 선택
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("프롬프트 타입:"))
        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.addItems([
            "설명문 (desc)",
            "연출컷 (styled)",
            "착용컷 (wear)",
            "클로즈업 (wear_closeup)",
            "썸네일 (thumb)"
        ])
        self.prompt_type_combo.currentIndexChanged.connect(self.load_prompt)
        type_layout.addWidget(self.prompt_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # 기본 프롬프트 편집
        prompt_group = QGroupBox("기본 프롬프트")
        prompt_layout = QVBoxLayout()
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setMinimumHeight(200)
        prompt_layout.addWidget(self.prompt_edit)
        
        # 저장 버튼
        save_btn_layout = QHBoxLayout()
        save_btn_layout.addStretch()
        self.save_prompt_btn = QPushButton("프롬프트 저장")
        self.save_prompt_btn.clicked.connect(self.save_prompt)
        save_btn_layout.addWidget(self.save_prompt_btn)
        prompt_layout.addLayout(save_btn_layout)
        
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)
        
        # 주얼리별 추가 프롬프트
        jewelry_group = QGroupBox("주얼리 타입별 추가 프롬프트")
        jewelry_layout = QVBoxLayout()
        
        # 주얼리 타입 선택
        jewelry_type_layout = QHBoxLayout()
        jewelry_type_layout.addWidget(QLabel("주얼리 타입:"))
        self.jewelry_type_combo = QComboBox()
        self.jewelry_type_combo.addItems([
            "ring",
            "necklace",
            "earring",
            "bracelet",
            "anklet",
            "other"
        ])
        self.jewelry_type_combo.currentIndexChanged.connect(self.load_jewelry_prompts)
        jewelry_type_layout.addWidget(self.jewelry_type_combo)
        
        # 새 타입 추가
        self.new_type_line = QLineEdit()
        self.new_type_line.setPlaceholderText("새 타입 추가...")
        self.new_type_line.setMaximumWidth(150)
        jewelry_type_layout.addWidget(self.new_type_line)
        
        self.add_type_btn = QPushButton("추가")
        self.add_type_btn.clicked.connect(self.add_jewelry_type)
        jewelry_type_layout.addWidget(self.add_type_btn)
        
        jewelry_type_layout.addStretch()
        jewelry_layout.addLayout(jewelry_type_layout)
        
        # 추가 프롬프트 테이블
        self.jewelry_prompts_table = QTableWidget(5, 2)
        self.jewelry_prompts_table.setHorizontalHeaderLabels(["프롬프트 타입", "추가 내용"])
        self.jewelry_prompts_table.setVerticalHeaderLabels([
            "desc", "styled", "wear", "wear_closeup", "thumb"
        ])
        
        # 테이블 크기 및 표시 설정 개선
        self.jewelry_prompts_table.horizontalHeader().setStretchLastSection(True)
        self.jewelry_prompts_table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        
        # 행 높이를 적당히 늘려서 텍스트가 잘 보이도록 (너무 크지 않게)
        self.jewelry_prompts_table.verticalHeader().setDefaultSectionSize(60)
        
        # 첫 번째 열(프롬프트 타입) 너비 고정
        self.jewelry_prompts_table.setColumnWidth(0, 120)
        
        # 텍스트 줄바꿈 허용
        self.jewelry_prompts_table.setWordWrap(True)
        
        # 행 크기를 내용에 맞게 자동 조정
        self.jewelry_prompts_table.resizeRowsToContents()
        
        jewelry_layout.addWidget(self.jewelry_prompts_table)
        
        # 저장 버튼
        jewelry_save_layout = QHBoxLayout()
        jewelry_save_layout.addStretch()
        self.save_jewelry_prompts_btn = QPushButton("추가 프롬프트 저장")
        self.save_jewelry_prompts_btn.clicked.connect(self.save_jewelry_prompts)
        jewelry_save_layout.addWidget(self.save_jewelry_prompts_btn)
        jewelry_layout.addLayout(jewelry_save_layout)
        
        jewelry_group.setLayout(jewelry_layout)
        layout.addWidget(jewelry_group)
        
        prompt_widget.setLayout(layout)
        
        # 초기 로드
        self.load_prompt()
        self.load_jewelry_prompts()
        
        return prompt_widget
    
    def get_prompt_type_key(self):
        """현재 선택된 프롬프트 타입의 키 반환"""
        type_map = {
            0: "desc",
            1: "styled",
            2: "wear",
            3: "wear_closeup",
            4: "thumb"
        }
        return type_map.get(self.prompt_type_combo.currentIndex(), "desc")
    
    def load_prompt(self):
        """선택된 프롬프트 로드"""
        prompts_config = config_manager.load_prompts_config()
        prompt_type = self.get_prompt_type_key()
        
        base_prompts = prompts_config.get("base_prompts", {})
        content = base_prompts.get(prompt_type, "")
        
        self.prompt_edit.setPlainText(content)
    
    def save_prompt(self):
        """기본 프롬프트 저장"""
        prompt_type = self.get_prompt_type_key()
        content = self.prompt_edit.toPlainText()
        
        config_manager.update_base_prompt(prompt_type, content)
        
        QMessageBox.information(
            self,
            "저장 완료",
            f"{prompt_type} 프롬프트가 저장되었습니다."
        )
    
    def load_jewelry_prompts(self):
        """선택된 주얼리 타입의 추가 프롬프트 로드"""
        prompts_config = config_manager.load_prompts_config()
        jewelry_type = self.jewelry_type_combo.currentText()
        
        jewelry_specific = prompts_config.get("jewelry_specific", {})
        type_prompts = jewelry_specific.get(jewelry_type, {})
        
        # 테이블 초기화
        prompt_types = ["desc", "styled", "wear", "wear_closeup", "thumb"]
        for i, prompt_type in enumerate(prompt_types):
            # 타입명 표시 (읽기 전용)
            type_item = QTableWidgetItem(prompt_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self.jewelry_prompts_table.setItem(i, 0, type_item)
            
            # 추가 프롬프트
            content = type_prompts.get(prompt_type, "")
            content_item = QTableWidgetItem(content)
            # 텍스트 줄바꿈 지원 및 세로 정렬
            content_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.jewelry_prompts_table.setItem(i, 1, content_item)
        
        # 내용에 맞게 행 높이 자동 조정
        self.jewelry_prompts_table.resizeRowsToContents()
    
    def save_jewelry_prompts(self):
        """주얼리별 추가 프롬프트 저장"""
        jewelry_type = self.jewelry_type_combo.currentText()
        prompt_types = ["desc", "styled", "wear", "wear_closeup", "thumb"]
        
        for i, prompt_type in enumerate(prompt_types):
            item = self.jewelry_prompts_table.item(i, 1)
            if item and item.text().strip():
                config_manager.update_jewelry_specific_prompt(
                    jewelry_type,
                    prompt_type,
                    item.text().strip()
                )
        
        QMessageBox.information(
            self,
            "저장 완료",
            f"{jewelry_type} 타입의 추가 프롬프트가 저장되었습니다."
        )
    
    def add_jewelry_type(self):
        """새 주얼리 타입 추가"""
        new_type = self.new_type_line.text().strip().lower()
        
        if not new_type:
            return
        
        # 이미 있는지 확인
        for i in range(self.jewelry_type_combo.count()):
            if self.jewelry_type_combo.itemText(i) == new_type:
                QMessageBox.warning(
                    self,
                    "경고",
                    f"'{new_type}'은(는) 이미 존재합니다."
                )
                return
        
        # 추가
        self.jewelry_type_combo.addItem(new_type)
        self.jewelry_type_combo.setCurrentText(new_type)
        self.new_type_line.clear()
        
        # inbox 폴더 생성
        work_folder = config_manager.get_work_folder()
        if work_folder:
            new_folder = work_folder / "inbox" / new_type
            new_folder.mkdir(exist_ok=True)
            
            QMessageBox.information(
                self,
                "타입 추가 완료",
                f"'{new_type}' 타입이 추가되었습니다.\n"
                f"inbox/{new_type} 폴더가 생성되었습니다."
            )


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