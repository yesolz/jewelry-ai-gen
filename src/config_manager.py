"""
설정 관리 모듈
사용자 설정 저장/로드 및 작업 폴더 관리
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
import shutil


class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self):
        # 설정 파일 경로 (사용자 홈 디렉토리의 .jewelryai 폴더)
        self.config_dir = Path.home() / ".jewelryai"
        self.config_file = self.config_dir / "config.json"
        self.prompts_file = self.config_dir / "prompts.json"
        self.default_prompts_file = Path(__file__).parent.parent / "default_prompts.json"
        self.default_config = {
            "work_folder": "",
            "last_opened": "",
            "auto_archive": True,
            "max_workers": 2,
            "window_geometry": {},
            "first_run": True,
            "openai_api_key": "",
            "model_text": "gpt-4o",
            "model_image": "gpt-image-1",
            "default_out_root": "out"
        }
        self._ensure_config_dir()
        self._ensure_prompts_config()
    
    def _ensure_config_dir(self):
        """설정 디렉토리 생성"""
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self) -> Dict:
        """설정 파일 로드"""
        if not self.config_file.exists():
            return self.default_config.copy()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 기본값과 병합
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
        except (json.JSONDecodeError, Exception) as e:
            print(f"설정 파일 로드 실패: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 저장 실패: {e}")
    
    def get_work_folder(self) -> Optional[Path]:
        """작업 폴더 경로 반환"""
        config = self.load_config()
        work_folder = config.get("work_folder", "")
        if work_folder and Path(work_folder).exists():
            return Path(work_folder)
        return None
    
    def set_work_folder(self, folder_path: str):
        """작업 폴더 경로 설정"""
        config = self.load_config()
        config["work_folder"] = str(folder_path)
        config["first_run"] = False
        self.save_config(config)
    
    def is_first_run(self) -> bool:
        """첫 실행 여부 확인"""
        config = self.load_config()
        return config.get("first_run", True)
    
    def create_work_folders(self, base_path: Path):
        """작업에 필요한 폴더들 생성"""
        folders = [
            "inbox",
            "inbox/ring",
            "inbox/necklace", 
            "inbox/earring",
            "inbox/bracelet",
            "inbox/anklet",
            "inbox/other",
            "out",
            "export", 
            "logs",
            "work",
            "archive",
            "archive/success",
            "archive/failed",
            "samples",
            "presets"
        ]
        
        created_folders = []
        for folder in folders:
            folder_path = base_path / folder
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                created_folders.append(folder)
        
        return created_folders
    
    def get_folder_paths(self) -> Dict[str, Path]:
        """각 폴더 경로들 반환"""
        work_folder = self.get_work_folder()
        if not work_folder:
            return {}
        
        return {
            "work": work_folder,
            "inbox": work_folder / "inbox",
            "out": work_folder / "out", 
            "export": work_folder / "export",
            "logs": work_folder / "logs",
            "archive": work_folder / "archive",
            "samples": work_folder / "samples",
            "presets": work_folder / "presets"
        }
    
    def update_setting(self, key: str, value):
        """특정 설정 업데이트"""
        config = self.load_config()
        config[key] = value
        self.save_config(config)
    
    def get_openai_api_key(self) -> str:
        """OpenAI API 키 반환"""
        config = self.load_config()
        api_key = config.get("openai_api_key", "")
        
        # 설정에 없으면 환경변수에서 확인
        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY", "")
        
        # .env 파일에서도 확인
        if not api_key:
            api_key = self._load_env_file()
        
        return api_key
    
    def set_openai_api_key(self, api_key: str):
        """OpenAI API 키 설정"""
        config = self.load_config()
        config["openai_api_key"] = api_key
        self.save_config(config)
        
        # 환경변수에도 설정 (현재 세션용)
        import os
        os.environ["OPENAI_API_KEY"] = api_key
    
    def _load_env_file(self) -> str:
        """작업 폴더의 .env 파일에서 API 키 로드"""
        work_folder = self.get_work_folder()
        if not work_folder:
            return ""
        
        env_file = work_folder / ".env"
        if not env_file.exists():
            return ""
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception as e:
            print(f".env 파일 읽기 실패: {e}")
        
        return ""
    
    def _load_all_env_vars(self) -> dict:
        """작업 폴더의 .env 파일에서 모든 환경변수 로드"""
        work_folder = self.get_work_folder()
        if not work_folder:
            return {}
        
        env_file = work_folder / ".env"
        if not env_file.exists():
            return {}
        
        env_vars = {}
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
        except Exception as e:
            print(f".env 파일 읽기 실패: {e}")
        
        return env_vars
    
    def get_model_settings(self) -> dict:
        """모델 설정들 반환"""
        config = self.load_config()
        env_vars = self._load_all_env_vars()
        
        return {
            "model_text": env_vars.get("MODEL_TEXT") or config.get("model_text", "gpt-4o"),
            "model_image": env_vars.get("MODEL_IMAGE") or config.get("model_image", "gpt-image-1"),
            "default_out_root": env_vars.get("DEFAULT_OUT_ROOT") or config.get("default_out_root", "out")
        }
    
    def set_model_settings(self, model_text: str, model_image: str, default_out_root: str):
        """모델 설정들 저장"""
        config = self.load_config()
        config["model_text"] = model_text
        config["model_image"] = model_image  
        config["default_out_root"] = default_out_root
        self.save_config(config)
    
    def apply_environment_variables(self):
        """모든 환경변수를 시스템에 적용"""
        import os
        
        # API 키 설정
        api_key = self.get_openai_api_key()
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # 모델 설정들 적용
        model_settings = self.get_model_settings()
        os.environ["MODEL_TEXT"] = model_settings["model_text"]
        os.environ["MODEL_IMAGE"] = model_settings["model_image"]
        os.environ["DEFAULT_OUT_ROOT"] = model_settings["default_out_root"]
    
    def has_valid_api_key(self) -> bool:
        """유효한 API 키가 있는지 확인"""
        api_key = self.get_openai_api_key()
        return bool(api_key and api_key.startswith("sk-"))
    
    def _ensure_prompts_config(self):
        """프롬프트 설정 파일 초기화"""
        if not self.prompts_file.exists() and self.default_prompts_file.exists():
            # 기본 프롬프트 파일을 사용자 설정으로 복사
            shutil.copy2(self.default_prompts_file, self.prompts_file)
    
    def load_prompts_config(self) -> Dict:
        """프롬프트 설정 로드"""
        if not self.prompts_file.exists():
            # 기본 프롬프트 파일이 있으면 로드
            if self.default_prompts_file.exists():
                with open(self.default_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 없으면 빈 설정 반환
                return {
                    "base_prompts": {},
                    "jewelry_specific": {}
                }
        
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"프롬프트 설정 파일 로드 실패: {e}")
            # 기본 프롬프트로 폴백
            if self.default_prompts_file.exists():
                with open(self.default_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "base_prompts": {},
                "jewelry_specific": {}
            }
    
    def save_prompts_config(self, prompts: Dict):
        """프롬프트 설정 저장"""
        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(prompts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"프롬프트 설정 파일 저장 실패: {e}")
    
    def get_combined_prompt(self, prompt_type: str, jewelry_type: str) -> str:
        """주얼리 타입에 맞게 조합된 프롬프트 반환"""
        prompts_config = self.load_prompts_config()
        
        # 기본 프롬프트 가져오기
        base_prompt = prompts_config.get("base_prompts", {}).get(prompt_type, "")
        
        # {JEWELRY_TYPE} 치환
        combined_prompt = base_prompt.replace("{JEWELRY_TYPE}", jewelry_type)
        
        # 주얼리 타입별 추가 프롬프트 확인
        jewelry_specific = prompts_config.get("jewelry_specific", {})
        if jewelry_type in jewelry_specific:
            type_prompts = jewelry_specific[jewelry_type]
            if prompt_type in type_prompts:
                combined_prompt += type_prompts[prompt_type]
        
        return combined_prompt
    
    def update_base_prompt(self, prompt_type: str, content: str):
        """기본 프롬프트 업데이트"""
        prompts_config = self.load_prompts_config()
        if "base_prompts" not in prompts_config:
            prompts_config["base_prompts"] = {}
        prompts_config["base_prompts"][prompt_type] = content
        self.save_prompts_config(prompts_config)
    
    def update_jewelry_specific_prompt(self, jewelry_type: str, prompt_type: str, content: str):
        """주얼리 타입별 추가 프롬프트 업데이트"""
        prompts_config = self.load_prompts_config()
        if "jewelry_specific" not in prompts_config:
            prompts_config["jewelry_specific"] = {}
        if jewelry_type not in prompts_config["jewelry_specific"]:
            prompts_config["jewelry_specific"][jewelry_type] = {}
        prompts_config["jewelry_specific"][jewelry_type][prompt_type] = content
        self.save_prompts_config(prompts_config)
    
    def get_jewelry_types_with_prompts(self) -> list:
        """추가 프롬프트가 설정된 주얼리 타입 목록"""
        prompts_config = self.load_prompts_config()
        return list(prompts_config.get("jewelry_specific", {}).keys())


# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()